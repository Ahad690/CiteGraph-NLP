import asyncio
import re

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
    # Set only by a title search. How closely the returned title matched what
    # was asked for, and how many candidates that choice was made from, so a
    # weak match can be reported to the user rather than presented as a
    # lookup.
    match_score: Optional[float] = None
    candidates_considered: Optional[int] = None


def title_tokens(value: Optional[str]) -> set[str]:
    """Lowercased alphanumeric tokens, for comparing titles across providers."""
    if not value:
        return set()
    return set(re.sub(r"[^a-z0-9 ]", " ", value.lower()).split())


def title_similarity(a: Optional[str], b: Optional[str]) -> float:
    """Jaccard overlap of title tokens, 0.0 to 1.0.

    Token-level rather than character-level because provider titles differ by
    subtitle, casing and punctuation rather than by typos.
    """
    ta, tb = title_tokens(a), title_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# A title search below this similarity is reported as no match rather than
# returned. Jaccard on tokens, so "Attention Is All You Need" against
# "Channel Attention Is All You Need for Video" scores 0.55 and is rejected.
MIN_TITLE_MATCH = 0.6
# How many candidates to pull before re-ranking.
TITLE_SEARCH_CANDIDATES = 25


def _best_title_match(wanted: str, candidates: list, get_title,
                      cited_by=None, min_score: float = MIN_TITLE_MATCH):
    """Pick the candidate whose title best matches `wanted`.

    Returns (candidate, score), or (None, 0.0) when nothing clears min_score.
    A provider's own relevance ranking is not trusted on its own: searching a
    famous title returns a cluster of mirror and duplicate records, and the one
    the provider ranks first is not reliably the one the user meant.

    `cited_by` reads a citation count off a candidate and breaks ties among
    equally good title matches, preferring the record the literature actually
    points at. Providers name that field differently, so the caller supplies
    the accessor.
    """
    scored = []
    for candidate in candidates:
        score = title_similarity(wanted, get_title(candidate))
        if score >= min_score:
            cites = 0
            if cited_by is not None:
                try:
                    cites = int(cited_by(candidate) or 0)
                except (TypeError, ValueError):
                    cites = 0
            scored.append((round(score, 3), cites, score, candidate))
    if not scored:
        return None, 0.0
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    best = scored[0]
    return best[3], best[2]

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
