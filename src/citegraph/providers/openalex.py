import httpx
import logging
from typing import Any, Optional
from datetime import datetime
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from citegraph.providers.base import (
    MetadataProvider,
    ProviderResult,
    _best_title_match,
    get_shared_client,
    is_transient_error,
)
from citegraph.models.paper import Paper, PaperQuery
from citegraph.models.citation import CitationEdge
from citegraph.config import settings
from citegraph.utils.ids import IdCanonicalizer

logger = logging.getLogger(__name__)

class OpenAlexProvider:
    name = "openalex"

    # OpenAlex allows up to 50 ids per OR-filter and 50 results per page.
    BATCH_SIZE = 50
    MAX_FORWARD_CITATIONS = 200
    # Candidates pulled before re-ranking a title search by title similarity.
    TITLE_SEARCH_CANDIDATES = 25
    WORK_FIELDS = (
        "id,doi,ids,display_name,authorships,publication_year,"
        "primary_location,abstract_inverted_index"
    )

    def __init__(self):
        self.base_url = "https://api.openalex.org"
        self.email = settings.openalex_email
        self.headers = {"User-Agent": f"CiteGraph-NLP/0.1.0 (mailto:{self.email})"} if self.email else {}
        self._work_id_cache: dict[str, str] = {}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        # Do not burn the backoff budget on a definitive 404.
        retry=retry_if_exception(is_transient_error),
        reraise=True,
    )
    async def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        client = await get_shared_client()
        response = await client.get(
            f"{self.base_url}{endpoint}", params=params, headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    async def resolve(self, query: PaperQuery) -> ProviderResult:
        try:
            if query.query_type == "title":
                return await self._resolve_by_title(query.value)

            oa_id = IdCanonicalizer.to_openalex_id(query.value)
            if not oa_id:
                return ProviderResult(
                    error=f"Not an identifier OpenAlex can look up: {query.value}"
                )
            data = await self._get(f"/works/{oa_id}", {})
            paper = self._map_to_paper(data)
            return ProviderResult(paper=paper, raw_data=data)
        except Exception as e:
            logger.error(f"OpenAlex resolution failed: {e}")
            return ProviderResult(error=str(e))

    async def _resolve_by_title(self, title: str) -> ProviderResult:
        """Search by title and return the best-matching work.

        OpenAlex ranks by its own relevance score, which for a famous title
        puts near-duplicate and mirror records alongside the real one. The
        first hit is therefore not taken on trust: candidates are re-ranked by
        how closely their title matches what was asked for, and citation count
        breaks ties among equally good matches.
        """
        page = await self._get("/works", {
            "search": title,
            "per-page": self.TITLE_SEARCH_CANDIDATES,
            "select": "id,doi,display_name,title,publication_year,cited_by_count,"
                      "authorships,primary_location,abstract_inverted_index,ids",
        })
        results = (page or {}).get("results") or []
        if not results:
            return ProviderResult(error="No OpenAlex results for that title")

        best, score = _best_title_match(
            title, results, lambda w: w.get("display_name") or w.get("title")
        )
        if best is None:
            return ProviderResult(error="No OpenAlex result resembled that title")

        paper = self._map_to_paper(best)
        return ProviderResult(paper=paper, raw_data=best,
                              match_score=score, candidates_considered=len(results))

    @staticmethod
    def openalex_id_of(data: dict[str, Any]) -> str:
        """Short OpenAlex work id (W...) for a raw API record."""
        return IdCanonicalizer.canonicalize(data.get("id", "").split("/")[-1])

    @staticmethod
    def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
        """Fetch a nested object, treating an explicit null as an empty object.

        OpenAlex returns ``"primary_location": {"source": null}`` for works with
        no indexed venue (roughly half the results in some queries), and
        ``dict.get(key, {})`` returns None in that case because the key exists.
        """
        value = data.get(key)
        return value if isinstance(value, dict) else {}

    def _map_to_paper(self, data: dict[str, Any]) -> Paper:
        # Extract basic info
        openalex_id = self.openalex_id_of(data)
        doi = IdCanonicalizer.canonicalize(data.get("doi"))
        ids = self._section(data, "ids")
        pmid = IdCanonicalizer.canonicalize(ids.get("pmid"))
        pmcid = IdCanonicalizer.canonicalize(ids.get("pmcid"))

        # Prefer the DOI as the canonical paper_id so that the same work resolved
        # via OpenAlex and via Crossref collapses onto a single graph node.
        paper_id = doi or pmid or openalex_id

        authors = [
            self._section(auth, "author").get("display_name")
            for auth in (data.get("authorships") or [])
            if isinstance(auth, dict)
        ]
        authors = [a for a in authors if a]

        journal = self._section(self._section(data, "primary_location"), "source").get(
            "display_name"
        )

        return Paper(
            paper_id=paper_id,
            doi=doi,
            pmid=pmid,
            pmcid=pmcid,
            openalex_id=openalex_id,
            title=data.get("display_name") or "Unknown Title",
            authors=authors,
            year=data.get("publication_year"),
            journal=journal,
            abstract=self._parse_abstract(data.get("abstract_inverted_index")),
            source_ids={"openalex": openalex_id},
            metadata_confidence=0.9,
            provenance={"openalex": {"retrieved_at": datetime.utcnow().isoformat()}}
        )

    def _parse_abstract(self, inverted_index: Optional[dict[str, list[int]]]) -> Optional[str]:
        if not inverted_index:
            return None
        
        # OpenAlex uses inverted index for abstract. Reconstruct it.
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        
        word_positions.sort()
        return " ".join([word for pos, word in word_positions])

    async def _to_work_id(self, paper_id: str) -> str:
        """Resolve any identifier to a real OpenAlex work id (W...).

        OpenAlex filters such as ``cites:`` only accept work ids; passing
        ``doi:10.x/y`` there returns an empty result set with HTTP 200 instead
        of an error, which silently produced zero forward citations.
        """
        cid = IdCanonicalizer.canonicalize(paper_id)
        if cid.upper().startswith("W") and cid[1:].isdigit():
            return cid.upper()
        if cid in self._work_id_cache:
            return self._work_id_cache[cid]

        oa_id = IdCanonicalizer.to_openalex_id(paper_id)
        if not oa_id:
            return ""
        data = await self._get(f"/works/{oa_id}", {"select": "id"})
        work_id = self.openalex_id_of(data)
        self._work_id_cache[cid] = work_id
        return work_id

    async def get_works_batch(self, openalex_ids: list[str]) -> dict[str, Paper]:
        """Fetch metadata for many OpenAlex works at once.

        Returns a ``{W-id: Paper}`` mapping. OpenAlex accepts up to 50 ids per
        ``openalex_id`` filter, so this replaces N individual lookups with
        ceil(N/50) requests.
        """
        wanted = []
        for raw in openalex_ids:
            cid = IdCanonicalizer.canonicalize(raw)
            if cid.upper().startswith("W") and cid[1:].isdigit() and cid.upper() not in wanted:
                wanted.append(cid.upper())

        papers: dict[str, Paper] = {}
        for i in range(0, len(wanted), self.BATCH_SIZE):
            chunk = wanted[i:i + self.BATCH_SIZE]
            try:
                data = await self._get("/works", {
                    "filter": "openalex_id:" + "|".join(chunk),
                    "per-page": self.BATCH_SIZE,
                    "select": self.WORK_FIELDS,
                })
            except Exception as e:
                logger.error(f"OpenAlex batch fetch failed for {len(chunk)} ids: {e}")
                continue
            for work in data.get("results", []):
                work_id = self.openalex_id_of(work)
                if not work_id:
                    continue
                try:
                    papers[work_id] = self._map_to_paper(work)
                except Exception as e:
                    # Isolate per-record faults: one malformed work must not
                    # discard the other 49 in the batch.
                    logger.warning("Skipping unmappable OpenAlex work %s: %s", work_id, e)
        return papers

    async def get_works_by_doi_batch(self, dois: list[str]) -> dict[str, Paper]:
        """Fetch metadata for many DOIs at once. Returns a ``{doi: Paper}`` mapping."""
        wanted = []
        for raw in dois:
            cid = IdCanonicalizer.canonicalize(raw)
            if cid.startswith("10.") and cid not in wanted:
                wanted.append(cid)

        papers: dict[str, Paper] = {}
        for i in range(0, len(wanted), self.BATCH_SIZE):
            chunk = wanted[i:i + self.BATCH_SIZE]
            try:
                data = await self._get("/works", {
                    "filter": "doi:" + "|".join(chunk),
                    "per-page": self.BATCH_SIZE,
                    "select": self.WORK_FIELDS,
                })
            except Exception as e:
                logger.error(f"OpenAlex DOI batch fetch failed for {len(chunk)} dois: {e}")
                continue
            for work in data.get("results", []):
                doi = IdCanonicalizer.canonicalize(work.get("doi"))
                if not doi:
                    continue
                try:
                    papers[doi] = self._map_to_paper(work)
                except Exception as e:
                    logger.warning("Skipping unmappable OpenAlex work %s: %s", doi, e)
        return papers

    async def get_references(self, paper_id: str) -> list[CitationEdge]:
        try:
            oa_id = IdCanonicalizer.to_openalex_id(paper_id)
            data = await self._get(f"/works/{oa_id}", {"select": "id,referenced_works"})

            ref_ids = data.get("referenced_works", [])
            edges = []
            for ref_id in ref_ids:
                ref_id_short = ref_id.split("/")[-1]
                edges.append(CitationEdge(
                    edge_id=f"{paper_id}_cites_{ref_id_short}",
                    source_paper_id=paper_id,
                    target_paper_id=ref_id_short,
                    providers=["openalex"],
                    confidence=1.0,
                    retrieved_at=datetime.utcnow()
                ))
            return edges
        except Exception as e:
            logger.error(f"OpenAlex references retrieval failed: {e}")
            return []

    async def get_citations(self, paper_id: str, limit: int | None = None) -> list[CitationEdge]:
        try:
            work_id = await self._to_work_id(paper_id)
            if not work_id:
                logger.warning(f"Could not map {paper_id} to an OpenAlex work id; no forward citations")
                return []

            limit = limit or self.MAX_FORWARD_CITATIONS
            edges: list[CitationEdge] = []
            cursor = "*"
            while cursor and len(edges) < limit:
                page = await self._get("/works", {
                    "filter": f"cites:{work_id}",
                    "per-page": min(self.BATCH_SIZE, limit - len(edges)),
                    # Most-cited first: a highly cited paper has tens of thousands of
                    # citing works, so take the influential ones rather than an
                    # arbitrary page.
                    "sort": "cited_by_count:desc",
                    "cursor": cursor,
                    "select": "id",
                })
                results = page.get("results", [])
                if not results:
                    break
                for work in results:
                    citing_id = self.openalex_id_of(work)
                    if not citing_id:
                        continue
                    edges.append(CitationEdge(
                        edge_id=f"{citing_id}_cites_{paper_id}",
                        source_paper_id=citing_id,
                        target_paper_id=paper_id,
                        providers=["openalex"],
                        confidence=1.0,
                        retrieved_at=datetime.utcnow()
                    ))
                cursor = page.get("meta", {}).get("next_cursor")
            return edges
        except Exception as e:
            logger.error(f"OpenAlex citations retrieval failed: {e}")
            return []
