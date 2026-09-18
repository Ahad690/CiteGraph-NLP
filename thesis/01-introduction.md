# Chapter 1: Introduction

## 1.1 Background and Motivation

Scientific knowledge is cumulative, and the citation is the mechanism by which
that accumulation is recorded. When a paper cites another, it declares a
dependency: some part of the new work rests on the earlier one. Garfield's
proposal for a citation index [garfield1955] rested on exactly this
observation, that the network of citations is itself a navigable structure, and
that following it backwards should let a reader reach the origin of an idea.

Seventy years later, the network exists and is machine-readable. OpenAlex
[priem2022openalex], Crossref [hendricks2020crossref] and Europe PMC
[europepmc2015] between them expose hundreds of millions of works and their
reference lists through open APIs. What has not kept pace is the interpretation
of that network. The dominant summary statistics, citation count, h-index
[hirsch2005hindex], journal impact factor, all treat citations as
interchangeable units. A citation is a citation.

That assumption is convenient and, for many purposes, wrong. Consider two
papers in the same reference list of a clinical review:

- A multinational randomised controlled trial that randomised 43,548
  participants across two arms.
- A case report describing three patients.

Both contribute exactly one to the cited paper's citation count. Both appear as
a single unweighted edge in a citation graph. Yet a reader tracing the
evidential basis of a clinical claim would not treat them as equivalent for a
moment. The scale of the study population is one of the most basic signals a
reader uses when judging how much weight a piece of evidence can bear, and it is
entirely absent from the citation graph as normally constructed.

The methodological literature reinforces the point. Ioannidis argues that a
large fraction of published findings are false, with small study size among the
principal contributors [ioannidis2005why]. Button and colleagues demonstrate
that low statistical power both reduces the chance of detecting a true effect
and reduces the probability that a detected effect is real [button2013power].
If sample size materially changes how much a result should be trusted, then a
graph that discards sample size is discarding something a reader needs.

## 1.2 Problem Statement

A researcher who wants to know *which earlier papers a body of work actually
rests on* currently has three unsatisfactory options.

**Manual reference following.** Open the seed paper, read its reference list,
open the interesting references, repeat. This is accurate but does not scale.
A paper with forty references, each with forty references, presents 1,600
second-level works.

**Citation-count ranking.** Use a bibliometric tool to sort candidates by
citation count. This scales, but rewards popularity rather than evidential
weight, and is well known to be confounded by field, age and venue
[waltman2016review]. Highly cited papers are disproportionately recent reviews
rather than foundational primary studies.

**Systematic review methodology.** Follow PRISMA [moher2009prisma] and appraise
each study with an instrument such as the Cochrane risk-of-bias tool
[higgins2011cochrane]. This is the rigorous answer and is the correct one when
the stakes justify it, but a full systematic review is a months-long
undertaking by a trained team.

The gap this project addresses sits between the second and third options: an
automated traversal that is aware, however imperfectly, of how much evidence
each cited paper actually reports, and that is honest about the imperfection.

## 1.3 Research Questions

This project is organised around four questions.

**RQ1.** Can study population sizes be extracted from abstracts reliably enough
to be used as an edge-weighting signal, using pattern-based information
extraction rather than a trained model?

**RQ2.** What proportion of papers reachable in a citation traversal actually
carry the text needed for such extraction, and does that proportion constrain
the approach more than extraction accuracy does?

**RQ3.** Does weighting citation edges by extracted population evidence produce
a foundational-paper ranking that a domain reader would find defensible?

**RQ4.** Can a citation traversal over public scholarly APIs be made fast enough
for interactive use, and what dominates its cost?

Chapter 6 answers RQ1, RQ2 and RQ4 with measured results. RQ3 is answered
qualitatively and with explicit acknowledgement that no formal relevance
judgement study was conducted; Section 7.3 treats this as a threat to validity.

## 1.4 Aim and Objectives

**Aim.** To design, implement and evaluate a system that constructs a citation
graph from a single seed paper, weights its edges by extracted study-scale
evidence, and surfaces the uncertainty of that extraction to the user.

**Objectives.**

