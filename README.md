# CiteGraph-NLP

**Confidence-Aware Citation Lineage and Study-Scale Knowledge Graph System**

CiteGraph-NLP is an NLP + Knowledge Graph system for analyzing scientific papers, tracing citation lineages, extracting study population evidence, and ranking **probable foundational papers** using confidence-aware graph analytics.

The project is a research prototype that makes uncertainty visible using confidence scores, provenance tracking, and ambiguity labels.

## Group Members

- M. Ahad Imran (F23607034)
- Syed Zain-ul-Abidin (F23607031)
- Hamza Abdul Karim (F23607046)
- M. Usman Nasir (F23607004)

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
3. **Citation Traversal** — BFS-based backward (references) and forward (citations) traversal with configurable depth limits
4. **Population Extraction** — Regex-based extraction of sample sizes from abstracts/text with semantic classification
5. **Population Resolution** — Select best N_eff candidate per paper using confidence and type priority scoring
6. **Edge Weighting** — Weight citation edges by normalized population evidence + journal score + confidence
7. **Graph Analytics** — PageRank-based foundational paper ranking and citation path ranking
8. **Export** — Results available as JSON, CSV, Markdown report, and graph visualization data

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
| `EVENT_COUNT` | Event/outcome counts |
| `FOLLOWUP_COUNT` | Follow-up counts |
| `UNKNOWN_NUMERIC` | Unclassified numbers |

---

## Tech Stack

### Backend
- Python 3.11+
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
- TanStack Query, React Router
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
│       │   └── routes.py         # All API endpoints
│       ├── models/
│       │   ├── paper.py          # Paper, PaperQuery
│       │   ├── study.py          # Study
│       │   ├── population.py     # PopulationCandidate, PopulationResolution
│       │   ├── citation.py       # CitationEdge
│       │   └── run.py            # RunResult
│       ├── input/
│       │   └── normalizer.py     # InputNormalizer
│       ├── providers/
│       │   ├── base.py           # MetadataProvider protocol, ProviderResult
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
├── tests/
│   ├── conftest.py
│   ├── test_input_normalizer.py
│   ├── test_population_patterns.py
│   └── test_api_comprehensive.py
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
git clone https://github.com/your-username/citegraph-nlp.git
cd citegraph-nlp
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

#### JSON Export
```http
GET /api/runs/{run_id}/export/json
```
Returns the full `RunResult` as raw JSON.

#### CSV Export
```http
GET /api/runs/{run_id}/export/csv
```
Returns a CSV string with paper metadata and N_eff:
```json
{
  "csv": "paper_id,title,year,journal,n_eff\n..."
}
```

#### Markdown Report
```http
GET /api/runs/{run_id}/export/markdown
```
Returns a formatted markdown analysis report:
```json
{
  "report": "# CiteGraph-NLP Analysis Report\n..."
}
```

---

## Edge Weighting Formula

Citation edges are weighted using population evidence and confidence:

```
N_score = log1p(N_eff) / log1p(N_reference)
base_weight = alpha * N_score + beta * journal_score
final_weight = base_weight * pop_confidence * edge_confidence
```

Defaults: `alpha = 0.75`, `beta = 0.25`, `N_reference = 100000`

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

### Demo URL + Sample Input Frontend
- **Local:** `http://localhost:`
- **Live:** [https://citegraphnlp.web.app/](https://citegraphnlp.web.app/)

### API
- **Local docs:** `http://localhost:/docs`

### Health Check
- [https://hetznerapi.duckdns.org/citegraph/health](https://hetznerapi.duckdns.org/citegraph/health)

### Sample DOI
- `10.1038/s41467-021-23458-5`

### Paper Used in Demo
- **Title:** [Nature Communications](https://www.nature.com/articles/s41467-021-23458-5)

### Result Snapshot
- [https://citegraph-nlp1.web.app/export/2c9e2880-64c2-4511-906d-aa48a6cb40ff](https://citegraph-nlp1.web.app/export/2c9e2880-64c2-4511-906d-aa48a6cb40ff)


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
