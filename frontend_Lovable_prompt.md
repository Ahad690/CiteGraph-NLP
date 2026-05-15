Build a complete, production-ready research analysis dashboard called **“CiteGraph-NLP”** — a premium AI-research dashboard for exploring citation lineage, population-size extraction, confidence-aware evidence ranking, and probable foundational papers.

This is a frontend dashboard only. It connects to an existing backend API.

IMPORTANT:
- Do NOT build a landing page.
- Do NOT build a public marketing page.
- Do NOT build the DOI / PMID / Paper Title ingestion form.
- Do NOT build the initial Search / Analyze page.
- Assume the analysis run has already been created elsewhere.
- This dashboard starts after a backend run already exists.
- The dashboard should focus only on viewing, exploring, visualizing, ranking, and exporting analysis results.

API Base URL:
`http://localhost:8000`

The dashboard should feel like a premium AI-powered research platform for academics, biomedical researchers, NLP students, and data scientists.

---

# PRODUCT CONTEXT

CiteGraph-NLP analyzes research papers and citation networks.

The backend:
- Resolves paper metadata
- Retrieves citation relationships
- Extracts population-size evidence
- Builds a citation graph
- Calculates confidence-aware citation weights
- Ranks probable foundational papers
- Produces exportable reports

The frontend dashboard must make these results easy to explore.

Important scientific wording:
- Use “probable foundational papers”
- Use “confidence-aware extraction”
- Use “citation lineage estimate”
- Use “evidence-weighted ranking”
- Use “ambiguous extraction”
- Use “metadata coverage may be incomplete”

Never say:
- “absolute original paper”
- “guaranteed parent paper”
- “perfect extraction”
- “fully accurate ranking”
- “definitive origin paper”

---

# DESIGN SYSTEM

## Brand

Name:
**CiteGraph-NLP**

Tagline:
**Confidence-aware citation lineage and study-scale research analysis**

Personality:
- Premium
- Scientific
- Intelligent
- Trustworthy
- Modern AI-research aesthetic
- Data-rich but not cluttered
- Professional, not playful

Logo concept:
- A connected-node graph icon
- Use deep indigo and cyan gradient
- Optional small “CG” monogram inside a rounded square

---

## Theme

Dark mode by default.

The app should look like a premium AI dashboard with subtle glassmorphism, soft gradients, data cards, glowing graph accents, and research-grade UI.

## Colors

Background:
- Main background: `#020617`
- Secondary background: `#0f172a`
- Surface: `rgba(15, 23, 42, 0.72)`
- Surface strong: `#111827`
- Surface hover: `#1e293b`

Borders:
- Default border: `rgba(148, 163, 184, 0.16)`
- Strong border: `rgba(148, 163, 184, 0.28)`

Text:
- Primary text: `#f8fafc`
- Secondary text: `#cbd5e1`
- Muted text: `#94a3b8`
- Disabled text: `#64748b`

Accent colors:
- Primary Indigo: `#4f46e5`
- Cyan: `#06b6d4`
- Purple: `#8b5cf6`
- Emerald success: `#10b981`
- Amber warning: `#f59e0b`
- Rose error: `#f43f5e`

Graph colors:
- Seed paper: Indigo/Cyan gradient
- High confidence: Emerald
- Medium confidence: Amber
- Low confidence: Rose
- Missing population: Slate gray
- Citation edge: Cyan with opacity
- Strong weighted edge: Bright cyan / indigo glow

---

## Typography

Use **Inter** or a similar modern sans-serif font.

Typography scale:
- Tiny labels: 11px, uppercase, letter-spacing 0.08em
- Small text: 12px
- Body text: 14px
- Normal UI text: 15px
- Section heading: 18px
- Page heading: 28px
- Hero/dashboard title: 34px

Use strong hierarchy:
- Page titles should feel bold and premium
- Metadata labels should use small uppercase text
- Numeric values in stat cards should be large and clear

