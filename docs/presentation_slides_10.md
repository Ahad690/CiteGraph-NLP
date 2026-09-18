# Slide 1 — Project Title & Team
## CiteGraph-NLP
**Confidence-Aware Citation Lineage and Study-Scale Knowledge Graph System**

**Team Members**
- M. Ahad Imran (F23607034)
- Syed Zain-ul-Abidin (F23607031)
- Hamza Abdul Karim (F23607046)
- M. Usman Nasir (F23607004)

---

# Slide 2 — Project Scope and Requirements
## Scope
- Input a seed paper (DOI, PMID, PMCID, title, URL).
- Build citation lineage (backward + forward traversal).
- Extract population evidence (`N_eff`) from paper text.
- Rank probable foundational papers using weighted graph analytics.

## Requirements
- Multi-provider metadata coverage (OpenAlex, Crossref, Europe PMC).
- Confidence-aware extraction and ambiguity handling.
- Usable dashboard for metadata, graph, paths, rankings, and export.
- Deployable stack: frontend + backend with reproducible setup.

---

# Slide 3 — Pipeline Overview
## End-to-End Pipeline
1. Input normalization
2. Metadata resolution (parallel providers)
3. Citation traversal (BFS, depth-limited)
4. Population extraction (regex + semantic typing)
5. Population resolution (`n_eff` selection)
6. Edge weighting and graph analytics
7. Output/export + visualization

## Core Output
- Probable foundational papers
- Ranked citation paths
- Confidence-aware population evidence

---

# Slide 4 — Pipeline Details
## Key Processing Logic
- **Metadata merge:** field-level precedence across providers.
- **Traversal control:** configurable depth and max paper cap.
- **Population resolver:** picks best candidate using confidence + semantic priority.
- **Weighting formula:**  
  `N_score = log1p(N_eff) / log1p(N_reference)`  
  `base_weight = alpha*N_score + beta*journal_score`  
  `final_weight = base_weight * pop_confidence * edge_confidence`

## Foundational Ranking
- Combined score:
  `0.5*PageRank + 0.3*year_score + 0.2*evidence_score`

---

# Slide 5 — Dataset(s)
## Data Sources
- **OpenAlex:** metadata, references, forward citations
- **Crossref:** DOI metadata, title search, references
- **Europe PMC:** biomedical metadata and ID resolution

## Input Dataset Nature
- Dynamic retrieval from public scholarly APIs (no fixed static dataset).
- Supports biomedical and clinical literature best.
- Optional local PDF parsing path for richer extraction.

---

# Slide 6 — Model(s) and Methods
## Methods Used
- **NLP Extraction:** pattern-based numeric extraction with semantic classes.
- **Confidence Scoring:** rule-based confidence + ambiguity status.
- **Graph Modeling:** NetworkX directed weighted graph.
- **Ranking Model:** weighted PageRank + temporal + evidence signals.

## Why This Choice
- Interpretable outputs
- Fast iteration for research prototype
- Confidence visibility over black-box scoring

---

# Slide 7 — Evaluations
## Technical Evaluation
- Unit and integration tests for:
  - Input validation and normalization
  - API run lifecycle
  - Citation retrieval/traversal
  - Ranking stability and export endpoints

## Functional Evaluation (Example Run)
- End-to-end run returns structured outputs:
  - papers
  - population resolutions
  - citation edges
  - ranked paths
  - foundational rankings

## Quality Signals Tracked
- Extraction status (`resolved`, `ambiguous`, `missing`)
- Confidence scores per candidate/resolution
- Graph/ranking consistency under fixed settings

---

# Slide 8 — Strengths and Limitations
## Strengths
- Confidence-aware design (not just raw extraction).
- Multi-source citation + metadata integration.
- Explainable ranking logic (formula-based).
- Full-stack implementation with deploy pipeline.

## Limitations
- Population extraction is regex-based; misses complex phrasing.
- Many papers have sparse abstracts, reducing extractable evidence.
- Citation coverage depends on external provider completeness.
- Rankings are probabilistic, not absolute ground truth.

---

# Slide 9 — Future Direction
## Next Improvements
- Add stronger extraction model (hybrid rules + ML/LLM-based IE).
- Expand to full-text parsing pipeline for Methods sections.
- Better disambiguation of trial-level entities across papers.
- Add benchmark suite against tools like Semantic Scholar/ResearchRabbit.
- Improve robustness under provider rate limits and network instability.

## Product Direction
- Better collaboration/export for research teams
- Explainability overlays in graph and path views

---

# Slide 10 — Running Demo with Code
## Local Demo Steps
```powershell
cd C:\Users\subha\Documents\PROJECTS\CiteGraph-NLP
.\start-local.ps1 -Install
```

## Manual Start (Alternative)
```powershell
# Backend
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="$PWD\src"
uvicorn citegraph.api.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

## Demo URL + Sample Input
- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- Sample DOI: `10.1038/s41467-021-23458-5`
