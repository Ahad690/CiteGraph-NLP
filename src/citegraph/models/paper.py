import re
from pydantic import BaseModel, Field, model_validator
from typing import Any, Literal

DOI_REGEX = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
PMID_REGEX = r'^\d{1,9}$'
PMCID_REGEX = r'^PMC\d{1,9}$'

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
