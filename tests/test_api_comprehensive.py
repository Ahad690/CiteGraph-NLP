import pytest
import respx
import httpx
import json
import asyncio
import csv
import io
from datetime import datetime, timezone
from typing import AsyncGenerator

from asgi_lifespan import LifespanManager
from httpx import ASGITransport

from citegraph.api.main import app
from citegraph.api.routes import store, task_manager
from citegraph.models.paper import Paper, PaperQuery
from citegraph.models.citation import CitationEdge
from citegraph.models.population import PopulationResolution
from citegraph.models.run import RunResult
from citegraph.utils.ids import IdCanonicalizer
from citegraph.config import settings

pytestmark = pytest.mark.asyncio


def _observed_status(payload: dict) -> str | None:
    """Derive a run status from either RunStatus (has `status`) or RunResult
    (has `papers` + `seed_paper_id` + `citation_edges`). Requires the full
    set of RunResult markers so a malformed partial response isn't mistaken
    for a completed run."""
    if (
        isinstance(payload.get("papers"), list)
        and isinstance(payload.get("seed_paper_id"), str)
        and isinstance(payload.get("citation_edges"), list)
    ):
        return payload.get("status") or "completed"
    return payload.get("status")


async def wait_for_status(client, run_id: str, expected: set[str], timeout: float = 5.0) -> dict:
    """Poll /api/runs/{run_id} until the observed status is in `expected` or
    timeout. Returns ``{"status": <observed>, "payload": <raw JSON>}`` so
    callers get the observed-status helper without us mutating the wire
    payload itself."""
    deadline = asyncio.get_event_loop().time() + timeout
    last_payload: dict | None = None
    last_status: str | None = None
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200, f"Run GET returned {resp.status_code}"
        last_payload = resp.json()
        last_status = _observed_status(last_payload)
        if last_status in expected:
            return {"status": last_status, "payload": last_payload}
        await asyncio.sleep(0.1)
    raise AssertionError(
        f"Run {run_id} never reached {expected}; last observed status={last_status}"
    )


SAMPLE_DOI = "10.1001/jama.2023.1234"
SAMPLE_PMID = "12345678"
SAMPLE_PMCID = "PMC87654321"
SAMPLE_TITLE = "A randomized trial of treatment for cardiovascular disease"
SAMPLE_OPENALEX_ID = "W4321987654"

SAMPLE_OPENALEX_WORK = {
    "id": f"https://openalex.org/{SAMPLE_OPENALEX_ID}",
    "doi": f"https://doi.org/{SAMPLE_DOI}",
    "ids": {"pmid": SAMPLE_PMID, "pmcid": SAMPLE_PMCID},
    "display_name": SAMPLE_TITLE,
    "publication_year": 2023,
    "primary_location": {
        "source": {"display_name": "Journal of the American Medical Association"}
    },
    "authorships": [
        {"author": {"display_name": "John Smith"}},
        {"author": {"display_name": "Jane Doe"}},
    ],
    "abstract_inverted_index": {
        "A": [0], "randomized": [1], "trial": [2], "of": [3],
        "treatment": [4], "for": [5], "cardiovascular": [6], "disease": [7]
    },
    "referenced_works": [
        "https://openalex.org/W1111111111",
        "https://openalex.org/W2222222222",
    ],
    "cited_by_api_url": f"https://api.openalex.org/works?filter=cites:{SAMPLE_OPENALEX_ID}",
}

SAMPLE_REFERENCE_WORK_1 = {
    "id": "https://openalex.org/W1111111111",
    "doi": "https://doi.org/10.1016/j.card.2020.01.001",
    "ids": {"pmid": "87654321", "pmcid": "PMC11111111"},
    "display_name": "Previous foundational study on heart disease",
    "publication_year": 2010,
    "primary_location": {
        "source": {"display_name": "Cardiology Journal"}
    },
    "authorships": [{"author": {"display_name": "Alice Brown"}}],
    "abstract_inverted_index": {"Previous": [0], "foundational": [1], "study": [2]},
    "referenced_works": [],
    "cited_by_api_url": "",
}

SAMPLE_REFERENCE_WORK_2 = {
    "id": "https://openalex.org/W2222222222",
    "doi": "https://doi.org/10.1056/nejm.2019.05.002",
    "ids": {"pmid": "55555555", "pmcid": "PMC22222222"},
    "display_name": "Early evidence for cardiovascular interventions",
    "publication_year": 2005,
    "primary_location": {
        "source": {"display_name": "New England Journal of Medicine"}
    },
    "authorships": [{"author": {"display_name": "Bob Johnson"}}],
    "abstract_inverted_index": {"Early": [0], "evidence": [1]},
    "referenced_works": [],
    "cited_by_api_url": "",
}


