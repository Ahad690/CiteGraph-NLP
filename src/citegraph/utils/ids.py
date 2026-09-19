import re
from typing import Optional

# A DOI is a "10." prefix, a registrant code, "/", then a suffix. Anchored, so
# a title or a URL cannot satisfy it.
DOI_RE = re.compile(r"10\.\d{4,9}/\S+")
# OpenAlex work ids are W followed by digits.
OPENALEX_WORK_RE = re.compile(r"W\d+")
PMCID_RE = re.compile(r"PMC\d+")
PMID_RE = re.compile(r"\d{1,9}")


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
        """Format an ID for OpenAlex's /works/{id} endpoint.

        Returns "" for anything that is not a recognised identifier. This used
        to fall through to `return cid`, which meant a title or a URL was sent
        as a path segment: a search for "Attention Is All You Need" became
        GET /works/Attention%20Is%20All%20You%20Need, and an IEEE article URL
        became GET /works/https://ieeexplore.ieee.org/document/4812104. Both
        404, so OpenAlex contributed nothing to either lookup while appearing
        in the logs as a provider failure rather than as a caller error.
        """
        cid = IdCanonicalizer.canonicalize(paper_id)
        if not cid:
            return ""

        if OPENALEX_WORK_RE.fullmatch(cid):
            return cid
        if cid.startswith("PMC") and cid[3:].isdigit():
            return f"pmcid:{cid}"
        if cid.isdigit():
            return f"pmid:{cid}"
        if DOI_RE.fullmatch(cid):
            return f"doi:{cid}"

        return ""


def detect_query_type(value: str) -> str:
    """Work out what kind of identifier a user pasted.

    Exists so the dashboard does not have to ask. Every branch is a shape a
    person can actually type, and the order matters: a DOI embedded in a URL
    should be recognised as a URL so the URL resolver gets a chance to strip
    publisher view segments, while a bare DOI should not.

    Returns one of "doi", "pmid", "pmcid", "url", "title". Falls back to
    "title" because free text is the only input with no distinguishing shape,
    so anything unrecognised is better searched than rejected.
    """
    if not value:
        return "title"
    text = value.strip()
    if not text:
        return "title"

    lowered = text.lower()

    # A URL, including the doi.org form. Checked first: a publisher URL often
    # contains a DOI, and the URL resolver knows how to extract it.
    if lowered.startswith(("http://", "https://", "www.")):
        return "url"

    # PMC identifiers, with or without the prefix people copy from Europe PMC.
    if PMCID_RE.fullmatch(text.upper().replace("PMCID:", "").strip()):
        return "pmcid"

    # "doi:10.xxxx/yyy" and bare "10.xxxx/yyy".
    candidate = text
    for prefix in ("doi:", "doi "):
        if lowered.startswith(prefix):
            candidate = text[len(prefix):].strip()
            break
    if DOI_RE.fullmatch(candidate):
        return "doi"

    # "PMID: 12345678" and a bare run of digits.
    digits = text.upper().replace("PMID:", "").strip()
    if PMID_RE.fullmatch(digits):
        return "pmid"

    # An OpenAlex work id resolves through the DOI path in the providers.
    if OPENALEX_WORK_RE.fullmatch(text.upper()):
        return "doi"

    return "title"
