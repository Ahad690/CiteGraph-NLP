# Chapter 8: Conclusion and Future Work

## 8.1 Conclusion

This thesis set out to determine whether study-scale evidence could be
automatically extracted from scholarly abstracts and used to weight the edges of
a citation graph, so that a reader tracing a line of research could distinguish
a citation to a 43,548-participant trial from a citation to a case report.

A working system was built, deployed and measured. Against the four research
questions of Section 1.3:

**RQ1, Can population sizes be extracted reliably enough by pattern-based
methods?** Partially. Detection achieved precision 0.917 and recall 1.000 (F1
0.957, accuracy 95% CI [0.764, 0.991]) on a 20-paper gold standard, and exact
values were correct in 10 of 11 positive cases. But semantic type
classification reached only 6 of 10, and, more seriously, the confidence scores
attached to extractions do not discriminate correct from incorrect results
(mean 0.91 when right, 0.90 when wrong). Extraction is good enough to drive
edge weighting; the uncertainty signalling around it is not yet trustworthy.

**RQ2. What proportion of papers carry the text needed, and does availability
constrain the approach more than accuracy?** Yes, decisively. In a
representative 40-paper graph, 28% of papers carried no abstract in the primary
provider. All were recoverable from a second provider in a single batched
request. Data availability, not extraction logic, was the binding constraint on
coverage, and the cheaper of the two to fix.

**RQ3, Does evidence weighting produce a defensible ranking?** Unproven. The
system produces plausible output, seeded with the 2021 AlphaFold paper it
surfaced Anfinsen's 1973 paper founding the protein-folding problem, but no
relevance judgement study was run and no comparison against unweighted PageRank
was performed. This thesis shows the ranking *can be computed* and *looks
sensible*, not that it is better than the unweighted baseline. This is the
principal unaddressed question in the work.

**RQ4. Can traversal be made fast enough for interactive use, and what
dominates?** Yes. A 40-paper analysis completes in a mean of 19 s, and a
100-paper analysis in about 31 s. The cost is overwhelmingly network I/O (63%);
all graph analytics together account for 2.5%. The largest single improvement
came not from algorithmic work but from reusing one pooled HTTP client instead
of creating one per request, which cut a representative run from 93.3 s to 27.9
s.

Beyond the research questions, the work produced a second result the authors
did not anticipate. Six substantial defects were found in a system that passed
102 automated tests, and four of them produced no error and no visible symptom,
including one that discarded roughly half of every graph, one that made every
forward-citation query silently return zero, and one that collapsed every edge
weight to zero while a Python truthiness accident concealed it by substituting
1.0. For a system whose output is a ranked list, testing that the pipeline runs
establishes very little. Correctness required measurement against known
quantities, which is precisely what the project proposal's evaluation plan
specified and what had been left unimplemented.

The system's honest standing is therefore this. It is a working prototype that
demonstrates the *feasibility* of evidence-weighted citation analysis and
characterises its constraints with measured evidence. It is not a validated
instrument for evidence appraisal, it does not read full text, and its
uncertainty signalling is weaker than its interface implies.

## 8.2 Future Work

Ordered by expected value relative to cost.

### 8.2.1 Calibrate the confidence scores

The clearest and most valuable correction. Confidence currently encodes which
pattern matched rather than how likely the match is to be correct (§6.4.4).
Calibrating against held-out labelled data, for example by fitting a logistic
model over pattern identity, sentence features and competing-candidate
structure, would make the score mean what the interface claims. This requires a
larger gold standard, which §8.2.3 addresses, and would make the system's
distinguishing feature actually trustworthy.

### 8.2.2 Compare against an unweighted baseline

The central unanswered question (§7.3.4). A comparison of evidence-weighted
against unweighted PageRank, with domain readers judging the relevance of
ranked outputs blind to condition, would establish whether the weighting helps.
Without it, the system's core premise is plausible but untested. This is the
first experiment a continuation of this work should run.

### 8.2.3 Extend and re-annotate the gold standard

Twenty papers with one annotator produces wide intervals and no agreement
measure. Extending to 150–200 papers with at least two independent annotators
and a reported Cohen's κ would narrow the intervals, enable calibration, and
remove the most serious methodological weakness identified in §7.3.2.

### 8.2.4 Supervised extraction

Type classification at 60% is where pattern methods are weakest (§7.1.2).
Fine-tuning a domain-adapted encoder such as BioBERT [lee2020biobert] or
SciBERT [beltagy2019scibert] on PICO population annotations [nye2018ebmnlp]
would target exactly the semantic discrimination surface patterns cannot make.
A hybrid retaining patterns for high-precision cases and deferring ambiguous
ones to the model would preserve the auditability that the current design
provides.

### 8.2.5 Full-text extraction

The largest functional gap against the proposal (§7.4). Sample sizes often
appear only in a Methods section. Europe PMC provides open-access full text,
and GROBID [lopez2009grobid] is already anticipated in the configuration.
Unpaywall [martin2021oadoi] would determine which articles are legally
retrievable, keeping the system within the bounds §7.6 describes.

### 8.2.6 Study-level deduplication

Implementing the study-aware graph the proposal described (§7.4), so that a
protocol, primary results paper and secondary analysis of one trial collapse to
a single study node. Without it, well-published trials are over-weighted
because their evidence is counted once per paper. Trial registry identifiers
offer a practical join key.

### 8.2.7 A frozen evaluation corpus

Snapshotting the gold-standard records so the evaluation does not depend on live
APIs (§7.3.3), making results exactly reproducible and allowing regression
detection when extraction logic changes.

### 8.2.8 Parameter sensitivity analysis

Several numbers in the system were set by judgement and never varied: the
PageRank damping factor of 0.85 inherited from the library default
(§4.6.1), the weights 0.5/0.3/0.2 combining PageRank, age and evidence, the
weighting constants α = 0.75 and β = 0.25, and the path-length penalty of
1/√(length). None has been swept.

The damping factor is the one with published reason to expect sensitivity.
Boldi, Santini and Vigna show the induced ranking changes with it, and that
the dependence grows with the proportion of dangling nodes
[boldi2005damping]. In a graph capped at 200 papers, every node at the
traversal frontier is dangling by construction, so the proportion is large and
determined by where the budget ran out rather than by the literature. Re-running
the rankings across a grid of damping values and reporting the rank correlation
between them would establish whether the foundational-paper ordering is a
property of the evidence or of the parameter, and it needs no new data.

### 8.2.9 Citation context and sentiment

Garfield's original caveat (§2.1.1): a citation may be critical rather than
supportive. Classifying citation context would let the graph distinguish
support from refutation, a substantially harder problem, and the most
speculative item here.

## 8.3 Closing Remarks

The most durable lesson of this project was not about citation graphs.

The system produced plausible output throughout a period in which it was
discarding half of every graph, returning zero forward citations for every
paper, and running an unweighted ranking while presenting it as
evidence-weighted. Every automated test passed. What exposed the faults was
measuring the system against quantities known independently, how many
references the provider reported, what a human reading the abstract found, how
long each stage took.

The evaluation plan that would have caught most of this was written in the
project proposal before implementation began, and was left as an empty
directory until the thesis was drafted. The measurement was not an afterthought
to the engineering; it was the part of the engineering that had been deferred,
and deferring it is what allowed the defects to persist. That is the finding the
authors would carry into another project.