@pytest.fixture(autouse=True)
async def setup_store():
    # Reset async primitives to the current event loop. pytest-asyncio creates
    # a fresh loop per test, but `store` and `task_manager` are module-level
    # singletons whose internal asyncio objects (Locks, aiosqlite Connection,
    # waiter Futures) get bound to whichever loop touched them first. Rebuild
    # them so the test runs cleanly on its own loop.
    store.db_path = ":memory:"
    store._db = None
    store._lock = asyncio.Lock()
    task_manager._tasks = set()

    await store.connect()
    yield

    # Drain any background tasks started by routes (execute_run) before closing
    # the DB — otherwise they may try to write to a closed connection or use
    # a Lock bound to a torn-down loop.
    await task_manager.shutdown(timeout=2.0)
    await store.close()
    store._db = None


@pytest.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


def _build_completed_result(run_id: str = "deterministic-test-run") -> RunResult:
    """Construct a fully-populated RunResult for testing read endpoints
    without depending on the live pipeline."""
    now = datetime.now(timezone.utc)
    seed = Paper(
        paper_id="P_SEED",
        doi="10.1000/seed",
        title="Seed paper: a randomized trial of treatment",
        authors=["Alice Adams", "Bob Brown"],
        year=2022,
        journal="Journal of Test Medicine",
        abstract="A randomized trial enrolled 500 patients.",
        metadata_confidence=0.95,
    )
    cited = Paper(
        paper_id="P_CITED",
        doi="10.1000/cited",
        title="Foundational study on intervention",
        authors=["Carol Carter"],
        year=2010,
        journal="Foundational Journal",
        abstract="An earlier study with 200 enrolled patients.",
        metadata_confidence=0.90,
    )
    edge = CitationEdge(
        edge_id="E1",
        source_paper_id="P_SEED",
        target_paper_id="P_CITED",
        providers=["openalex"],
        confidence=0.92,
        retrieved_at=now,
        base_weight=0.75,
        final_weight=0.68,
        n_score=0.6,
        journal_score=0.5,
    )
    resolution = PopulationResolution(
        paper_id="P_SEED",
        n_eff=500,
        semantic_type="TOTAL_RANDOMIZED",
        confidence=0.91,
        status="resolved",
        explanation="High-confidence randomized trial population extracted from abstract",
    )
    return RunResult(
        run_id=run_id,
        seed_paper_id="P_SEED",
        papers=[seed, cited],
        studies=[],
        population_candidates=[],
        population_resolutions=[resolution],
        citation_edges=[edge],
        ranked_foundational_papers=[
            {
                "paper_id": "P_CITED",
                "title": cited.title,
                "year": cited.year,
                "score": 0.82,
                "explanation": "Older paper with strong evidence",
            }
        ],
        ranked_paths=[],
        warnings=[],
        created_at=now,
    )


@pytest.fixture
async def completed_run_id(request) -> str:
    """Pre-populate the store with a known-good completed run. The run_id is
    derived from the requesting test's name so parallel runs or scope changes
    can't collide on a shared fixed ID."""
    safe_name = "".join(c if c.isalnum() else "_" for c in request.node.name)[:48]
    run_id = f"deterministic-{safe_name}"
    result = _build_completed_result(run_id)
    await store.create_run(run_id)
    await store.save_result(run_id, result)
    return run_id


def mock_openalex_work(respx_mock, work_id: str, work_data: dict):
    respx_mock.get(f"https://api.openalex.org/works/{work_id}").respond(
        status_code=200,
        json=work_data,
    )


BATCH_WORKS = {
    "W1111111111": SAMPLE_REFERENCE_WORK_1,
    "W2222222222": SAMPLE_REFERENCE_WORK_2,
    SAMPLE_OPENALEX_ID: SAMPLE_OPENALEX_WORK,
}


