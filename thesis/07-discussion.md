# Chapter 7: Discussion

## 7.1 Interpretation of Results

### 7.1.1 Extraction works better than the project expected; availability is the real ceiling

The headline extraction result, precision 0.917, recall 1.000, F1 0.957, is
better than a hand-written pattern system might be expected to achieve, and the
temptation is to attribute this to the patterns. The measurement in Section 6.3
argues otherwise. Before the abstract backfill, 28% of papers in a
representative graph could not be evaluated at all: there was no text to read.
Extraction accuracy on the papers that *had* text was never the binding
constraint; the availability of text was.

This reframes what limits the system. On a 40-paper graph, the improvement from
fixing the extraction logic (Section 5.5) raised coverage from 7 papers to 15;
adding a second abstract provider raised it from 15 to 20. Data plumbing
delivered as much as algorithmic work, and it is the cheaper of the two, one
additional API call per run.

The generalisable observation is that in a pipeline drawing on external
catalogues, coverage gaps in the upstream source present as *model* failures.
A paper with no abstract produces no extraction, which is indistinguishable in
the output from an extraction that failed. Without separating the two, effort
goes to the wrong place.

### 7.1.2 Semantic typing is the genuine weakness

Type accuracy of 6/10 is the weakest result, and the errors are not random. All
four are adjacent-category confusions, randomised versus enrolled versus
analysed, among quantities that are frequently numerically identical.
Distinguishing them requires reading the *role* the number plays in the study
design, which is a semantic judgement rather than a lexical one. Surface
patterns are the wrong instrument.

The impact on the system is bounded, because the weighting uses the value and
not the type. But the aspiration in the proposal, to classify evidence by study
role, is not achieved, and a supervised model trained on PICO annotations
[nye2018ebmnlp] is the natural route to it.

### 7.1.3 The confidence scores do not mean what they appear to

Section 6.4.4 is, in the authors' view, the most important negative result.
Mean confidence was 0.91 when the extracted value was correct and 0.90 when it
was wrong. The score does not discriminate.

This matters disproportionately because surfacing uncertainty is the system's
distinguishing claim. A user filtering for high-confidence extractions would
retain the false positive, a systematic review misread at confidence 0.90,
alongside the correct results. The confidence currently encodes *which pattern
matched*, a property of the system, not *how likely this match is to be right*,
a property of the world. Those are different quantities and the interface
presents the first as though it were the second.

Nothing in the architecture prevents fixing this. Confidence would need to be
calibrated against held-out labelled data, which requires a larger gold set
than twenty papers.

### 7.1.4 The system is I/O-bound, and that is a design conclusion

Graph analytics account for 2.5% of runtime; network calls account for 63%. Two
consequences follow for anyone building similar systems. The choice of graph
library is nearly irrelevant at this scale, and effort spent optimising
PageRank would be wasted. Conversely, HTTP-level engineering, connection
pooling, request batching, avoiding per-item lookups, produced the largest
single performance gain in the project: 93.3 s to 27.9 s, a 3.3× improvement
from reusing one pooled client rather than creating one per request.

## 7.2 Reflections on the Development Process

The defect catalogue in Chapter 5 supports a conclusion the authors did not
anticipate at the outset: **a passing test suite established very little about
whether this system was correct.**

Six defects reached a system with 102 passing tests. Four produced no error and
no visible symptom. The traversal defect discarded roughly half of every graph
while the suite passed, because the tests asserted that a run completed and
returned a structure of the right shape, not that the structure bore any
relation to the available literature.

The defects that are hardest to find share a signature: they *degrade* rather
than break. A graph with 19 nodes instead of 40 looks like a sparse literature.
A malformed API filter returning HTTP 200 with zero results looks like a paper
with no citing works. An edge weight of 0.0 silently rewritten to 1.0 by
Python's `or` still yields a ranking. In each case the system produced a
defensible-looking answer to the wrong question.

What surfaced them was not more testing but *measurement against known
quantities*: comparing the number of nodes retrieved against the number of
references the provider reported, comparing extracted populations against
hand-read abstracts, timing each stage. Notably, the evaluation plan that would
have caught most of these was specified in the project proposal from the start
and left unimplemented, the empty `evaluation/` directory was itself the
strongest early warning available, and nothing in the repository made its
emptiness visible.

## 7.3 Threats to Validity

### 7.3.1 Construct validity

**Sample size is a partial proxy for evidential weight.** Section 2.5 is explicit
that appraisal instruments treat size as one dimension among several
[higgins2011cochrane]. A large poorly-conducted trial outranks a small rigorous
one under this system's weighting. The system must not be presented as
appraising quality, and the generated reports state this.

