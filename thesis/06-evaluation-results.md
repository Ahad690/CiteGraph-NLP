# Chapter 6: Evaluation and Results

All results in this chapter were produced by `scripts/run_evaluation.py`,
committed to the project repository. Appendix C gives the commands. The run
reported here was generated on 2026-09-18. Every figure can be recomputed by a
reader with network access; because the underlying scholarly APIs change over
time, exact reproduction is not guaranteed and this is discussed in
Section 7.3.

## 6.1 Gold Standard

### 6.1.1 Composition

Twenty papers, annotated by reading the abstract retrieved through the same
providers the pipeline uses.

| Design | Papers | Label |
|--------|-------:|-------|
| Randomised controlled trial | 5 | positive |
| Cohort study | 2 | positive |
| Case series | 2 | positive |
| Epidemiological analysis | 1 | positive |
| Modelling study | 1 | positive |
| **Positives** | **11** | |
| Review article | 3 | negative |
| Clinical guideline | 1 | negative |
| Virus characterisation | 2 | negative |
| Computational (no human subjects) | 2 | negative |
| **Negatives** | **9** | |

Positive sample sizes span 41 to 43,548 subjects, three orders of magnitude,
which is the range the logarithmic normalisation in Section 4.5 is designed
for.

### 6.1.2 Hard negatives

Four negatives contain large, salient numbers that are *not* study populations:

| Paper | Distractor | Why it is not the answer |
|-------|-----------|--------------------------|
| Zhou et al., *Nature* 2020 | "2,794 laboratory-confirmed infections" | Epidemic tally, not this study's sample |
| Wynants et al., *BMJ* 2020 | counts of reviewed studies | A systematic review; units are studies |
| Jumper et al., *Nature* 2021 | CASP14 target counts | Protein targets, not human subjects |
| Krizhevsky et al., *CACM* 2017 | "1.2 million high-resolution images" | Dataset size, not a study population |

A gold set of positives only cannot measure false positives. Since a confident
wrong number damages user trust more than a missing one, these cases are the
most informative in the set.

### 6.1.3 Annotation protocol and its limits

Each label records the effective population, the total human subjects the
primary analysis rests on, as stated in the abstract, with the supporting
sentence quoted verbatim so the label is auditable. Where no human study
population is stated, the label is negative and correct behaviour is to extract
nothing.

The limitations stated in Section 3.5.4 apply throughout: single annotator who
is also a system author, no inter-annotator agreement, twenty papers, abstracts
only, biomedical concentration.

## 6.2 Metadata Resolution

| Metric | Result |
|--------|--------|
| Papers attempted | 20 |
| Papers resolved | 20 (100%) |
| DOI exact match | 20 (100%) |
| Title present | 100% |
| Year present | 100% |
| Journal present | 100% |
| Authors present | 100% |
| Abstract present *after backfill* | 100% |
| Abstracts recovered from Europe PMC | 4 |

Resolution and field completeness are perfect on this set. Two qualifications
prevent over-reading it. The gold papers are well-indexed works from major
journals, which is the easy case; papers from small venues, older literature and
non-English publications are not represented. And the 100% abstract figure is
*post-backfill*: four of twenty papers (20%) had no abstract from the primary
resolution path and were recovered only because a second provider was queried.

## 6.3 Abstract Availability

Because extraction requires text, abstract availability bounds everything
downstream. Measured on a 40-paper traversal graph:

| Measure | Value |
|---------|------:|
| Papers in graph | 40 |
| No abstract in OpenAlex | 11 (28%) |
| Recoverable from Europe PMC | 11 of 11 (100%) |
| Recoverable from Crossref | 0 of 11 |
| Remaining without abstract after backfill | 0 |

This is the single most consequential measurement in the evaluation, and it
answers **RQ2**. Before the backfill, 28% of papers could not be evaluated at
all, not because extraction failed, but because there was nothing to read.
Every one of those abstracts existed in Europe PMC, and none in Crossref.

Two conclusions follow. First, a pipeline drawing abstracts from a single
provider inherits that provider's coverage gaps as an invisible ceiling on
recall. Second, the fix is cheap: an OR-joined Europe PMC query returned all
eleven abstracts in **one request in 0.81 s**, so the backfill costs one
additional API call per run.

## 6.4 Population Extraction

### 6.4.1 Detection

Detection is the binary decision: does this paper report a study population?

| | Predicted positive | Predicted negative |
|---|---:|---:|
| **Actually positive** | TP = 11 | FN = 0 |
| **Actually negative** | FP = 1 | TN = 8 |

| Metric | Value | 95% CI |
|--------|------:|--------|
| Precision | 0.917 | n/a |
| Recall | 1.000 | n/a |
| Specificity | 0.889 | n/a |
| F1 | 0.957 | n/a |
| Accuracy | 0.950 | [0.764, 0.991] |

Recall is perfect on this set: every paper that reports a population had one
extracted. The confidence interval on accuracy is wide, [0.764, 0.991], and
must be quoted with the point estimate. A recall of 1.000 on eleven positives
is statistically consistent with a true recall substantially below 1.

