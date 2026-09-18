# Chapter 5 (continued) — Dashboard and Interaction Design

The analysis pipeline produces a graph, a ranking and a set of confidence-scored
extractions. None of that is useful to a reader unless it can be interrogated.
This chapter describes the dashboard, and in particular how the uncertainty
described in Section 4.7 is represented in the interface.

## 5.11 Technology and Structure

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Framework | React 19 + TypeScript | Typed contracts against the API schema |
| Build | Vite | Fast rebuilds; static output deployable to a CDN |
| Routing | TanStack Router | File-based routes with typed parameters |
| Server state | TanStack Query | Polling, caching and retry for long-running runs |
| Styling | Tailwind CSS + shadcn/ui | Consistent primitives without a heavy component library |
| Graph rendering | Cytoscape.js | Handles a few hundred nodes interactively |

The application is a client-rendered single-page application deployed as static
files. It holds no secrets and performs no server-side rendering; every dynamic
value comes from the API. This is what allows it to be served from a content
delivery network with a catch-all rewrite to `index.html`.

### 5.11.1 Route structure

| Route | Purpose |
|-------|---------|
| `/` | Landing page |
| `/start` | Submit a paper; configure depth and graph size |
| `/dashboard/$runId` | Overview: summary counts, warnings, entry points |
| `/metadata/$runId` | Resolved bibliographic records with provenance |
| `/population/$runId` | Extracted populations with confidence and status |
| `/graph/$runId` | Interactive citation graph |
| `/rankings/$runId` | Ranked foundational papers |
| `/paths/$runId` | Ranked citation paths from the seed |
| `/export/$runId` | Downloads in five formats |

The separation of `population` from `rankings` is deliberate. The ranking is
the system's headline output, but the population evidence is what the ranking
*rests on*, and a reader who wants to judge the ranking must be able to inspect
the evidence independently of it.

## 5.12 The Submission Flow

`/start` accepts any of the five input types. Two decisions in this screen
proved important.

**Clamping is visible, not silent.** The graph-size control is a 10–200 slider
rather than a free-text field, so the API's clamping (Section 3.2.3) is
expressed in the interface rather than applied invisibly to an out-of-range
value the user typed. The default of 100 reflects the measurement in
Section 6.6.2: 100 papers completes in about 31 s, while 200 takes around
3.5 minutes.

**Runs are asynchronous and the wait is honest.** Submission returns a run
identifier immediately and the client polls. Because a run takes tens of
seconds, the interface reports the elapsed time rather than an indeterminate
spinner. An indeterminate spinner at 30 s reads as a hang.

## 5.13 Representing Uncertainty

This is where the interface does the work that distinguishes the system, and
where Section 6.4.4 shows it currently overstates its case.

### 5.13.1 Status before number

Every extracted population is displayed with its status — `resolved`,
`ambiguous` or `missing` — adjacent to the value, not in a tooltip or a detail
panel. The three states are visually distinct. A number presented without its
status invites the reader to treat an ambiguous extraction as a settled fact.

### 5.13.2 The supporting sentence is reachable

Selecting an extracted population reveals the sentence it came from. This is
the single most useful affordance in the interface: a reader who doubts a
number can verify it in one interaction, without leaving the application or
opening the source paper. It is possible only because the extractor retains
`sentence` on every candidate (Section 4.2.2).

### 5.13.3 Absence is reported, not implied

Run warnings appear on the dashboard overview rather than being logged
server-side and discarded. A graph with few nodes is accompanied by the reason:
how many abstracts were unavailable, how many were recovered from a secondary
provider, how many duplicate records were merged. Without this, a sparse graph
is ambiguous between "this paper has few citations" and "the system failed",
and a user cannot distinguish them.

### 5.13.4 An honest limitation of the current presentation

The interface presents confidence as a number and, by placing it beside the
extraction, implies it indicates reliability. Section 6.4.4 shows it does not:
mean confidence was 0.91 when the extracted value was correct and 0.90 when it
was wrong. A user filtering for high confidence would retain the errors.

This is a presentation problem as much as a modelling one. Until the score is
calibrated (Section 8.2.1), displaying it as a precise quantity overstates what
is known. A coarser presentation — or an explicit statement that the score
reflects which pattern matched rather than probability of correctness — would
be more truthful with the current model.

## 5.14 Graph Visualisation

The graph view renders nodes sized by extracted population and edges weighted by
the final edge weight, with the seed paper distinguished.

Three constraints shaped it.

**Bounded node count.** At most 200 nodes, which Cytoscape handles interactively.
A force-directed layout over an unbounded graph would neither render nor be
readable, which is a second reason for the traversal budget.

**Every link has both endpoints.** The renderer would silently drop an edge
whose endpoints are absent from the node set, so a graph with dangling edges
displays as *fewer edges than the data contains* with no error. The traversal
guarantee in Section 4.4.2 exists partly for this reason, and Section 6.5
verifies it: zero dangling edges across three runs.

**Weights are visible.** Edge thickness encodes the final weight. Before the
defect in Section 5.6 was found, every weight was zero and every edge rendered
identically — which, in retrospect, was an available visual signal that
something was wrong, and one nobody read as such.

## 5.15 Export Design

Five formats, each with a distinct audience.

| Format | Intended use |
|--------|--------------|
| JSON | Programmatic reuse; complete result |
| CSV (papers) | Spreadsheet triage: one row per paper with rank, degree, evidence |
| CSV (edges) | The graph as a relation, with every weight component |
| Markdown | A readable report for inclusion in notes or a literature review |
| GraphML | Import into Gephi, yEd or Cytoscape Desktop for further analysis |

Two exports exist because of things learned during evaluation. The **edge list**
was added because a paper list cannot express a graph, and any external analysis
of the weighting needs the components. **GraphML** was added because the
frontend already advertised it as a format although no endpoint existed — the
button returned 404.

The Markdown report states explicitly when no population evidence was found and
what that means for the weights, rather than presenting an effectively
unweighted ranking as though it were evidence-weighted. This is the same
honesty requirement as Section 5.13.3, applied to the artifact a reader is most
likely to circulate.

---
