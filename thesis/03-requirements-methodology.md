# Chapter 3: Requirements and Methodology

## 3.1 Requirements Elicitation

Requirements were derived from three sources, in order of authority: the
project proposal approved by the department, a Product Requirement Document
(PRD) written during the design phase, and a feasibility study commissioned
before implementation began.

The feasibility study is worth describing because it shaped the scope
materially. It assessed each intended component, metadata resolution, PDF
parsing, population extraction, citation traversal, graph construction, and
judged the difficulty of each independently. Its conclusion on full-text
parsing was the decisive one: obtaining legal full text at scale is gated by
open-access status rather than by parsing capability, and a pipeline that
depends on full text will fail for a large fraction of inputs regardless of how
good its parser is. The delivered system reads abstracts only, and Chapter 6
quantifies what that costs.

## 3.2 Functional Requirements

Requirements are stated in the form *the system shall*, with a verification
method and the section reporting the result.

### 3.2.1 Input handling

| ID | Requirement | Verification |
|----|-------------|--------------|
| FR-1 | Accept a DOI, PMID, PMCID, free-text title or article URL as the seed identifier | Automated test, §6.2 |
| FR-2 | Canonicalise all identifiers to a single normalised form | Automated test |
| FR-3 | Extract an embedded identifier from an article URL without fetching the page where possible | Automated test, §5.7 |
| FR-4 | Reject malformed identifiers with a message naming the expected form | Automated test |

### 3.2.2 Metadata resolution

| ID | Requirement | Verification |
|----|-------------|--------------|
| FR-5 | Query OpenAlex, Crossref and Europe PMC concurrently | Code inspection |
| FR-6 | Merge provider results with field-level precedence | Code inspection |
| FR-7 | Record per-provider provenance for each resolved paper | Data inspection |
| FR-8 | Recover abstracts absent from the primary provider from a secondary provider | Measured, §6.3 |

### 3.2.3 Citation traversal

| ID | Requirement | Verification |
|----|-------------|--------------|
| FR-9 | Traverse backward references to a configurable depth (0–3) | Measured, §6.5 |
| FR-10 | Traverse forward citations to a configurable depth (0–2) | Measured, §6.5 |
| FR-11 | Bound the total number of papers per run (1–200) | Automated test |
| FR-12 | Collapse records describing one work under multiple identifiers onto one node | Measured, §6.5 |
| FR-13 | Emit no edge whose endpoints are not both present as nodes | Measured, §6.5 |

### 3.2.4 Population extraction

| ID | Requirement | Verification |
|----|-------------|--------------|
| FR-14 | Extract candidate population sizes from abstract text | Measured, §6.4 |
| FR-15 | Classify each candidate into a semantic type | Measured, §6.4 |
| FR-16 | Resolve competing candidates to one effective size per paper | Measured, §6.4 |
| FR-17 | Attach a confidence score and a status of resolved, ambiguous or missing | Measured, §6.4 |
| FR-18 | Not treat years, percentages, p-values or dosages as population sizes | Automated test, §5.5 |

### 3.2.5 Weighting, ranking and output

| ID | Requirement | Verification |
|----|-------------|--------------|
| FR-19 | Weight each edge by normalised population evidence scaled by confidence | Code inspection, §5.6 |
| FR-20 | Assign a non-zero weight to edges lacking population evidence | Automated test, §5.6 |
| FR-21 | Rank probable foundational papers over the weighted graph | Measured, §6.5 |
| FR-22 | Rank citation paths from the seed | Measured, §6.6 |
| FR-23 | Export results as JSON, CSV, edge-list CSV, Markdown and GraphML | Automated test, §5.8 |
| FR-24 | Provide a REST API and a web dashboard | Deployment, §5.9 |

## 3.3 Non-Functional Requirements

| ID | Requirement | Target | Result |
|----|-------------|--------|--------|
| NFR-1 | A 40-paper run completes within 60 s | < 60 s | 19 s mean, §6.6 |
| NFR-2 | Graph analytics are a minority of runtime | < 25% | 2.5%, §6.6 |
| NFR-3 | Provider failures degrade the run rather than aborting it | No unhandled exception | §5.4 |
| NFR-4 | No paywalled full text is retrieved | Zero | By construction |
| NFR-5 | Outbound fetches cannot reach private network addresses | Zero | §5.7 |
| NFR-6 | Browser access is restricted to a configured origin | Configured origin only | §5.9 |
| NFR-7 | Every reported metric is recomputable from a committed script | 100% | Appendix C |

NFR-7 is a response to a specific failure mode. The project proposal specified
an evaluation plan that was never executed, and its absence was not visible
because nothing in the repository recorded that the metrics were missing.
Making recomputability an explicit requirement means a gap of that kind becomes
detectable.

