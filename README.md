# CiteGraph-NLP

**Confidence-Aware Citation Lineage and Study-Scale Knowledge Graph System**

CiteGraph-NLP is an NLP + Knowledge Graph system for analyzing scientific papers, tracing citation lineages, extracting study population evidence, and ranking **probable foundational papers** using confidence-aware graph analytics.

The project is a research prototype that makes uncertainty visible using confidence scores, provenance tracking, and ambiguity labels.

## Group Members

- M. Ahad Imran (F23607034)
- Syed Zain-ul-Abidin (F23607031)
- Anas Zafar (F22607024)

---

## Live Deployment

| Component | URL |
|-----------|-----|
| Frontend (Cloudflare Pages) | https://citegraph-nlp.pages.dev |
| Backend API | https://citegraph-api.penora.us |
| API docs | https://citegraph-api.penora.us/docs |
| Health check | https://citegraph-api.penora.us/health |

The backend runs as a Docker container bound to `127.0.0.1:18030` on a shared
host, behind nginx with a Let's Encrypt certificate. It is not reachable
directly; only nginx can reach the port.

`CORS_ORIGINS` is set to the Pages origin, so the API accepts browser requests
from the deployed frontend and no other site. `VITE_API_BASE` is inlined by
Vite at build time, so the frontend must be rebuilt if the API host changes.

The previous Firebase URLs are kept alive and now 301-redirect here, preserving
any links in already-submitted coursework:

- `https://citegraph-nlp1.web.app/*` -> `https://citegraph-nlp.pages.dev/*`
- `https://citegraph-nlp1.firebaseapp.com/*` -> `https://citegraph-nlp.pages.dev/*`

Both deployments run from GitHub Actions on a push to `main`
(`.github/workflows/deploy-backend.yml`, `deploy-frontend.yml`). The frontend
workflow needs the `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`
repository secrets.

---

## What It Does

CiteGraph-NLP starts from a research paper identifier and builds a structured citation analysis pipeline:

### Supported Inputs
- **DOI** (e.g. `10.1001/jama.2023.1234`)
- **PMID** (e.g. `12345678`)
- **PMCID** (e.g. `PMC87654321`)
- **Paper title** (free-text search via Crossref)
- **URL** (auto-extracts DOI/PMID/PMCID from PubMed or doi.org links)
- **PDF path** (for optional PDF text extraction via GROBID)

### Pipeline Stages
1. **Input Normalization** — Canonicalize identifiers (DOI/PMID/PMCID/OpenAlex ID)
2. **Metadata Resolution** — Query OpenAlex, Crossref, and EuropePMC in parallel, merge results
3. **Citation Traversal** — Level-by-level BFS over backward references and forward citations, with batched metadata lookups. Records describing the same work under different identifiers are merged before the paper budget is applied, so deduplication never costs graph slots
4. **Abstract Backfill** — Papers with no OpenAlex abstract are topped up from Europe PMC in one batched query; population evidence can only be read from text
5. **Population Extraction** — Regex-based extraction of sample sizes from abstracts with semantic classification
6. **Population Resolution** — Select best N_eff candidate per paper using confidence and type priority scoring
7. **Edge Weighting** — Weight citation edges by normalized population evidence + journal score + confidence
8. **Graph Analytics** — PageRank-based foundational paper ranking and citation path ranking
9. **Export** — Results available as JSON, CSV, Markdown report, and graph visualization data

### Population Semantic Types
| Type | Description |
|------|-------------|
| `TOTAL_RANDOMIZED` | Patients randomized/assigned |
| `TOTAL_ANALYZED` | Patients analyzed |
| `TOTAL_ENROLLED` | Patients enrolled/eligible |
| `SAMPLE_SIZE_GENERIC` | Generic N = value |
| `ARM_SIZE` | Individual arm/group size |
| `SCREENED` | Patients screened |
| `COMPLETERS` | Patients who completed |
| `EVENT_COUNT` | Event/outcome counts — *defined in the model, no extraction pattern emits it yet* |
| `FOLLOWUP_COUNT` | Follow-up counts |
| `UNKNOWN_NUMERIC` | Unclassified numbers — *defined in the model, no extraction pattern emits it yet* |

