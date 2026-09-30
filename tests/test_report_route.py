"""The two provider-backed routes.

Both routes share one property that is worth more than the happy path: an
unconfigured provider is a NORMAL state, not an error. GLM ships disabled and
unkeyed, so if these routes returned 503 they would make the common case an
error page. Each test below pins the fallback shape, because the failure of a
fallback is that it 500s and takes the run down with it.

The key-leak tests exist because the one thing this endpoint must never do is
echo a credential. The provider raises with a message that has already been
scrubbed, and the route reports the exception CLASS rather than its text, so
even an unscrubbed message could not reach the client.
"""
from __future__ import annotations

import json

import pytest

from citegraph.config import settings
from citegraph.llm import glm as glm_mod
from citegraph.llm.base import ProviderUnavailable

FAKE_KEY = "sk-" + "notarealkey" + "0" * 24


@pytest.fixture(autouse=True)
def clean_providers(monkeypatch, tmp_path):
    """Every test starts with both providers off, keyed, or budget-blocked
    explicitly. Settings are process-wide, so a test that leaves GLM enabled
    changes the behaviour of the next one."""
    for name, value in (
        ("enable_glm", False), ("glm_api_key", None),
        ("enable_jev", False), ("jev_api_key", None),
        ("provider_cost_record", str(tmp_path / "cost.jsonl")),
        ("provider_daily_budget_usd", 1.00),
        ("provider_cache_path", str(tmp_path / "cache.jsonl")),
        ("provider_cache_ttl_s", 0.0),
    ):
        monkeypatch.setattr(settings, name, value)


class TestTheReportRouteFallsBack:
    @pytest.mark.asyncio
    async def test_the_route_is_registered_and_dispatches(self):
        """Registered and callable. A route that 404s because it was never added
        would satisfy every other test here, since they all call the function
        directly.

        getattr, not attribute access: app.routes can hold entries that are not
        APIRoute at all, and this test passed in isolation while failing in the
        full suite. Reading .path directly made the result depend on what other
        tests had already mounted.
        """
        from citegraph.api.main import app

        paths = {getattr(route, "path", None) for route in app.routes}
        # Under the router's /api prefix, so the assertion is written against
        # the mounted path rather than the bare decorator string.
        assert "/api/runs/{run_id}/report" in paths

    @pytest.mark.asyncio
    async def test_disabled_reports_none_and_says_why(self, monkeypatch):
        result = await _call_report(monkeypatch, enabled=False)
        assert result["report"] is None
        assert result["source"] == "none"
        assert "disabled" in result["reason"]

    @pytest.mark.asyncio
    async def test_budget_reached_reports_none_and_says_the_run_is_unaffected(
        self, monkeypatch
    ):
        result = await _call_report(monkeypatch, enabled=True, budget_blocked=True)
        assert result["report"] is None
        assert "budget" in result["reason"]
        assert "unaffected" in result["reason"]

    @pytest.mark.asyncio
    async def test_a_provider_error_does_not_take_the_run_down(self, monkeypatch):
        result = await _call_report(monkeypatch, enabled=True, raises=True)
        assert result["report"] is None
        assert result["source"] == "none"

    @pytest.mark.asyncio
    async def test_an_exception_text_never_reaches_the_client(self, monkeypatch):
        """Even a message that somehow carried the key must not come back."""
        result = await _call_report(
            monkeypatch, enabled=True, raises=True, message=f"401 for key {FAKE_KEY}"
        )
        assert FAKE_KEY not in json.dumps(result), "a key reached the response"

    @pytest.mark.asyncio
    async def test_a_hit_returns_the_report_and_the_evidence_counts(self, monkeypatch):
        result = await _call_report(monkeypatch, enabled=True, report="A grounded report.")
        assert result["source"] == "glm"
        assert result["report"] == "A grounded report."
        assert result["papers_considered"] > 0
        assert "edges_considered" in result


