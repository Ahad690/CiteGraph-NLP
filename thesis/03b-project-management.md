# Chapter 3 (continued): Project Management

## 3.6 Team Organisation

Three members worked across a pipeline that decomposes naturally into
independent modules with narrow interfaces. Work was organised by module rather
than by person, into the four areas below, so that two people rarely edited the
same file; review was shared, and the fourth area was covered jointly.

| Area | Primary responsibility |
|------|------------------------|
| Provider layer, metadata resolution, identifier canonicalisation | Retrieval |
| Citation traversal, graph construction, analytics | Graph |
| Population extraction, resolution, pattern design | NLP |
| API, dashboard, deployment, CI | Delivery |

The module boundaries described in Chapter 4 were as much a coordination
mechanism as an architectural one. Because the provider layer exposes a fixed
`ProviderResult` contract, the retrieval and graph work proceeded in parallel
against a stub; because the extractor consumes plain text and emits candidates,
the NLP work was testable without a working traversal.

This had a cost that Chapter 5 makes visible. Clean interfaces let each module
be tested in isolation, and each module *was* correct in isolation. The
traversal defect (Section 5.3) lived precisely at the seam, the traversal
correctly asked the resolver for a paper, and the resolver correctly rejected
an identifier it was never designed to receive. Both sides behaved as
specified. Interface-level correctness does not compose into system-level
correctness, and nothing in the division of labour was positioned to notice.

## 3.7 Development Timeline

| Phase | Focus | Outcome |
|-------|-------|---------|
| Proposal and feasibility | Scope definition; feasibility assessment of each component | Full-text parsing descoped; abstract-only pipeline adopted |
| Design | PRD, data models, architecture | Module contracts fixed |
| Core implementation | Providers, resolver, traversal, extractor, graph | End-to-end pipeline producing output |
| Interface | REST API, React dashboard, exports | System usable by a non-author |
| Deployment | Containerisation, CI, hosting, TLS | Publicly reachable instance |
| **Measurement and correction** | **Instrumentation, evaluation harness, defect resolution** | **Eight defects found; evaluation plan implemented** |
| Documentation | Thesis, reproducibility artifacts | This document |

The final phase is the one worth commentary. It was originally scoped as
"testing and documentation", a wrap-up phase. It became the phase in which most
of the project's substantive faults were found, because it was the first time
the system was measured rather than exercised.

Had the evaluation harness been built when the proposal specified it, the same
defects would have surfaced months earlier and at lower cost. The empty
`evaluation/` directory was, in retrospect, the single most informative artifact
in the repository, and nobody read it as a warning.

## 3.8 Risk Management

Risks identified during planning, with what actually happened.

| Risk | Planned mitigation | Outcome |
|------|--------------------|---------|
| Scholarly APIs rate-limit or block the client | Honour polite-pool conventions; identify the caller | Did not materialise. Polite-pool identification also improved latency (§C.1) |
| Reference-list coverage is incomplete | Query several providers and merge | **Materialised, worse than expected.** Crossref holds no reference list for many works; the mitigation was necessary rather than precautionary (§5.3) |
| Full-text access is legally constrained | Restrict to abstracts | Materialised as predicted by the feasibility study; abstract-only scope adopted from the outset, with a fallback to open-access XML full text added later (§5.2) |
| Population extraction is too inaccurate to be useful | Pattern-based approach with confidence scoring | Partially materialised: detection is strong, **type classification and confidence calibration are not** (§6.4) |
| A single provider becomes unavailable | Provider toggles; degrade rather than abort | Not triggered in practice; the degradation path is implemented and tested |
| Graph algorithms do not scale | Bound the graph size | Over-mitigated. Analytics are 2.5% of runtime (§6.6.1); the real cost was network I/O |

Two risks were *not* on the register and caused more disruption than those that
were:

**Silent data loss inside the pipeline.** No risk entry anticipated that the
system might run to completion while discarding most of its input. The register
was oriented toward external failures, APIs down, rate limits, legal limits,
and assumed internal correctness would follow from testing.

**A test suite that passes while the system is wrong.** The plan treated tests
as the verification mechanism. Section 5.10 and Appendix F.4 record why that was
insufficient for a system whose output is a ranked list.

## 3.9 Tools and Infrastructure

| Purpose | Tool |
|---------|------|
| Version control | Git / GitHub |
| Continuous integration | GitHub Actions |
| Backend hosting | Docker on a shared Linux host, nginx, Let's Encrypt |
| Frontend hosting | Cloudflare Pages |
| Run persistence | SQLite |
| Testing | pytest, pytest-asyncio, respx |
| Documentation | Markdown; Pandoc for rendering |

Deployment is automated from the main branch: backend changes rebuild the
container and restart it behind nginx; frontend changes rebuild the static
bundle and publish it. The backend container binds the loopback interface only,
because the host is shared with unrelated services, a constraint that produced
its own defect, recorded in Section 5.9.

## 3.10 Lessons for Process

Three conclusions the team would carry forward.

**Build the measurement harness with the first module, not after the last.**
The evaluation plan existed from the proposal. Deferring it deferred all the
information it would have produced.

**Prefer measurements over assertions for pipelines.** A test that a stage
returns the right *shape* is cheap and weak. A measurement compares a stage's
output against a quantity known independently: how many references the provider
reported, or what a human read in the abstract. That costs more to build and is
far stronger.

**Treat silence as suspicious.** Every defect in Chapter 5 was silent: a
warning-level log, an HTTP 200 with an empty result, a falsy value coerced to a
default. A pipeline stage that never reports anything is not necessarily a stage
that never has anything to report.
