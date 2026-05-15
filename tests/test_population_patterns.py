import pytest
from citegraph.nlp.population_extractor import PopulationExtractor

def test_population_extraction():
    extractor = PopulationExtractor()
    text = "A total of 8,500 patients were randomized to receive the drug."
    candidates = extractor.extract_candidates("test_paper", text, section="abstract")
    
    assert len(candidates) >= 1
    best = candidates[0]
    assert best.value == 8500
    assert "TOTAL_RANDOMIZED" in best.semantic_type or "TOTAL_ENROLLED" in best.semantic_type

def test_population_extraction_n_equals():
    extractor = PopulationExtractor()
    text = "The sample size was N=245 participants."
    candidates = extractor.extract_candidates("test_paper", text)
    
    assert any(c.value == 245 for c in candidates)
