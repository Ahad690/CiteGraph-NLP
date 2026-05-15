from typing import Dict, Any, List
from citegraph.models.paper import Paper
from citegraph.providers.base import ProviderResult
import logging

logger = logging.getLogger(__name__)

class MetadataMerger:
    def merge(self, provider_results: Dict[str, ProviderResult]) -> Paper:
        """
        Merge metadata from multiple providers using precedence rules.
        """
        # Collect all papers found
        papers = {name: res.paper for name, res in provider_results.items() if res.paper}
        
        if not papers:
            raise ValueError("No papers found to merge")

        # Select a primary ID (prefer DOI, then PMID, then any ID)
        all_dois = [p.doi for p in papers.values() if p.doi]
        all_pmids = [p.pmid for p in papers.values() if p.pmid]
        
        primary_doi = all_dois[0] if all_dois else None
        primary_pmid = all_pmids[0] if all_pmids else None
        
        # Paper ID should be consistent. We'll use DOI as ID if available.
        paper_id = primary_doi or primary_pmid or list(papers.values())[0].paper_id

        # Merge fields based on precedence
        # Precedence: Crossref > OpenAlex for DOI, Title, Authors, Year, Journal
        # Precedence: OpenAlex for Abstract (Crossref usually doesn't have it)
        
        def get_field(field_name: str, sources: List[str]):
            for source in sources:
                if source in papers:
                    val = getattr(papers[source], field_name)
                    if val:
                        return val, source
            return None, None

        title, title_src = get_field("title", ["crossref", "openalex"])
        year, year_src = get_field("year", ["crossref", "openalex"])
        authors, authors_src = get_field("authors", ["crossref", "openalex"])
        journal, journal_src = get_field("journal", ["crossref", "openalex"])
        abstract, abstract_src = get_field("abstract", ["openalex", "crossref"])
        
        # Combine provenance
        provenance = {}
        for name, p in papers.items():
            provenance[name] = p.provenance.get(name, {})

        # Combine source IDs
        source_ids = {}
        for p in papers.values():
            source_ids.update(p.source_ids)

        return Paper(
            paper_id=paper_id,
            doi=primary_doi,
            pmid=primary_pmid,
            pmcid=next((p.pmcid for p in papers.values() if p.pmcid), None),
            title=title or "Unknown Title",
            authors=authors or [],
            year=year,
            journal=journal,
            abstract=abstract,
            source_ids=source_ids,
            metadata_confidence=0.95 if len(papers) > 1 else 0.8,
            provenance=provenance
        )
