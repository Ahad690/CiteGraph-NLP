import logging
from typing import List
from citegraph.models.citation import CitationEdge
from citegraph.providers.openalex import OpenAlexProvider
from citegraph.providers.crossref import CrossrefProvider
from citegraph.config import settings

logger = logging.getLogger(__name__)

class CitationRetriever:
    def __init__(self):
        self.providers = []
        if settings.enable_openalex:
            self.providers.append(OpenAlexProvider())
        if settings.enable_crossref:
            self.providers.append(CrossrefProvider())

    async def get_references(self, paper_id: str) -> List[CitationEdge]:
        """Retrieve references for a paper from all providers."""
        all_edges = []
        for provider in self.providers:
            edges = await provider.get_references(paper_id)
            all_edges.extend(edges)
        
        # Deduplicate edges by (source, target)
        unique_edges = {}
        for edge in all_edges:
            key = (edge.source_paper_id, edge.target_paper_id)
            if key not in unique_edges:
                unique_edges[key] = edge
            else:
                # Merge provider lists
                for p in edge.providers:
                    if p not in unique_edges[key].providers:
                        unique_edges[key].providers.append(p)
        
        return list(unique_edges.values())

    async def get_citations(self, paper_id: str) -> List[CitationEdge]:
        """Retrieve forward citations for a paper from all providers."""
        all_edges = []
        for provider in self.providers:
            edges = await provider.get_citations(paper_id)
            all_edges.extend(edges)
            
        # Deduplicate edges
        unique_edges = {}
        for edge in all_edges:
            key = (edge.source_paper_id, edge.target_paper_id)
            if key not in unique_edges:
                unique_edges[key] = edge
            else:
                for p in edge.providers:
                    if p not in unique_edges[key].providers:
                        unique_edges[key].providers.append(p)
                        
        return list(unique_edges.values())
