import re
from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal

DOI_REGEX = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
PMID_REGEX = r'^\d{1,9}$'
PMCID_REGEX = r'^PMC\d{1,9}$'

class PaperQuery(BaseModel):
    query_type: Literal["doi", "pmid", "pmcid", "title", "url"]
    value: str
    pdf_path: str | None = None

    @field_validator('value')
    @classmethod
    def validate_value(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError("Query value cannot be empty")
        
        val = v.strip()
        q_type = info.data.get('query_type')
        
        if q_type == "doi" and not re.match(DOI_REGEX, val, re.I):
            # Allow some flexibility for input, but it must look like a DOI
            if not (val.startswith("10.") and "/" in val):
                raise ValueError(f"Invalid DOI format: {val}")
        elif q_type == "pmid" and not re.match(PMID_REGEX, val):
            raise ValueError(f"Invalid PMID format: {val}")
        elif q_type == "pmcid" and not re.match(PMCID_REGEX, val, re.I):
            raise ValueError(f"Invalid PMCID format: {val}")
            
        return val

class Paper(BaseModel):
    paper_id: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    openalex_id: str | None = None
    title: str
    authors: list[str] = []
    year: int | None = None
    journal: str | None = None
    abstract: str | None = None
    source_ids: dict[str, str] = {}
    metadata_confidence: float = 0.0
    provenance: dict[str, Any] = {}
