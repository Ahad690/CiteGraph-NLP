# Chapter 4 — System Design and Architecture

## 4.1 Architectural Overview

The system is a layered pipeline. A request enters at the API layer, passes
through nine processing stages, and produces a persisted result that is read
back by the dashboard and the export endpoints.

```
                    ┌─────────────────────────────────┐
   Browser ────────▶│  React SPA (Cloudflare Pages)   │
                    └────────────────┬────────────────┘
                                     │ HTTPS / JSON
                    ┌────────────────▼────────────────┐
                    │  FastAPI  ·  REST + background  │
                    │  jobs  ·  optional API-key gate │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │     Pipeline Orchestrator       │
                    └────────────────┬────────────────┘
        ┌──────────────┬─────────────┼─────────────┬──────────────┐
        ▼              ▼             ▼             ▼              ▼
   ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌─────────┐  ┌────────────┐
   │  Input  │  │ Metadata  │  │ Citation │  │   NLP   │  │   Graph    │
   │ Normal. │  │ Resolver  │  │ Traversal│  │ Extract │  │ Analytics  │
   └─────────┘  └─────┬─────┘  └────┬─────┘  └─────────┘  └────────────┘
                      │             │
                ┌─────▼─────────────▼─────┐
                │   Provider Layer        │
                │  OpenAlex · Crossref ·  │
                │  Europe PMC (pooled     │
                │  HTTP client)           │
                └─────────────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │   SQLite run persistence        │
                    └─────────────────────────────────┘
```

### 4.1.1 Design principles

**Separation of retrieval from interpretation.** The provider layer knows how
to talk to external APIs and nothing about population extraction or graph
analysis. This allowed the Europe PMC abstract backfill described in
Section 4.4.3 to be added as a pipeline stage without modifying either the
traversal or the extractor.

**Explicit uncertainty.** Every population resolution carries a confidence and
a status. Uncertainty is a first-class field in the data model rather than
something inferred from a missing value, because "no population found" and
"population found but ambiguous" are different states that a reader must be
able to distinguish.

**Bounded work.** Every stage operates under an explicit budget. The citation
graph is unbounded in principle, so traversal is limited by depth and by total
paper count, and path enumeration is limited by a cap on paths examined. A
stage that could run unboundedly is a stage that will eventually hang.

**Degradation rather than failure.** A provider that fails degrades the result
instead of aborting the run. A paper whose abstract cannot be retrieved still
appears as a node; its edges simply carry no evidential term.

## 4.2 Data Model

Five entities, defined as Pydantic models so that validation happens at
construction.

### 4.2.1 Paper

The canonical record of a work.

| Field | Type | Notes |
|-------|------|-------|
| `paper_id` | str | Canonical identifier; DOI preferred, then PMID, then OpenAlex ID |
| `doi`, `pmid`, `pmcid`, `openalex_id` | str? | All known identifiers, retained for aliasing |
| `title`, `authors`, `year`, `journal` | — | Bibliographic metadata |
| `abstract` | str? | Extraction input; may be backfilled from a secondary provider |
| `source_ids` | dict | Provider-specific identifiers |
| `metadata_confidence` | float | Higher when several providers agree |
| `provenance` | dict | Per-provider retrieval record |

The choice of a DOI-preferred `paper_id` is load-bearing. The same work
retrieved from OpenAlex and from Crossref must collapse to one node, and the
DOI is the identifier both share. Section 5.3 describes what happened before
this rule was applied consistently.

### 4.2.2 PopulationCandidate and PopulationResolution

A *candidate* is one extracted number with its context; a *resolution* is the
single value selected for a paper.

| PopulationCandidate | Notes |
|---------------------|-------|
| `value` | The extracted integer |
| `raw_text`, `sentence` | The matched span and its sentence, for audit |
| `semantic_type` | One of the categories in 4.2.3 |
| `section`, `start_char`, `end_char` | Provenance within the source text |
| `confidence` | Pattern weight plus a section bonus |

| PopulationResolution | Notes |
|----------------------|-------|
| `n_eff` | Selected effective population, or null |
| `semantic_type` | Type of the selected candidate |
| `confidence` | Confidence of the selected candidate |
| `status` | `resolved`, `ambiguous` or `missing` |
| `explanation` | Human-readable justification |

