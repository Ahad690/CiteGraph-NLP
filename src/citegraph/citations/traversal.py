import asyncio
import logging
from typing import List, Dict, Set
from citegraph.models.paper import Paper, PaperQuery
from citegraph.models.citation import CitationEdge
from citegraph.metadata.resolver import MetadataResolver
from citegraph.citations.retriever import CitationRetriever

logger = logging.getLogger(__name__)

class CitationTraversal:
    def __init__(self, resolver: MetadataResolver, retriever: CitationRetriever):
        self.resolver = resolver
        self.retriever = retriever
        self.papers: Dict[str, Paper] = {}
        self.edges: List[CitationEdge] = []
        self.visited: Set[str] = set()

    async def traverse(self, seed_paper: Paper, backward_depth: int = 2, forward_depth: int = 1, max_papers: int = 100):
        """Perform depth-limited traversal starting from seed paper."""
        self.papers[seed_paper.paper_id] = seed_paper
        
        # We use a queue for BFS-like traversal
        # (paper_id, current_depth, direction)
        queue = [(seed_paper.paper_id, 0, "backward")]
        if forward_depth > 0:
            queue.append((seed_paper.paper_id, 0, "forward"))
            
        self.visited.add(seed_paper.paper_id)

        while queue and len(self.papers) < max_papers:
            paper_id, depth, direction = queue.pop(0)
            
            if direction == "backward" and depth < backward_depth:
                new_edges = await self.retriever.get_references(paper_id)
                await self._process_edges(new_edges, depth, direction, queue, max_papers)
                
            elif direction == "forward" and depth < forward_depth:
                new_edges = await self.retriever.get_citations(paper_id)
                await self._process_edges(new_edges, depth, direction, queue, max_papers)

    async def _process_edges(self, new_edges: List[CitationEdge], depth: int, direction: str, queue: list, max_papers: int):
        for edge in new_edges:
            # Avoid duplicate edges
            edge_key = (edge.source_paper_id, edge.target_paper_id)
            if any((e.source_paper_id, e.target_paper_id) == edge_key for e in self.edges):
                continue
                
            self.edges.append(edge)
            
            # Determine the paper we need to fetch metadata for
            target_id = edge.target_paper_id if direction == "backward" else edge.source_paper_id
            
            if target_id not in self.visited and len(self.papers) < max_papers:
                self.visited.add(target_id)
                
                # Fetch metadata for the new paper
                try:
                    # Determine query type from ID format
                    if target_id.startswith("10."):
                        query_type = "doi"
                    elif target_id.isdigit():
                        query_type = "pmid"
                    else:
                        # Default to title or let resolver try to guess (OpenAlex ID)
                        query_type = "doi" # resolver will try to handle W... IDs via OpenAlex
                        
                    query = PaperQuery(query_type=query_type, value=target_id)
                    new_paper = await self.resolver.resolve_full(query)
                    self.papers[new_paper.paper_id] = new_paper
                    queue.append((new_paper.paper_id, depth + 1, direction))
                except Exception as e:
                    logger.warning(f"Failed to resolve metadata for {target_id}: {e}")