This answers the first half of **RQ1**: pattern-based extraction detects the
presence of a reported population reliably enough to drive edge weighting, with
the sample-size caveat above.

### 6.4.2 Value accuracy

| Metric | Value | 95% CI |
|--------|------:|--------|
| Exact value correct | 10 / 11 (0.909) | [0.623, 0.984] |

The single failure is instructive. For Wang et al., *JAMA* 2020, a case series
of 138 hospitalised patients, the system extracted **36**. The abstract states
the cohort size in the Design section and then reports numerous subgroup counts
in Results; the resolver selected a subgroup. This is a *resolution* failure,
not a detection failure: the correct candidate was extracted, and the selection
policy in Section 4.2.2 preferred another.

### 6.4.3 Semantic type classification

| Metric | Value |
|--------|------:|
| Type correct, among correct values | 6 / 10 (0.600) |

This is the weakest measured result, and it answers the second half of **RQ1**
negatively: surface patterns do not reliably distinguish the clinical
categories. The four errors:

| Paper | Gold | Predicted |
|-------|------|-----------|
| Polack et al. 2020 | `TOTAL_RANDOMIZED` | `SAMPLE_SIZE_GENERIC` |
| Folegatti et al. 2020 | `TOTAL_ENROLLED` | `TOTAL_RANDOMIZED` |
| Huang et al. 2020 | `TOTAL_ANALYZED` | `TOTAL_ENROLLED` |
| Verity et al. 2020 | `SAMPLE_SIZE_GENERIC` | `TOTAL_ANALYZED` |

All four are *adjacent-category* confusions among quantities that are often
numerically equal, a trial that randomises 4,744 and analyses 4,744 differs
only in framing. The first error has a traceable cause: the phrase "A total of
43,548 participants underwent randomization" matches a generic `a total of N`
pattern that is typed `SAMPLE_SIZE_GENERIC`, and that pattern outranked the
randomisation-specific one. This is a pattern-priority defect, not an inherent
limit.

The practical impact on the system is smaller than the number suggests: the
weighting formula uses the *value*, not the type. Type accuracy affects the
displayed explanation rather than the ranking. It is nonetheless the clearest
argument for the supervised approach discussed in Section 8.2.

### 6.4.4 The false positive, and confidence calibration

The one false positive is Wynants et al., *BMJ* 2020, a systematic review of
prediction models. The system extracted **27** with confidence **0.90**.

This exposes a calibration failure that matters more than the single error:

| | Mean confidence |
|---|---:|
| When the extracted value was correct | 0.91 |
| When the extracted value was wrong | 0.90 |

**Confidence does not discriminate correct from incorrect extractions.** This
is a genuine weakness in a system whose stated purpose is to surface
uncertainty. Confidence currently reflects *which pattern matched*, not *how
likely the match is to be right*, and a user filtering on high confidence would
retain the errors along with the correct results. Section 8.2 proposes
calibration against held-out data as the remedy.

## 6.5 Citation graph construction

Three traversals at `max_papers = 40`, backward depth 2, forward depth 1:

| Seed | Nodes | Edges | Dangling | Isolated | Merged | Mean degree | Time |
|------|------:|------:|---------:|---------:|-------:|------------:|-----:|
| Guan et al. 2020 (COVID cohort) | 40 | 81 | 0 | 0 | 2 | 4.05 | 19.9 s |
| Jumper et al. 2021 (AlphaFold) | 40 | 39 | 0 | 0 | 0 | 1.95 | 10.7 s |
| McMurray et al. 2019 (DAPA-HF) | 40 | 90 | 0 | 0 | 0 | 4.50 | 26.3 s |

| Aggregate | Value |
|-----------|------:|
| Runs completed | 3 / 3 |
| Total dangling edges | **0** |
| Total isolated nodes | **0** |
| Connected fraction | 1.000 |
| Duplicate records merged | 2 |
| Mean runtime | 19.0 s |

Every run filled its budget with distinct papers, every edge had both endpoints
present, and no node was orphaned. Duplicate merging occurred before the budget
was consumed, so the two merges on the first graph did not reduce it below 40,
which matters for interpretation: a sparse graph indicates few citations, not
records lost to deduplication.

Mean degree varies by more than a factor of two across seeds. The AlphaFold
graph is markedly sparser (1.95) than the two clinical graphs (4.05, 4.50),
reflecting that its neighbourhood spans structural biology, machine learning and
chemistry, which cite each other less densely than a tight clinical literature
does.

**On ranking quality (RQ3).** A qualitative observation: seeded with the 2021
AlphaFold paper, the top-ranked foundational paper was Anfinsen's 1973
*"Principles that Govern the Folding of Protein Chains"*, the work that founded
the protein-folding problem. This is the behaviour the design intends. It is an
anecdote, not a measurement. No relevance judgement study was conducted, no
comparison against unweighted PageRank was run, and a single favourable example
does not establish that evidence weighting improves ranking. Section 7.3
records this as the principal unaddressed question.

