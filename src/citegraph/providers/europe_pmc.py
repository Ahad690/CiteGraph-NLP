import httpx
import logging
from typing import Any, Optional
from datetime import datetime
from citegraph.providers.base import MetadataProvider, ProviderResult
from citegraph.models.paper import Paper, PaperQuery
from citegraph.models.citation import CitationEdge
from citegraph.utils.ids import IdCanonicalizer

logger = logging.getLogger(__name__)

class EuropePMCProvider:
    name = "europe_pmc"

    def __init__(self):
        self.base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    async def resolve(self, query: PaperQuery) -> ProviderResult:
        try:
            cid = IdCanonicalizer.canonicalize(query.value)
            if not cid:
                return ProviderResult(error="Invalid or empty ID")

            # Format query for Europe PMC
            search_query = None
            if query.query_type == "doi":
                search_query = f'DOI:"{cid}"'
            elif query.query_type == "pmid":
                search_query = f'EXT_ID:{cid}'
            elif query.query_type == "title":
                search_query = f'TITLE:"{cid}"'
            
            if not search_query:
                return ProviderResult(error=f"Unsupported Europe PMC query type: {query.query_type}")
                
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/search", 
                    params={"query": search_query, "format": "json", "resultType": "core"}
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get("resultList", {}).get("result", [])
                if not results:
                    return ProviderResult(error=f"No results found in Europe PMC for {search_query}")
                
                paper_data = results[0]
                paper = self._map_to_paper(paper_data)
                return ProviderResult(paper=paper, raw_data=paper_data)
        except Exception as e:
            logger.error(f"Europe PMC resolution failed: {e}")
            return ProviderResult(error=str(e))

    def _map_to_paper(self, data: dict[str, Any]) -> Paper:
        paper_id = data.get("id", data.get("pmid", data.get("doi")))
        return Paper(
            paper_id=IdCanonicalizer.canonicalize(paper_id),
            doi=IdCanonicalizer.canonicalize(data.get("doi")),
            pmid=IdCanonicalizer.canonicalize(data.get("pmid")),
            pmcid=IdCanonicalizer.canonicalize(data.get("pmcid")),
            title=data.get("title", "Unknown Title"),
            authors=[a.get("fullName") for a in data.get("authorList", {}).get("author", []) if a.get("fullName")],
            year=int(data.get("pubYear")) if data.get("pubYear") else None,
            journal=data.get("journalInfo", {}).get("journal", {}).get("title"),
            abstract=data.get("abstractText"),
            source_ids={"europe_pmc": paper_id},
            metadata_confidence=0.85,
            provenance={"europe_pmc": {"retrieved_at": datetime.utcnow().isoformat()}}
        )

    async def get_references(self, paper_id: str) -> list[CitationEdge]:
        return []

    async def get_citations(self, paper_id: str) -> list[CitationEdge]:
        return []