Retaining `sentence` for every candidate is what makes the extraction
auditable: a user who doubts a number can read the sentence it came from. The
gold-standard evaluation in Chapter 6 relies on the same property.

### 4.2.3 Semantic types

| Type | Meaning |
|------|---------|
| `TOTAL_RANDOMIZED` | Subjects randomised or assigned |
| `TOTAL_ANALYZED` | Subjects included in the analysis |
| `TOTAL_ENROLLED` | Subjects enrolled or recruited |
| `SAMPLE_SIZE_GENERIC` | An unqualified total |
| `ARM_SIZE` | Size of one arm or group |
| `SCREENED` | Subjects screened for eligibility |
| `COMPLETERS` | Subjects completing the protocol |
| `FOLLOWUP_COUNT` | Subjects followed up |
| `EVENT_COUNT` | Outcome event counts — *no pattern emits this* |
| `UNKNOWN_NUMERIC` | Unclassified — *no pattern emits this* |

The last two are defined in the model but no extraction pattern produces them.
They are listed here as specified-but-unimplemented rather than quietly omitted.

### 4.2.4 CitationEdge

| Field | Notes |
|-------|-------|
| `source_paper_id`, `target_paper_id` | Direction: source cites target |
| `providers` | Which APIs asserted this edge |
| `confidence` | Confidence in the edge itself |
| `n_score`, `journal_score` | Weight components |
| `base_weight`, `final_weight` | Unconfidenced and final weights |

Retaining the components rather than only the final weight means a user can see
*why* an edge is weighted as it is, and the edge-list export exposes all of them.

## 4.3 Metadata Resolution

### 4.3.1 Parallel query and merge

The resolver queries all enabled providers concurrently and merges the results.
Merging is field-level with per-field precedence rather than
whole-record: Crossref is preferred for title, year, authors and journal because
it carries publisher-deposited metadata; OpenAlex is preferred for abstracts
because it reconstructs them from an inverted index.

Concurrency here is genuine parallelism of I/O — three providers queried at once
rather than in sequence — and is the reason seed resolution costs under two
seconds rather than six.

### 4.3.2 Identifier canonicalisation

All identifiers pass through a canonicaliser that:

- reduces `https://doi.org/10.x/y` to `10.x/y` and lowercases it;
- reduces `https://pubmed.ncbi.nlm.nih.gov/12345678` to `12345678`;
- uppercases PMCIDs and OpenAlex work identifiers;
- trims publisher view segments (`/full`, `/pdf`, `/abstract`) that a greedy
  DOI match absorbs from an article URL.

Each of these rules exists because its absence caused an observed failure.
Section 5.7 documents the URL cases.

## 4.4 Citation Traversal

### 4.4.1 Level-synchronous breadth-first search

Traversal is breadth-first and **level-synchronous**: the complete frontier at
depth *d* is expanded before any node at depth *d+1*. This is not the natural
formulation — a simple queue-based BFS is shorter — but it is what makes
batching possible. Because the entire frontier's neighbours are known at once,
their metadata can be fetched in batches of fifty rather than one request per
paper. Section 5.3 quantifies the difference.

### 4.4.2 Identity aliasing

A single work is referred to by different identifiers by different providers:
OpenAlex returns `W2741809807`, Crossref returns `10.1016/j.jhin.2015.08.027`.
The traversal maintains an alias table mapping every identifier seen to one
canonical `paper_id`. Edges are recorded with raw provider identifiers and
rewritten through the alias table at commit time.

Two consequences follow, both load-bearing:

1. An edge is committed **only if both endpoints resolve**. An edge pointing at
   a paper that was never retrieved is dropped rather than emitted as a
   dangling reference. Section 6.5 measures the result: zero dangling edges.
2. Duplicate detection operates **before** the paper budget is consumed, so a
   merged duplicate never costs a graph slot. A run capped at 40 papers returns
   40 distinct papers, not 40 minus the duplicates.

### 4.4.3 Abstract backfill

Population evidence can only be extracted from text. Measurement showed 28% of
papers in a representative graph carry no abstract in OpenAlex, so a backfill
stage was added between traversal and extraction: papers lacking an abstract
are collected and queried against Europe PMC in a single OR-joined request.
Section 6.3 reports the recovery rate.