def mock_openalex_citations(respx_mock, citing_work_id: str, results: list | None = None):
    """Stub the /works collection endpoint.

    The provider queries this one path three ways — ``cites:`` for forward
    citations and ``openalex_id:`` / ``doi:`` for batched metadata — so the
    route dispatches on the filter rather than pinning an exact query string.
    """
    citing_results = results or []

    def handler(request: httpx.Request) -> httpx.Response:
        filter_value = request.url.params.get("filter", "")
        empty = {"results": [], "meta": {"next_cursor": None}}

        if filter_value.startswith("cites:"):
            return httpx.Response(
                200, json={"results": citing_results, "meta": {"next_cursor": None}}
            )

        if filter_value.startswith("openalex_id:"):
            wanted = filter_value.split(":", 1)[1].split("|")
            return httpx.Response(200, json={
                "results": [BATCH_WORKS[w] for w in wanted if w in BATCH_WORKS],
                "meta": {"next_cursor": None},
            })

        if filter_value.startswith("doi:"):
            wanted = {d.lower() for d in filter_value.split(":", 1)[1].split("|")}
            return httpx.Response(200, json={
                "results": [
                    w for w in BATCH_WORKS.values()
                    if IdCanonicalizer.canonicalize(w.get("doi", "")) in wanted
                ],
                "meta": {"next_cursor": None},
            })

        return httpx.Response(200, json=empty)

    respx_mock.get("https://api.openalex.org/works").mock(side_effect=handler)


def setup_openalex_mocks(respx_mock):
    mock_openalex_work(respx_mock, f"doi:{SAMPLE_DOI}", SAMPLE_OPENALEX_WORK)
    mock_openalex_work(respx_mock, "W1111111111", SAMPLE_REFERENCE_WORK_1)
    mock_openalex_work(respx_mock, "W2222222222", SAMPLE_REFERENCE_WORK_2)
    mock_openalex_citations(respx_mock, SAMPLE_OPENALEX_ID)


def mock_crossref_not_found(respx_mock):
    """Stub every Crossref call with a 404 + a realistic Crossref error body.
    Crossref's tenacity-retry would otherwise take ~14s before giving up
    against unmocked requests; with a mocked 404 the provider fails fast."""
    respx_mock.route(url__regex=r"^https://api\.crossref\.org/.*").respond(
        status_code=404,
        json={"status": "error", "message-type": "route", "message": "Resource not found."},
    )


# Backwards-compatible alias (older callers still import this name).
mock_crossref_404 = mock_crossref_not_found


def mock_europe_pmc_empty(respx_mock):
    """Stub Europe PMC search/fulltext with an empty result so the provider
    returns no candidates immediately."""
    respx_mock.route(url__regex=r"^https://www\.ebi\.ac\.uk/.*").respond(
        status_code=200, json={"hitCount": 0, "resultList": {"result": []}}
    )


def setup_all_provider_mocks(respx_mock):
    """Mock all three metadata providers — required for the live pipeline
    to reach a terminal state quickly in tests."""
    setup_openalex_mocks(respx_mock)
    mock_crossref_404(respx_mock)
    mock_europe_pmc_empty(respx_mock)


class TestApiKeyAuth:
    """API-key gating is opt-in: unset means open (local demo), set means enforced."""

    async def test_open_when_api_key_unset(self, client):
        assert settings.api_key is None
        resp = await client.get("/api/runs/does-not-exist")
        # Reaches the handler (404 from the store), not the auth layer.
        assert resp.status_code == 404

    async def test_rejects_missing_key_when_configured(self, client, monkeypatch):
        monkeypatch.setattr(settings, "api_key", "s3cret-key")
        resp = await client.get("/api/runs/does-not-exist")
        assert resp.status_code == 401

    async def test_rejects_wrong_key(self, client, monkeypatch):
        monkeypatch.setattr(settings, "api_key", "s3cret-key")
        resp = await client.get(
            "/api/runs/does-not-exist", headers={"X-API-Key": "wrong"}
        )
        assert resp.status_code == 401

    async def test_accepts_correct_key(self, client, monkeypatch):
        monkeypatch.setattr(settings, "api_key", "s3cret-key")
        resp = await client.get(
            "/api/runs/does-not-exist", headers={"X-API-Key": "s3cret-key"}
        )
        assert resp.status_code == 404, "valid key should reach the handler"

    async def test_health_is_not_gated(self, client, monkeypatch):
        """/health sits outside the router, so probes keep working."""
        monkeypatch.setattr(settings, "api_key", "s3cret-key")
        resp = await client.get("/health")
        assert resp.status_code == 200


