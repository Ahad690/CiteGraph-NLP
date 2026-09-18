# FYP Thesis — Progress

Skill: `ai-research-writing` (jin-s13), audit pass reserved for
`academic-writing-skills` (bahayonghang).

Target: BSAI Final Year Project thesis, ~100 pages when rendered to PDF.
Output format: Markdown (no university template supplied yet; author will
adapt to the NUTECH template when issued).

## Contract

- Mode: full document, as-built system thesis (not a conference paper).
- Evidence rule: every number traces to a script, log, or artifact in this
  repository. No invented citations, no invented results.
- Claims to avoid: state-of-the-art performance, novelty of PageRank on
  citation graphs, clinical validity of extracted populations.

## Stage

| Stage | State |
|---|---|
| 1. Contract declared | done |
| 2. Evidence inventory | in progress |
| 3. Story + literature position | not started |
| 4. Core sections (Method, Evaluation, Results) | not started |
| 5. Framing (Related Work, Intro, Conclusion, Abstract) | not started |
| 6. Figures and tables | not started |
| 7. Citation verification | not started |
| 8. Review pass | not started |

## Known evidence gaps (from repository audit)

1. `src/citegraph/evaluation/` is an empty directory. The proposal's
   Section 13 specifies ~19 metrics across four modules; none were ever
   computed. BLOCKER for a Results chapter -> being generated now.
2. No literature review or reference list exists anywhere in the repo.
   BLOCKER for Related Work -> requires real citation research.
3. GROBID full-text parsing, Neo4j storage, and the Streamlit dashboard are
   specified in the PRD but not implemented. Must be reported as scope
   reductions, not described as working.
4. Study-aware knowledge graph is a 1:1 paper->study mapping with a
   hardcoded `dedupe_confidence=0.8`; study-level deduplication was not
   implemented.

## Evidence already measured (this session, reproducible)

- Traversal correctness: 0 dangling edges, 0 isolated nodes.
- Duplicate merging: 2 merged on a 40-paper graph, 0 duplicate titles left.
- Extraction recall: 7 -> 15 of 29 papers with abstract text.
- Abstract coverage: 11/40 absent from OpenAlex, 11/11 recovered via Europe PMC.
- Performance: 93.3s -> 27.9s per 40-paper run; stage breakdown recorded.
- Connection pooling: ~634 ms/request saved, 58% of request time.
