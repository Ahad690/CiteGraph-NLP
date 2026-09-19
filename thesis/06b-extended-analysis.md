# Chapter 6 (continued): Extended Analysis

## 6.9 Performance by Study Design

Aggregate metrics conceal where a system succeeds and fails. Breaking the
gold-standard results down by study design shows that performance is not
uniform, and that the failures cluster.

| Design | n | Positives | Correct decision | Exact value | Mean confidence |
|--------|--:|----------:|-----------------:|------------:|----------------:|
| Randomised controlled trial | 5 | 5 | 5/5 | **5/5** | 0.96 |
| Cohort study | 2 | 2 | 2/2 | 2/2 | 0.90 |
| Case series | 2 | 2 | 2/2 | **1/2** | 0.85 |
| Epidemiological | 1 | 1 | 1/1 | 1/1 | 0.85 |
| Modelling | 1 | 1 | 1/1 | 1/1 | 0.85 |
| Review | 3 | 0 | 3/3 | n/a | 0.00 |
| Virus characterisation | 2 | 0 | 2/2 | n/a | 0.00 |
| Computational | 2 | 0 | 2/2 | n/a | 0.00 |
| Guideline | 1 | 0 | 1/1 | n/a | 0.00 |
| **Systematic review** | **1** | **0** | **0/1** | n/a | **0.90** |

Gold populations span 41 to 43,548 subjects, median 1,099.

Three patterns are visible.

**Randomised trials are the easy case, and the system is built for them.** Five
of five correct, with the highest mean confidence (0.96). RCT abstracts follow
a reporting convention that surface patterns capture well: a single headline
number introduced by *randomised*, *assigned* or *enrolled*. This is
unsurprising given that the pattern set was written with trial phrasing in
mind, and it should temper any generalisation from the headline F1.

**Clear negatives are handled cleanly.** Reviews, guidelines, virus
characterisation and computational papers were all correctly rejected, with
confidence 0.00, including the hard negatives containing an ImageNet dataset
size and an epidemic case tally. The ignore rules and the requirement that a
number appear in a population-bearing construction are doing real work here.

**The two failures are both structural, not lexical.** The case-series miss
(138 predicted as 36) and the systematic-review false positive (27 at
confidence 0.90) share a cause: both abstracts contain *many* numbers in
population-like constructions, and the system has no mechanism for deciding
which one the abstract is *about*. In a case series, subgroup counts compete
with the cohort total; in a systematic review, counts of included studies
compete with nothing at all, because there is no cohort.

The systematic-review row is the most informative line in the table. It is the
only design where the system was wrong *and* confident, and it is the design
whose abstracts most resemble clinical reports without describing a cohort.

## 6.10 The confidence calibration failure in detail

Section 6.4.4 reported that mean confidence was 0.91 when extraction was
correct and 0.90 when it was wrong. The design breakdown explains why: there is
no model behind the score at all, so there is nothing that could have been
fitted well or badly.

Confidence is computed as:

```
confidence = min(1.0, pattern_weight + section_bonus)
```

`pattern_weight` is a constant attached to each regular expression, chosen by
the developer; `section_bonus` is 0.1 when the text came from an abstract. The
score is therefore a property of *which pattern fired*, fixed before any data
was seen. It cannot vary with evidence, because nothing in its computation
depends on the input beyond pattern identity.

This has a consequence that the aggregate numbers hide. A pattern assigned
weight 0.9 produces confidence 0.9 whether it matched the cohort total of a
well-structured trial abstract or a count of reviewed studies in a systematic
review. The systematic-review false positive carries confidence 0.90 for
exactly this reason: it matched a high-weight pattern, and the system has no
means of noticing that the match is out of domain.

The fix is not to adjust the weights. It is to make confidence a function of
observed correctness, fitting a calibration model over features such as pattern
identity, the number and spread of competing candidates, sentence position, and
the presence of design-indicating terms, which requires labelled data at a
scale the present gold standard does not reach. Section 8.2.1 and 8.2.3 are
therefore coupled: calibration is blocked on corpus size.