---

## Spacing and Radius

Use an 8px spacing grid.

Border radius:
- Small controls: 10px
- Inputs: 12px
- Cards: 18px
- Panels: 22px
- Modals/drawers: 24px
- Main dashboard containers: 28px

Shadows:
- Cards should use subtle shadows
- Important cards may use glow shadows with indigo/cyan opacity
- Avoid harsh black shadows

Glassmorphism:
- Use backdrop blur on cards and sidebar
- Cards should have translucent dark backgrounds with subtle borders

---

# APP ROUTING

Create the following routes:

1. `/dashboard/:runId`
   - Main dashboard route using path parameter

2. `/dashboard?run_id=run_abc123`
   - Also support query parameter fallback

3. `/metadata/:runId`
   - Metadata view

4. `/population/:runId`
   - Population extraction view

5. `/graph/:runId`
   - Citation graph view

6. `/paths/:runId`
   - Citation paths view

7. `/rankings/:runId`
   - Foundational rankings view

8. `/export/:runId`
   - Export report view

If no run ID exists:
- Show a polished empty state
- Message: “No analysis run selected”
- Subtext: “Start an analysis first to view citation lineage results.”
- Include a soft button labeled “Start New Analysis”
- This button may link to `/`
- Do NOT build the landing or ingestion page

---

# RUN ID LOADING LOGIC

The dashboard must load the active run ID in this order:

1. Route parameter:
   `/dashboard/:runId`

2. Query parameter:
   `/dashboard?run_id=run_abc123`

3. localStorage:
   `active_run_id`

When a run ID is found:
- Store it in localStorage
- Call `GET /api/runs/{run_id}`
- Poll every 2 seconds while status is:
  - `pending`
  - `running`
  - `processing`
  - `started`

Stop polling when status is:
- `completed`
- `failed`

Show a run status card at all times.

---

# API CONTRACT

API Base URL:
`http://localhost:8000`

## Main Run Endpoint

