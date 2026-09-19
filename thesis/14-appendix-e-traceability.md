# Appendix E: Requirements Traceability

This appendix maps every requirement from Chapter 3 to the implementing module,
the verifying test or measurement, and the section reporting the outcome. Its
purpose is to make partial and unmet requirements visible rather than leaving
them to be inferred from absence.

## E.1 Functional requirements

| ID | Requirement | Implemented in | Verified by | Status |
|----|-------------|----------------|-------------|--------|
| FR-1 | Accept DOI, PMID, PMCID, title, URL | `models/paper.py`, `input/normalizer.py` | `test_input_normalizer.py`, `test_api_comprehensive.py` | Met |
| FR-2 | Canonicalise identifiers | `utils/ids.py` | `test_input_normalizer.py` | Met |
| FR-3 | Extract identifier from URL text | `input/url_resolver.py` | `test_url_resolver.py` | Met |
| FR-4 | Reject malformed identifiers | `models/paper.py` | `test_api_comprehensive.py` | Met |
| FR-5 | Concurrent multi-provider query | `metadata/resolver.py` | Code inspection; §6.6.1 | Met |
| FR-6 | Field-level merge precedence | `metadata/merger.py` | §4.8 | Met |
| FR-7 | Per-provider provenance | `models/paper.py` | Data inspection | Met |
| FR-8 | Recover missing abstracts | `providers/europe_pmc.py`, `pipeline/orchestrator.py` | §6.3 | Met |
| FR-9 | Backward traversal, depth 0–3 | `citations/traversal.py` | §6.5 | Met |
| FR-10 | Forward traversal, depth 0–2 | `citations/traversal.py`, `providers/openalex.py` | §6.5 | Met |
| FR-11 | Bound total papers 1–200 | `api/routes.py` | `test_api_comprehensive.py` | Met |
| FR-12 | Merge duplicate records | `citations/traversal.py` | §6.5 | Met; **merge precision unmeasured** (§7.3.2) |
| FR-13 | No dangling edges | `citations/traversal.py` | §6.5, 0 across 3 runs | Met |
| FR-14 | Extract population candidates | `nlp/population_extractor.py` | §6.4.1 | Met |
| FR-15 | Classify semantic type | `nlp/population_patterns.py` | §6.4.3, 6/10 | **Partially met** |
| FR-16 | Resolve to one value per paper | `nlp/population_resolver.py` | §6.4.2, 10/11 | Met |
| FR-17 | Attach confidence and status | `models/population.py` | §6.4.4 | **Partially met, confidence uncalibrated** |
| FR-18 | Ignore years, percentages, p-values | `nlp/population_extractor.py` | `test_population_patterns.py` | Met |
| FR-19 | Evidence-based edge weighting | `graph/weighting.py` | §5.6 | Met |
| FR-20 | Non-zero weight without evidence | `graph/weighting.py`, `graph/builder.py` | §5.6 | Met |
| FR-21 | Rank foundational papers | `graph/analytics.py` | §6.5 | Met; **ranking quality unvalidated** (§7.3.4) |
| FR-22 | Rank citation paths | `graph/analytics.py` | §6.6.4 | Met |
| FR-23 | Five export formats | `api/routes.py` | `test_api_comprehensive.py` | Met |
| FR-24 | REST API and dashboard | `api/`, `frontend/` | §5.9, §5.11 | Met |

**Summary:** 22 of 24 met; FR-15 and FR-17 partially met. Both partial results
concern the same underlying weakness, the system's semantic and probabilistic
judgements about extractions are weaker than its value extraction.

## E.2 Non-functional requirements

| ID | Requirement | Target | Measured | Status |
|----|-------------|--------|----------|--------|
| NFR-1 | 40-paper run within 60 s | < 60 s | 19.0 s mean (§6.5) | Met at 40 and 100 papers; **fails at 200** (209 s, §6.6.2) |
| NFR-2 | Analytics a minority of runtime | < 25% | 2.5% (§6.6.1) | Met |
| NFR-3 | Provider failure degrades, not aborts | No unhandled exception | §5.4 | Met |
| NFR-4 | No paywalled full text retrieved | Zero | By construction | Met |
| NFR-5 | No outbound fetch to private addresses | Zero | §5.7 | Met |
| NFR-6 | Browser access restricted to one origin | Configured origin | §5.9 | Met |
| NFR-7 | Every metric recomputable from a script | 100% | Appendix C | Met |

## E.3 Proposal capabilities not delivered

Listed for completeness; discussed in Section 7.4.

| Capability | State | Evidence |
|------------|-------|----------|
| GROBID full-text parsing | Configuration flag only | No module; `ENABLE_GROBID` unused |
| Neo4j graph store | Configuration flags only | No driver integration |
| Study-level deduplication | 1:1 paper→study mapping | `dedupe_confidence` hardcoded 0.8 |
| Streamlit dashboard | Not implemented | Superseded by the React SPA |
| `EVENT_COUNT` semantic type | Model only | No pattern emits it |
| `UNKNOWN_NUMERIC` semantic type | Model only | No pattern emits it |
| Journal quality term | Constant 0.5 | `weighting.py` |

## E.4 Research questions to evidence

| RQ | Question | Answered in | Verdict |
|----|----------|-------------|---------|
| RQ1 | Reliable pattern-based extraction? | §6.4 | Partially, detection strong (F1 0.957), typing weak (0.60), confidence uncalibrated |
| RQ2 | Does text availability constrain more than accuracy? | §6.3 | Yes, 28% of papers lacked abstracts; all recoverable from a second provider |
| RQ3 | Defensible evidence-weighted ranking? | §6.5 | **Unproven**, plausible output, no relevance study, no baseline comparison |
| RQ4 | Fast enough, and what dominates? | §6.6 | Yes, 19 s mean; 63% network I/O, 2.5% analytics |
