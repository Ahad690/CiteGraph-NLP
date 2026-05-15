from citegraph.models.paper import PaperQuery
from citegraph.utils.ids import IdCanonicalizer

class InputNormalizer:
    def normalize_query(self, query: PaperQuery) -> PaperQuery:
        """
        Normalize the value in a PaperQuery based on its type using IdCanonicalizer.
        """
        normalized_value = query.value
        
        if query.query_type in ["doi", "pmid", "pmcid"]:
            normalized_value = IdCanonicalizer.canonicalize(query.value)
        elif query.query_type == "title":
            normalized_value = query.value.strip()
            
        return PaperQuery(
            query_type=query.query_type,
            value=normalized_value,
            pdf_path=query.pdf_path
        )
