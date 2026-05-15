import httpx
import logging
from typing import Any, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from citegraph.providers.base import MetadataProvider, ProviderResult
from citegraph.models.paper import Paper, PaperQuery
from citegraph.models.citation import CitationEdge
from citegraph.config import settings
from citegraph.utils.ids import IdCanonicalizer

logger = logging.getLogger(__name__)

class OpenAlexProvider:
    name = "openalex"

    def __init__(self):
        self.base_url = "https://api.openalex.org"
        self.email = settings.openalex_email
        self.headers = {"User-Agent": f"CiteGraph-NLP/0.1.0 (mailto:{self.email})"} if self.email else {}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(headers=self.headers, timeout=20.0) as client:
            response = await client.get(f"{self.base_url}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()

    async def resolve(self, query: PaperQuery) -> ProviderResult:
        try:
            oa_id = IdCanonicalizer.to_openalex_id(query.value)
            if oa_id:
                data = await self._get(f"/works/{oa_id}", {})
            else:
                return ProviderResult(error=f"Unsupported or malformed ID for OpenAlex: {query.value}")

            paper = self._map_to_paper(data)
            return ProviderResult(paper=paper, raw_data=data)
        except Exception as e:
            logger.error(f"OpenAlex resolution failed: {e}")
            return ProviderResult(error=str(e))

    def _map_to_paper(self, data: dict[str, Any]) -> Paper:
        # Extract basic info
        paper_id = IdCanonicalizer.canonicalize(data.get("id", "").split("/")[-1])
        doi = IdCanonicalizer.canonicalize(data.get("doi"))
        pmid = IdCanonicalizer.canonicalize(data.get("ids", {}).get("pmid"))
        pmcid = IdCanonicalizer.canonicalize(data.get("ids", {}).get("pmcid"))

        authors = [auth.get("author", {}).get("display_name") for auth in data.get("authorships", [])]
        authors = [a for a in authors if a]

        return Paper(
            paper_id=paper_id,
            doi=doi,
            pmid=pmid,
            pmcid=data.get("ids", {}).get("pmcid"),
            openalex_id=paper_id,
            title=data.get("display_name", "Unknown Title"),
            authors=authors,
            year=data.get("publication_year"),
            journal=data.get("primary_location", {}).get("source", {}).get("display_name"),
            abstract=self._parse_abstract(data.get("abstract_inverted_index")),
            source_ids={"openalex": paper_id},
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

    async def get_references(self, paper_id: str) -> list[CitationEdge]:
    async def get_references(self, paper_id: str) -> list[CitationEdge]:
        try:
            oa_id = IdCanonicalizer.to_openalex_id(paper_id)
            data = await self._get(f"/works/{oa_id}", {})

            data = await self._get(f"/works/{oa_id}", {})
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

    async def get_citations(self, paper_id: str) -> list[CitationEdge]:
    async def get_citations(self, paper_id: str) -> list[CitationEdge]:
        try:
            oa_id = IdCanonicalizer.to_openalex_id(paper_id)

            # Query works that cite this work
            data = await self._get("/works", {"filter": f"cites:{oa_id}", "per_page": 50})
            edges = []
            for work in data.get("results", []):
                work_id = work.get("id", "").split("/")[-1]
                edges.append(CitationEdge(
                    edge_id=f"{work_id}_cites_{paper_id}",
                    source_paper_id=work_id,
                    target_paper_id=paper_id,
                    providers=["openalex"],
                    confidence=1.0,
                    retrieved_at=datetime.utcnow()
                ))
            return edges
        except Exception as e:
            logger.error(f"OpenAlex citations retrieval failed: {e}")
            return []
