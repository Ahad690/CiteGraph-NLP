import logging
from typing import Any
from citegraph.providers.base import MetadataProvider, ProviderResult
from citegraph.models.paper import Paper, PaperQuery
from citegraph.models.citation import CitationEdge
from citegraph.utils.ids import IdCanonicalizer

logger = logging.getLogger(__name__)

class EuropePMCProvider:
    name = "europe_pmc"

    async def resolve(self, query: PaperQuery) -> ProviderResult:
        # Placeholder for Europe PMC resolution
        cid = IdCanonicalizer.canonicalize(query.value)
        logger.info(f"Europe PMC placeholder resolving {cid}")
        return ProviderResult(error="Europe PMC provider not fully implemented")

    async def get_references(self, paper_id: str) -> list[CitationEdge]:
        return []

    async def get_citations(self, paper_id: str) -> list[CitationEdge]:
        return []