---

## Tech Stack

### Backend
- Python 3.10+ (the Docker image is `python:3.10-slim`)
- FastAPI (async REST API)
- Pydantic v2 (models & validation)
- httpx (async HTTP client for API calls)
- NetworkX (graph construction & PageRank)
- SQLite + aiosqlite (run persistence)
- spaCy (NLP sentence splitting, optional fallback)
- Tenacity (retry logic for external APIs)
- pytest / pytest-asyncio / respx (testing)

### Data Providers
- **OpenAlex** — metadata resolution, backward references, forward citations
- **Crossref** — metadata resolution, title search, backward references
- **EuropePMC** — metadata resolution, URL-based ID extraction

### Dashboard / Frontend
- React + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- TanStack Query, TanStack Router
- Cytoscape.js graph visualization

---

## Project Structure

```text
citegraph-nlp/
├── README.md
├── .env.example
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── Makefile
│
├── src/
│   └── citegraph/
│       ├── api/
│       │   ├── main.py           # FastAPI app, CORS, router registration
│       │   ├── routes.py         # All API endpoints
│       │   └── security.py       # Optional API-key gate (API_KEY)
│       ├── models/
│       │   ├── paper.py          # Paper, PaperQuery
│       │   ├── study.py          # Study
│       │   ├── population.py     # PopulationCandidate, PopulationResolution
│       │   ├── citation.py       # CitationEdge
│       │   └── run.py            # RunResult
│       ├── input/
│       │   ├── normalizer.py     # InputNormalizer
│       │   └── url_resolver.py   # URL -> identifier, with SSRF guard
│       ├── providers/
│       │   ├── base.py           # Provider protocol, pooled HTTP client, retry policy
│       │   ├── openalex.py       # OpenAlex API client
│       │   ├── crossref.py       # Crossref API client
│       │   └── europe_pmc.py     # Europe PMC API client
│       ├── metadata/
│       │   ├── resolver.py       # MetadataResolver (parallel provider queries)
│       │   └── merger.py         # MetadataMerger (field-level merge)
│       ├── nlp/
│       │   ├── population_patterns.py   # Regex patterns & ignore rules
│       │   ├── population_extractor.py  # PopulationExtractor
│       │   └── population_resolver.py   # PopulationResolver
│       ├── citations/
│       │   ├── retriever.py      # CitationRetriever (aggregate from providers)
│       │   └── traversal.py      # CitationTraversal (BFS traversal)
│       ├── graph/
│       │   ├── builder.py        # GraphBuilder (NetworkX)
│       │   ├── weighting.py      # WeightCalculator (evidence-weighted edges)
│       │   ├── analytics.py      # GraphAnalytics (PageRank, path ranking)
│       │   └── exporters.py      # GraphExporter (JSON, GraphML)
│       ├── pipeline/
│       │   └── orchestrator.py   # PipelineOrchestrator (full workflow)
│       ├── storage/
│       │   └── sqlite.py         # SQLiteStore (run persistence)
│       ├── utils/
│       │   ├── ids.py            # IdCanonicalizer (DOI/PMID/PMCID normalization)
│       │   └── tasks.py          # TaskManager (background task lifecycle)
│       ├── config.py             # Settings (pydantic-settings)
│       └── logging_config.py     # Logging setup
│
├── frontend/                     # React dashboard
├── tests/                        # 102 tests
│   ├── conftest.py
│   ├── test_add_citegraph_route.py
│   ├── test_api_comprehensive.py
│   ├── test_input_normalizer.py
│   ├── test_population_patterns.py
│   ├── test_ranking.py
│   ├── test_sqlite_store.py
│   ├── test_task_manager.py
│   └── test_url_resolver.py
│
├── scripts/
├── data/
│   ├── cache/
│   ├── uploads/
│   ├── parsed/
│   └── exports/
│
└── docs/
```