**The ranking target is not operationally defined.** "Probable foundational
paper" has no agreed definition, so the ranking cannot be scored against a
ground truth. The weights (0.5 / 0.3 / 0.2) were set by judgement, and no
sensitivity analysis was performed.

### 7.3.2 Internal validity

**Single annotator.** The gold standard was labelled by one person who is also
an author of the system. Knowledge of how the extractor works may have
influenced label choices, particularly in ambiguous cases. No inter-annotator
agreement was measured. This is the most serious methodological weakness in
the evaluation.

**Confidence is uncalibrated.** Section 6.4.4.

**Duplicate-merge precision is unmeasured.** Merges are counted and survivors
checked, but no gold standard of known duplicate pairs exists, so a merge that
incorrectly collapsed two distinct papers would not be detected.

### 7.3.3 External validity

**Sample size.** Twenty papers, eleven positive. The confidence intervals,
accuracy [0.764, 0.991], value accuracy [0.623, 0.984], are wide and are
reported alongside every point estimate for this reason.

**Domain concentration.** Positives are biomedical, mostly COVID-era and
cardiology. Performance on other literatures is unmeasured.

**Temporal instability.** The evaluation queries live APIs. OpenAlex and
Crossref revise records continuously, so an exact rerun may differ. A frozen
corpus would be more reproducible and is proposed in Section 8.2.

### 7.3.4 Conclusion validity

**No comparative baseline.** The central question, does evidence-weighted
ranking outperform unweighted PageRank?, was **not tested**. No A/B comparison
was run and no human relevance judgements were collected. The AlphaFold-to-
Anfinsen result in Section 6.5 is a single favourable anecdote. This thesis
therefore demonstrates that evidence-weighted ranking *can be computed* and
*produces plausible output*, not that it is better. That is the most
significant unaddressed question in the work.

## 7.4 Divergence from the Project Proposal

The proposal specified capabilities the delivered system does not have. They
are listed here rather than omitted.

| Specified | Delivered | Consequence |
|-----------|-----------|-------------|
| GROBID full-text PDF parsing | Configuration flags only; no implementation | Extraction is abstract-only. Sample sizes stated only in Methods are unreachable. This is the largest functional shortfall. |
| Neo4j study-aware graph store | NetworkX in-memory | No practical consequence at 200 nodes; §6.6 supports the choice |
| Study-aware knowledge graph | One-to-one paper→study mapping, `dedupe_confidence` hardcoded to 0.8 | Papers reporting the same trial are counted as independent evidence |
| Streamlit dashboard | Not implemented; React SPA delivered instead | None, the React dashboard supersedes it |
| `EVENT_COUNT`, `UNKNOWN_NUMERIC` types | Defined in the model; no pattern emits either | Two documented categories can never appear |
| Journal quality term | Constant 0.5 | The β term is a uniform floor, not a signal |
| Evaluation plan (§13) | Implemented during thesis preparation | Reported in Chapter 6 |

The study-aware graph is the most conceptually significant omission. The
proposal's intent was that several papers reporting one trial, a protocol, a
primary results paper, a secondary analysis, collapse to one study node, so the
trial's evidence is counted once. The delivered system treats them as three
independent papers, which overstates the evidential weight of well-published
trials. The identity aliasing described in Section 4.4.2 solves the easier
adjacent problem, duplicate *records* of one paper, not multiple papers of one
study.

## 7.5 Known open issues

Issues present in the delivered system and not resolved:

1. **The deployed API is unauthenticated.** An optional API-key gate exists but
   is unset, because a public single-page application cannot hold a secret.
   Anyone can submit runs against the deployment.
2. **Run identifiers are not portable.** Run records live in the host's SQLite
   database, so a shared result link breaks if the backend moves.
3. **Confidence is uncalibrated** (§6.4.4).
4. **No rate limiting.** The system depends on public APIs and follows
   OpenAlex's polite-pool convention, but does not throttle its own callers.
5. **Runs at `max_total_papers = 200` take about 3.5 minutes**, exceeding
   NFR-1's 60-second target.

## 7.6 Ethical and legal considerations

All data is retrieved from public APIs under their published terms. The
OpenAlex polite-pool convention is honoured by sending a contact address. No
paywalled content is retrieved or redistributed, which is a consequence of the
abstract-only scope: the legal question that made full text difficult is the
same one that keeps the system within bounds.

Two risks deserve statement. First, **misplaced authority**: a ranked list
presented by software invites more confidence than a heuristic deserves. The
mitigations in Section 4.7, status labels, explicit reporting of absence, a
standing caution in generated reports, are partial, and Section 6.4.4 shows one
of them is weaker than it appears. Second, **entrenchment of visibility**: any
citation-based ranking amplifies already-visible work, and the age term here
does not correct for the systematic under-citation of research from
under-resourced institutions and non-English literatures.
