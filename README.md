# CiteGraph-NLP

**Confidence-Aware Citation Lineage and Study-Scale Knowledge Graph System**

CiteGraph-NLP is an NLP + Knowledge Graph prototype for analyzing scientific papers, tracing citation lineage, extracting study population evidence, and ranking **probable foundational papers** using confidence-aware graph analytics.

The project is designed as a realistic research prototype. It does **not** claim to find the absolute original paper or perfectly extract every sample size. Instead, it makes uncertainty visible using confidence scores, provenance, and ambiguity labels.

---

## What It Does

CiteGraph-NLP starts from a research paper identifier or file and builds a structured citation analysis workflow.

Supported inputs:

- DOI
- PMID
- PMCID
- Paper title
- User-provided PDF

Core capabilities:

- Resolve paper metadata using scholarly APIs
- Retrieve backward references and forward citations where available
- Parse full text or abstracts when accessible
- Extract population-size candidates such as `N = 10,000`, `8,500 randomized patients`, or `25,000 participants`
- Classify population evidence into semantic types such as `TOTAL_RANDOMIZED`, `TOTAL_ANALYZED`, `TOTAL_ENROLLED`, and `ARM_SIZE`
- Assign confidence scores to extracted evidence
- Build a study-aware citation Knowledge Graph
- Calculate evidence-weighted citation edges
- Rank probable foundational papers
- Export results as JSON, CSV, GraphML, and Markdown

---

## Important Scientific Positioning

CiteGraph-NLP is confidence-aware by design.

It should say:

- **Probable foundational papers**
- **Confidence-aware extraction**
- **Citation lineage estimate**
- **Evidence-weighted ranking**
- **Metadata coverage may be incomplete**

It should not say:

- Absolute original paper
- Guaranteed parent paper
- Perfect extraction
- Definitive evidence ranking

---

## Tech Stack

### Backend

- Python 3.11+
- FastAPI
- Pydantic v2
- HTTPX
- NetworkX
- Pandas / NumPy
- SQLite for local cache
- Optional Neo4j
- Optional GROBID for PDF parsing

### Dashboard

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- React Router
- TanStack Query
- Lucide React
- Cytoscape.js or React Force Graph

---

## Recommended Project Structure

```text
citegraph-nlp/
├── README.md
├── PRD.md
├── .gitignore
├── .env.example
├── requirements.txt
├── pyproject.toml
├── docker-compose.yml
├── Makefile
│
├── src/
│   └── citegraph/
│       ├── api/
│       ├── models/
│       ├── input/
│       ├── providers/
│       ├── metadata/
│       ├── parsing/
│       ├── nlp/
│       ├── citations/
│       ├── graph/
│       ├── storage/
│       ├── pipeline/
│       ├── evaluation/
│       └── utils/
│
├── dashboard/
│   ├── app.py
│   └── pages/
│
├── frontend/
│   └── citegraph-dashboard/
│
├── scripts/
├── tests/
├── data/
│   ├── uploads/
│   ├── cache/
│   ├── parsed/
│   ├── exports/
│   └── samples/
│
└── docs/
```

---

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/citegraph-nlp.git
cd citegraph-nlp
```

### 2. Create a Python Virtual Environment

```bash
python -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 3. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create Environment File

```bash
cp .env.example .env
```

Example `.env` values:

```env
APP_ENV=development
LOG_LEVEL=INFO

OPENALEX_EMAIL=your_email@example.com
SEMANTIC_SCHOLAR_API_KEY=
NCBI_API_KEY=

ENABLE_OPENALEX=true
ENABLE_CROSSREF=true
ENABLE_EUROPE_PMC=true
ENABLE_PUBMED=false
ENABLE_SEMANTIC_SCHOLAR=false
ENABLE_GROBID=false
ENABLE_NEO4J=false

DATA_DIR=./data
SQLITE_PATH=./data/cache/citegraph.sqlite

DEFAULT_BACKWARD_DEPTH=2
DEFAULT_FORWARD_DEPTH=1
DEFAULT_MAX_TOTAL_PAPERS=100

WEIGHT_ALPHA=0.75
WEIGHT_BETA=0.25
N_REFERENCE=100000
```

---

## Optional Services

### Run GROBID

GROBID is used for scholarly PDF parsing.

```bash
docker compose up -d grobid
```

GROBID should be available at:

```text
http://localhost:8070
```

### Run Neo4j

Neo4j is optional. NetworkX is the default graph engine for the MVP.

```bash
docker compose --profile neo4j up -d neo4j
```

Neo4j browser:

```text
http://localhost:7474
```

---

## Run the Backend API

```bash
uvicorn citegraph.api.main:app --reload
```

Backend URL:

