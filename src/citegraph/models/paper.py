import re
from pathlib import Path
from pydantic import BaseModel, Field, model_validator
from typing import Any, Literal

DOI_REGEX = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
PMID_REGEX = r'^\d{1,9}$'
PMCID_REGEX = r'^PMC\d{1,9}$'


def _validate_pdf_path(raw: str) -> str:
    """Confine a caller-supplied PDF path to the uploads directory.

    Nothing dereferences this value today, but it arrives from the request body
    and is threaded through the pipeline. Constraining it here means wiring up
    PDF parsing later cannot silently turn it into an arbitrary-file-read.
    """
    from citegraph.config import settings

    candidate = raw.strip()
    if not candidate:
        raise ValueError("pdf_path cannot be empty")
    if candidate.lower().rsplit(".", 1)[-1] != "pdf":
        raise ValueError("pdf_path must point to a .pdf file")

    uploads_root = (settings.data_dir / "uploads").resolve()
    resolved = (uploads_root / candidate).resolve() if not Path(candidate).is_absolute() \
        else Path(candidate).resolve()

    if resolved != uploads_root and uploads_root not in resolved.parents:
        raise ValueError("pdf_path must be inside the uploads directory")
    return str(resolved)

class PaperQuery(BaseModel):
    query_type: Literal["doi", "pmid", "pmcid", "title", "url"]
    value: str
    pdf_path: str | None = None

    @model_validator(mode='after')
    def validate_query(self) -> 'PaperQuery':
        v = self.value.strip()
        q_type = self.query_type
        
        if not v:
            raise ValueError("Query value cannot be empty")
            
        # Canonicalize DOI, PMID, and PMCID before regex matching
        if q_type in ("doi", "pmid", "pmcid"):
            from citegraph.utils.ids import IdCanonicalizer
            v = IdCanonicalizer.canonicalize(v)
            
        self.value = v
        
        if q_type == "doi":
            if not re.match(DOI_REGEX, v, re.I):
                raise ValueError(f"Invalid DOI format (must be 10.xxxx/yyyy): {v}")
        elif q_type == "pmid":
            if not re.match(PMID_REGEX, v):
                raise ValueError(f"Invalid PMID format (numeric digits only): {v}")
        elif q_type == "pmcid":
            if not re.match(PMCID_REGEX, v, re.I):
                raise ValueError(f"Invalid PMCID format (PMC prefix + digits): {v}")
        elif q_type == "url":
            from urllib.parse import urlparse
            try:
                parsed = urlparse(v)
                if not parsed.scheme or not parsed.netloc:
                    raise ValueError("URL must contain a scheme and a domain (netloc)")
            except Exception as e:
                raise ValueError(f"Invalid URL: {v}")
        elif q_type == "title":
            if len(v) < 5:
                raise ValueError("Title is too short for a reliable search")

        if self.pdf_path is not None:
            self.pdf_path = _validate_pdf_path(self.pdf_path)

        return self

class Paper(BaseModel):
    paper_id: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    openalex_id: str | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    abstract: str | None = None
    source_ids: dict[str, str] = Field(default_factory=dict)
    metadata_confidence: float = 0.0
    provenance: dict[str, Any] = Field(default_factory=dict)