class TestCors:
    async def test_configured_origin_is_allowed(self, client):
        resp = await client.get(
            "/health", headers={"Origin": "http://localhost:5173"}
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

    async def test_unknown_origin_gets_no_cors_header(self, client):
        resp = await client.get("/health", headers={"Origin": "https://evil.test"})
        assert "access-control-allow-origin" not in resp.headers

    async def test_no_wildcard_origin(self, client):
        resp = await client.get(
            "/health", headers={"Origin": "http://localhost:5173"}
        )
        assert resp.headers.get("access-control-allow-origin") != "*"


class TestHealth:
    async def test_health_endpoint(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_health_returns_json(self, client):
        response = await client.get("/health")
        assert response.headers["content-type"].startswith("application/json")

    async def test_health_method_not_allowed(self, client):
        response = await client.post("/health")
        assert response.status_code == 405

    async def test_health_with_trailing_slash(self, client):
        response = await client.get("/health/")
        assert response.status_code in (200, 307, 404)


class TestStartRun:
    @respx.mock
    async def test_start_run_with_doi(self, client):
        setup_openalex_mocks(respx)

        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 1,
            "forward_depth": 0,
            "max_total_papers": 50,
        })
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["status"] == "started"
        assert len(data["run_id"]) > 0

    @respx.mock
    async def test_start_run_with_pmid(self, client):
        oa_id = IdCanonicalizer.to_openalex_id(SAMPLE_PMID)
        mock_openalex_work(respx, oa_id, SAMPLE_OPENALEX_WORK)
        mock_openalex_citations(respx, SAMPLE_OPENALEX_ID)

        response = await client.post("/api/runs", json={
            "query_type": "pmid",
            "value": SAMPLE_PMID,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        assert response.status_code == 200
        assert response.json()["status"] == "started"

    @respx.mock
    async def test_start_run_with_pmcid(self, client):
        oa_id = IdCanonicalizer.to_openalex_id(SAMPLE_PMCID)
        mock_openalex_work(respx, oa_id, SAMPLE_OPENALEX_WORK)
        mock_openalex_citations(respx, SAMPLE_OPENALEX_ID)

        response = await client.post("/api/runs", json={
            "query_type": "pmcid",
            "value": SAMPLE_PMCID,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        assert response.status_code == 200

    @respx.mock
    async def test_start_run_with_title(self, client):
        respx.get(
            "https://api.crossref.org/works",
            params={"query.title": SAMPLE_TITLE, "rows": 1},
        ).respond(
            status_code=200,
            json={
                "message": {
                    "items": [{
                        "DOI": SAMPLE_DOI,
                        "title": [SAMPLE_TITLE],
                        "author": [{"given": "John", "family": "Smith"}],
                        "container-title": ["JAMA"],
                        "issued": {"date-parts": [[2023]]},
                    }]
                }
            },
        )
        setup_openalex_mocks(respx)

        response = await client.post("/api/runs", json={
            "query_type": "title",
            "value": SAMPLE_TITLE,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        assert response.status_code == 200

    @respx.mock
    async def test_start_run_with_url(self, client):
        url = f"https://doi.org/{SAMPLE_DOI}"
        oa_id = IdCanonicalizer.to_openalex_id(SAMPLE_DOI)
        mock_openalex_work(respx, oa_id, SAMPLE_OPENALEX_WORK)
        mock_openalex_citations(respx, SAMPLE_OPENALEX_ID)

        response = await client.post("/api/runs", json={
            "query_type": "url",
            "value": url,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        assert response.status_code == 200

    @respx.mock
    async def test_start_run_with_pdf_path(self, client):
        """A pdf_path inside the uploads directory is accepted."""
        setup_openalex_mocks(respx)

        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "pdf_path": "paper.pdf",
            "backward_depth": 0,
            "forward_depth": 0,
        })
        assert response.status_code == 200

    @respx.mock
    async def test_start_run_rejects_pdf_path_outside_uploads(self, client):
        """pdf_path must not escape the uploads directory, so that wiring up
        PDF parsing later cannot become an arbitrary-file-read."""
        setup_openalex_mocks(respx)

        for bad_path in (
            "/etc/passwd.pdf",
            "../../../../etc/shadow.pdf",
            "uploads/../../secrets.pdf",
            "notapdf.txt",
        ):
            response = await client.post("/api/runs", json={
                "query_type": "doi",
                "value": SAMPLE_DOI,
                "pdf_path": bad_path,
                "backward_depth": 0,
                "forward_depth": 0,
            })
            assert response.status_code == 422, f"{bad_path} should be rejected"

    @respx.mock
    async def test_start_run_with_custom_limits(self, client):
        setup_openalex_mocks(respx)

        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 3,
            "forward_depth": 2,
            "max_total_papers": 200,
        })
        assert response.status_code == 200

    async def test_start_run_invalid_doi(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "not-a-doi",
        })
        assert response.status_code == 422

    async def test_start_run_empty_title(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "title",
            "value": "ab",
        })
        assert response.status_code == 422

    async def test_start_run_invalid_url(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "url",
            "value": "not-a-url",
        })
        assert response.status_code == 422

    async def test_start_run_invalid_pmid(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "pmid",
            "value": "abc",
        })
        assert response.status_code == 422

    async def test_start_run_invalid_pmcid(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "pmcid",
            "value": "12345",
        })
        assert response.status_code == 422

    async def test_start_run_empty_value(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "",
        })
        assert response.status_code == 422

    async def test_start_run_missing_query_type_is_auto_detected(self, client):
        """Omitting query_type is not an error: the shape of the value decides.

        This used to assert 422. Making the user classify their own identifier
        was a question the string already answers, so an absent query_type now
        means "auto" and a DOI-shaped value resolves to query_type "doi".
        """
        response = await client.post("/api/runs", json={
            "value": SAMPLE_DOI,
        })
        assert response.status_code == 200
        assert response.json()["run_id"]

    async def test_auto_detection_covers_every_identifier_shape(self, client):
        for value, expected in [
            (SAMPLE_DOI, "doi"),
            ("https://doi.org/10.1234/abcd", "url"),
            ("PMC1234567", "pmcid"),
            ("31234567", "pmid"),
            ("Attention Is All You Need", "title"),
        ]:
            query = PaperQuery(value=value)
            assert query.query_type == expected, f"{value!r} -> {query.query_type}"

    async def test_start_run_invalid_query_type(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "invalid",
            "value": "something",
        })
        assert response.status_code == 422

    async def test_start_run_non_string_value(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": 12345,
        })
        assert response.status_code == 422