class TestTheCacheReachesTheProviders:
    @pytest.mark.asyncio
    async def test_a_second_identical_call_makes_no_provider_call(self, monkeypatch,
                                                                  tmp_path):
        """The end-to-end version of the cache contract. If this does not hold,
        the cache is a file that gets written and never read."""
        monkeypatch.setattr(settings, "enable_glm", True)
        monkeypatch.setattr(settings, "glm_api_key", FAKE_KEY)
        client = glm_mod.GLMClient()
        calls = {"n": 0}

        async def fake_post(path, body):
            calls["n"] += 1
            return {
                "model": "glm-5.3-flash",
                "choices": [{"message": {"content": "the same report"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50,
                          "cost": 0.01},
            }, None

        monkeypatch.setattr(client, "post_json", fake_post)

        papers = [{"paper_id": "p1", "title": "A paper", "year": 2020, "rank": 1}]
        edges = [{"source": "p1", "target": "p2"}]

        first, first_usage = await client.generate_report("q", papers, edges=edges)
        second, second_usage = await client.generate_report("q", papers, edges=edges)

        assert first == second == "the same report"
        assert calls["n"] == 1, "the second call reached the transport"
        # A hit spends nothing, so it must not be charged to today's ceiling.
        assert first_usage.cost_usd == 0.01
        assert second_usage.cost_usd == 0.0, "a cache hit was charged for"
        assert second_usage.input_tokens == 0

    @pytest.mark.asyncio
    async def test_different_edges_are_a_different_answer(self, monkeypatch):
        """The edges are the subject of the report, so two runs with the same
        papers but different links must not share an answer."""
        monkeypatch.setattr(settings, "enable_glm", True)
        monkeypatch.setattr(settings, "glm_api_key", FAKE_KEY)
        client = glm_mod.GLMClient()
        calls = {"n": 0}

        async def fake_post(path, body):
            calls["n"] += 1
            return {
                "model": "glm-5.3-flash",
                "choices": [{"message": {"content": f"report {calls['n']}"}}],
                "usage": {},
            }, None

        monkeypatch.setattr(client, "post_json", fake_post)
        papers = [{"paper_id": "p1", "title": "A paper"}]

        await client.generate_report("q", papers, edges=[{"source": "a", "target": "b"}])
        await client.generate_report("q", papers, edges=[{"source": "c", "target": "d"}])

        assert calls["n"] == 2, "different evidence shared one answer"


class TestThePromptCarriesTheEdges:
    def test_edges_are_in_the_prompt(self):
        prompt = glm_mod.GLMClient().build_prompt(
            "q", [{"title": "A"}], edges=[{"source": "p1", "target": "p2"}]
        )
        assert "p1 -> p2" in prompt
        assert "CITATION EDGES" in prompt

    def test_the_prompt_refuses_to_invent(self):
        """The grounding instruction is the whole point of the feature, so it is
        asserted rather than assumed present."""
        prompt = glm_mod.GLMClient().build_prompt("q", [{"title": "A"}])
        assert "does not support" in prompt

    def test_absent_edges_are_fine(self):
        prompt = glm_mod.GLMClient().build_prompt("q", [{"title": "A"}])
        assert "CITATION EDGES" not in prompt


# --- helpers -----------------------------------------------------------------

async def _call_report(monkeypatch, *, enabled, budget_blocked=False, raises=False,
                       report="A grounded report.", message="provider exploded"):
    """Drive the route function directly, with the store and client stubbed.

    Going through the HTTP client for each case would drag in a stored run for
    every test, and the thing under test is the route's fallback logic, not the
    store.
    """
    from citegraph.api import routes

    async def fake_load(run_id):
        from citegraph.models.run import RunResult

        return RunResult.model_validate(_SAMPLE_RESULT)

    monkeypatch.setattr(routes, "_load_result", fake_load)

    if budget_blocked:
        monkeypatch.setattr(routes, "budget_exhausted", lambda: True)

    class StubClient:
        # Built from a factory rather than `enabled = enabled`, because a class
        # body does not read the enclosing function's locals for a name it is
        # also assigning. That reads as working and raises NameError instead.
        def __init__(self, is_enabled: bool) -> None:
            self.enabled = is_enabled

        async def generate_report(self, question, papers, edges=None, run_id=None):
            if raises:
                raise ProviderUnavailable(message)
            from citegraph.llm.base import Usage

            return report, Usage(provider="glm", model_served="glm-5.3-flash")

    monkeypatch.setattr(routes, "get_glm", lambda: StubClient(enabled))

    return await routes.generate_report("run-1", routes.ReportRequest())


_SAMPLE_RESULT = {
    "run_id": "run-1",
    "seed_paper_id": "seed-1",
    "query": "foundational work in X",
    "papers": [],
    "studies": [],
    "population_candidates": [],
    "population_resolutions": [],
    "citation_edges": [],
    "ranked_foundational_papers": [
        {"rank": 1, "paper_id": "p1", "title": "A foundational paper",
         "year": 2019, "score": 0.91, "cited_by_count": 120},
        {"rank": 2, "paper_id": "p2", "title": "Another paper",
         "year": 2021, "score": 0.77, "cited_by_count": 30},
    ],
    "ranked_paths": [],
    "warnings": [],
    "created_at": "2026-09-29T00:00:00+00:00",
}