1. Normalise heterogeneous scholarly identifiers (DOI, PMID, PMCID, free-text
   title, article URL) to a single canonical form.
2. Resolve metadata for a paper by querying multiple scholarly APIs in parallel
   and merging the results with field-level precedence.
3. Traverse the citation network in both directions to a configurable depth
   under a bounded budget of papers.
4. Extract candidate study population sizes from abstract text and classify
   them into semantic categories.
5. Resolve competing candidates within a paper to a single effective population
   size with an explicit confidence and status.
6. Weight citation edges using the normalised population score, scaled by
   extraction confidence, without discarding edges that lack evidence.
7. Rank probable foundational papers using PageRank over the weighted graph.
8. Expose the analysis through a REST API and a web dashboard, with exports in
   machine-readable and human-readable formats.
9. Evaluate each module against the metrics specified in the project proposal.

Objective 9 deserves particular note. The project proposal specified an
evaluation plan covering four modules, but at the point where this thesis was
begun, the evaluation directory in the repository was empty and no metric had
been computed. Chapter 6 reports the results of implementing that plan.

## 1.5 Scope and Delimitations

**In scope.** Biomedical and clinical literature, where reported sample sizes
are conventional and abstracts are structured. Abstract-level extraction.
Graphs bounded at 200 papers. Backward references to depth 3 and forward
citations to depth 2. Three metadata providers: OpenAlex, Crossref, Europe PMC.

**Explicitly out of scope.**

- *Full-text parsing.* The project proposal specified GROBID [lopez2009grobid]
  for PDF structure extraction. This was not implemented. The system reads
  abstracts only. Section 7.4 discusses the consequence.
- *Exhaustive citation retrieval.* A heavily cited paper may have tens of
  thousands of citing works; the system samples the most-cited subset within
  its paper budget. It does not claim completeness.
- *Clinical interpretation.* An extracted population size is a reading of the
  abstract, not a verified study characteristic. The system is an exploratory
  aid, not an evidence-appraisal instrument.
- *Study-level deduplication.* The proposal described a study-aware graph in
  which several papers reporting one trial collapse to a single study node.
  The implementation maps papers to studies one-to-one.

## 1.6 Contributions

This thesis makes the following contributions.

**C1. A working, deployed pipeline.** An end-to-end system from identifier to
ranked graph, deployed and publicly reachable, with 102 automated tests.

**C2. An edge-weighting formulation that degrades honestly.** Population
evidence scales the evidential term of the edge weight while a structural term
always applies, so an edge whose evidence could not be extracted retains a
uniform non-zero weight instead of vanishing. Section 5.6 shows that the
original formulation, multiplying the entire weight by confidence, silently
collapsed every edge weight to exactly zero for any paper outside clinical
phrasing, and that the defect was masked by a Python truthiness accident.

**C3. A measured evaluation with hard negatives.** A 20-paper gold standard in
which nine negatives contain large but irrelevant numbers, so false positives
are measured rather than hidden. Results in Chapter 6.

**C4. A quantified account of the data-availability ceiling.** Measurement
showing that 28% of papers in a representative graph carry no abstract in the
primary provider, that all of those were recoverable from a second provider,
and that this data gap constrained recall more than extraction logic did.

**C5. A documented catalogue of defects found by measurement.** Chapter 5
records eight defects in the delivered system that were found only by
instrumenting and measuring it, including a traversal fault that discarded the
majority of every graph. These are reported because a thesis that describes
only the working system teaches less than one that describes how the faults
were found.

## 1.7 Thesis Structure

**Chapter 2** reviews citation analysis, scholarly data infrastructure,
biomedical information extraction and evidence appraisal, and positions this
work against each.

**Chapter 3** states functional and non-functional requirements, describes the
development methodology, and defines the evaluation strategy.

**Chapter 4** presents the architecture, the data model and the algorithms.

**Chapter 5** describes the implementation, including the defects found during
measurement and how each was resolved.

**Chapter 6** reports the evaluation: gold standard construction, measured
results for each module, performance characterisation, and failure analysis.

**Chapter 7** interprets the results, states threats to validity, and
catalogues every divergence between the proposal and the delivered system.

**Chapter 8** concludes and sets out future work.

---