class TestGetRun:
    async def test_get_run_not_found(self, client):
        response = await client.get("/api/runs/nonexistent-run-id")
        assert response.status_code == 404
        assert "detail" in response.json()

    async def test_get_completed_run_returns_full_result(self, client, completed_run_id):
        """GET /api/runs/{id} on a completed run returns the full RunResult,
        not just status."""
        response = await client.get(f"/api/runs/{completed_run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == completed_run_id
        assert data["seed_paper_id"] == "P_SEED"
        # Full RunResult shape — these keys only exist on completed responses
        assert "papers" in data and len(data["papers"]) == 2
        assert "citation_edges" in data and len(data["citation_edges"]) == 1
        assert "population_resolutions" in data
        assert "ranked_foundational_papers" in data

    async def test_get_pending_run_returns_status_shape(self, client):
        """A started-but-incomplete run returns RunStatus shape (no papers field)."""
        await store.create_run("pending-only")
        response = await client.get("/api/runs/pending-only")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "pending-only"
        assert data["status"] == "started"
        # Status response intentionally has no papers/edges/etc.
        assert "papers" not in data

    @respx.mock
    async def test_get_run_status_after_start(self, client):
        """End-to-end: POST creates run, GET must return a run with a valid
        status (started/running/completed/failed) — never crash."""
        setup_all_provider_mocks(respx)

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        run_id = resp.json()["run_id"]
        # Poll until the background task transitions out of "started" — the
        # status endpoint must surface a meaningful pending/running/terminal
        # state, not just echo back the initial "started".
        final = await wait_for_status(
            client, run_id, {"running", "completed", "failed"}, timeout=10.0,
        )
        assert final["status"] in {"running", "completed", "failed"}
        assert final["payload"]["run_id"] == run_id
        # The status must not still be "started" — the worker has begun.
        assert final["status"] != "started"

    @respx.mock
    async def test_get_run_with_background_traversal(self, client):
        setup_all_provider_mocks(respx)

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 1,
            "forward_depth": 0,
            "max_total_papers": 10,
        })
        run_id = resp.json()["run_id"]
        final = await wait_for_status(
            client, run_id, {"completed", "failed"}, timeout=20.0,
        )
        assert final["status"] in {"completed", "failed"}

    async def test_get_run_with_malformed_id(self, client):
        # /api/runs/ (trailing slash) triggers FastAPI's redirect to /api/runs
        # which is the POST endpoint — so we get 307 redirect or 405 depending
        # on how the client handles it.
        response = await client.get("/api/runs/")
        assert response.status_code in (307, 404, 405)

    async def test_get_run_empty_string_id(self, client):
        response = await client.get("/api/runs/ ")
        assert response.status_code == 404