## 3.4 Development Methodology

### 3.4.1 Process

Development followed an iterative build–measure–correct cycle rather than a
waterfall. Given a four-person team, a fixed academic deadline and external
dependencies whose behaviour was not fully known in advance, planning the
system completely before building it was not realistic, a judgement the
feasibility study supported.

Each iteration comprised: implement a pipeline stage; write automated tests;
run the stage against live scholarly APIs; inspect the output for correctness;
correct what the inspection revealed.

The final phase of the project departed from this pattern in a way worth
recording, because it produced most of the defects catalogued in Chapter 5.
Rather than implementing new features, that phase consisted of *instrumenting
and measuring the existing system*. Eight defects were found. Several had been
present since early in development, had passed every test, and had produced
output that appeared plausible. Section 5.10 draws the methodological lesson.

### 3.4.2 Version control and quality gates

All work is version-controlled in Git with descriptive commits. The test suite
comprises 102 automated tests. Continuous integration deploys the backend to a
shared host and the frontend to a content delivery network on merge to the main
branch.

Two properties of the test suite are worth noting because they bear on Chapter
5. First, the suite passed in full throughout the period in which the traversal
defect described in Section 5.3 was discarding the majority of every graph; the
tests asserted that the pipeline completed and returned a structure of the
right shape, not that the structure was correct. Second, two defects in the
test suite itself were found, one hung the entire suite indefinitely, and one
masked a failure on the database read path. A test suite is software and is
subject to the same defects as the system it tests.

## 3.5 Evaluation Strategy

### 3.5.1 Evaluation design

Evaluation follows the module structure of the proposal's evaluation plan:
metadata resolution, population extraction, citation graph construction, and
ranking. Each is evaluated against a measurable criterion where one exists, and
reported as unmeasured where one does not.

### 3.5.2 Gold standard construction

Population extraction is evaluated against a hand-annotated gold standard of 20
papers. The construction protocol is:

1. Select papers spanning study designs, randomised trials, cohort studies, case series, epidemiological analyses, modelling studies, plus negatives: reviews, guidelines, and computational papers with no human subjects. 2. Retrieve the abstract through the same providers the pipeline uses. 3. Read each abstract and record the effective population size, defined as the total number of human subjects the paper's primary analysis rests on as stated in the abstract. 4. Record the supporting sentence verbatim so every label is auditable. 5. Where no human study population is stated, label the paper negative; the correct system behaviour is to extract nothing.

Nine of the twenty are negatives, and several are *hard* negatives whose
abstracts contain large, salient numbers that are not study populations: an
epidemic case tally of 2,794 laboratory-confirmed infections, an ImageNet
dataset size of 1.2 million images, and a systematic review whose units are
studies rather than patients. Including these is a deliberate design choice, a
positives-only gold set cannot measure false positives, and false positives are
the failure mode that most damages user trust.

### 3.5.3 Statistical treatment

Proportions are reported with 95% Wilson score intervals. The Wilson interval
is used rather than the normal approximation because the sample is small
(n = 20 overall, n = 11 positives), where the normal approximation is
unreliable and degenerates entirely at proportions of 0 or 1.

The intervals are wide, and Chapter 6 reports them alongside every point
estimate rather than quoting point estimates alone. A recall of 1.000 on
eleven positives is consistent with a true recall as low as roughly 0.74.

### 3.5.4 Acknowledged limitations of the evaluation

Four limitations are stated in advance because they bound every result in
Chapter 6.

- **Single annotator.** The gold standard was annotated by one person, who is
  also an author of the system. No inter-annotator agreement was measured.
  This is the most serious limitation; Section 7.3 discusses it.
- **Small sample.** Twenty papers, eleven positive. Interval estimates are
  correspondingly wide.
- **Abstracts only.** Sample sizes stated solely in a full-text Methods section
  are out of scope. This matches what the pipeline reads, so the evaluation is
  fair to the system as built, but it does not measure the task in general.
- **Domain concentration.** The positives are biomedical. Performance on other
  literatures is not measured and should not be assumed.

### 3.5.5 What is not evaluated

Two things the proposal listed are not evaluated, and are reported as gaps
rather than passed over.

**Ranking quality.** No relevance judgement study was conducted. The proposal
proposed "manual inspection of selected papers", which is not a metric. Section
6.5 reports a qualitative observation and Section 7.3 records the absence of a
formal ranking evaluation as an unaddressed threat.

**Duplicate detection accuracy.** Duplicate merging is measured by counting
merges performed and verifying no duplicate survives in the output, but no
gold standard of known duplicate pairs was constructed, so precision of the
merge decision is unmeasured. A merge that incorrectly collapses two distinct
papers would not be detected by the present measurement.
