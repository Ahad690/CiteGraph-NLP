from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime
from citegraph.models.paper import Paper
from citegraph.models.study import Study
from citegraph.models.population import PopulationCandidate, PopulationResolution
from citegraph.models.technical_evidence import TechnicalEvidence
from citegraph.models.citation import CitationEdge

class RunResult(BaseModel):
    run_id: str
    seed_paper_id: str
    papers: list[Paper]
    studies: list[Study]
    population_candidates: list[PopulationCandidate]
    population_resolutions: list[PopulationResolution]
    technical_evidence: list[TechnicalEvidence] = Field(default_factory=list)
    citation_edges: list[CitationEdge]
    ranked_foundational_papers: list[dict[str, Any]]
    ranked_paths: list[dict[str, Any]]
    warnings: list[str]
    created_at: datetime
