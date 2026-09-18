import httpx
from typing import Protocol, Any, Optional
from pydantic import BaseModel, Field
from citegraph.models.paper import Paper, PaperQuery
from citegraph.models.citation import CitationEdge

# Statuses worth trying again: rate limiting and server-side faults.
RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


def is_transient_error(exc: BaseException) -> bool:
    """True when a failed provider call is worth retrying.

    A 404 means the provider simply does not hold that record, which is routine
    for Crossref and Europe PMC. Retrying it cannot change the answer and costs
    the exponential-backoff budget on every miss, so only rate limits, server
    faults and transport errors are retried.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS_CODES
    return isinstance(exc, (httpx.TransportError, httpx.StreamError))

class ProviderResult(BaseModel):
    paper: Optional[Paper] = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
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
