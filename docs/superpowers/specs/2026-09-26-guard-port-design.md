# Guard port: Terminux → CiteGraph-NLP

Date: 2026-09-26
Source: `C:\Users\subha\Documents\PROJECTS\_mining\TERMINUX_GUARDS.md`
(Terminux guards pass, 95 families, pinned to `Ahad690/Terminux@5ddccbc`,
manifest SHA-256 `618fe03a…`.)

## Why

The Terminux catalogue is not a list of checks. Its finding is that a repository
gets unsafe when a check it *believes in* stops looking, starts passing on prose,
protects its own file, counts the wrong set, or prints a number after the action
changed it. This repository already has one real guard
(`tests/test_the_thesis_does_not_drift.py`, 437 lines, written 2026-09-25 after
three drift incidents found by hand) and it already contains two of those failure
shapes:

1. **A guard that stopped looking.** `test_the_thesis_does_not_drift.py:344` is
   `fitz = pytest.importorskip("fitz")`. If PyMuPDF is missing or half-installed,
   three PDF guards silently stop and the suite stays green. This is Terminux
   R19/R22 — "could not look" is not "clean".
2. **A hand-maintained registry that drifted.** `README.md` documented
   `score = 0.5 * PageRank + 0.3 * year_score + 0.2 * evidence_score` after
   `4c982f2` had changed the formula to the normalised `influence`. It was fixed
   by hand, in a session, not by a check. This is Terminux R14/C13 — two
   registries that must be compared in both directions.
3. Near-miss: `deploy-backend.yml` carried `46.225.8.77` as a fallback after that
   box was deleted on 2026-05-31.

So the port is not "add checks". It is: make every existing guard prove it still
looks, and add the ones whose absence has already cost something.

## Non-goals

- **The ECC material is out of scope.** `ECC_MINING_2.md` (45 hooks, 292 skills)
  is undecided and may not apply. Nothing from it is ported.
- **Terminux families guarding surfaces this app does not have are refused, not
  faked.** Auth/OAuth state binding (B26), billing rates (B16), tenancy (B17),
  GROBID/DB migrations (C10), the `gate_runner` product gates (G1–G7), workspace
  containment (B19), prompt scrubbing (B21). A guard that passes because nothing
  can violate it is the exact defect this port exists to remove. Every refusal is
  recorded in `guards/ledger.json` with its reason.

## The thirteen guards

Every guard file: `tests/test_<the property as a sentence>.py`, opening docstring
stating **one incident sentence** (or "not recorded" — no invented war stories),
then a red proof on the real regression, a negative control, and an
input-size floor. Terminux §5.8 items 1–18 are the writing checklist.

| # | Guard | Incident | Red proof |
|---|---|---|---|
| G1 | `test_the_test_job_proves_it_ran.py` | `tests.yml` emits no JUnit report, so green-with-nothing-ran is possible | delete the report path in a fixture; zero-testcase and skipped-case reports must be refused |
| G2 | `test_the_documented_response_fields_are_the_fields_the_api_returns.py` | README quoted the pre-`4c982f2` formula | a field present in the models and absent from the docs, and the inverse, both go red |
| G3 | `scripts/check_deployed_build.py` + `GET /version` | the deleted-box IP; nothing tied the running build to a commit | an unstamped, unknown, unreachable, and behind sha are each refused distinctly |
| G4 | `test_the_baseline_pin_is_not_above_reality.py` | the drift ratchet is one-sided: a stale pin never fails | a pin above the measured count goes red |
| G5 | `test_a_guard_that_cannot_look_does_not_report_clean.py` | `importorskip("fitz")` silently skips 3 PDF guards | simulate the missing dependency; the guard must fail, not skip |
| G6 | `test_no_source_file_carries_a_control_character.py` | R12 — a literal BACKSPACE where `\b` was meant made a checker pass green twice | the literal backspace fixture, plus a named-tree floor |
| G7 | `test_a_constant_is_not_defined_twice_in_one_file.py` | R13 — a fail-closed gate list redeclared as a dataclass field | a real double definition, and an allowance that is still needed |
| G8 | `test_no_secret_is_committed_to_this_tree.py` | R25–R30 — a scanner nobody has seen fail | one planted sample per detector, a clean-tree control, fail-closed on unreadable token-shaped values. **Blocks.** |
| G9 | `test_the_config_refuses_every_problem_at_once.py` | `enable_neo4j` starts with no password; the deploy already has to force `ENABLE_GROBID false` | production with no `api_key`, wildcard CORS, and neo4j-without-password each refuse; development does not |
| G10 | `test_a_rebaseline_must_carry_the_plan_it_printed.py` | P6/P7 — `rebaseline_thesis.py` mutates a committed baseline with no dry run | `--apply` without the printed token refuses; a stale token refuses |
| G11 | `test_the_ci_workflows_have_no_path_filters_and_one_always_runs.py` | C1–C3 — a `paths:` filter hid a fix until hand-dispatch | a workflow carrying `paths:` goes red |
| G12 | `test_every_guard_checker_has_a_caller.py` | "a correct check with no caller", the Terminux repo's recurring one | a checker with no workflow or test reference goes red |
| G13 | `test_the_guard_ledger_matches_the_guards_on_disk.py` | the count must not be mistaken for absence | a ledger row with no file, and a file with no row, both go red |

## Product changes (two, both small)

- **`GET /version`**, unauthenticated beside `/health`, returning
  `{"git_sha", "built_at"}` from `GIT_SHA`/`BUILD_TIME` env. The deploy passes
  `GIT_SHA=${{ github.sha }}` to `docker run`; no Dockerfile change.
- **`Settings.problems()`** in `src/citegraph/config.py`: collect *every*
  configuration fault, then refuse at startup in production. `enable_grobid`
  default becomes `False` (the deploy already overrides it to `false`, which is
  the honest default for a box with no GROBID service).

## Workflow changes

- `tests.yml`: `--junitxml`, upload the report, and a step that runs G1
  unconditionally — never inside the pytest step's `if`.
- `deploy-backend.yml`: pass `GIT_SHA`, then run `check_deployed_build.py` after
  the HTTPS health check.
- G11 forbids `paths:`/`paths-ignore:` on *guard-bearing* workflows. Deploy
  workflows keep their filters deliberately, and that exception is recorded in
  the guard rather than hidden in it.

## The ledger

`guards/ledger.json` — one row per Terminux family, all 95, each with
`id`, `name`, `status` (`ported` | `adapted` | `already_present` | `refused`),
`reason`, and the CiteGraph guard that carries it (`[]` when refused).
`guards/LEDGER.md` is the human table. G13 keeps the two in step with the files
on disk, both directions, non-empty.

## Verification

`python -m pytest -q` green, including the existing drift guard. Each new guard
additionally demonstrated red on its own regression before being committed — the
transcript of that is the guard's own docstring claim, and G6/G7/G12 carry the
fixture so the claim is executable. Thesis page and test counts are updated if
they move, as `test_the_thesis_does_not_drift.py` requires.
