import re
from typing import Optional

class IdCanonicalizer:
    # Path segments publishers append after the DOI in an article URL
    # (frontiersin.org/.../10.3389/fcomp.2024.1387354/full).
    DOI_VIEW_SEGMENTS = frozenset({
        "abs", "abstract", "citation", "citations", "download", "epub",
        "figure", "figures", "full", "full-text", "fulltext", "html", "meta",
        "pdf", "print", "references", "summary", "supplementary", "text",
    })

    @staticmethod
    def strip_doi_view_suffix(doi: str) -> str:
        """Drop trailing view segments a greedy DOI match swallowed from a URL.

        The DOI character class legitimately includes ``/``, so matching against
        a URL path runs straight past the end of the DOI into the publisher's
        view segment. A DOI always keeps its ``prefix/suffix`` core, so only
        segments beyond the first two are ever removed.
        """
        if not doi:
            return doi
        parts = doi.split("/")
        while len(parts) > 2 and parts[-1].lower() in IdCanonicalizer.DOI_VIEW_SEGMENTS:
            parts.pop()
        return "/".join(parts)

    @staticmethod
    def canonicalize(paper_id: str) -> str:
        """
        Normalize scholarly identifiers into a consistent string format.
        Handles DOIs, PMIDs, PMCIDs, and OpenAlex IDs.
        """
        if not paper_id:
            return ""
            
        paper_id = paper_id.strip()

        # 0. OpenAlex reports ids.pmid / ids.pmcid as full URLs
        #    (https://pubmed.ncbi.nlm.nih.gov/39893240), so reduce those to the
        #    bare identifier before the checks below.
        if "pubmed.ncbi.nlm.nih.gov/" in paper_id:
            paper_id = paper_id.split("pubmed.ncbi.nlm.nih.gov/")[-1].strip("/")
        elif "/pmc/articles/" in paper_id:
            paper_id = paper_id.split("/pmc/articles/")[-1].strip("/")

        # 1. DOI check (starts with 10. or contains doi.org)
        if "doi.org/" in paper_id:
            return paper_id.split("doi.org/")[-1].lower()
        if paper_id.startswith("10."):
            return paper_id.lower()
        if paper_id.lower().startswith("doi:"):
            return paper_id[4:].lower()
            
        # 2. PMCID check (starts with PMC)
        if paper_id.upper().startswith("PMC"):
            return paper_id.upper()
            
        # 3. PMID check (starts with pmid: or is typically 1-8 digits)
        if paper_id.lower().startswith("pmid:"):
            return paper_id.lower()[5:].strip()
        if paper_id.isdigit() and 1 <= len(paper_id) <= 9:
            # Short numeric strings are likely PMIDs
            return paper_id
            
        # 4. OpenAlex check (starts with W and followed by 10 digits)
        if paper_id.upper().startswith("W") and paper_id[1:].isdigit():
            return paper_id.upper()
            
        # Fallback: remove common prefixes and lowercase if it looks like a DOI
        if "/" in paper_id and (paper_id[0].isdigit() or paper_id.startswith("10.")):
            # DOIs usually look like 10.xxxx/yyyy
            return paper_id.lower()
            
        return paper_id

    @staticmethod
    def to_openalex_id(paper_id: str) -> str:
        """Format an ID specifically for OpenAlex API calls."""
        cid = IdCanonicalizer.canonicalize(paper_id)
        if not cid:
            return ""
            
        if cid.startswith("W"):
            return cid
        if cid.startswith("PMC"):
            return f"pmcid:{cid}"
        if cid.isdigit():
            return f"pmid:{cid}"
        if "/" in cid and (cid.startswith("10.") or cid[0].isdigit()):
            return f"doi:{cid}"
        
        # If it's a raw DOI without prefix
        if cid.startswith("10."):
            return f"doi:{cid}"
            
        return cid
