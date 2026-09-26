# Appendix F: Test Suite and Verification Inventory

## F.1 Composition

272 automated tests across 25 files. All external HTTP is intercepted at
transport level by `respx` or replaced with test doubles, so the suite requires
no network access and no API credentials, and completes in roughly 15 to 40
seconds.

Thirteen of the 25 files are behaviour tests: they assert that the system does
something. The other twelve are guards, and they assert something different —
that a check still works. `guards/LEDGER.md` records all 95 guard families
catalogued from another project, what happened to each one here, and why 33 were
refused rather than ported.

| File | Tests | Covers |
|------|------:|--------|
| `test_api_comprehensive.py` | 73 | Endpoints, validation, clamping, auth, CORS, exports, pipeline end-to-end with mocked providers |
| `test_query_detection.py` | 34 | Identifier auto-detection and the title matching behind run ac66eb9e |
| `test_the_thesis_does_not_drift.py` | 20 | This thesis against its evidence, its figures, its PDFs and its baseline (Section C.5) |
| `test_flow_diagram.py` | 18 | Stage and layout rules of the flow-diagram reader (Section 6.14) |
| `test_technical_evidence.py` | 12 | Research-field detection, arXiv links and dataset-size extraction |
| `test_the_config_refuses_every_problem_at_once.py` | 11 | Configuration faults gathered in one pass; production refuses a wildcard CORS origin, an empty origin list, a Neo4j profile with a placeholder password, and a key that is set but too short. The deployed values must start, and the open API is reported |
| `test_the_documented_response_fields_are_the_fields_the_api_returns.py` | 8 | The documented field tables against the Pydantic models, both directions, and every route against the documents that name it |
| `test_no_secret_is_committed_to_this_tree.py` | 8 | Credential shapes, each driven by a planted sample; a real contact address in a template; the `.env.example`/`Settings` contract |
| `test_the_guard_ledger_matches_what_is_on_disk.py` | 6 | All 95 catalogued families accounted for, every guard on disk classified, the generated table current |
| `test_sqlite_store.py` | 8 | Persistence, lock retry policy, backoff jitter, error classification |
| `test_the_ci_workflows_have_no_path_filters_and_one_always_runs.py` | 8 | No path filter on a workflow that runs checks, one always-running job, full-history checkout, each deploy exemption still needed, and no variable the deploy sends to the box that it does not pass |
| `test_the_test_job_proves_it_ran.py` | 5 | That the Tests job emits a JUnit report and asserts on it in a step no `if:` can disable |
| `test_the_baseline_is_not_stale_in_either_direction.py` | 4 | The thesis record equal to the thesis in both directions; a fall keeps its reason; a dry run writes nothing |
| `test_every_guard_checker_has_a_caller.py` | 4 | Every `check_*` and `verify_*` script reachable from a workflow, a test or the documentation |
| `test_the_deployed_build_reads_its_reply.py` | 4 | That the domain serves the build just deployed, and can say so apart from a network failure |
| `test_ranking.py` | 8 | Foundational scoring and path ranking |
| `test_add_citegraph_route.py` | 7 | Deployment route-insertion helper |
| `test_population_patterns.py` | 6 | Extraction patterns and ignore-span behaviour |
| `test_full_text_population.py` | 6 | The open-access full-text fallback of Section 5.2 |
| `test_a_constant_is_not_defined_twice_in_one_file.py` | 3 | A constant bound twice in one scope, and one redeclared as a dataclass field |
| `test_a_guard_that_cannot_look_does_not_report_clean.py` | 3 | That the PDF checks in the drift guard are reading, rather than skipping on a missing PyMuPDF |
| `test_no_source_file_carries_a_control_character.py` | 3 | Invisible control bytes, which turn a pattern into one that cannot fire |
| `test_task_manager.py` | 5 | Background task lifecycle and shutdown semantics |
| `test_url_resolver.py` | 5 | URL→identifier extraction, DOI view-segment trimming |
| `test_input_normalizer.py` | 3 | Identifier canonicalisation |
| **Total** | **272** | |