```http
GET /api/runs/{run_id}
````

Expected response shape:

```json
{
  "run_id": "run_abc123",
  "status": "completed",
  "seed_paper_id": "paper_1",
  "papers": [
    {
      "paper_id": "paper_1",
      "title": "Example Paper",
      "doi": "10.xxxx/example",
      "pmid": "123456",
      "pmcid": "PMC123456",
      "authors": ["Author A", "Author B"],
      "year": 2022,
      "journal": "Example Journal",
      "abstract": "Example abstract",
      "metadata_confidence": 0.95,
      "citation_count": 125,
      "source_ids": {
        "openalex": "W123",
        "crossref": "10.xxxx/example"
      },
      "provenance": {}
    }
  ],
  "population_resolutions": [
    {
      "paper_id": "paper_1",
      "study_id": "study_1",
      "n_eff": 8500,
      "semantic_type": "TOTAL_RANDOMIZED",
      "confidence": 0.86,
      "status": "resolved",
      "evidence": "A total of 8,500 patients were randomized...",
      "section": "Methods",
      "explanation": "Selected because it is a randomized total found in the Methods section."
    }
  ],
  "population_candidates": [
    {
      "candidate_id": "cand_1",
      "paper_id": "paper_1",
      "value": 8500,
      "raw_text": "8,500 patients",
      "sentence": "A total of 8,500 patients were randomized...",
      "section": "Methods",
      "semantic_type": "TOTAL_RANDOMIZED",
      "confidence": 0.86,
      "extraction_method": "regex_context"
    }
  ],
  "citation_edges": [
    {
      "edge_id": "edge_1",
      "source_paper_id": "paper_1",
      "target_paper_id": "paper_2",
      "confidence": 0.95,
      "base_weight": 0.82,
      "final_weight": 0.78,
      "n_score": 0.84,
      "journal_score": 0.5,
      "providers": ["openalex"]
    }
  ],
  "ranked_foundational_papers": [
    {
      "paper_id": "paper_2",
      "rank": 1,
      "score": 0.91,
      "explanation": "Older paper with strong citation connectivity and high evidence weight.",
      "evidence_summary": "High weighted connectivity and strong population evidence."
    }
  ],
  "ranked_paths": [
    {
      "rank": 1,
      "path_score": 0.84,
      "paper_ids": ["paper_1", "paper_2", "paper_3"],
      "edge_weights": [0.78, 0.82],
      "average_confidence": 0.88,
      "path_length": 2,
      "explanation": "High-confidence path through older evidence-rich studies."
    }
  ],
  "warnings": [
    "Population extraction for 3 papers was ambiguous."
  ],
  "created_at": "2026-05-15T10:00:00Z"
}
```

## Export Endpoints

```http
GET /api/runs/{run_id}/export/json
GET /api/runs/{run_id}/export/csv
GET /api/runs/{run_id}/export/graphml
GET /api/runs/{run_id}/export/markdown
```

If an export endpoint is unavailable:

* Show disabled button
* Tooltip: “Export endpoint not available yet.”

---

# GLOBAL LAYOUT

Create a full dashboard shell.

## Layout Structure

* Fixed left sidebar
* Top header bar
* Main content area
* Optional right-side detail drawer
* Toast notification area

Desktop layout:

* Sidebar width: 280px
* Header height: 76px
* Main content padding: 28px

Tablet:

* Sidebar collapses to icon-only mode
* Main content remains full width

Mobile:

* Sidebar becomes drawer
* Tables become stacked cards
* Graph remains interactive but controls collapse into filter drawer

---

# SIDEBAR

The sidebar should be visually premium.

Style:

* Dark translucent glass panel
* Subtle border on the right
* Backdrop blur
* Indigo/cyan gradient accent at the top

Top section:

* Logo icon
* “CiteGraph-NLP”
* Small subtitle: “Research Graph Intelligence”

Run Status Card inside sidebar:

* Run ID
* Status badge
* Seed paper title, truncated
* Last updated time
* Small progress indicator

Navigation links:

1. Overview
2. Metadata
3. Population Extraction
4. Citation Graph
5. Citation Paths
6. Foundational Rankings
7. Export Report

Each nav item:

* Icon
* Label
* Active state with indigo/cyan gradient background
* Hover state with subtle border and glow

Bottom section:

* Button: “Start New Analysis”
* Link to `/`
* Do not implement the page
* Small limitations note:
  “Results are confidence-aware estimates.”

---

# TOP HEADER

The top header should show:

Left:

* Current page title
* Short description

Center:

* Optional global search field:
  Placeholder: “Search papers, authors, journals…”

Right:

* Run status badge
* Refresh button
* Export shortcut button
* Theme toggle, optional
* User/avatar placeholder, optional

Header should use:

* Sticky positioning
* Glass background
* Subtle bottom border

---

# PAGE 1 — OVERVIEW

Route:
`/dashboard/:runId`

Purpose:
Give a high-level summary of the current analysis.

## Overview Content

Top hero card:

* Title: “Citation Lineage Overview”
* Subtitle: “Confidence-aware map of papers, population evidence, and probable foundational studies.”
* Seed paper title
* Seed paper year and journal
* Status badge

Stat cards:

1. Papers Found
2. Citation Edges
3. Resolved Population Extractions
4. Ambiguous Extractions
5. Missing Population Data
6. Average Confidence
7. Top Foundational Score
8. Warnings

Stat card design:

* Glass card
* Icon
* Large number
* Small description
* Tiny trend or status text

Pipeline Progress Panel:
Show pipeline states:

* Metadata resolved
* Citations retrieved
* Population evidence extracted
* Knowledge graph built
* Rankings calculated

Each step:

* Icon
* Status: pending/running/completed/failed
* Small progress animation if running

Warnings Panel:

* Display backend warnings
* Use amber styling
* If no warnings, show success state

Quick Action Cards:

* View Metadata
* Inspect Population Evidence
* Open Citation Graph
* See Foundational Rankings
* Export Report

Each quick action card should have:

* Icon
* Description
* Hover glow
* Link to relevant route

---

# PAGE 2 — METADATA VIEW

Route:
`/metadata/:runId`

Purpose:
Show all papers found in the citation network.

## Metadata Table

Columns:

* Title
* Year
* Journal
* Authors
* DOI / PMID
* Citation Count
* Metadata Confidence
* Role

Role badges:

* Seed Paper
* Cited Paper
* Citing Paper
* Foundational Candidate

Seed paper:

* Highlight row
* Add “Seed Paper” badge
* Add subtle indigo/cyan border

Features:

* Search by title, author, journal, DOI
* Sort by year
* Sort by confidence
* Sort by citation count
* Filter by journal
* Filter by year range
* Filter by confidence level
* Filter: Has DOI
* Filter: Seed only

Row click:

* Open Paper Detail Drawer

## Paper Detail Drawer

Drawer width:

* 480px desktop
* Full width mobile

Show:

* Title
* Authors
* Year
* Journal
* DOI
* PMID
* PMCID
* Abstract
* Citation count
* Metadata confidence
* Source provider IDs
* Provenance block if available

Drawer actions:

* Copy DOI
* Copy citation metadata
* Open external DOI link if DOI exists

---

# PAGE 3 — POPULATION EXTRACTION

Route:
`/population/:runId`

Purpose:
Show confidence-aware population-size extraction results.

## Main Population Table

Columns:

* Paper Title
* N_eff
* Semantic Type
* Status
* Confidence
* Source Section
* Evidence Sentence
* Explanation

Semantic types:

* TOTAL_RANDOMIZED
* TOTAL_ANALYZED
* TOTAL_ENROLLED
* ARM_SIZE
* SCREENED
* COMPLETERS
* EVENT_COUNT
* FOLLOWUP_COUNT
* SAMPLE_SIZE_GENERIC
* UNKNOWN_NUMERIC

Status badges:

* Resolved: emerald
* Ambiguous: amber
* Missing: slate
* Low confidence: rose

Confidence badges:

* High: confidence >= 0.75
* Medium: 0.45 to 0.74
* Low: below 0.45

N_eff formatting:

* Use comma formatting
* Example: `8,500`
* If missing: `—`

Evidence sentence:

* Show as italic quoted text
* Truncate after 180 characters
* Expand on click

Row click:

* Open Candidate Detail Drawer

## Candidate Detail Drawer

Show all candidate population values for selected paper.

For each candidate:

* Candidate value
* Raw text
* Full sentence
* Section
* Semantic type
* Confidence
* Extraction method

Add visual confidence meter:

* Horizontal bar
* Color changes based on confidence

Add explanation box:

* Explain why selected N_eff was chosen
* If ambiguous, clearly show ambiguity warning

Important:

* Do not hide uncertain or missing results.
* Make uncertainty visible and understandable.

---

# PAGE 4 — CITATION GRAPH

Route:
`/graph/:runId`

Purpose:
Show interactive citation network visualization.

Use a graph visualization library:

* Prefer Cytoscape.js or React Force Graph
* If one is easier to implement, choose the most reliable option

## Graph Rules

Nodes:

* Represent papers
* Node label: short paper title
* Seed paper visually distinct
* Node size based on N_eff
* Node color based on population confidence
* Node ring/border for foundational candidates

Edges:

* Represent citation relationships
* Direction should be visible
* Edge thickness based on `final_weight`
* Edge opacity based on edge confidence
* Edge hover shows provider and weight details

## Node Styling

Seed paper:

* Larger node
* Indigo/cyan gradient
* Glowing ring
* Badge: “Seed”

High confidence:

* Emerald

Medium confidence:

* Amber

Low confidence:

* Rose

Missing:

* Slate gray

Foundational candidate:

* Purple/cyan outer ring

## Graph Interactions

Required:

* Zoom
* Pan
* Drag nodes
* Hover node tooltip
* Click node to open Paper Detail Drawer
* Click edge to open Edge Detail Panel
* Fit graph to screen button
* Reset layout button

Tooltip content:

* Title
* Year
* Journal
* N_eff
* Confidence
* Role

Edge detail panel:

* Source paper
* Target paper
* Final weight
* Base weight
* Edge confidence
* N_score
* Journal score
* Providers

## Graph Controls

Left or top control panel:

* Minimum confidence slider
* Minimum edge weight slider
* Year range filter
* Toggle: Show only seed-connected paths
* Toggle: Hide missing population data
* Toggle: Show only high-confidence extractions
* Toggle: Highlight foundational candidates
* Button: Reset filters

## Graph Legend

Show a floating legend:

* Node size = population size
* Edge thickness = weighted citation strength
* Node color = confidence
* Ring = foundational candidate
* Glow = seed paper

---

# PAGE 5 — CITATION PATHS

Route:
`/paths/:runId`

Purpose:
Show ranked citation paths from the seed paper toward older cited papers.

## Path Cards

Each ranked path card should show:

* Path rank
* Path score
* Average confidence
* Path length
* Explanation
* Papers in path
* Edge weights between papers

Visual style:

* Timeline layout
* Connected paper cards
* Direction from seed paper to older cited papers
* Edge labels between cards showing weight

Each paper in path:

* Title
* Year
* Journal
* N_eff if available
* Confidence badge
* Click opens Paper Detail Drawer

Add filters:

* Minimum path score
* Maximum path length
* Only high-confidence paths
* Only paths with population evidence

Empty state:

* “No ranked citation paths available”
* Explain that citation data may be incomplete

---

# PAGE 6 — FOUNDATIONAL RANKINGS

Route:
`/rankings/:runId`

Purpose:
Show top probable foundational papers.

## Ranking Header

Title:
“Top Probable Foundational Papers”

Subtitle:
“These papers are ranked using citation position, graph connectivity, population evidence, source metrics, and confidence scores.”

Add caution panel:
“This ranking estimates probable foundational papers. It does not guarantee discovery of the absolute first or original paper.”

## Ranking Cards

Use premium ranking cards, not a plain table.

Each card should show:

* Rank number
* Title
* Year
* Journal
* Authors
* Score
* Explanation from backend
* Evidence summary
* N_eff if available
* Confidence badge
* Citation connectivity summary if available

Design:

* Rank #1 should be visually prominent
* Use gradient border for top 3
* Use small graph icon
* Use score meter/progress ring

Card interactions:

* Click opens Paper Detail Drawer
* Button: “View in Graph”
* Button: “Copy Explanation”

Filters:

* Minimum score
* Year range
* Has population evidence
* High confidence only

---

# PAGE 7 — EXPORT REPORT

Route:
`/export/:runId`

Purpose:
Allow user to download analysis outputs.

## Export Panel

Create four export cards:

1. JSON Report

* Endpoint: `GET /api/runs/{run_id}/export/json`
* Description: “Complete structured analysis result”

2. CSV Tables

* Endpoint: `GET /api/runs/{run_id}/export/csv`
* Description: “Metadata, population extraction, rankings, and paths”

3. GraphML

* Endpoint: `GET /api/runs/{run_id}/export/graphml`
* Description: “Graph format for Gephi, NetworkX, and graph tools”

4. Markdown Report

* Endpoint: `GET /api/runs/{run_id}/export/markdown`
* Description: “Readable report for documentation or submission”

Each card:

* Icon
* Format name
* Description
* File type badge
* Download button

If export fails:

* Show toast error
* Keep page stable

If endpoint unavailable:

* Disable button
* Tooltip: “Export endpoint not available yet.”

## Report Preview

Show a preview card:

* Seed paper summary
* Number of papers
* Number of edges
* Number of resolved population values
* Top foundational paper
* Warnings count
* Limitations note

Limitations note:
“Citation coverage depends on available public metadata. Population extraction is confidence-aware and may be ambiguous.”

---

# GLOBAL COMPONENTS

Create reusable components:

1. `AppShell`
2. `Sidebar`
3. `TopHeader`
4. `RunStatusCard`
5. `OverviewStats`
6. `PipelineProgress`
7. `WarningPanel`
8. `MetadataTable`
9. `PopulationTable`
10. `CandidateDrawer`
11. `PaperDetailDrawer`
12. `EdgeDetailPanel`
13. `ConfidenceBadge`
14. `StatusBadge`
15. `RoleBadge`
16. `CitationGraph`
17. `GraphLegend`
18. `GraphFilters`
19. `RankingCard`
20. `CitationPathTimeline`
21. `ExportPanel`
22. `LoadingSkeleton`
23. `ErrorState`
24. `EmptyState`
25. `ToastProvider`

---

# LOADING STATES

Use loading skeletons everywhere.

Skeletons required for:

* Overview stat cards
* Metadata table rows
* Population table rows
* Graph canvas
* Ranking cards
* Export cards

Run processing state:

* Show animated progress steps
* Show message:
  “Analysis is still running. Results will appear automatically.”

Failed state:

* Show polished error panel
* Include run ID
* Show retry button
* Show “Back to start” button linking to `/`

No data state:

* Use friendly empty states
* Avoid broken tables

---

# TOAST NOTIFICATIONS

Use toast notifications for:

* Run loaded
* Run completed
* Run failed
* Export started
* Export failed
* Export downloaded
* Copied DOI
* Copied explanation

Toast style:

* Bottom-right
* Glass surface
* Left color border
* Icon
* Auto-dismiss after 4 seconds

---

# RESPONSIVE BEHAVIOR

Desktop:

* Full sidebar
* Tables are full width
* Graph has side filters
* Drawers open on right

Laptop:

* Sidebar narrower
* Table columns remain visible
* Graph filters can collapse

Tablet:

* Sidebar collapses
* Tables become horizontally scrollable
* Graph filters move above graph

Mobile:

* Sidebar becomes slide-out menu
* Tables become stacked cards
* Drawers become full-screen sheets
* Graph controls collapse into a filter button
* Cards stack vertically

---

# ANIMATIONS

Use subtle, premium animations.

Required:

* Page transitions: fade + slight upward motion
* Card hover: subtle lift and border glow
* Buttons: scale(0.98) on press
* Sidebar nav active indicator: smooth transition
* Drawers: slide in from right
* Modals/sheets: fade + scale
* Graph panel: fade in after layout
* Loading skeleton shimmer
* Toast slide in/out

Timing:

* Fast UI transitions: 150ms
* Page transitions: 220ms
* Drawer transitions: 250ms
* Toast transitions: 300ms

---

# TECHNICAL REQUIREMENTS

Use:

* React
* TypeScript
* Tailwind CSS
* React Router
* React Query / TanStack Query
* Lucide React icons
* Cytoscape.js or React Force Graph
* Recharts if charts are needed
* shadcn/ui components if available

State:

* Use React Query for server state
* Use localStorage for active run ID
* Use local component state for filters and drawers
* Optional Zustand if needed for global UI state

File organization:

```text
src/
├── components/
│   ├── layout/
│   ├── dashboard/
│   ├── metadata/
│   ├── population/
│   ├── graph/
│   ├── rankings/
│   ├── paths/
│   ├── export/
│   └── ui/
├── lib/
│   ├── api.ts
│   ├── utils.ts
│   ├── formatters.ts
│   └── graph.ts
├── pages/
│   ├── OverviewPage.tsx
│   ├── MetadataPage.tsx
│   ├── PopulationPage.tsx
│   ├── CitationGraphPage.tsx
│   ├── CitationPathsPage.tsx
│   ├── RankingsPage.tsx
│   └── ExportPage.tsx
├── types/
│   └── api.ts
└── App.tsx
```

---

# API UTILITY REQUIREMENTS

Create `src/lib/api.ts`.

Functions:

* `getRun(runId: string)`
* `downloadExport(runId: string, format: "json" | "csv" | "graphml" | "markdown")`
* `getRunIdFromRouteOrStorage()`
* `saveActiveRunId(runId: string)`

Use proper error handling:

* Backend unavailable
* Run not found
* Export failed
* Malformed response

---

# TYPESCRIPT TYPES

Create `src/types/api.ts`.

Include interfaces for:

* `RunResult`
* `Paper`
* `PopulationResolution`
* `PopulationCandidate`
* `CitationEdge`
* `RankedFoundationalPaper`
* `RankedPath`
* `RunStatus`

Use union types for:

* Confidence levels
* Population statuses
* Semantic types
* Export formats

---

# FORMATTING HELPERS

Create helper functions:

* `formatNumber(value)`
* `formatConfidence(score)`
* `getConfidenceLevel(score)`
* `getConfidenceColor(score)`
* `truncateTitle(title, length)`
* `getPaperById(papers, paperId)`
* `getPopulationForPaper(paperId)`
* `getCandidatesForPaper(paperId)`
* `getEdgesForPaper(paperId)`
* `buildGraphElements(runResult)`
* `downloadBlob(response, filename)`

---

# GRAPH DATA MAPPING

Convert backend data to graph nodes and edges.

Node object:

```ts
{
  id: paper.paper_id,
  label: paper.title,
  year: paper.year,
  journal: paper.journal,
  nEff: population?.n_eff,
  confidence: population?.confidence,
  isSeed: paper.paper_id === seed_paper_id,
  isFoundationalCandidate: ranked_foundational_papers.some(...)
}
```

Edge object:

```ts
{
  id: edge.edge_id,
  source: edge.source_paper_id,
  target: edge.target_paper_id,
  weight: edge.final_weight,
  confidence: edge.confidence,
  providers: edge.providers
}
```

---

# DEVELOPMENT FALLBACK

If backend is unavailable in development mode:

* Show a clear warning banner:
  “Backend unavailable — displaying demo data.”
* Use mock demo data only for UI preview.
* Do not hide that it is demo data.

In production:

* Do not silently use mock data.

---

# ACCESSIBILITY

Requirements:

* Keyboard-accessible navigation
* Visible focus states
* Buttons must have aria-labels where needed
* Graph controls must be accessible
* Color should not be the only indicator of confidence/status
* Use tooltips and text labels for meaning

---

# IMPORTANT NOTES

1. The citation graph is the star of the dashboard. It should feel interactive, intelligent, and visually impressive.
2. The UI must make uncertainty visible instead of hiding it.
3. The system should never overclaim research certainty.
4. The seed paper should always be easy to identify.
5. Foundational rankings should look premium and explainable.
6. Population extraction should clearly show evidence sentences and confidence.
7. Use dense data layouts, but keep them readable.
8. Keep the entire app focused on post-ingestion analysis.
9. Do not build the landing page or ingestion form.
10. Make the dashboard demo-ready even if backend results are partially missing.

---

# FINAL GOAL

Create a polished, production-ready, Lovable-generated frontend dashboard for CiteGraph-NLP that connects to the backend at `http://localhost:8000`, loads an existing run by `run_id`, displays metadata, population extraction, citation graph visualization, citation paths, probable foundational paper rankings, and export options.

The final result should look like a premium AI research intelligence dashboard, not a basic CRUD admin panel.