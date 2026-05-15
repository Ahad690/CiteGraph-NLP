from typing import Protocol, Any, Optional
from pydantic import BaseModel
from citegraph.models.paper import Paper, PaperQuery
from citegraph.models.citation import CitationEdge

class ProviderResult(BaseModel):
    paper: Optional[Paper] = None
    raw_data: dict[str, Any] = {}
    error: Optional[str] = None

class MetadataProvider(Protocol):
    name: str
    
    async def resolve(self, query: PaperQuery) -> ProviderResult:
        """Resolve metadata for a paper based on a query."""
        ...

    async def get_references(self, paper_id: str) -> list[CitationEdge]:
        """Retrieve backward references for a paper."""
        ...

    async def get_citations(self, paper_id: str) -> list[CitationEdge]:
        """Retrieve forward citations for a paper."""
        ...
