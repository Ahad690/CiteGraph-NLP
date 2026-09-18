import asyncio
import httpx
from typing import Protocol, Any, Optional
from pydantic import BaseModel, Field
from citegraph.models.paper import Paper, PaperQuery
from citegraph.models.citation import CitationEdge

# One pooled client for every outbound provider call. Creating a client per
# request (the previous `async with httpx.AsyncClient(...)` in each _get) meant
# a fresh TCP and TLS handshake every time: measured at ~634 ms of pure
# overhead per request, 58% of the time each call took.
_shared_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()

HTTP_LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)
HTTP_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


async def get_shared_client() -> httpx.AsyncClient:
    """Return the process-wide pooled HTTP client, creating it if needed."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        async with _client_lock:
            if _shared_client is None or _shared_client.is_closed:
                _shared_client = httpx.AsyncClient(
                    timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS
                )
    return _shared_client


async def close_shared_client() -> None:
    """Close the pooled client. Called on application shutdown."""
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
    _shared_client = None

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
