import math
import logging
from typing import List, Dict
from citegraph.models.citation import CitationEdge
from citegraph.models.population import PopulationResolution
from citegraph.config import settings

logger = logging.getLogger(__name__)

class WeightCalculator:
    def __init__(self):
        self.alpha = settings.weight_alpha
        self.beta = settings.weight_beta
        self.n_reference = settings.n_reference

    def calculate_weights(self, edges: List[CitationEdge], resolutions: List[PopulationResolution]) -> List[CitationEdge]:
        """Calculate weights for all citation edges."""
        res_map = {r.paper_id: r for r in resolutions}
        
        for edge in edges:
            # We weight based on the TARGET paper (the cited evidence)
            target_res = res_map.get(edge.target_paper_id)
            
            n_eff = target_res.n_eff if target_res and target_res.n_eff else 0
            n_score = math.log1p(n_eff) / math.log1p(self.n_reference)
            n_score = max(0.0, min(1.0, n_score))
            
            # For now, journal score is neutral fallback as per PRD
            journal_score = 0.5
            
            base_weight = (self.alpha * n_score) + (self.beta * journal_score)
            
            # Adjust by confidence
            pop_confidence = target_res.confidence if target_res else 0.5
            final_weight = base_weight * pop_confidence * edge.confidence
            
            edge.n_score = n_score
            edge.journal_score = journal_score
            edge.base_weight = base_weight
            edge.final_weight = final_weight
            
        return edges