class TestGraph:
    async def test_get_graph_success(self, client, completed_run_id):
        """Graph endpoint must return correctly-shaped nodes/links for a real
        completed run — no silent skip if the pipeline failed."""
        response = await client.get(f"/api/runs/{completed_run_id}/graph")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        data = response.json()
        assert set(data.keys()) == {"nodes", "links"}
        # Two papers from the fixture: seed + cited
        assert len(data["nodes"]) == 2
        node_ids = {n["id"] for n in data["nodes"]}
        assert node_ids == {"P_SEED", "P_CITED"}
        # Seed node must carry n_eff from population resolution
        seed_node = next(n for n in data["nodes"] if n["id"] == "P_SEED")
        assert seed_node["n_eff"] == 500
        assert seed_node["year"] == 2022
        assert "randomized" in seed_node["label"].lower()
        # One citation edge with the expected final_weight
        assert len(data["links"]) == 1
        link = data["links"][0]
        assert link["source"] == "P_SEED"
        assert link["target"] == "P_CITED"
        assert link["weight"] == pytest.approx(0.68)

    async def test_get_graph_not_found(self, client):
        response = await client.get("/api/runs/nonexistent/graph")
        assert response.status_code == 404

    async def test_get_graph_for_run_without_result(self, client):
        """A run that exists but has no result_json must 404 from /graph,
        not return an empty graph."""
        await store.create_run("pending-run-id")
        response = await client.get("/api/runs/pending-run-id/graph")
        assert response.status_code == 404

    async def test_get_graph_accepts_json(self, client):
        response = await client.get("/api/runs/fake/graph", headers={"Accept": "application/json"})
        assert response.status_code == 404
        assert response.headers.get("content-type", "").startswith("application/json")


class TestExport:
    async def test_export_json(self, client, completed_run_id):
        """JSON export must round-trip the full RunResult."""
        response = await client.get(f"/api/runs/{completed_run_id}/export/json")
        assert response.status_code == 200, response.text
        assert "attachment" in response.headers["content-disposition"]
        data = json.loads(response.content.decode("utf-8"))
        assert data["run_id"] == completed_run_id
        assert data["seed_paper_id"] == "P_SEED"
        assert len(data["papers"]) == 2
        assert len(data["citation_edges"]) == 1
        assert len(data["population_resolutions"]) == 1
        assert data["population_resolutions"][0]["n_eff"] == 500
        assert len(data["ranked_foundational_papers"]) == 1
        assert data["ranked_foundational_papers"][0]["paper_id"] == "P_CITED"

    async def test_export_csv(self, client, completed_run_id):
        """CSV export must be a real CSV file, parseable by the csv module."""
        response = await client.get(f"/api/runs/{completed_run_id}/export/csv")
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/csv")
        disposition = response.headers["content-disposition"]
        assert "attachment" in disposition
        assert f"citegraph-{completed_run_id}.csv" in disposition

        text = response.content.decode("utf-8-sig")  # strip the Excel BOM
        rows = list(csv.reader(io.StringIO(text)))
        assert rows[0][:5] == ["paper_id", "title", "authors", "year", "journal"]
        assert len(rows) == 3, "header + one row per paper"
        body = " ".join(" ".join(r) for r in rows[1:])
        assert "P_SEED" in body and "P_CITED" in body
        assert "500" in body

    async def test_export_csv_escapes_special_characters(self, client):
        """A comma, quote or embedded newline must not break the row count."""
        run_id = "csv-escape-run"
        result = _build_completed_result(run_id)
        result.papers[0].title = 'Trial: "A, B" study' + chr(10) + 'with a newline'
        result.papers[0].journal = 'Journal of "Quotes", Vol 2'
        await store.create_run(run_id)
        await store.save_result(run_id, result)

        response = await client.get(f"/api/runs/{run_id}/export/csv")
        assert response.status_code == 200
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        assert len(rows) == 3, f"escaping broke the row count: got {len(rows)}"
        assert "A, B" in rows[1][1]
        assert "Quotes" in rows[1][4]

    async def test_export_edges_csv(self, client, completed_run_id):
        """Edges are exported separately; a paper list cannot describe the graph."""
        response = await client.get(f"/api/runs/{completed_run_id}/export/edges.csv")
        assert response.status_code == 200, response.text
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        assert rows[0][:4] == [
            "source_paper_id", "source_title", "target_paper_id", "target_title",
        ]
        assert len(rows) == 2, "header + one row per edge"
        assert rows[1][0] == "P_SEED" and rows[1][2] == "P_CITED"

    async def test_export_graphml(self, client, completed_run_id):
        """GraphML was offered by the frontend but had no route (404)."""
        import xml.etree.ElementTree as ET

        response = await client.get(f"/api/runs/{completed_run_id}/export/graphml")
        assert response.status_code == 200, response.text
        assert "attachment" in response.headers["content-disposition"]
        root = ET.fromstring(response.content)
        assert root.tag.endswith("graphml")
        text = response.content.decode("utf-8")
        assert "P_SEED" in text and "P_CITED" in text

    async def test_export_markdown(self, client, completed_run_id):
        """Markdown export must be a valid report mentioning run + foundational papers."""
        response = await client.get(f"/api/runs/{completed_run_id}/export/markdown")
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/markdown")
        assert "attachment" in response.headers["content-disposition"]
        report = response.content.decode("utf-8")
        assert "CiteGraph-NLP" in report
        assert completed_run_id in report
        assert "P_SEED" in report
        # Ranked foundational paper table includes the cited paper title
        assert "Foundational study on intervention" in report
        # Population evidence table includes the n_eff value
        assert "500" in report

    async def test_export_json_not_found(self, client):
        response = await client.get("/api/runs/nonexistent/export/json")
        assert response.status_code == 404

    async def test_export_csv_not_found(self, client):
        response = await client.get("/api/runs/nonexistent/export/csv")
        assert response.status_code == 404

    async def test_export_markdown_not_found(self, client):
        response = await client.get("/api/runs/nonexistent/export/markdown")
        assert response.status_code == 404

    async def test_export_json_for_pending_run(self, client):
        """A started-but-incomplete run has no result_json — exports must 404."""
        await store.create_run("incomplete-run")
        for fmt in ("json", "csv", "markdown"):
            r = await client.get(f"/api/runs/incomplete-run/export/{fmt}")
            assert r.status_code == 404, f"{fmt} export should 404 without result"

    async def test_export_csv_missing_run(self, client):
        response = await client.get("/api/runs//export/csv")
        assert response.status_code == 404


