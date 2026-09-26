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

Two of the planned guards changed shape while being written, and the ledger
records the result rather than the plan: the rebaseline plan-token guard was
folded into CG4, and the CI-workflow guard became CG12. `CG` is the id prefix
because Terminux's own product-gate families are `G1`–`G7`, and a ledger using
`G1` for two different things would be its own R14.

| id | Guard | Incident it answers | Red proof |
|---|---|---|---|
| CG1 | `test_the_test_job_proves_it_ran.py` + `scripts/check_test_report.py` | `tests.yml` emitted no JUnit report, so green-with-nothing-ran was possible | absent, malformed, empty, failing, erroring and skipping reports are each refused |
| CG2 | `test_the_documented_response_fields_are_the_fields_the_api_returns.py` | docs drifted from the code after `4c982f2` | a field in the models and not the docs, the inverse, and an undocumented route |
| CG3 | `scripts/check_deployed_build.py` + `GET /version` | the deleted-box IP; nothing tied the running build to a commit | unstamped, unknown, unreachable and behind are each refused distinctly |
| CG4 | `test_the_baseline_is_not_stale_in_either_direction.py` | the drift ratchet was one-sided, and the record lagged the thesis by two live sections | a hand-deleted and a hand-invented record entry are each visible |
| CG5 | `test_a_guard_that_cannot_look_does_not_report_clean.py` | `importorskip("fitz")` silently skips 3 PDF guards | hiding PyMuPDF flips the state to blind, both ways |
| CG6 | `test_no_source_file_carries_a_control_character.py` | R12 — a literal BACKSPACE where `\b` was meant | the literal backspace fixture, plus a tree-size floor |
| CG7 | `test_a_constant_is_not_defined_twice_in_one_file.py` | R13 — a fail-closed list redeclared as a dataclass field | a real twin, and the recorded incident's shape |
| CG8 | `test_no_secret_is_committed_to_this_tree.py` | R27 — a scanner nobody has seen fail is trusted when it reports clean | one planted sample per detector, a clean-tree control, a real address found in `.env.example` |
| CG9 | `test_the_config_refuses_every_problem_at_once.py` | `enable_grobid` defaulted on with no service; neo4j started with no password | production with no `api_key`, wildcard CORS and neo4j-with-placeholder all refuse; development does not |
| CG10 | `test_every_guard_checker_has_a_caller.py` | "a correct check with no caller" — two checkers had none | a name with no reference is an orphan |
| CG11 | `test_the_guard_ledger_matches_what_is_on_disk.py` | the count must not be mistaken for absence | an unclassified test file, a missing guard file, a stale rendered table |
| CG12 | `test_the_ci_workflows_have_no_path_filters_and_one_always_runs.py` | C1–C3 — a `paths:` filter hid a fix until hand-dispatch | a workflow carrying `paths:` goes red; an exemption that stops filtering goes red |
| CG13 | `test_the_thesis_does_not_drift.py` | the pre-existing guard, registered so the ledger covers it | already proven red — it caught a rounding error of mine and a stale file count during this work |

## Product changes (three, all small)

- **`GET /version`**, unauthenticated beside `/health`, returning
  `{"git_sha", "built_at", "version", "service"}` from `GIT_SHA`/`BUILD_TIME` env.
  The deploy passes `GIT_SHA=${{ github.sha }}` to `docker run`; no Dockerfile
  change.
- **`Settings.problems()`** in `src/citegraph/config.py`: collect *every*
  configuration fault with a severity, then refuse at startup in production.
  `enable_grobid` becomes `False` (the deploy already overrode it, which is how
  the wrong default was found).
- **`.env.example` holds `your_email@example.com`, not the real address.** The
  deploy's substitution for that placeholder had been dead code, because the
  template already held the real value, so the address was committed rather than
  injected.

## Workflow changes

- `tests.yml`: `--junitxml`, an unconditional step running
  `scripts/check_test_report.py`, an always-run artifact upload, and
  `fetch-depth: 0`.
- `deploy-backend.yml`: `fetch-depth: 0`, `GIT_SHA` and `BUILD_TIME` at
  `docker run`, a `/version` fetch from inside the box, and a step that proves
  the domain serves the build just deployed.
- CG12 forbids `paths:`/`paths-ignore:` on *check* workflows. Deploy workflows
  keep their filters deliberately, and each exemption is asserted still needed.

## The ledger

`guards/ledger.json` — one row per Terminux family, all 95, each with `id`,
`name`, `kind`, `status` (`ported` 35, `adapted` 17, `already_present` 10,
`refused` 33), `reason`, and the guards that carry it. `guards/LEDGER.md` is
generated from the same table and its hash is recorded, so it cannot go stale
unnoticed. `scripts/build_guard_ledger.py` is the single source; it asserts the
id set is exactly R1–30, C1–18, B1–28, P1–12, G1–7 before writing anything.

## Verification

`python -m pytest -q` — 268 passed, 0 skipped. Each new guard demonstrated red on
its own regression before being committed, and three of them found real defects
in this repository while being written: the dead `OPENALEX_EMAIL` substitution,
five documentation gaps, and the one-sided thesis record.

