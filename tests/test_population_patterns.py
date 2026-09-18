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


def test_count_survives_a_year_in_the_same_sentence():
    """A date elsewhere in the sentence must not discard the sample size.

    Ignore patterns previously skipped the whole sentence, so almost every
    real abstract lost its count: clinical abstracts nearly always mention a
    year or a percentage alongside the number.
    """
    extractor = PopulationExtractor()
    text = (
        "We extracted data regarding 1099 patients with laboratory-confirmed "
        "Covid-19 from 552 hospitals in 30 provinces through January 29, 2020."
    )
    candidates = extractor.extract_candidates("p1", text, section="abstract")
    values = {c.value for c in candidates}
    assert 1099 in values, f"expected the cohort size, got {values}"
    assert 2020 not in values, "the year must not be read as a population"


def test_percentage_in_sentence_does_not_discard_count():
    extractor = PopulationExtractor()
    text = "A total of 250 patients were enrolled; 41.9% were female."
    values = {c.value for c in extractor.extract_candidates("p2", text, section="abstract")}
    assert 250 in values, f"expected 250, got {values}"


def test_year_alone_is_not_a_population():
    extractor = PopulationExtractor()
    text = "The outbreak began in Wuhan in December 2019 and spread rapidly."
    values = {c.value for c in extractor.extract_candidates("p3", text, section="abstract")}
    assert 2019 not in values


def test_observational_phrasings_are_extracted():
    """Epidemiological papers report cases and totals, not randomisation."""
    extractor = PopulationExtractor()
    cases = {
        "We analyzed data on the first 425 confirmed cases in Wuhan.": 425,
        "A total of 1500 subjects were followed.": 1500,
        "The study included 320 consecutive patients.": 320,
        "We screened 800 participants for eligibility.": 800,
    }
    for text, expected in cases.items():
        values = {c.value for c in extractor.extract_candidates("p", text, section="abstract")}
        assert expected in values, f"{text!r} -> {values}"