```text
http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/health
```

---

## Run the Dashboard

If using the Streamlit MVP dashboard:

```bash
streamlit run dashboard/app.py
```

If using the React/Vite frontend:

```bash
cd frontend/citegraph-dashboard
npm install
npm run dev
```

Default Vite URL:

```text
http://localhost:5173
```

---

## API Overview

### Health Check

```http
GET /health
```

### Start a New Analysis Run

```http
POST /api/runs
```

Example request:

```json
{
  "query_type": "doi",
  "value": "10.xxxx/example",
  "backward_depth": 2,
  "forward_depth": 1,
  "max_total_papers": 100,
  "use_pdf_parsing": false,
  "use_semantic_scholar": false
}
```

### Get Run Result

```http
GET /api/runs/{run_id}
```

### Export Results

```http
GET /api/runs/{run_id}/export/json
GET /api/runs/{run_id}/export/csv
GET /api/runs/{run_id}/export/graphml
GET /api/runs/{run_id}/export/markdown
```

---

## Data Model Summary

Main entities:

- `Paper`
- `Study`
- `PopulationCandidate`
- `PopulationResolution`
- `CitationEdge`
- `RunResult`

Main graph relationships:

- `PAPER_CITES_PAPER`
- `PAPER_REPORTS_STUDY`
- `STUDY_HAS_POPULATION_OBSERVATION`
- `PAPER_PUBLISHED_IN_JOURNAL`

---

## Population Extraction

The system extracts candidate sample-size mentions and assigns semantic labels.

Example text:

```text
A total of 8,500 patients were randomized, with 4,250 assigned to treatment and 4,250 assigned to control.
```

Expected result:

```json
{
  "n_eff": 8500,
  "semantic_type": "TOTAL_RANDOMIZED",
  "confidence": 0.86,
  "status": "resolved",
  "evidence": "A total of 8,500 patients were randomized...",
  "section": "Methods"
}
```

Supported semantic types:

```text
TOTAL_RANDOMIZED
TOTAL_ANALYZED
TOTAL_ENROLLED
ARM_SIZE
SCREENED
COMPLETERS
EVENT_COUNT
FOLLOWUP_COUNT
SAMPLE_SIZE_GENERIC
UNKNOWN_NUMERIC
```

---

## Edge Weighting

Citation edges are weighted using normalized population evidence, journal/source metrics, and confidence.

```text
base_weight = alpha * N_score + beta * journal_score
final_weight = base_weight * confidence_score
```

Defaults:

```text
alpha = 0.75
beta = 0.25
N_reference = 100000
```

Population score:

```text
N_score = log1p(N_eff) / log1p(N_reference)
```

---

## Testing

Run all tests:

```bash
pytest -q
```

Recommended tests:

- DOI normalization
- Metadata merging
- Population regex extraction
- False positive filtering
- Semantic type classification
- Population resolver
- Citation traversal limits
- Graph construction
- Edge weighting
- Export generation

---

## Example Demo Flow

1. Enter a DOI.
2. Resolve metadata from OpenAlex and Crossref.
3. Retrieve references.
4. Extract population evidence from abstract or parsed text.
5. Build a citation graph.
6. Rank probable foundational papers.
7. Export the analysis report.

---

## Limitations

CiteGraph-NLP is a prototype and has important limitations:

- Citation coverage depends on public metadata APIs.
- Some papers may not have complete references available.
- Population extraction may be ambiguous.
- PDF parsing can fail for scanned or poorly structured PDFs.
- Journal metrics may be missing or incomplete.
- Foundational paper detection is probabilistic, not definitive.
- The prototype works best for biomedical and clinical papers.

---

## Ethical and Legal Notes

- Do not scrape paywalled full text without permission.
- Do not upload or process documents you are not allowed to use.
- Treat rankings as exploratory research aids, not final academic judgments.
- Always review extracted evidence manually before using it in serious research.

---

## Development Commands

```bash
# Install dependencies
make install

# Run backend API
make run-api

# Run Streamlit dashboard
make run-dashboard

# Run GROBID
make run-grobid

# Run tests
make test
```

---

## Roadmap

Planned improvements:

- PubMed and Europe PMC provider integration
- Semantic Scholar enrichment
- ClinicalTrials.gov validation
- Neo4j persistence
- Better table extraction
- Manual review interface for ambiguous population values
- Batch seed paper ingestion
- Community detection and centrality analytics
- Cypher export
- Full React dashboard

---

## Academic Disclaimer

CiteGraph-NLP provides exploratory research analysis. Results depend on metadata availability, extraction quality, and citation database coverage. The system identifies **probable foundational papers**, not guaranteed original sources. All results should be reviewed by domain experts.