## 6.6 Performance

### 6.6.1 Stage breakdown

Instrumented 40-paper run:

| Stage | Time | Share |
|-------|-----:|------:|
| Resolve seed (3 providers in parallel) | 1.8 s | 6.5% |
| **Citation traversal (network-bound)** | **17.5 s** | **62.6%** |
| Population extraction (local) | 7.9 s | 28.3% |
| Edge weighting | 0.00 s | 0.0% |
| Graph construction | 0.00 s | 0.0% |
| PageRank ranking | 0.7 s | 2.5% |
| Path ranking | 0.00 s | 0.0% |
| **Total** | **27.9 s** | |

This answers **RQ4**. The system is I/O-bound: 58 HTTP requests across three
providers dominate, and all graph analytics together are 2.5% of runtime. The
graph algorithms are not the bottleneck and, at this scale, never will be,
which retrospectively validates the choice of an in-memory graph over a
database (Section 5.1). Population extraction at 28% is now the second cost and
the first place local optimisation would pay.

### 6.6.2 Scaling with graph size

| `max_total_papers` | Runtime |
|-------------------:|--------:|
| 60 | 30 s |
| 100 | 31 s |
| 200 | 209 s |

Growth from 60 to 100 is nearly free because batching amortises the additional
lookups. The jump to 200 is disproportionate: the graph becomes substantially
denser, so depth-2 expansion covers many more nodes. NFR-1 (under 60 s) holds
at 100 papers and fails at 200.

### 6.6.3 Effect of connection pooling

Each provider request originally created a fresh HTTP client, paying a full TCP
and TLS handshake:

| Mode | Median | Total (8 sequential requests) |
|------|-------:|------------------------------:|
| New client per request | 1.03 s | 8.72 s |
| One pooled client | 0.42 s | 3.65 s |

Approximately 634 ms of handshake per request, 58% of the time each call took. On a full run with identical output: 
| | Before | After | |---|---:|---:| | Mean request latency | 2,893 ms | 573 ms | | 40-paper run | 93.3 s | 27.9 s |

### 6.6.4 Path ranking complexity

The original path ranking called `all_simple_paths` once per target node,
re-walking the reachable subgraph for every node in the graph, and materialised
a result dictionary for every path before discarding all but ten. Measured on
synthetic layered graphs:

| Nodes | Edges | Before | After | Speed-up |
|------:|------:|-------:|------:|---------:|
| 61 | 820 | 3.53 s | 0.03 s | 126× |
| 91 | 1,830 | 11.92 s | 0.06 s | 191× |
| 151 | 5,050 | 117.96 s | 0.27 s | 434× |

The redesign, one depth-limited DFS feeding a bounded heap, returns an
identical top-ten (verified by comparing path sets and scores against the
exhaustive computation). The speed-up widens with size because the original was
O(nodes × paths) and the replacement is O(paths).

## 6.7 Methodological note: reference verification

The reference list was verified programmatically: every candidate DOI was
resolved against Crossref, with OpenAlex as fallback, and the returned title
compared against the intended work.

This caught three identifiers that had been assigned incorrectly:

| Key | Assigned DOI | What it actually is |
|-----|--------------|---------------------|
| Europe PMC | `10.1093/nar/gkz947` | *Expression Atlas update* |
| PageRank on citations | `10.1016/j.joi.2007.01.001` | A journal-impact-factor rank-order paper |
| Trialstreamer | `10.1093/jamia/ocv044` | RobotReviewer |

A fourth candidate, the 1999 PageRank technical report, has no resolvable DOI
and was dropped rather than cited with a fabricated identifier; PageRank is
cited through Brin and Page (1998) and Chen et al. (2007) instead.

This is reported because it is a result about method. Citations composed from
memory are wrong at a non-trivial rate, three of twenty-nine here, roughly 10%,
and the errors are invisible without verification, since a plausible DOI looks
exactly like a correct one. All twenty-nine entries in the final bibliography
resolve.

## 6.8 Summary of Results against objectives

| Objective | Status | Evidence |
|-----------|--------|----------|
| 1. Identifier normalisation | Met | §6.2, automated tests |
| 2. Multi-provider metadata resolution | Met | 20/20 resolved, §6.2 |
| 3. Bidirectional bounded traversal | Met | §6.5 |
| 4. Population candidate extraction | Met | P 0.917 / R 1.000, §6.4 |
| 5. Candidate resolution with confidence | Partially met | Value 10/11; **confidence uncalibrated**, §6.4.4 |
| 6. Evidence-based edge weighting | Met | §5.6 |
| 7. Foundational ranking | Met, **unvalidated** | Produced; no relevance study, §6.5 |
| 8. API and dashboard | Met | §5.9 |
| 9. Module-level evaluation | Met | This chapter |

Two objectives are qualified rather than met outright, and the qualifications
are the honest findings of the evaluation: confidence scores do not discriminate
correct from incorrect extractions (6.4.4), and the ranking, while producing
defensible output on inspection, has not been validated against human judgement
(6.5).
