from typing import Literal

from pydantic import BaseModel


class TechnicalEvidence(BaseModel):
    paper_id: str
    status: Literal["resolved", "ambiguous", "missing"]
    kind: Literal["training_examples", "evaluation_examples", "dataset_examples"] | None = None
    value: int | None = None
    unit: str | None = None
    confidence: float = 0.0
    evidence: str | None = None
    section: str | None = None
    explanation: str
