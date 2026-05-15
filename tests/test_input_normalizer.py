import pytest
from citegraph.input.normalizer import InputNormalizer
from citegraph.models.paper import PaperQuery

def test_normalize_doi():
    normalizer = InputNormalizer()
    assert normalizer.normalize_doi("https://doi.org/10.1001/jama.2023.1234") == "10.1001/jama.2023.1234"
    assert normalizer.normalize_doi("doi:10.1001/jama.2023.1234") == "10.1001/jama.2023.1234"
    assert normalizer.normalize_doi(" 10.1001/JAMA.2023.1234 ") == "10.1001/jama.2023.1234"

def test_normalize_pmid():
    normalizer = InputNormalizer()
    assert normalizer.normalize_pmid("PMID: 12345678") == "12345678"
    assert normalizer.normalize_pmid(" 12345678 ") == "12345678"

def test_normalize_query():
    normalizer = InputNormalizer()
    query = PaperQuery(query_type="doi", value="DOI:10.1001/JAMA.2023.1234")
    normalized = normalizer.normalize_query(query)
    assert normalized.value == "10.1001/jama.2023.1234"
    assert normalized.query_type == "doi"
