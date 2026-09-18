import httpx
import logging
from typing import Any
from datetime import datetime
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from citegraph.providers.base import MetadataProvider, ProviderResult, is_transient_error
from citegraph.models.paper import Paper, PaperQuery
from citegraph.models.citation import CitationEdge
from citegraph.utils.ids import IdCanonicalizer

logger = logging.getLogger(__name__)

class CrossrefProvider:
    name = "crossref"

    def __init__(self):
        self.base_url = "https://api.crossref.org"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        # Do not burn the backoff budget on a definitive 404.
        retry=retry_if_exception(is_transient_error),
        reraise=True,
    )
    async def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{self.base_url}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()

    async def resolve(self, query: PaperQuery) -> ProviderResult:
        try:
            if query.query_type == "doi":
                data = await self._get(f"/works/{query.value}", {})
                work_data = data.get("message", {})
            elif query.query_type == "title":
                results = await self._get("/works", {"query.title": query.value, "rows": 1})
                items = results.get("message", {}).get("items", [])
                if not items:
                    return ProviderResult(error="No results found for title")
                work_data = items[0]
            else:
                return ProviderResult(error=f"Unsupported query type for Crossref: {query.query_type}")

            paper = self._map_to_paper(work_data)
            return ProviderResult(paper=paper, raw_data=work_data)
        except Exception as e:
            logger.error(f"Crossref resolution failed: {e}")
            return ProviderResult(error=str(e))

    def _map_to_paper(self, data: dict[str, Any]) -> Paper:
        doi = data.get("DOI")
        
        authors = []
        for author in data.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            authors.append(f"{given} {family}".strip())

        title = data.get("title", ["Unknown Title"])[0]
        journal = data.get("container-title", [None])[0]
        
        # Parse year
        year = None
        issued = data.get("issued", {}).get("date-parts", [[]])[0]
        if issued:
            year = issued[0]

        return Paper(
            paper_id=doi if doi else "unknown",
            doi=doi,
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            source_ids={"crossref": doi} if doi else {},
            metadata_confidence=0.9,
            provenance={"crossref": {"retrieved_at": datetime.utcnow().isoformat()}}
        )

    async def get_references(self, paper_id: str) -> list[CitationEdge]:
        # Crossref references are often missing or require specialized permissions
        # but sometimes they are in the 'reference' field.
        try:
            data = await self._get(f"/works/{paper_id}", {})
            references = data.get("message", {}).get("reference", [])
            edges = []
            for ref in references:
                # Crossref returns DOIs in mixed case; canonicalize so a reference
                # also seen via OpenAlex collapses onto the same graph node.
                ref_doi = IdCanonicalizer.canonicalize(ref.get("DOI") or "")
                if ref_doi:
                    edges.append(CitationEdge(
                        edge_id=f"{paper_id}_cites_{ref_doi}",
                        source_paper_id=paper_id,
                        target_paper_id=ref_doi,
                        providers=["crossref"],
                        confidence=1.0,
                        retrieved_at=datetime.utcnow()
                    ))
            return edges
        except Exception as e:
            logger.error(f"Crossref references retrieval failed: {e}")
            return []

    async def get_citations(self, paper_id: str) -> list[CitationEdge]:
        # Crossref does not provide a direct 'cited-by' API in the same way OpenAlex does
        return []
