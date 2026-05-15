import re
from typing import Optional

class IdCanonicalizer:
    @staticmethod
    def canonicalize(paper_id: str) -> str:
        """
        Normalize scholarly identifiers into a consistent string format.
        Handles DOIs, PMIDs, PMCIDs, and OpenAlex IDs.
        """
        if not paper_id:
            return ""
            
        paper_id = paper_id.strip()
        
        # 1. DOI check (starts with 10. or contains doi.org)
        if "doi.org/" in paper_id:
            return paper_id.split("doi.org/")[-1].lower()
        if paper_id.startswith("10."):
            return paper_id.lower()
        if paper_id.startswith("doi:"):
            return paper_id[4:].lower()
            
        # 2. PMCID check (starts with PMC)
        if paper_id.upper().startswith("PMC"):
            return paper_id.upper()
            
        # 3. PMID check (starts with pmid: or is purely numeric)
        if paper_id.startswith("pmid:"):
            return paper_id[5:]
        if paper_id.isdigit():
            # Most short numeric strings are PMIDs, but we'll leave as is
            return paper_id
            
        # 4. OpenAlex check (starts with W)
        if paper_id.startswith("W") and paper_id[1:].isdigit():
            return paper_id
            
        # Fallback: remove common prefixes and lowercase if it looks like a DOI
        if "/" in paper_id and paper_id[0].isdigit():
            return paper_id.lower()
            
        return paper_id

    @staticmethod
    def to_openalex_id(paper_id: str) -> str:
        """Format an ID specifically for OpenAlex API calls."""
        cid = IdCanonicalizer.canonicalize(paper_id)
        if cid.startswith("W"):
            return cid
        if cid.startswith("PMC"):
            return f"pmcid:{cid}"
        if cid.isdigit():
            return f"pmid:{cid}"
        if cid.startswith("10."):
            return f"doi:{cid}"
        return cid
