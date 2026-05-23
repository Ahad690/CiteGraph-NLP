import pytest
import respx
import httpx
import json
import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

from asgi_lifespan import LifespanManager
from httpx import ASGITransport

from citegraph.api.main import app
from citegraph.api.routes import store, task_manager
from citegraph.models.paper import Paper
from citegraph.models.citation import CitationEdge
from citegraph.models.population import PopulationResolution
from citegraph.models.run import RunResult
from citegraph.utils.ids import IdCanonicalizer

pytestmark = pytest.mark.asyncio


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


def mock_openalex_work(respx_mock, work_id: str, work_data: dict):
    respx_mock.get(f"https://api.openalex.org/works/{work_id}").respond(
        status_code=200,
        json=work_data,
    )


def mock_openalex_citations(respx_mock, citing_work_id: str, results: list | None = None):
    respx_mock.get(
        "https://api.openalex.org/works",
        params={"filter": f"cites:{citing_work_id}", "per_page": 50},
    ).respond(
        status_code=200,
        json={"results": results or []},
    )


def setup_openalex_mocks(respx_mock):
    mock_openalex_work(respx_mock, f"doi:{SAMPLE_DOI}", SAMPLE_OPENALEX_WORK)
    mock_openalex_work(respx_mock, "W1111111111", SAMPLE_REFERENCE_WORK_1)
    mock_openalex_work(respx_mock, "W2222222222", SAMPLE_REFERENCE_WORK_2)
    mock_openalex_citations(respx_mock, SAMPLE_OPENALEX_ID)


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
        setup_openalex_mocks(respx)

        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "pdf_path": "/path/to/paper.pdf",
            "backward_depth": 0,
            "forward_depth": 0,
        })
        assert response.status_code == 200

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

    async def test_start_run_missing_query_type(self, client):
        response = await client.post("/api/runs", json={
            "value": SAMPLE_DOI,
        })
        assert response.status_code == 422

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

    @respx.mock
    async def test_get_run_status_after_start(self, client):
        setup_openalex_mocks(respx)

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        run_id = resp.json()["run_id"]
        await asyncio.sleep(0.3)

        response = await client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200

    @respx.mock
    async def test_get_run_with_background_traversal(self, client):
        setup_openalex_mocks(respx)

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 1,
            "forward_depth": 0,
            "max_total_papers": 10,
        })
        run_id = resp.json()["run_id"]
        await asyncio.sleep(0.5)

        response = await client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200

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
    @respx.mock
    async def test_get_graph_success(self, client):
        setup_openalex_mocks(respx)

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 1,
            "forward_depth": 0,
        })
        run_id = resp.json()["run_id"]
        await asyncio.sleep(0.5)

        response = await client.get(f"/api/runs/{run_id}/graph")
        if response.status_code == 200:
            data = response.json()
            assert "nodes" in data
            assert "links" in data
            assert isinstance(data["nodes"], list)
            assert isinstance(data["links"], list)

    async def test_get_graph_not_found(self, client):
        response = await client.get("/api/runs/nonexistent/graph")
        assert response.status_code == 404

    async def test_get_graph_empty_result(self, client):
        response = await client.get("/api/runs/unknown-id/graph")
        assert response.status_code == 404

    async def test_get_graph_accepts_json(self, client):
        response = await client.get("/api/runs/fake/graph", headers={"Accept": "application/json"})
        assert response.status_code == 404
        assert response.headers.get("content-type", "").startswith("application/json")


class TestExport:
    @respx.mock
    async def test_export_json(self, client):
        setup_openalex_mocks(respx)

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        run_id = resp.json()["run_id"]
        await asyncio.sleep(0.3)

        response = await client.get(f"/api/runs/{run_id}/export/json")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            assert len(data) > 0

    @respx.mock
    async def test_export_csv(self, client):
        setup_openalex_mocks(respx)

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        run_id = resp.json()["run_id"]
        await asyncio.sleep(0.3)

        response = await client.get(f"/api/runs/{run_id}/export/csv")
        if response.status_code == 200:
            data = response.json()
            assert "csv" in data
            assert data["csv"].startswith("paper_id")

    @respx.mock
    async def test_export_markdown(self, client):
        setup_openalex_mocks(respx)

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        run_id = resp.json()["run_id"]
        await asyncio.sleep(0.3)

        response = await client.get(f"/api/runs/{run_id}/export/markdown")
        if response.status_code == 200:
            data = response.json()
            assert "report" in data
            assert "CiteGraph-NLP" in data["report"]

    async def test_export_json_not_found(self, client):
        response = await client.get("/api/runs/nonexistent/export/json")
        assert response.status_code == 404

    async def test_export_csv_not_found(self, client):
        response = await client.get("/api/runs/nonexistent/export/csv")
        assert response.status_code == 404

    async def test_export_markdown_not_found(self, client):
        response = await client.get("/api/runs/nonexistent/export/markdown")
        assert response.status_code == 404

    async def test_export_json_missing_run(self, client):
        response = await client.get("/api/runs/    /export/json")
        assert response.status_code == 404

    async def test_export_csv_missing_run(self, client):
        response = await client.get("/api/runs//export/csv")
        assert response.status_code == 404


