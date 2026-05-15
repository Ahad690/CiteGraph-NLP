from pydantic import BaseModel

class Study(BaseModel):
    study_id: str
    registry_id: str | None = None
    design: str | None = None
    domain: str | None = None
    inferred: bool = True
    dedupe_confidence: float = 0.0
