import asyncio
import logging
from typing import Dict, List, Optional, Set

from citegraph.models.paper import Paper, PaperQuery
from citegraph.models.citation import CitationEdge
from citegraph.metadata.resolver import MetadataResolver
from citegraph.citations.retriever import CitationRetriever
from citegraph.providers.openalex import OpenAlexProvider
from citegraph.utils.ids import IdCanonicalizer

logger = logging.getLogger(__name__)


class CitationTraversal:
    """Breadth-first citation traversal.

    Neighbours are discovered a whole level at a time so their metadata can be
    fetched in batches instead of one request per paper. Identifiers coming back
    from different providers (OpenAlex W ids, Crossref DOIs, PMIDs) are collapsed
    onto a single canonical paper_id via an alias table, so the same work never
    appears as two nodes and no edge is left pointing at a missing node.
    """

    # Concurrent reference/citation lookups per level.
    MAX_CONCURRENT_EXPANSIONS = 5
    # Concurrent fallback resolutions (only for ids the batch endpoints missed).
    MAX_CONCURRENT_RESOLUTIONS = 8
    # Share of the paper budget reserved for forward citations when both
    # directions are active. Backward traversal keeps the rest, because
    # foundational-paper ranking depends on reaching far enough back.
    FORWARD_BUDGET_SHARE = 0.35

    def __init__(self, resolver: MetadataResolver, retriever: CitationRetriever):
        self.resolver = resolver
        self.retriever = retriever
        self.openalex = OpenAlexProvider()

        self.papers: Dict[str, Paper] = {}
        self.edges: List[CitationEdge] = []
        self.visited: Set[str] = set()
        self.warnings: List[str] = []

        # Any identifier we have ever seen -> canonical paper_id.
        self._aliases: Dict[str, str] = {}
        # source/target pairs already emitted, for O(1) edge dedup.
        self._edge_keys: Set[tuple] = set()
        # Ids we tried and failed to resolve, so we do not retry them each level.
        self._unresolvable: Set[str] = set()

    # ---------------------------------------------------------------- ids ---

    def _register(self, paper: Paper) -> None:
        """Store a paper and map every identifier it carries onto its paper_id."""
        self.papers[paper.paper_id] = paper
        self.visited.add(paper.paper_id)
        for raw in (paper.paper_id, paper.doi, paper.pmid, paper.pmcid, paper.openalex_id):
            if raw:
                self._aliases[IdCanonicalizer.canonicalize(raw)] = paper.paper_id

    def _alias(self, raw_id: str, paper_id: str) -> None:
        cid = IdCanonicalizer.canonicalize(raw_id)
        if cid:
            self._aliases[cid] = paper_id

    def _canonical(self, raw_id: str) -> Optional[str]:
        """Canonical paper_id for an identifier, or None if not yet resolved."""
        if not raw_id:
            return None
        return self._aliases.get(IdCanonicalizer.canonicalize(raw_id))

    # ---------------------------------------------------------- traversal ---

    async def traverse(self, seed_paper: Paper, backward_depth: int = 2,
                       forward_depth: int = 1, max_papers: int = 100):
        """Depth-limited traversal outward from the seed paper."""
        self._register(seed_paper)

        frontiers = {
            "backward": [seed_paper.paper_id] if backward_depth > 0 else [],
            "forward": [seed_paper.paper_id] if forward_depth > 0 else [],
        }
        depth_limits = {"backward": backward_depth, "forward": forward_depth}
        budgets = self._allocate_budget(backward_depth, forward_depth, max_papers)
        spent = {"backward": 0, "forward": 0}

        # Interleave the two directions level by level so a wide citation fan-out
        # cannot consume the whole paper budget before the references are walked.
        for depth in range(max(backward_depth, forward_depth)):
            for direction in ("backward", "forward"):
                if depth >= depth_limits[direction] or not frontiers[direction]:
                    frontiers[direction] = []
                    continue
                if len(self.papers) >= max_papers:
                    frontiers[direction] = []
                    continue

                other = "forward" if direction == "backward" else "backward"
                other_can_still_run = bool(frontiers[other]) and depth < depth_limits[other]
                if other_can_still_run:
                    allowance = budgets[direction] - spent[direction]
                else:
                    # Nothing left for the other direction to spend: release its
                    # reservation so a paper with no citing works still gets a
                    # full reference tree.
                    allowance = max_papers - len(self.papers)
                if allowance <= 0:
                    frontiers[direction] = []
                    continue

                # Cap this level at both the global budget and the direction share.
                limit = min(max_papers, len(self.papers) + allowance)
                before = len(self.papers)
                frontiers[direction] = await self._expand_level(
                    frontiers[direction], direction, limit
                )
                spent[direction] += len(self.papers) - before

        logger.info(
            "Traversal complete: %d papers, %d edges", len(self.papers), len(self.edges)
        )

    def _allocate_budget(self, backward_depth: int, forward_depth: int,
                         max_papers: int) -> Dict[str, int]:
        """Split the paper budget between the two traversal directions."""
        budget = max(max_papers - 1, 0)  # the seed already occupies one slot
        if backward_depth <= 0:
            return {"backward": 0, "forward": budget}
        if forward_depth <= 0:
            return {"backward": budget, "forward": 0}
        forward = int(budget * self.FORWARD_BUDGET_SHARE)
        return {"backward": budget - forward, "forward": forward}

    async def _expand_level(self, frontier: List[str], direction: str,
                            max_papers: int) -> List[str]:
        """Expand one BFS level; returns the paper ids forming the next level."""
        raw_edges = await self._fetch_edges(frontier, direction)
        if not raw_edges:
            return []

        # Identifiers of neighbours we have not resolved yet.
        pending: List[str] = []
        for edge in raw_edges:
            neighbour = edge.target_paper_id if direction == "backward" else edge.source_paper_id
            cid = IdCanonicalizer.canonicalize(neighbour)
            if not cid or cid in self._unresolvable:
                continue
            if self._canonical(cid) is None and cid not in pending:
                pending.append(cid)

        newly_added: List[str] = []
        if pending and len(self.papers) < max_papers:
            newly_added = await self._resolve_neighbours(pending, max_papers)

        self._commit_edges(raw_edges, direction)
        return newly_added

    async def _fetch_edges(self, frontier: List[str], direction: str) -> List[CitationEdge]:
        """Fetch references/citations for every paper in the frontier concurrently."""
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_EXPANSIONS)

        async def fetch(paper_id: str) -> List[CitationEdge]:
            async with semaphore:
                try:
                    if direction == "backward":
                        return await self.retriever.get_references(paper_id)
                    return await self.retriever.get_citations(paper_id)
                except Exception as e:
                    msg = f"Failed to fetch {direction} citations for {paper_id}: {e}"
                    logger.warning(msg)
                    self.warnings.append(msg)
                    return []

        results = await asyncio.gather(*(fetch(pid) for pid in frontier))
        return [edge for batch in results for edge in batch]

    async def _resolve_neighbours(self, pending: List[str], max_papers: int) -> List[str]:
        """Resolve metadata for pending identifiers, batching wherever possible."""
        work_ids = [i for i in pending if i.upper().startswith("W") and i[1:].isdigit()]
        dois = [i for i in pending if i.startswith("10.")]
        others = [i for i in pending if i not in work_ids and i not in dois]

        added: List[str] = []
        resolved: Set[str] = set()

        def absorb(raw_id: str, paper: Paper) -> None:
            """Register a resolved paper, or alias it onto one we already have."""
            resolved.add(raw_id)
            if paper.paper_id not in self.papers:
                if len(self.papers) >= max_papers:
                    return
                self._register(paper)
                added.append(paper.paper_id)
            self._alias(raw_id, paper.paper_id)

        def headroom(ids: List[str]) -> List[str]:
            # Over-request by one batch: some ids resolve onto papers we already
            # have, so a strict slice would under-fill the budget.
            return ids[: max(max_papers - len(self.papers), 0) + self.openalex.BATCH_SIZE]

        # Batch OpenAlex work ids (50 per request).
        if work_ids and len(self.papers) < max_papers:
            try:
                fetched = await self.openalex.get_works_batch(headroom(work_ids))
            except Exception as e:
                logger.warning("OpenAlex batch resolution failed: %s", e)
                fetched = {}
            for work_id, paper in fetched.items():
                absorb(IdCanonicalizer.canonicalize(work_id), paper)

        # Batch DOIs through OpenAlex as well.
        if dois and len(self.papers) < max_papers:
            try:
                fetched = await self.openalex.get_works_by_doi_batch(headroom(dois))
            except Exception as e:
                logger.warning("OpenAlex DOI batch resolution failed: %s", e)
                fetched = {}
            for doi, paper in fetched.items():
                absorb(IdCanonicalizer.canonicalize(doi), paper)

        # Anything the batch endpoints missed falls back to the full multi-provider
        # resolver, run concurrently and only while budget remains.
        leftovers = [i for i in (dois + others) if i not in resolved]
        if leftovers and len(self.papers) < max_papers:
            leftovers = leftovers[: max(max_papers - len(self.papers), 0)]
            semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_RESOLUTIONS)

            async def resolve_one(raw_id: str):
                query = self._build_query(raw_id)
                if query is None:
                    return raw_id, None
                async with semaphore:
                    try:
                        return raw_id, await self.resolver.resolve_full(query)
                    except Exception as e:
                        logger.debug("Failed to resolve metadata for %s: %s", raw_id, e)
                        return raw_id, None

            for raw_id, paper in await asyncio.gather(*(resolve_one(i) for i in leftovers)):
                if paper is not None:
                    absorb(raw_id, paper)

        # Remember what could not be resolved so later levels skip it.
        for raw_id in pending:
            if self._canonical(raw_id) is None:
                self._unresolvable.add(raw_id)

        return added

    @staticmethod
    def _build_query(raw_id: str) -> Optional[PaperQuery]:
        """Build a PaperQuery for an identifier, or None if it is not a valid one."""
        if raw_id.startswith("10."):
            query_type = "doi"
        elif raw_id.isdigit():
            query_type = "pmid"
        elif raw_id.upper().startswith("PMC"):
            query_type = "pmcid"
        else:
            # OpenAlex ids and anything else are handled by the batch path.
            return None
        try:
            return PaperQuery(query_type=query_type, value=raw_id)
        except Exception:
            return None

    def _commit_edges(self, raw_edges: List[CitationEdge], direction: str) -> None:
        """Rewrite edge endpoints to canonical ids and keep only resolved ones."""
        dropped = 0
        for edge in raw_edges:
            source = self._canonical(edge.source_paper_id)
            target = self._canonical(edge.target_paper_id)
            if not source or not target or source == target:
                dropped += 1
                continue

            key = (source, target)
            if key in self._edge_keys:
                continue
            self._edge_keys.add(key)

            edge.source_paper_id = source
            edge.target_paper_id = target
            edge.edge_id = f"{source}_cites_{target}"
            self.edges.append(edge)

        if dropped:
            logger.debug(
                "Dropped %d %s edges whose endpoint was outside the paper budget",
                dropped, direction,
            )
