import logging
from typing import List, Optional
from citegraph.models.population import PopulationCandidate, PopulationResolution

logger = logging.getLogger(__name__)

class PopulationResolver:
    def resolve(self, paper_id: str, candidates: List[PopulationCandidate]) -> PopulationResolution:
        """
        Select the most likely effective population size (N_eff) from candidates.
        """
        if not candidates:
            return PopulationResolution(
                paper_id=paper_id,
                confidence=0.0,
                status="missing",
                explanation="No population candidates found."
            )

        # Sort candidates by confidence
        sorted_candidates = sorted(candidates, key=lambda x: x.confidence, reverse=True)
        
        # Priority mapping
        type_priority = {
            "TOTAL_RANDOMIZED": 10,
            "TOTAL_ANALYZED": 9,
            "TOTAL_ENROLLED": 8,
            "SAMPLE_SIZE_GENERIC": 7,
            "ARM_SIZE": 5,
            "SCREENED": 4,
            "COMPLETERS": 3,
            "FOLLOWUP_COUNT": 2,
            "EVENT_COUNT": 1,
            "UNKNOWN_NUMERIC": 0
        }

        # Filter out low confidence
        filtered = [c for c in sorted_candidates if c.confidence > 0.4]
        
        if not filtered:
            return PopulationResolution(
                paper_id=paper_id,
                confidence=0.0,
                status="missing",
                explanation="No candidates met minimum confidence threshold."
            )

        # Apply priority and confidence to pick the best
        def scoring_func(c: PopulationCandidate):
            return c.confidence * (1 + type_priority.get(c.semantic_type, 0) / 10.0)

        best_candidate = max(filtered, key=scoring_func)
        
        # Check for ambiguity
        # If there's another candidate with similar score but different value, mark as ambiguous
        best_score = scoring_func(best_candidate)
        ambiguous = False
        for c in filtered:
            if c.candidate_id == best_candidate.candidate_id:
                continue
            if scoring_func(c) > best_score * 0.9 and abs(c.value - best_candidate.value) > (best_candidate.value * 0.1):
                ambiguous = True
                break

        return PopulationResolution(
            paper_id=paper_id,
            n_eff=best_candidate.value,
            semantic_type=best_candidate.semantic_type,
            confidence=best_candidate.confidence,
            status="ambiguous" if ambiguous else "resolved",
            selected_candidate_id=best_candidate.candidate_id,
            explanation=f"Selected {best_candidate.semantic_type} ({best_candidate.value}) from {best_candidate.section} section."
        )