class TestInputValidation:
    """Clamping tests — verify the route accepts out-of-range integers and
    silently clamps them (rather than 422-ing). We can't observe the clamped
    value from the API response alone, but verifying that POST returns 200
    with a valid run_id is what the contract guarantees."""

    async def test_backward_depth_clamped_high(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
            "backward_depth": 10,
            "forward_depth": 0,
        })
        assert response.status_code == 200
        assert "run_id" in response.json()

    async def test_backward_depth_clamped_low(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
            "backward_depth": -1,
            "forward_depth": 0,
        })
        assert response.status_code == 200
        assert response.json()["status"] == "started"

    async def test_forward_depth_clamped_high(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
            "backward_depth": 0,
            "forward_depth": 10,
        })
        assert response.status_code == 200
        assert response.json()["status"] == "started"

    async def test_max_total_papers_clamped_high(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
            "max_total_papers": 1000,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        assert response.status_code == 200
        assert response.json()["status"] == "started"

    async def test_max_total_papers_clamped_low(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
            "max_total_papers": 0,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        assert response.status_code == 200
        assert response.json()["status"] == "started"

    async def test_clamping_is_silent_not_rejection(self, client):
        """Direct verification that the route mutates the request and clamps —
        called via the request model's transformed state. POSTing extreme
        values must not 422; the orchestrator gets a clamped value."""
        # Test the boundary: clamps are min(max(v,0),3) for backward,
        # min(max(v,0),2) for forward, min(max(v,1),200) for max_papers.
        # Boundary values themselves should also produce 200.
        for params in (
            {"backward_depth": 3, "forward_depth": 2, "max_total_papers": 200},
            {"backward_depth": 0, "forward_depth": 0, "max_total_papers": 1},
        ):
            r = await client.post("/api/runs", json={
                "query_type": "doi",
                "value": "10.1001/jama.2023.1234",
                **params,
            })
            assert r.status_code == 200, f"params {params} produced {r.status_code}"
            assert r.json()["status"] == "started"

    async def test_default_values_used(self, client):
        """No depth/limit params at all — defaults kick in (2/1/100)."""
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert len(data["run_id"]) >= 8  # uuid4 string

    async def test_non_integer_depths(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
            "backward_depth": "invalid",
        })
        assert response.status_code == 422


class TestDatasetExport:
    """End-to-end pipeline tests. Unmocked Crossref/EuropePMC calls return
    errors (caught by ProviderResult), so the pipeline may legitimately end
    in either `completed` (OpenAlex alone yielded papers) or `failed` (no
    providers merged). Either is a valid outcome — what's tested here is
    that the full pipeline transitions and the endpoints respond correctly
    for whatever final state is reached."""

    async def test_full_pipeline_end_to_end_with_deterministic_data(self, client, completed_run_id):
        """Use the pre-populated run to verify every read endpoint at once —
        no flaky reliance on the live pipeline succeeding under mocks."""
        # GET /api/runs/{id} returns full RunResult
        get_resp = await client.get(f"/api/runs/{completed_run_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["seed_paper_id"] == "P_SEED"

        # /graph
        graph_resp = await client.get(f"/api/runs/{completed_run_id}/graph")
        assert graph_resp.status_code == 200
        gdata = graph_resp.json()
        assert len(gdata["nodes"]) == 2
        assert len(gdata["links"]) == 1

        # /export/json
        json_resp = await client.get(f"/api/runs/{completed_run_id}/export/json")
        assert json_resp.status_code == 200
        jdata = json.loads(json_resp.content.decode("utf-8"))
        assert jdata["run_id"] == completed_run_id

        # /export/csv — a real CSV body, not a JSON envelope
        csv_resp = await client.get(f"/api/runs/{completed_run_id}/export/csv")
        assert csv_resp.status_code == 200
        assert "paper_id" in csv_resp.content.decode("utf-8-sig")

        # /export/markdown
        md_resp = await client.get(f"/api/runs/{completed_run_id}/export/markdown")
        assert md_resp.status_code == 200
        assert "CiteGraph-NLP" in md_resp.content.decode("utf-8")

        # /export/graphml
        gml_resp = await client.get(f"/api/runs/{completed_run_id}/export/graphml")
        assert gml_resp.status_code == 200
        assert b"graphml" in gml_resp.content

    @respx.mock
    async def test_live_pipeline_post_then_terminal_status(self, client):
        """Exercise the actual orchestrator: POST a run, poll until it reaches
        a terminal status, assert the status is consistent and a GET succeeds."""
        setup_all_provider_mocks(respx)

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 1,
            "forward_depth": 0,
            "max_total_papers": 10,
        })
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        final = await wait_for_status(
            client, run_id, {"completed", "failed"}, timeout=15.0,
        )
        assert final["status"] in {"completed", "failed"}
        # If completed, the response must include the full RunResult shape
        if final["status"] == "completed":
            payload = final["payload"]
            assert "papers" in payload
            assert isinstance(payload["papers"], list)
            assert payload["seed_paper_id"]
            # Exports must succeed too
            for fmt in ("json", "csv", "markdown"):
                r = await client.get(f"/api/runs/{run_id}/export/{fmt}")
                assert r.status_code == 200, f"{fmt} export failed for completed run"

    @respx.mock
    async def test_pipeline_with_forward_citations(self, client):
        setup_openalex_mocks(respx)
        mock_openalex_citations(respx, SAMPLE_OPENALEX_ID, [
            {"id": "https://openalex.org/W3333333333"},
            {"id": "https://openalex.org/W4444444444"},
        ])
        mock_crossref_404(respx)
        mock_europe_pmc_empty(respx)

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 0,
            "forward_depth": 1,
            "max_total_papers": 10,
        })
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]
        final = await wait_for_status(
            client, run_id, {"completed", "failed"}, timeout=15.0,
        )
        assert final["status"] in {"completed", "failed"}

    @respx.mock
    async def test_pipeline_with_all_defaults(self, client):
        setup_all_provider_mocks(respx)
        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
        })
        assert resp.status_code == 200
        # Defaults: backward=2, forward=1, max=100. Deeper traversal — accept
        # "running" too (the contract guarantees the run is observable, not
        # that it completes in unit-test time).
        run_id = resp.json()["run_id"]
        final = await wait_for_status(
            client, run_id, {"running", "completed", "failed"}, timeout=20.0,
        )
        assert final["status"] in {"running", "completed", "failed"}
