import re
from citegraph.models.paper import PaperQuery

class InputNormalizer:
    @staticmethod
    def normalize_doi(doi: str) -> str:
        """
        Normalize DOI into a consistent internal format.
        Examples:
        - https://doi.org/10.xxxx/yyyy -> 10.xxxx/yyyy
        - doi:10.xxxx/yyyy -> 10.xxxx/yyyy
        """
        # Remove whitespace
        doi = doi.strip()
        
        # Remove URL prefixes
        doi = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', doi, flags=re.IGNORECASE)
        
        # Remove doi: prefix
        doi = re.sub(r'^doi:', '', doi, flags=re.IGNORECASE)
        
        # Remove any leading /
        doi = doi.lstrip('/')
        
        return doi.lower()

    @staticmethod
    def normalize_pmid(pmid: str) -> str:
        """
        Normalize PMID.
        Example: PMID: 12345678 -> 12345678
        """
        pmid = pmid.strip()
        pmid = re.sub(r'^pmid[:\s]*', '', pmid, flags=re.IGNORECASE)
        return pmid

    @staticmethod
    def normalize_pmcid(pmcid: str) -> str:
        """
        Normalize PMCID.
        Example: PMCID: PMC1234567 -> PMC1234567
        """
        pmcid = pmcid.strip()
        pmcid = re.sub(r'^pmcid[:\s]*', '', pmcid, flags=re.IGNORECASE)
        if not pmcid.upper().startswith('PMC'):
            pmcid = 'PMC' + pmcid
        return pmcid

    def normalize_query(self, query: PaperQuery) -> PaperQuery:
        """
        Normalize the value in a PaperQuery based on its type.
        """
        normalized_value = query.value
        
        if query.query_type == "doi":
            normalized_value = self.normalize_doi(query.value)
        elif query.query_type == "pmid":
            normalized_value = self.normalize_pmid(query.value)
        elif query.query_type == "pmcid":
            normalized_value = self.normalize_pmcid(query.value)
        elif query.query_type == "title":
            normalized_value = query.value.strip()
            
        return PaperQuery(
            query_type=query.query_type,
            value=normalized_value,
            pdf_path=query.pdf_path
        )