## F.2 Regression tests added during evaluation

Each corresponds to a defect in Chapter 5, and each fails against the
pre-correction code.

| Test | Pins |
|------|------|
| `test_count_survives_a_year_in_the_same_sentence` | A sample size beside a date is not discarded (§5.5). Asserts 1099 is extracted and 2020 is not. |
| `test_percentage_in_sentence_does_not_discard_count` | A percentage elsewhere in the sentence does not suppress the count |
| `test_year_alone_is_not_a_population` | A bare year is still never read as a population |
| `test_observational_phrasings_are_extracted` | *cases*, *a total of*, *consecutive patients*, *screened* phrasings (§5.5) |
| `test_doi_extraction_strips_publisher_view_segments` | `/full`, `/pdf`, `/abs` trimmed from URL-embedded DOIs (§5.7) |
| `test_doi_with_legitimate_slashes_is_preserved` | Trimming never damages a DOI that genuinely contains slashes |
| `test_export_csv_escapes_special_characters` | Commas, quotes and newlines in titles do not break CSV rows (§5.8) |
| `test_export_edges_csv`, `test_export_graphml` | Endpoints exist and produce parseable output |
| `test_start_run_rejects_pdf_path_outside_uploads` | Path confinement on `pdf_path` |
| API-key and CORS suites | Auth gating and origin restriction (§5.9) |

## F.3 Defects found *in the test suite itself*

Two, both recorded because a test suite is software subject to the same faults
as the system it verifies.

**A hang, not a failure.** `test_uncooperative_task_does_not_hang_past_timeout`
constructed a task that suppresses `CancelledError`, then cleaned up with
`asyncio.wait_for`. On timeout, `wait_for` cancels the task *and awaits the
cancellation*, which never completes for a task that refuses to die. The entire
pytest session hung indefinitely. The name is unintentionally accurate: the test
for not hanging was the thing that hung. Resolved by giving the fake task a stop
event and waiting with `asyncio.wait`, which always returns.

**A double that could not exercise the code path.** `test_get_run_also_retries_
under_lock` replaced `aiosqlite`'s `execute` with a bare `async def`. The real
method is wrapped so its return value supports both `await` and `async with`; a
plain coroutine supports only `await`. The production read path uses
`async with`, so the test failed with a `TypeError` about the coroutine
protocol rather than exercising the retry policy it was written to verify.
Resolved by wrapping the doubles in aiosqlite's own `Result`.

## F.4 What the suite does not establish

Stated because Section 5.10 turns on it. Throughout the period in which the
traversal was discarding roughly half of every graph, forward citations were
universally empty, and every edge weight was zero, **the suite passed in full**.

It did so because it asserted *shape*, not *correctness*: that a run completed,
that the response carried the expected fields, that the types were right. No
test asserted that the number of retrieved nodes bore any relation to the number
of references the provider reported, that forward edges ever existed, or that
edge weights varied between papers.

The suite is a regression guard, not a correctness argument. Correctness for
this system required measurement against independently known quantities, which
is what Chapter 6 reports.

## F.5 Manual verification performed

Checks carried out by inspection or ad-hoc measurement rather than automated
tests, listed so the evidence base is complete.

| Check | Method | Section |
|-------|--------|---------|
| SSRF guard blocks internal addresses | Local HTTP listener; verified zero requests received | §5.7 |
| Redirect pivot to internal host refused | Mocked 302 from a public host to loopback | §5.7 |
| Connection pooling benefit | 8 sequential requests, pooled versus per-request client | §6.6.3 |
| Path ranking equivalence | Top-ten compared against exhaustive enumeration | §6.6.4 |
| Weighting ordering after correction | Synthetic resolutions across n_eff and confidence | §5.6 |
| Duplicate merging | Title-key collision check over produced graphs | §6.5 |
| Reference resolution | Every DOI resolved against Crossref/OpenAlex | §6.7 |
| Deployment isolation | Container port confirmed bound to loopback | §5.9 |