### 4.4.4 Budget allocation

Both directions compete for one budget of papers. A heavily cited paper would
otherwise consume the entire budget on citing works, starving the backward walk
that finds foundational papers — which is the system's purpose. The traversal
therefore reserves a share for each direction, defaulting to 65% backward and
35% forward, and releases a direction's unused reservation to the other when it
can no longer expand.

## 4.5 Edge Weighting

### 4.5.1 Formulation

Each edge is weighted by the evidence reported in the **target** paper — the
work being cited, since that is where the evidence being relied upon resides.

```
N_score       = log1p(N_eff) / log1p(N_reference)
evidence_term = α · N_score · pop_confidence
final_weight  = (evidence_term + β · journal_score) · edge_confidence
```

with α = 0.75, β = 0.25, N_reference = 100,000 and `journal_score` currently a
constant 0.5 (see 4.5.3).

The logarithm is deliberate. Sample sizes span several orders of magnitude,
from single-digit case series to six-figure cohorts, and a linear scale would
let one very large study dominate every path it appears on. On a log scale the
difference between 100 and 1,000 participants carries the same weight as that
between 1,000 and 10,000, which better matches how a reader treats the
difference.

### 4.5.2 Why confidence scales only the evidential term

Confidence multiplies the evidence term only; the journal term always applies.
This matters more than it appears. If confidence multiplied the whole weight,
then a paper with no extractable population — confidence 0.0 by definition —
would produce an edge weight of exactly zero. Every edge in a non-clinical
graph would be zero, and the weighted ranking would silently become unweighted.

This is not hypothetical. It was the delivered behaviour, and Section 5.6
describes how it was found and why it was invisible.

### 4.5.3 Acknowledged simplification

`journal_score` is a constant 0.5 for every paper. The proposal envisaged a
venue-quality term. It is not implemented, and the constant means the term
contributes a uniform 0.125 to every edge — a floor rather than a
discriminating signal. Section 7.4 lists this among the divergences from the
proposal.

## 4.6 Graph Analytics

### 4.6.1 Foundational paper ranking

```
score = 0.5 · PageRank + 0.3 · year_score + 0.2 · evidence_score
```

`year_score` rises with age, saturating at twenty years; `evidence_score` is the
normalised population score scaled by population confidence.

The age term is a deliberate inversion of the usual bibliometric bias. Citation
counts favour recent, highly visible work [waltman2016review]; this system is
looking for origins, so age is rewarded. The weights are not empirically tuned —
they were set by judgement and no sensitivity analysis was performed, which
Section 7.3 records as a limitation.

### 4.6.2 Citation path ranking

Paths from the seed are scored by mean edge weight, multiplied path confidence,
and a depth penalty of 1/√(length).

Path enumeration is the one component with combinatorial risk. A densely
interlinked graph contains an astronomical number of simple paths, and the
naive formulation — enumerate all simple paths to each node, score them, sort,
keep ten — is quadratic in a way that is easy to miss. Section 5.6 reports the
measurement and the redesign: a single depth-limited depth-first traversal
feeding a bounded heap, with a hard cap on paths examined.

## 4.7 Surfacing Uncertainty

A system that reports an extracted number without reporting its reliability
invites the reader to trust it more than the evidence warrants. Three mechanisms
address this.

**Status labels.** Every resolution is `resolved`, `ambiguous` or `missing`.
`ambiguous` means a competing candidate scored within 10% of the selected one
with a materially different value, which is a genuine signal that the abstract
is unclear rather than a system failure.

**Confidence propagation.** Confidence flows from pattern weight through
resolution to edge weight, so a low-confidence extraction produces a
correspondingly smaller evidential contribution.

**Explicit reporting of absence.** Run results carry warnings naming how many
abstracts were unavailable, how many were recovered from a secondary provider,
and how many duplicate records were merged. A sparse graph can therefore be
explained — few citations, or records merged, or lookups failed — rather than
leaving the user to guess.

The generated Markdown report states plainly when no population evidence was
found and what that implies for the weights, rather than presenting an
unweighted ranking as though it were evidence-weighted.

---