---

## Setup

### 1. Clone & Virtual Environment

```bash
git clone https://github.com/Ahad690/CiteGraph-NLP.git
cd CiteGraph-NLP
python -m venv .venv
# Activate:
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment name |
| `LOG_LEVEL` | `INFO` | Logging level |
| `API_KEY` | — | When set, every `/api` request must send a matching `X-API-Key` header |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated browser origins allowed to call the API |
| `OPENALEX_EMAIL` | — | Email for OpenAlex API (polite pool) |
| `ENABLE_OPENALEX` | `true` | Toggle OpenAlex provider |
| `ENABLE_CROSSREF` | `true` | Toggle Crossref provider |
| `ENABLE_EUROPE_PMC` | `true` | Toggle Europe PMC provider |
| `DATA_DIR` | `./data` | Data directory |
| `SQLITE_PATH` | `./data/cache/citegraph.sqlite` | SQLite database path |
| `GROBID_URL` | `http://localhost:8070` | GROBID server URL |
| `DEFAULT_BACKWARD_DEPTH` | `2` | Default backward traversal depth |
| `DEFAULT_FORWARD_DEPTH` | `1` | Default forward traversal depth |
| `DEFAULT_MAX_TOTAL_PAPERS` | `100` | Max papers per run |
| `WEIGHT_ALPHA` | `0.75` | Population evidence weight |
| `WEIGHT_BETA` | `0.25` | Journal score weight |
| `N_REFERENCE` | `100000` | Reference population for N-score normalization |

---

## Running the API

### Start the server

```bash
uvicorn citegraph.api.main:app --reload
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Optional Services

```bash
# GROBID for PDF parsing
docker compose up -d grobid

# Neo4j graph database (optional, NetworkX is default)
docker compose --profile neo4j up -d neo4j
```

---

## API Endpoints

### Health Check

```http
GET /health
```

Response:
```json
{"status": "ok"}
```

---

### Start an Analysis Run

```http
POST /api/runs
```

Initiates a background analysis pipeline. Returns immediately with a `run_id`.

**Request Body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query_type` | `string` | required | One of: `doi`, `pmid`, `pmcid`, `title`, `url` |
| `value` | `string` | required | The identifier value |
| `pdf_path` | `string` | `null` | Optional path to a PDF file |
| `backward_depth` | `int` | `2` | Depth for backward reference traversal (clamped 0–3) |
| `forward_depth` | `int` | `1` | Depth for forward citation traversal (clamped 0–2) |
| `max_total_papers` | `int` | `100` | Maximum papers to collect (clamped 1–200) |

**Input validation rules per query_type:**
- `doi`: Must match pattern `10.xxxx/yyyy` (case-insensitive)
- `pmid`: 1–9 digit numeric string
- `pmcid`: `PMC` prefix followed by digits
- `title`: Minimum 5 characters
- `url`: Must contain scheme and netloc; auto-extracts DOI/PMID/PMCID

Example:
```json
{
  "query_type": "doi",
  "value": "10.1001/jama.2023.1234",
  "backward_depth": 2,
  "forward_depth": 1,
  "max_total_papers": 100
}
```

Response (202):
```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "started"
}
```

---

### Get Run Status or Result

```http
GET /api/runs/{run_id}
```

Returns the run status while in progress, or the full `RunResult` when completed.

**While running:**
```json
{
  "run_id": "a1b2c3d4-...",
  "status": "running",
  "error": null,
  "created_at": "2024-01-01T00:00:00"
}
```

**When completed** — returns full `RunResult` object:

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `string` | Run identifier |
| `seed_paper_id` | `string` | ID of the seed paper |
| `papers` | `array` | All collected `Paper` objects |
| `studies` | `array` | Study nodes derived from papers |
| `population_candidates` | `array` | All extracted population candidates |
| `population_resolutions` | `array` | Resolved N_eff per paper |
| `citation_edges` | `array` | Weighted citation edges |
| `ranked_foundational_papers` | `array` | Papers ranked by combined PageRank + year + evidence score |
| `ranked_paths` | `array` | Citation paths from seed to foundational papers |
| `warnings` | `array` | Any warnings generated during the run |
| `created_at` | `datetime` | Run creation timestamp |

