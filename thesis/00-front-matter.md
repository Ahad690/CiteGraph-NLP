![National University of Technology](assets/nutech-logo.png){width=45mm}

# CiteGraph-NLP: A Confidence-Aware System for Citation Lineage Analysis and Study-Scale Evidence Extraction

**A thesis submitted in partial fulfilment of the requirements for the degree of**  
**Bachelor of Science in Artificial Intelligence**

**Department of Computer Science**  
**National University of Technology**

---

## Authors

| Name | Registration Number |
|------|---------------------|
| M. Ahad Imran | F23607034 |
| Syed Zain-ul-Abidin | F23607031 |
| Anas Zafar | F22607024 |

**Supervisor:** Dr. Amna Ikram

**Session:** 2023–2027

---

## Declaration

We declare that this thesis and the system it describes are our own work, except
where explicitly attributed. All external data is retrieved from public
scholarly APIs under their published terms of use. No paywalled full text was
scraped or redistributed. Every quantitative result reported in Chapter 6 was
produced by a script committed to the project repository and can be recomputed
by a reader with network access; the commands are given in Appendix C.

**Provenance of the work.** An initial prototype of this system was developed in
the sixth semester. The project has been carried forward into the Final Year
Project in the seventh semester, and the team composition has changed since the
prototype phase. The work presented here substantially extends that prototype.
The evaluation reported in Chapter 6 was designed and executed during the FYP
phase, and the corrections catalogued in Chapter 5, including the traversal,
weighting and extraction defects, were identified and resolved in this phase.
Where a result or component predates the FYP, this is stated at the point of use
rather than presented as new work.

Where the delivered system falls short of the original project proposal, this
thesis states the shortfall explicitly rather than describing the intended
behaviour as though it had been achieved. Section 6.8 and Chapter 7 catalogue
these divergences.

---

## Abstract

Determining which earlier papers a body of research actually rests on is a
manual and error-prone task. A reader who wants to trace a claim back to its
origin must follow reference lists by hand, and the citation counts that
bibliometric tools report treat every citation as equally informative. A
citation to a 43,548-participant randomised trial and a citation to a
three-patient case report are indistinguishable in a raw citation graph.

This thesis presents **CiteGraph-NLP**, a system that constructs a citation
graph from a single seed paper and weights its edges by the *scale of the
evidence* each cited paper reports, rather than by citation count alone. The
system resolves a user-supplied identifier (DOI, PMID, PMCID, title or URL)
against three public scholarly APIs, performs a depth-limited breadth-first
traversal over references and citing works, extracts reported study population
sizes from abstracts using a pattern-based information-extraction pipeline,
weights each citation edge by a normalised population score scaled by extraction
confidence, and ranks probable foundational papers using PageRank over the
weighted graph.

The contribution is not a new ranking algorithm. PageRank on citation networks
is long established [chen2007gems; walker2007citerank]. It is a working,
measured pipeline that makes the *uncertainty* of automated evidence extraction
visible to the user: every extracted population carries a confidence score and
a status of `resolved`, `ambiguous` or `missing`, and edges whose evidence
could not be established fall back to a uniform structural weight rather than
silently disappearing.

The system was evaluated against a 20-paper gold standard annotated from
abstract text, spanning randomised trials, cohort studies, case series,
epidemiological and modelling designs, together with deliberately hard negatives
whose abstracts contain large numbers that are *not* study populations.
Population detection achieved precision 0.917, recall 1.000 and F1 0.957;
exact sample-size values were correct for 10 of 11 positive cases; semantic type
classification was correct for 6 of 10. Metadata resolution succeeded for 20 of
20 papers. Three live citation traversals produced graphs with zero dangling
edges and zero isolated nodes.

The evaluation also exposes the system's limits honestly. Semantic type
accuracy of 60% shows that distinguishing *randomised* from *enrolled* from
*analysed* is not solved by surface patterns. A systematic review produced a
confident false positive. Twenty-eight per cent of papers in a typical graph
carry no abstract in the primary metadata source at all, and a second provider
had to be queried to recover them. Full-text parsing, specified in the project
proposal, was not implemented; the system reads abstracts only.

**Keywords:** citation analysis, knowledge graphs, information extraction,
biomedical NLP, PageRank, evidence synthesis, scholarly APIs

---

## Acknowledgements

*[to be completed by the authors]*

---

## Table of Contents

1. **Introduction**: motivation, problem statement, objectives, scope, contributions
2. **Literature Review**: citation analysis, scholarly infrastructure, biomedical information extraction, evidence appraisal
3. **Requirements and Methodology**: requirements capture, development process, evaluation strategy
4. **System Design and Architecture**: layered architecture, data model, algorithms
5. **Implementation**: pipeline stages, provider integration, engineering defects and their resolution
6. **Evaluation and Results**: gold standard, measured results, performance, failure analysis
7. **Discussion**: interpretation, threats to validity, divergence from the proposal
8. **Conclusion and Future Work**

**Appendices**

- A. API Reference
- B. Configuration Reference
- C. Reproducing the Results
- D. Gold Standard Annotations
- E. Requirements Traceability
- F. Test Inventory
- G. Source Listings
- H. Full-Scale Generated Diagrams

---

## List of Figures

Every structural figure is generated from the source tree by
`scripts/generate_diagrams.py`; Appendix H records how, and carries the
full-scale plates the chapter figures are reduced from.

| Figure | Subject |
|--------|---------|
| 4.1 | Inter-package dependencies |
| 4.2 | Object composition among related classes |
| 4.3 | Data model, query to population |
| 4.4 | Data model, population to run result |
| 5.1 | Calls made by the pipeline orchestrator |
| H.1 | Combined data model, all seven entities |
| H.2 | Complete class diagram |
| H.3 | Complete call graph |

---

## List of Abbreviations

| Term | Expansion |
|------|-----------|
| API | Application Programming Interface |
| BFS | Breadth-First Search |
| CORS | Cross-Origin Resource Sharing |
| DOI | Digital Object Identifier |
| FYP | Final Year Project |
| IE | Information Extraction |
| JATS | Journal Article Tag Suite |
| N_eff | Effective study population size |
| NLP | Natural Language Processing |
| PICO | Population, Intervention, Comparison, Outcome |
| PMCID | PubMed Central Identifier |
| PMID | PubMed Identifier |
| RCT | Randomised Controlled Trial |
| SPA | Single-Page Application |
| SSRF | Server-Side Request Forgery |
| TLS | Transport Layer Security |
