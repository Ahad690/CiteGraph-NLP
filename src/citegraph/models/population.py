from pydantic import BaseModel
from typing import Literal

class PopulationCandidate(BaseModel):
    candidate_id: str
    paper_id: str
    value: int
    raw_text: str
    sentence: str
    section: str | None = None
    semantic_type: Literal[
        "TOTAL_RANDOMIZED",
        "TOTAL_ANALYZED",
        "TOTAL_ENROLLED",
        "ARM_SIZE",
        "SCREENED",
        "COMPLETERS",
        "EVENT_COUNT",
        "FOLLOWUP_COUNT",
        "SAMPLE_SIZE_GENERIC",
        "UNKNOWN_NUMERIC"
    ]
    start_char: int | None = None
    end_char: int | None = None
    extraction_method: str
    confidence: float

class PopulationResolution(BaseModel):
    paper_id: str
    study_id: str | None = None
    n_eff: int | None = None
    semantic_type: str | None = None
    confidence: float
    status: Literal["resolved", "ambiguous", "missing", "not_applicable"]
    selected_candidate_id: str | None = None
    explanation: str
