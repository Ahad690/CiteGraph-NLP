# CiteGraph-NLP User Guide

## How to Set Up, Run, and Use the Application

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [Starting the Application](#4-starting-the-application)
5. [Running Your First Analysis](#5-running-your-first-analysis)
6. [Understanding the Dashboard](#6-understanding-the-dashboard)
7. [Exploring the Demo](#7-exploring-the-demo)
8. [Export Options](#8-export-options)
9. [API Reference](#9-api-reference)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

| Requirement | Version | Check Command |
|------------|---------|--------------|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | any | `git --version` |

**Optional** (not needed for basic testing):
- Docker (for GROBID PDF parsing or Neo4j graph storage)

---

## 2. Installation

### Clone the repository

```bash
git clone https://github.com/Ahad690/CiteGraph-NLP.git
cd CiteGraph-NLP
```

### Install backend dependencies

```bash
# Option A: Using Make
make install

# Option B: Manual
pip install -r requirements.txt
```

### Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### Download spaCy language model (for sentence splitting)

```bash
python -m spacy download en_core_web_sm
```

---

## 3. Configuration

### Create your environment file

```bash
cp .env.example .env
```

### Minimum configuration (works out of the box)

The defaults work for basic testing. The `.env.example` file contains sensible defaults:

```env
APP_ENV=development
LOG_LEVEL=INFO

# These providers work without API keys
ENABLE_OPENALEX=true
ENABLE_CROSSREF=true
ENABLE_EUROPE_PMC=true

# These are disabled by default (need API keys or Docker)
ENABLE_PUBMED=false
ENABLE_SEMANTIC_SCHOLAR=false
ENABLE_GROBID=false
ENABLE_NEO4J=false

# Storage
DATA_DIR=./data
SQLITE_PATH=./data/cache/citegraph.sqlite

# Analysis defaults
DEFAULT_BACKWARD_DEPTH=2
DEFAULT_FORWARD_DEPTH=1
DEFAULT_MAX_TOTAL_PAPERS=100
```

### Optional: Better rate limits

If you have an email address to share with OpenAlex (recommended for faster API responses):

```env
OPENALEX_EMAIL=your.email@university.edu
```

---

## 4. Starting the Application

You need **two terminals** — one for the backend, one for the frontend.

### Terminal 1: Start the backend

```bash
# Option A: Using Make
make run-api

# Option B: Manual
uvicorn src.citegraph.api.main:app --reload
```

The backend starts at **http://localhost:8000**.

Verify it works:
```bash
curl http://localhost:8000/health
# Should return: {"status": "ok"}
```

### Terminal 2: Start the frontend

```bash
# Option A: Using Make
make run-frontend

# Option B: Manual
npm --prefix frontend run dev
```

The frontend starts at **http://localhost:5173**.

---

## 5. Running Your First Analysis

### Step 1: Open the app

Go to **http://localhost:5173** in your browser.

### Step 2: Navigate to the analysis form

Click **"Start Analysis"** on the landing page, or go directly to **http://localhost:5173/start**.

### Step 3: Choose an input type and enter a paper identifier

The form accepts five input types:

| Tab | What to Enter | Example |
|-----|--------------|---------|
| **DOI** | A Digital Object Identifier | `10.1056/NEJMoa2034577` |
| **PMID** | A PubMed numeric ID | `33882225` |
| **PMCID** | A PubMed Central ID | `PMC8012345` |
| **Title** | Exact or near-exact paper title | `Attention Is All You Need` |
| **URL** | A link to the paper on PubMed/DOI | `https://pubmed.ncbi.nlm.nih.gov/33882225/` |

**Recommended first test** — paste this DOI:
```
10.1056/NEJMoa2034577
```
This is a well-cited NEJM paper with clear population data, good citation coverage, and strong metadata across providers.

### Step 4: (Optional) Configure graph parameters

Click **"Configure Graph Parameters & Depth"** to adjust:

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| Backward Depth | 2 | How many citation hops to trace backward (references of references) |
| Forward Depth | 1 | How many citation hops to trace forward (papers that cite this one) |
| Max Papers | 100 | Hard limit on total papers collected |

For a quick test, the defaults are fine. For deeper exploration, increase backward depth to 3 (slower, more comprehensive).

### Step 5: Click "Analyze Citation Lineage"

The system will:
1. Resolve the paper's metadata from OpenAlex, Crossref, and Europe PMC
2. Traverse the citation graph backward and forward
3. Extract population sizes from each paper's abstract
4. Calculate evidence-weighted citation edges
5. Rank probable foundational papers

You'll be redirected to the dashboard. The page polls every 2 seconds until analysis completes.

**Expected time**: 30 seconds to 3 minutes depending on the number of papers and API response times.

---

## 6. Understanding the Dashboard

Once analysis completes, you have access to seven pages via the left sidebar:

### Overview (`/dashboard/:runId`)

A summary of everything found:
- **Stats**: Total papers, citation edges, resolved/ambiguous/missing extractions
- **Pipeline progress**: Which stages completed successfully
- **Warnings**: Any issues encountered (ambiguous extractions, missing metadata)
- **Quick links**: Navigate to any detail page

### Metadata (`/metadata/:runId`)

A searchable, sortable table of all papers found in the citation network.

- **Search** by title, author, journal, or DOI
- **Sort** by year, confidence, citation count, or title
- **Filter**: "Seed only" (just the input paper) or "Has DOI" (papers with DOIs)
- **Click any row** to open the detail drawer with full metadata, abstract, identifiers, and population evidence

Each paper shows:
- **Confidence badge**: Green (high), amber (medium), red (low), gray (missing)
- **Role badge**: Seed Paper, Foundational, or Cited

### Population Evidence (`/population/:runId`)

The NLP extraction results for every paper.

- **Status cards** at the top: counts of Resolved, Ambiguous, Low Confidence, and Missing extractions
- **Click a status card** to filter the table by that status
- **Click any row** to open the candidate drawer showing:
  - The selected N_eff value with confidence
  - All candidate values that were considered
  - The exact evidence sentence from the paper
  - Confidence meters for each candidate
  - The explanation of why a particular value was selected

**What the statuses mean:**
| Status | Meaning |
|--------|---------|
| Resolved | A single best population value was confidently selected |
| Ambiguous | Multiple plausible values exist with similar confidence |
| Low Confidence | A value was found but extraction confidence is below threshold |
| Missing | No population evidence could be extracted |

### Citation Graph (`/graph/:runId`)

An interactive visualization of the citation network.

**Visual encoding:**
- **Node size** = N_eff (larger circles = larger study populations)
- **Node color** = Confidence level (green = high, amber = medium, red = low, gray = missing)
- **Edge thickness** = Final citation weight (thicker = stronger evidence link)
- **Edge direction** = Citation direction (from citing paper to cited paper)
- **Purple ring** = Foundational candidate
- **Pulsing cyan ring** = Seed paper

**Interactions:**
| Action | Effect |
|--------|--------|
| Click + drag background | Pan the view |
| Scroll wheel | Zoom in/out |
| Click + drag a node | Move it |
| Hover a node | Show tooltip with title, year, N_eff, confidence |
| Click a node | Open paper detail drawer |
| Click an edge | Show edge weight breakdown |
| "Fit" button | Reset zoom to fit all nodes |
| "Reset" button | Re-layout the entire graph |

**Left panel filters:**
- Min edge confidence / weight sliders
- Year range filter
- "Only seed-connected" — hide disconnected papers
- "Hide missing population" — remove papers without extracted N_eff
- "High-confidence only" — show only ≥ 75% confidence papers
- "Highlight foundational" — toggle purple rings

### Citation Paths (`/paths/:runId`)

Ranked chains of papers from the seed to deeper papers.

Each path shows:
- **Path score** (combined edge weight × confidence × depth bonus)
- **Average confidence** across all edges in the chain
- **Path length** (number of hops)
- **Visual timeline** of papers with arrows and edge weights between them
- **Explanation** of why this path is significant

Use filters to:
- Set minimum path score
- Limit maximum path length
- Show only high-confidence paths
- Show only paths with population evidence

### Foundational Rankings (`/rankings/:runId`)

The final output — probable foundational papers ranked by score.

Each ranked paper shows:
- **Rank and score** (0–100%)
- **Score breakdown**: Influence (PageRank), age, evidence quality
- **Paper metadata**: Title, authors, year, journal
- **Population evidence**: N_eff and confidence
- **Explanation**: Why this paper was ranked here
- **Evidence summary**: Supporting data points

The top 3 papers have a gradient border highlight.

**Important disclaimer** (shown on the page): This ranking estimates probable foundational papers. It does not guarantee discovery of the absolute first or original paper.

### Export (`/export/:runId`)

Download your analysis results in four formats:

| Format | File Extension | Use Case |
|--------|---------------|----------|
| JSON | `.json` | Complete structured data for programmatic analysis |
| CSV | `.csv` | Paper tables for spreadsheets |
| GraphML | `.graphml` | Import into Gephi, Cytoscape, NetworkX |
| Markdown | `.md` | Readable report for documentation |

---

## 7. Exploring the Demo

If you want to see the full UI without running the backend:

Go to: **http://localhost:5173/dashboard/demo_run_001**

This loads a built-in demo dataset based on hepatitis C clinical research with:
- 8 papers (seed + 7 cited papers)
- 9 citation edges
- Population extractions ranging from n=24 to n=195,000,000
- 5 ranked foundational papers
- 4 ranked citation paths

All dashboard pages work with this demo data. You can explore every feature without waiting for a real analysis.

---

## 8. Export Options

### From the UI

Navigate to `/export/:runId` and click the download button for any format.

### From the API directly

```bash
# JSON
curl http://localhost:8000/api/runs/{run_id}/export/json -o report.json

# CSV
curl http://localhost:8000/api/runs/{run_id}/export/csv -o report.csv

# GraphML (for Gephi/Cytoscape)
curl http://localhost:8000/api/runs/{run_id}/export/graphml -o graph.graphml

# Markdown
curl http://localhost:8000/api/runs/{run_id}/export/markdown -o report.md
```

---

## 9. API Reference

### Health Check

```
GET /health
Response: { "status": "ok" }
```

### Start Analysis

```
POST /api/runs
Content-Type: application/json

{
  "query_type": "doi",           // "doi" | "pmid" | "pmcid" | "title" | "url"
  "value": "10.1056/NEJMoa2034577",
  "backward_depth": 2,           // optional, default 2
  "forward_depth": 1,            // optional, default 1
  "max_total_papers": 100        // optional, default 100
}

Response: { "run_id": "abc123", "status": "started" }
```

### Get Run Results

```
GET /api/runs/{run_id}

Response (while running): { "run_id": "...", "status": "running", ... }
Response (completed):     { "run_id": "...", "status": "completed", "papers": [...], ... }
Response (not found):     404
```

### Export

```
GET /api/runs/{run_id}/export/json
GET /api/runs/{run_id}/export/csv
GET /api/runs/{run_id}/export/graphml
GET /api/runs/{run_id}/export/markdown
```

---

## 10. Troubleshooting

### Backend won't start

```
ModuleNotFoundError: No module named 'citegraph'
```
Make sure you're in the project root and have installed dependencies: `pip install -r requirements.txt`

### Frontend shows "Failed to load run"

The backend is not running or the API URL is wrong. Check:
1. Is the backend running? `curl http://localhost:8000/health`
2. Is `VITE_API_BASE` set correctly? (defaults to `http://localhost:8000`)

### Analysis is stuck on "Running"

Check the backend terminal for errors. Common causes:
- Network timeout reaching OpenAlex/Crossref (retry usually works)
- Invalid paper identifier (DOI doesn't exist)
- Rate limiting from metadata providers (wait and retry)

### "No population evidence" for a paper

This means the regex patterns couldn't find population numbers in the abstract. This is expected for:
- Review papers (no original study population)
- Papers without abstracts in the metadata
- Papers using unusual phrasing for sample sizes

### spaCy model not found

```bash
python -m spacy download en_core_web_sm
```
If spaCy is unavailable, the system falls back to regex-based sentence splitting (less accurate but functional).

### Port already in use

```bash
# Find what's using port 8000
lsof -i :8000   # macOS/Linux
netstat -ano | findstr :8000   # Windows

# Use a different port
uvicorn src.citegraph.api.main:app --reload --port 8001
```

### Docker alternative (if Python setup is problematic)

```bash
docker build -t citegraph .
docker run -p 8000:8000 citegraph
```

---

## Quick Reference Card

| Action | How |
|--------|-----|
| Start backend | `make run-api` |
| Start frontend | `make run-frontend` |
| View demo | Go to `/dashboard/demo_run_001` |
| Run analysis | Go to `/start`, paste a DOI, click "Analyze" |
| View results | Dashboard auto-redirects when done |
| Export data | Go to `/export/:runId` |
| Check API health | `curl http://localhost:8000/health` |
| Run tests | `make test` |