Until then, the honest framing for a user is that the confidence score indicates
*how specific the matched pattern was*, not *how likely the answer is to be
right*. Section 5.13.4 notes that the interface does not currently make this
distinction.

## 6.11 Sensitivity of the Graph to Seed Choice

The three traversals in Section 6.5 produced markedly different graph
structures from the same parameters.

| Seed | Field | Nodes | Edges | Mean degree | Time |
|------|-------|------:|------:|------------:|-----:|
| Guan et al. 2020 | Clinical (COVID) | 40 | 81 | 4.05 | 19.9 s |
| McMurray et al. 2019 | Clinical (cardiology) | 40 | 90 | 4.50 | 26.3 s |
| Jumper et al. 2021 | Computational biology | 40 | 39 | 1.95 | 10.7 s |

Mean degree differs by a factor of 2.3 between the clinical graphs and the
AlphaFold graph. Two explanations are consistent with the data, and the
evaluation does not distinguish them.

The first is topical: the AlphaFold neighbourhood spans structural biology,
machine learning and chemistry, and papers from different fields cite each other
less densely than papers within a tight clinical literature do. The second is
temporal: a 2021 paper's citing works are themselves recent and have had less
time to accumulate the cross-citations that create density.

Distinguishing these would require holding field constant and varying year, or
vice versa, across many more seeds than three. It is noted here because it
bears on how a user should read a sparse graph: low density may indicate an
interdisciplinary or recent seed rather than a thin literature, and the system
currently offers no signal to tell them apart.

The runtime difference follows directly from density. Fewer edges means fewer
neighbours to resolve, which reinforces the finding in Section 6.6.1 that cost
is driven by the number of external lookups rather than by graph computation.

## 6.12 What the abstract backfill changed, stage by stage

The effect of the Europe PMC backfill is worth tracing through the pipeline,
because it illustrates how an upstream data gap presents as a downstream model
failure.

| Stage | Before backfill | After backfill |
|-------|----------------:|---------------:|
| Papers in graph | 40 | 40 |
| Papers with abstract text | 29 (72%) | 40 (100%) |
| Papers yielding candidates | 15 | 20 |
| Papers with a resolved `n_eff` | 15 (38%) | 20 (50%) |
| High confidence (≥ 0.8) | 10 | 11 |
| Status `missing` | 25 | 20 |

Eleven papers moved from "no text" to "text available", and five of those then
yielded a population. The remaining six had text but no reportable population. That is correct: they were reviews, guidelines and discovery papers.

The distinction matters for how the result is read. Before the backfill, 25 of
40 papers reported `missing`, and nothing in the output distinguished *no
abstract available* from *abstract read, no population present*. Those are
different facts about a paper, and only the second is a statement about the
paper itself. The warnings described in Section 4.7 were added so that the
output now separates them.

## 6.13 Cumulative Effect of the Corrections

Measured on the same 40-paper graph across the correction sequence in
Chapter 5. Each row is the state after the named correction.

| State | Papers with `n_eff` | High confidence | Runtime |
|-------|--------------------:|----------------:|--------:|
| Initial (as delivered before measurement) | 7 (18%) | 3 | 93.3 s |
| After per-span ignore matching (§5.5) | 15 (38%) | 10 | n/a |
| After connection pooling (§6.6.3) | 15 | 10 | 27.9 s |
| After Europe PMC backfill (§6.3) | **20 (50%)** | **11** | 27.0 s |

Coverage of extractable evidence rose from 18% to 50% of the graph, and
high-confidence extractions from 3 to 11, while runtime fell by roughly 71%.

The composition of that gain is the point. Of the 13 additional papers with
evidence, eight came from correcting extraction logic and five from querying a
second data source. The second intervention is far cheaper, one additional API
call per run against a rewrite of the ignore-matching logic, and would not have
been identified without separating "no text" from "extraction failed" in the
measurement. Section 7.1.1 draws the general lesson.