**Paper model:**
| Field | Type | Description |
|-------|------|-------------|
| `paper_id` | `string` | Canonical identifier (prefers DOI) |
| `doi` | `string` | Digital Object Identifier |
| `pmid` | `string` | PubMed ID |
| `pmcid` | `string` | PubMed Central ID |
| `openalex_id` | `string` | OpenAlex ID (W...) |
| `title` | `string` | Paper title |
| `authors` | `array` | Author names |
| `year` | `int` | Publication year |
| `journal` | `string` | Journal name |
| `abstract` | `string` | Abstract text |
| `source_ids` | `object` | Provider-specific source IDs |
| `metadata_confidence` | `float` | 0–1 confidence in metadata |
| `provenance` | `object` | Per-provider retrieval metadata |

---

### Get Graph Visualization Data

```http
GET /api/runs/{run_id}/graph
```

Returns nodes and links for graph visualization.

Response:
```json
{
  "nodes": [
    {
      "id": "10.1001/jama.2023.1234",
      "label": "A randomized trial...",
      "year": 2023,
      "n_eff": 8500
    }
  ],
  "links": [
    {
      "source": "10.1001/jama.2023.1234",
      "target": "10.1016/j.card.2020.01.001",
      "weight": 0.85
    }
  ]
}
```

---

### Export Results

All export endpoints are available once a run reaches `completed` status.

Every export is returned as a downloadable file with a `Content-Disposition`
header, not wrapped in a JSON envelope, so saving the response body gives a
file that opens directly in Excel, a markdown viewer, or Gephi.

| Endpoint | Type | Contents |
|----------|------|----------|
| `GET /api/runs/{run_id}/export/json` | `application/json` | Full `RunResult`, indented |
| `GET /api/runs/{run_id}/export/csv` | `text/csv` | One row per paper: ids, authors, journal, N_eff, population status and confidence, in/out degree, foundational rank, seed flag |
| `GET /api/runs/{run_id}/export/edges.csv` | `text/csv` | One row per citation edge with every weight component |
| `GET /api/runs/{run_id}/export/markdown` | `text/markdown` | Report: seed details, summary table, foundational ranking, population evidence, top citation paths |
| `GET /api/runs/{run_id}/export/graphml` | `application/xml` | GraphML for Gephi / yEd / Cytoscape Desktop |

Both CSV exports are written with the `csv` module (so titles containing
commas, quotes or newlines stay in one field) and carry a UTF-8 BOM so Excel
renders accented author names correctly.

---

## Edge Weighting Formula

Citation edges are weighted by population evidence, scaled by how confident
the extraction was:

```
N_score       = log1p(N_eff) / log1p(N_reference)
evidence_term = alpha * N_score * pop_confidence
final_weight  = (evidence_term + beta * journal_score) * edge_confidence
```

Defaults: `alpha = 0.75`, `beta = 0.25`, `N_reference = 100000`

Confidence scales the **evidence term only**. The journal term is structural
and always applies, so a paper with no extractable population still produces a
usable edge weight (`0.25 * 0.5 = 0.125`) rather than zero. Multiplying the
whole weight by confidence collapsed every edge to exactly `0.0` for any paper
outside clinical-trial phrasing, which silently reduced the ranking to
unweighted PageRank.

`base_weight` (`alpha * N_score + beta * journal_score`) is still reported on
each edge as the unconfidenced score.

---

## Foundational Paper Ranking

Papers are ranked using a combined score:

```
score = 0.5 * PageRank + 0.3 * year_score + 0.2 * evidence_score
```

Where:
- **PageRank** — Citation influence from NetworkX PageRank on weighted edges
- **Year score** — Older papers get higher scores (max bonus at 20+ years old)
- **Evidence score** — `log1p(N_eff) / log1p(100000) * population_confidence`

