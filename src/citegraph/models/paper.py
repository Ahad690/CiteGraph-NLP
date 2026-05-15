from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal

class PaperQuery(BaseModel):
    query_type: Literal["doi", "pmid", "pmcid", "title", "url"]
    value: str
    pdf_path: str | None = None

    @field_validator('value')
    @classmethod
    def validate_value(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query value cannot be empty")
        return v.strip()

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
