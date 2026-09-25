import pytest
import httpx

from citegraph.config import settings
from citegraph.models.paper import Paper
from citegraph.models.population import PopulationResolution
from citegraph.pipeline.orchestrator import PipelineOrchestrator
from citegraph.providers.europe_pmc import EuropePMCProvider, _full_text_sections


FULL_TEXT_XML = b"""<article><body>
  <sec><title>Introduction</title><p>A previous study enrolled 900 patients.</p></sec>
  <sec><title>Methods</title>
    <sec><title>Study population</title><p>We enrolled 240 patients in this trial.</p></sec>
    <table-wrap><table><tr><td>Another study enrolled 800 patients.</td></tr></table></table-wrap>
  </sec>
  <sec><title>Results</title><p>We analyzed 220 participants.</p></sec>
  <sec><title>Discussion</title><p>Another cohort included 700 patients.</p>
    <sec><title>Study population</title><p>A cited trial had 600 patients.</p></sec>
  </sec>
</body><back><ref-list><ref>1,000 patients</ref></ref-list></back></article>"""


def test_full_text_sections_only_include_study_paragraphs():
    sections = _full_text_sections(FULL_TEXT_XML)
    assert sections == [
        ("methods", "We enrolled 240 patients in this trial."),
        ("results", "We analyzed 220 participants."),
    ]


async def test_europe_pmc_looks_up_open_access_full_text(respx_mock):
    provider = EuropePMCProvider()
    search = respx_mock.get(f"{provider.base_url}/search").respond(json={
        "resultList": {"result": [{"doi": "10.1234/example", "pmcid": "PMC1234567"}]}
    })
    full_text = respx_mock.get(f"{provider.base_url}/PMC1234567/fullTextXML").respond(
        content=FULL_TEXT_XML
    )

    found = await provider.find_open_access_pmcids_by_doi(["10.1234/example"])
    sections = await provider.get_full_text_sections(found["10.1234/example"])

    assert found == {"10.1234/example": "PMC1234567"}
    assert "OPEN_ACCESS:Y" in search.calls[0].request.url.params["query"]
    assert sections[0][0] == "methods"
    assert full_text.called


async def test_only_missing_abstract_extractions_use_full_text(monkeypatch):
    monkeypatch.setattr(settings, "enable_europe_pmc", True)
    pipeline = PipelineOrchestrator()
    fetched = []

    async def find_pmcids(dois, on_failure=None):
        assert dois == ["10.1234/missing"]
        return {"10.1234/missing": "PMC1234567"}

    async def get_sections(pmcid):
        fetched.append(pmcid)
        return _full_text_sections(FULL_TEXT_XML)

    monkeypatch.setattr(pipeline.europe_pmc, "find_open_access_pmcids_by_doi", find_pmcids)
    monkeypatch.setattr(pipeline.europe_pmc, "get_full_text_sections", get_sections)
    papers = {
        "missing": Paper(paper_id="missing", title="Trial", doi="10.1234/missing"),
        "resolved": Paper(paper_id="resolved", title="Other trial", pmcid="PMC7654321"),
    }
    resolutions = [
        PopulationResolution(paper_id="missing", study_id="study_missing", confidence=0, status="missing", explanation="No candidates"),
        PopulationResolution(paper_id="resolved", n_eff=50, confidence=0.8, status="resolved", explanation="From abstract"),
    ]

    candidates, recovered = await pipeline._recover_from_full_text(papers, resolutions)

    assert recovered == 1
    assert fetched == ["PMC1234567"]
    assert resolutions[0].n_eff == 240
    assert resolutions[0].study_id == "study_missing"
    assert resolutions[1].n_eff == 50
    assert {candidate.value for candidate in candidates} == {240, 220}
    assert all(candidate.section in {"methods", "results"} for candidate in candidates)
    assert papers["missing"].provenance["population_full_text"]["pmcid"] == "PMC1234567"


@pytest.fixture
def no_retry_wait(monkeypatch):
    """Keep the real retry policy but skip the backoff sleep in tests."""
    import tenacity
    monkeypatch.setattr(EuropePMCProvider._get.retry, "wait", tenacity.wait_none())


async def test_transient_503_is_retried_not_lost(respx_mock, no_retry_wait):
    """A single 503 used to drop the whole batch.

    Measured on one fixed set of 98 DOIs, four identical lookups returned 64,
    65, 62 and 84 abstracts, and one lost 12 PMCIDs to a single 503. That is
    why the same graph recovered 6, 11 and 9 populations on three runs.
    """
    provider = EuropePMCProvider()
    search = respx_mock.get(f"{provider.base_url}/search").mock(side_effect=[
        httpx.Response(503),
        httpx.Response(200, json={"resultList": {"result": [
            {"doi": "10.1234/example", "pmcid": "PMC1234567"},
        ]}}),
    ])
    lost = []

    found = await provider.find_open_access_pmcids_by_doi(["10.1234/example"], on_failure=lost.append)

    assert found == {"10.1234/example": "PMC1234567"}
    assert search.call_count == 2
    assert lost == []


async def test_batch_still_failing_after_retries_is_reported(respx_mock, no_retry_wait):
    """Give up after the retries, but say how many papers were affected."""
    provider = EuropePMCProvider()
    search = respx_mock.get(f"{provider.base_url}/search").respond(503)
    lost = []

    abstracts = await provider.get_abstracts_by_doi(
        ["10.1234/a", "10.1234/b"], on_failure=lost.append)

    assert abstracts == {}
    assert search.call_count == 3, "three attempts, the same policy as OpenAlex and Crossref"
    assert lost == [2]


async def test_not_found_is_not_retried(respx_mock, no_retry_wait):
    """A 404 means Europe PMC does not hold the paper; asking again cannot help."""
    provider = EuropePMCProvider()
    full_text = respx_mock.get(f"{provider.base_url}/PMC1234567/fullTextXML").respond(404)

    assert await provider.get_full_text_sections("PMC1234567") == []
    assert full_text.call_count == 1