---

## Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs at `http://localhost:5173` by default.

---

## Makefile Commands

```bash
make install         # Install Python dependencies
make run-api         # Start uvicorn dev server
make run-frontend    # Start frontend dev server
make run-dashboard   # Start Streamlit dashboard
make run-grobid      # Start GROBID via Docker
make run-neo4j       # Start Neo4j via Docker
make test            # Run all pytest tests
make format          # Format with black
make lint            # Lint with flake8
make demo            # Run demo script
```

---

## Testing

```bash
pytest
```

Run comprehensive API integration tests (requires mocked HTTP via respx):
```bash
pytest tests/test_api_comprehensive.py -v
```

Test coverage includes:
- Health endpoint
- Run creation with all query types (DOI, PMID, PMCID, title, URL)
- Input validation (invalid IDs, empty values, type checking)
- Parameter clamping (depth and max papers bounds)
- Run status polling
- Graph data export
- JSON / CSV / Markdown export
- Full pipeline end-to-end with mocked providers
- Forward citation traversal

---

## Configuration Reference

All configuration is in `src/citegraph/config.py` via `pydantic-settings`. Override via `.env` file or environment variables.

| Setting | Env Variable | Default | Description |
|---------|-------------|---------|-------------|
| `app_env` | `APP_ENV` | `development` | Runtime environment |
| `log_level` | `LOG_LEVEL` | `INFO` | Logging verbosity |
| `api_key` | `API_KEY` | `None` | Shared secret required in the `X-API-Key` header; unset leaves the API open |
| `cors_origins` | `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed browser origins (comma-separated) |
| `openalex_email` | `OPENALEX_EMAIL` | `None` | Email for OpenAlex polite pool |
| `enable_openalex` | `ENABLE_OPENALEX` | `True` | Enable OpenAlex provider |
| `enable_crossref` | `ENABLE_CROSSREF` | `True` | Enable Crossref provider |
| `enable_europe_pmc` | `ENABLE_EUROPE_PMC` | `True` | Enable Europe PMC provider |
| `enable_grobid` | `ENABLE_GROBID` | `True` | Enable GROBID PDF parsing |
| `grobid_url` | `GROBID_URL` | `http://localhost:8070` | GROBID server URL |
| `data_dir` | `DATA_DIR` | `./data` | Data storage directory |
| `sqlite_path` | `SQLITE_PATH` | `./data/cache/citegraph.sqlite` | SQLite database file |
| `enable_neo4j` | `ENABLE_NEO4J` | `False` | Enable Neo4j graph DB |
| `default_backward_depth` | `DEFAULT_BACKWARD_DEPTH` | `2` | Default backward traversal depth |
| `default_forward_depth` | `DEFAULT_FORWARD_DEPTH` | `1` | Default forward traversal depth |
| `default_max_total_papers` | `DEFAULT_MAX_TOTAL_PAPERS` | `100` | Max papers per run |
| `weight_alpha` | `WEIGHT_ALPHA` | `0.75` | Population evidence weight |
| `weight_beta` | `WEIGHT_BETA` | `0.25` | Journal score weight |
| `n_reference` | `N_REFERENCE` | `100000` | N-score normalization reference |
| `enable_pubmed` | `ENABLE_PUBMED` | `False` | Reserved; no PubMed provider is wired up |
| `enable_semantic_scholar` | `ENABLE_SEMANTIC_SCHOLAR` | `False` | Reserved; no Semantic Scholar provider is wired up |
| `enable_clinical_trials` | `ENABLE_CLINICAL_TRIALS` | `False` | Reserved; no ClinicalTrials provider is wired up |
| `enable_unpaywall` | `ENABLE_UNPAYWALL` | `False` | Reserved; no Unpaywall provider is wired up |
| `semantic_scholar_api_key` | `SEMANTIC_SCHOLAR_API_KEY` | `None` | Reserved for a future provider |
| `ncbi_api_key` | `NCBI_API_KEY` | `None` | Reserved for a future provider |
| `neo4j_uri` | `NEO4J_URI` | `bolt://localhost:7687` | Neo4j endpoint (optional profile) |
| `neo4j_user` | `NEO4J_USER` | `neo4j` | Neo4j user (optional profile) |
| `neo4j_password` | `NEO4J_PASSWORD` | `None` | Required before enabling the neo4j profile; no default |

