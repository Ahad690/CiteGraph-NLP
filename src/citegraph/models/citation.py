from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class CitationEdge(BaseModel):
    edge_id: str
    source_paper_id: str
    target_paper_id: str
    relation: Literal["CITES"] = "CITES"
    providers: list[str]
    confidence: float
    retrieved_at: datetime
    base_weight: float | None = None
    final_weight: float | None = None
    n_score: float | None = None
    journal_score: float | None = None