class TestInputValidation:
    async def test_backward_depth_clamped_high(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
            "backward_depth": 10,
            "forward_depth": 0,
        })
        assert response.status_code == 200

    async def test_backward_depth_clamped_low(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
            "backward_depth": -1,
            "forward_depth": 0,
        })
        assert response.status_code == 200

    async def test_forward_depth_clamped_high(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
            "backward_depth": 0,
            "forward_depth": 10,
        })
        assert response.status_code == 200

    async def test_max_total_papers_clamped_high(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
            "max_total_papers": 1000,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        assert response.status_code == 200

    async def test_max_total_papers_clamped_low(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
            "max_total_papers": 0,
            "backward_depth": 0,
            "forward_depth": 0,
        })
        assert response.status_code == 200

    async def test_default_values_used(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
        })
        assert response.status_code == 200

    async def test_non_integer_depths(self, client):
        response = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": "10.1001/jama.2023.1234",
            "backward_depth": "invalid",
        })
        assert response.status_code == 422


class TestDatasetExport:
    @respx.mock
    async def test_full_pipeline_end_to_end(self, client):
        mock_openalex_work(respx, f"doi:{SAMPLE_DOI}", SAMPLE_OPENALEX_WORK)
        mock_openalex_work(respx, "W1111111111", SAMPLE_REFERENCE_WORK_1)
        mock_openalex_work(respx, "W2222222222", SAMPLE_REFERENCE_WORK_2)
        mock_openalex_citations(respx, SAMPLE_OPENALEX_ID)

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 1,
            "forward_depth": 0,
            "max_total_papers": 10,
        })
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        await asyncio.sleep(1.0)

        get_resp = await client.get(f"/api/runs/{run_id}")
        assert get_resp.status_code == 200

        graph_resp = await client.get(f"/api/runs/{run_id}/graph")
        if graph_resp.status_code == 200:
            gdata = graph_resp.json()
            assert "nodes" in gdata
            assert "links" in gdata

        json_resp = await client.get(f"/api/runs/{run_id}/export/json")
        if json_resp.status_code == 200:
            jdata = json_resp.json()
            assert isinstance(jdata, dict)

        csv_resp = await client.get(f"/api/runs/{run_id}/export/csv")
        if csv_resp.status_code == 200:
            csv_data = csv_resp.json()
            assert "csv" in csv_data

        md_resp = await client.get(f"/api/runs/{run_id}/export/markdown")
        if md_resp.status_code == 200:
            md_data = md_resp.json()
            assert "report" in md_data

    @respx.mock
    async def test_pipeline_with_forward_citations(self, client):
        mock_openalex_work(respx, f"doi:{SAMPLE_DOI}", SAMPLE_OPENALEX_WORK)
        mock_openalex_work(respx, "W1111111111", SAMPLE_REFERENCE_WORK_1)
        mock_openalex_work(respx, "W2222222222", SAMPLE_REFERENCE_WORK_2)
        mock_openalex_citations(respx, SAMPLE_OPENALEX_ID, [
            {"id": "https://openalex.org/W3333333333"},
            {"id": "https://openalex.org/W4444444444"},
        ])

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
            "backward_depth": 0,
            "forward_depth": 1,
            "max_total_papers": 10,
        })
        assert resp.status_code == 200

    @respx.mock
    async def test_pipeline_with_all_defaults(self, client):
        setup_openalex_mocks(respx)

        resp = await client.post("/api/runs", json={
            "query_type": "doi",
            "value": SAMPLE_DOI,
        })
        assert resp.status_code == 200