---

## Docker

### One-command full project run

Optional but recommended: set an OpenAlex polite-pool email before starting the stack.

```bash
# macOS/Linux
export OPENALEX_EMAIL=your_email@example.com

# Windows PowerShell
$env:OPENALEX_EMAIL="your_email@example.com"
```

For a local demo/development run, the full app can then be started with one Docker Compose command:

```bash
docker compose up --build
```

This starts:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Backend health check: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
- GROBID service: `http://localhost:8070`

This Compose setup runs the frontend Vite dev server and the FastAPI development service. It is intended for local demos, not production hosting.

Application data is stored in a Docker named volume (`citegraph_data`) so the demo does not create root-owned files in the local `data/` directory on Linux.

To stop everything:

```bash
docker compose down
```

### Backend-only Docker run

```bash
docker build -t citegraph-api .
docker run -p 8000:8000 citegraph-api
```

### Optional Neo4j profile

```bash
docker compose --profile neo4j up --build
```

---

## Security Notes

The API performs outbound HTTP requests on behalf of the caller, so a public
deployment needs two settings configured:

- **`API_KEY`** — unset by default so the local demo and `docker compose up`
  work with no configuration. Set it before exposing the service to the
  internet; every `/api` route then requires an `X-API-Key` header. `/health`
  stays open for uptime probes.
- **`CORS_ORIGINS`** — defaults to the local Vite dev server. Set it to the
  deployed frontend origin (for example a Cloudflare Pages URL). A wildcard is
  deliberately not used: it would let any page a developer visits drive their
  locally running instance and read the responses.

URL inputs (`query_type: "url"`) are fetched server-side. Hosts resolving to
private, loopback, link-local, or reserved addresses are refused, and each
redirect hop is re-validated, so the endpoint cannot be used to reach internal
services. The optional Neo4j profile has no default password and binds only to
loopback; set `NEO4J_PASSWORD` before enabling it.

---
## Demo

### Frontend
- **Live:** https://citegraph-nlp.pages.dev
- **Local:** `http://localhost:5173`

### API
- **Live docs:** https://citegraph-api.penora.us/docs
- **Local docs:** `http://localhost:8000/docs`

### Health Check
- https://citegraph-api.penora.us/health

### Sample DOI
- `10.1038/s41467-021-23458-5`

### Paper Used in Demo
- **Title:** [Nature Communications](https://www.nature.com/articles/s41467-021-23458-5)

### Demo Video
- [docs/submission/NLP_Project_Demo.mp4](https://github.com/Ahad690/CiteGraph-NLP/blob/main/docs/submission/NLP_Project_Demo.mp4)

> The earlier result-snapshot link pointed at a run id stored on the previous
> server, which was decommissioned; run ids are not portable between hosts, so
> generate a fresh run to share a snapshot.

---


## Limitations

- Citation coverage depends on public metadata APIs (OpenAlex, Crossref, Europe PMC)
- Some papers may have incomplete references
- Population extraction is regex-based and may miss complex formulations
- PDF parsing requires GROBID and works best with well-structured PDFs
- Foundational paper detection is probabilistic (PageRank + heuristics), not definitive
- Best suited for biomedical and clinical research papers

---

## Ethical & Legal Notes

- Do not scrape or process paywalled content without permission
- Treat rankings as exploratory research aids, not final academic judgments
- Review extracted evidence manually before use in serious research

---

## License & Disclaimer

CiteGraph-NLP provides exploratory research analysis. Results depend on metadata availability, extraction quality, and citation database coverage. The system identifies **probable foundational papers**, not guaranteed original sources. All results should be reviewed by domain experts.
