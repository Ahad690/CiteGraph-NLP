"""Generate guards/ledger.json and guards/LEDGER.md from one table.

The table is the judgement; the two files are its rendering. Keeping it in a
script means the two artefacts cannot disagree, and re-running it after a guard is
renamed is a one-line change rather than an edit in two places.

`guards/ledger.json` is two registries, and
`tests/test_the_guard_ledger_matches_what_is_on_disk.py` holds them to the
filesystem in both directions:

  * `families` -- all 95 Terminux guard families, each with what happened to it
    here and the guards that carry it. A family with no guard is recorded as
    refused with its reason, so the count is never mistaken for absence.
  * `guards`  -- the guard artefacts in this repository, each with its path, the
    incident it answers, and the families it carries.
"""
import json
from pathlib import Path

ROOT = Path(r"C:\Users\subha\Documents\PROJECTS\CiteGraph-NLP")
OUT = ROOT / "guards"
SOURCE = ("_mining/TERMINUX_GUARDS.md, Terminux guards pass, 95 families, pinned to "
          "Ahad690/Terminux@5ddccbcaddb85170d3b2e207845d6daa07d26eba, manifest "
          "SHA-256 618fe03a11e519e97a1d3339c84955d85a1fed677c5585bc82c44e9717e38574")

# The guards this port added. The id space is CG* because Terminux's own product
# gate families are called G1..G7, and a ledger that used G1 for two different
# things would be its own R14.
GUARDS = [
    ("CG1", "tests/test_the_test_job_proves_it_ran.py",
     "The Tests job ran `pytest -q` and stopped there, so nothing downstream could "
     "tell a run of 205 tests from a run of none. Terminus kit item 1, R15, 5.6.5.",
     ["R15", "R22", "C4", "C5", "R9"], ["scripts/check_test_report.py"]),
    ("CG2", "tests/test_the_documented_response_fields_are_the_fields_the_api_returns.py",
     "README.md documented `score = 0.5 * PageRank + 0.3 * year_score + 0.2 * "
     "evidence_score` after 4c982f2 had replaced PageRank with the normalised "
     "`influence`. It was fixed by hand, in a session, not by a check. Terminux R14, "
     "C13, P10.",
     ["R14", "C13", "P10", "B28"], []),
    ("CG3", "scripts/check_deployed_build.py",
     "deploy-backend.yml carried 46.225.8.77 as a fallback after that box was deleted "
     "on 2026-05-31, and nothing tied the running container to the commit that was "
     "pushed. Terminus kit item 12, C15, C16, R17.",
     ["C15", "C16", "R17", "B7"], ["tests/test_the_deployed_build_reads_its_reply.py"]),
    ("CG4", "tests/test_the_baseline_is_not_stale_in_either_direction.py",
     "The drift guard compares the committed thesis record one way only, so deleting "
     "an entry from it by hand disabled protection for that section permanently, with "
     "no rebaseline and nothing in git log. The lag case was live: sections 5.6.4 and "
     "6.14.7 were unprotected from the day they were written. Terminus R2, R8, R16, "
     "C14, P6, P7, B5, B9, B12.",
     ["R2", "R8", "R16", "C14", "P6", "P7", "B5", "B9", "B12", "R3"], []),
    ("CG5", "tests/test_a_guard_that_cannot_look_does_not_report_clean.py",
     "test_the_thesis_does_not_drift.py:344 is `fitz = pytest.importorskip(\"fitz\")`, "
     "so a missing or half-installed PyMuPDF turned three PDF checks into a skip. A "
     "skip is green. Terminus R19, R22, R3, R6, R21, B8.",
     ["R19", "R22", "R3", "R6", "R21", "B8"], []),
    ("CG6", "tests/test_no_source_file_carries_a_control_character.py",
     "Terminus R12: two literal BACKSPACE bytes where `\\b` was intended made a "
     "checker report zero sites and pass green twice, because a pattern built from a "
     "byte nobody can see cannot fire.",
     ["R12", "R23"], []),
    ("CG7", "tests/test_a_constant_is_not_defined_twice_in_one_file.py",
     "Terminus R13: a fail-closed list of blocking gates was redeclared as a dataclass "
     "field and the two were kept equal by hand, so a floor written against one of "
     "them stopped matching when the other was edited.",
     ["R13", "R18", "R23"], []),
    ("CG8", "tests/test_no_secret_is_committed_to_this_tree.py",
     "Terminus R27 found ten real access tokens on its first run, and then shipped a "
     "pattern that matched nothing because a heredoc wrote a literal backspace. A "
     "scanner nobody has seen fail is trusted when it reports clean. R25-R30, P1-P3, "
     "B24, B28, G3.",
     ["R25", "R26", "R27", "R28", "R29", "R30", "P1", "P2", "P3", "B24", "B28", "G3"], []),
    ("CG9", "tests/test_the_config_refuses_every_problem_at_once.py",
     "enable_grobid defaulted to True on a box that runs no GROBID service, so "
     "deploy-backend.yml had to force it off on every deploy; enable_neo4j starts "
     "happily with no password; and an unset openalex_email silently uses the "
     "anonymous pool. Terminus B1, B3, B6, B7, B8, B15, P12, C11.",
     ["B1", "B3", "B6", "B7", "B8", "B15", "P12", "C11"], []),
    ("CG10", "tests/test_every_guard_checker_has_a_caller.py",
     "Terminus 5.7, 'a correct check with no caller': the merge refusal, the CSP "
     "check, the erasure plan and the reaper all existed with no production consumer. "
     "Terminus C18, R17.",
     ["C18", "R17"], []),
    ("CG11", "tests/test_the_guard_ledger_matches_what_is_on_disk.py",
     "The Terminux catalogue is explicit that a count must not be mistaken for "
     "absence. A ledger that lists a guard which does not exist, or omits one that "
     "does, is the same defect in the other direction. Terminus R14, kit item 11.",
     ["R14", "R23"], []),
    ("CG12", "tests/test_the_ci_workflows_have_no_path_filters_and_one_always_runs.py",
     "Terminus C1: a `**/*.md` path filter hid a documentation fix until someone "
     "dispatched the run by hand, and two history-scanning tests failed on the first "
     "CI run because the clone was depth-1. C2: four push runs were cancelled by a "
     "dispatch, and once the job that had to always run was itself made conditional. "
     "R15.",
     ["C1", "C2", "R15"], []),
    ("CG13", "tests/test_the_thesis_does_not_drift.py",
     "Written 2026-09-25 after three kinds of drift were found by hand in one "
     "afternoon: the abstract and four chapters still claiming the system read "
     "abstracts only, the appendix listing stale counts, and the page counts in two "
     "READMEs trailing the committed PDFs. It is the guard this port was measured "
     "against, and CG4 and CG5 exist because of what it was still missing.",
     ["R4", "R7", "R24", "P4", "P9"], []),
]

# Every remaining tests/test_*.py, classified rather than ignored. Hand-kept on
# purpose: a list derived from the filesystem would always agree with the
# filesystem, and the point is that adding a test file forces somebody to say
# whether it is a guard.
ORDINARY = {
    "test_add_citegraph_route.py": "asserts the nginx route helper writes a correct config",
    "test_api_comprehensive.py": "exercises the API's behaviour with mocked providers",
    "test_flow_diagram.py": "exercises the stage and layout rules the flow reader uses",
    "test_full_text_population.py": "exercises the open-access full-text fallback",
    "test_input_normalizer.py": "exercises identifier canonicalisation",
    "test_population_patterns.py": "exercises the extraction patterns and their ignore spans",
    "test_query_detection.py": "exercises query-type detection from the identifier's shape",
    "test_ranking.py": "exercises the foundational scoring and path ranking",
    "test_sqlite_store.py": "exercises persistence, lock retries and error classification",
    "test_task_manager.py": "exercises background task lifecycle and shutdown",
    "test_technical_evidence.py": "exercises field detection and dataset-size extraction",
    "test_url_resolver.py": "exercises URL to identifier extraction",
}

# (id, name, kind, status, guards, reason)
ROWS = [
    ("R1", "Unowned-obligation ratchet", "ratchet", "refused", [],
     "No requirement ledger with per-requirement owners exists here. The thesis has "
     "chapters, not a requirements table with an owner column, so there is no unowned "
     "count to hold still."),
    ("R2", "Pin-not-above-reality companion", "ratchet", "ported", ["CG4"],
     "The thesis record was allowed to lag the thesis, so a newly written section was "
     "unprotected until some later removal forced a rebaseline. CG4 requires the "
     "record to equal the thesis in both directions."),
    ("R3", "Gather-then-conclude ratchet", "ratchet", "ported", ["CG4", "CG5"],
     "Every comparison in the new guards asserts the size of the set it compared, so "
     "an empty extraction cannot agree with everything."),
    ("R4", "Every number says its path", "ratchet", "already_present", [],
     "The drift guard already compares each quoted count against the evidence file or "
     "PDF that produced it: test_technical_evidence, test_ranking_comparison, the "
     "figure counts and references_verified.json."),
    ("R5", "Owner-facing rule translations", "ratchet", "refused", [],
     "There is no rule registry and no owner to translate a rule for. The nearest "
     "surface, the documented API fields, is covered by CG2."),
    ("R6", "Infrastructure-gated test inventory", "ratchet", "adapted", ["CG5"],
     "The gated set here is three PDF checks that need PyMuPDF, which importorskip "
     "turned off silently. CG5 makes that absence a failure instead of a skip."),
    ("R7", "Specification baseline is not derived from its subject", "ratchet",
     "already_present", ["CG13"],
     "scripts/thesis_baseline.json is committed and the drift guard reads it from "
     "disk, with test_the_baseline_is_committed_rather_than_regenerated asserting "
     "that. Written 2026-09-25, before this port."),
    ("R8", "Re-baseline carries its reason", "ratchet", "ported", ["CG4"],
     "rebaseline_thesis.py already refused a reasonless rebaseline. CG4 extends it: "
     "the reason is appended to a history, a fall is named as a fall, and the original "
     "reason is carried forward rather than overwritten."),
    ("R9", "A message names what its branch tested", "ratchet", "adapted", ["CG1"],
     "check_test_report.py returns a named reason per failure shape (NO REPORT, NO "
     "TESTS, SKIPPED TESTS) rather than one message produced by one branch."),
    ("R10", "Generation tables accounted from migrations", "ratchet", "refused", [],
     "There is no schema and no migrations. Storage is a SQLite cache of provider "
     "responses, rebuilt from the providers rather than migrated."),
    ("R11", "No hand-rendered file:line", "ratchet", "refused", [],
     "No summariser interpolates line numbers. The scripts that report findings print "
     "whole file names, and the drift guard reports test names."),
    ("R12", "No control characters in source", "ratchet", "ported", ["CG6"],
     "Carried whole, including the literal-backspace red proof and the code-point "
     "construction that cannot be defeated by writing the wrong escape."),
    ("R13", "A constant is not defined twice in one file", "ratchet", "ported", ["CG7"],
     "Both shapes are carried: the same-scope twin, and the recorded incident of a "
     "fail-closed list redeclared as a dataclass field."),
    ("R14", "Tool registry both directions", "ratchet", "ported", ["CG2", "CG11"],
     "The registry here is the documented response fields against the models the API "
     "returns, and the guard ledger against the guards on disk. Both directions, both "
     "with a non-empty floor."),
    ("R15", "A guard's condition may not be its subject's condition", "ratchet",
     "ported", ["CG1", "CG12"],
     "The step that proves the suite ran has no `if:`, so the pytest step being "
     "conditional cannot take the proof with it. The report reader also lives outside "
     "tests/ so the suite carries no skip of its own."),
    ("R16", "A pin may not be the only owner of what it explains", "ratchet",
     "adapted", ["CG4"],
     "The record cannot be the authority on its own contents: CG4 recomputes it from "
     "the thesis, so hand-editing the record is visible."),
    ("R17", "Chokepoint wiring", "ratchet", "ported", ["CG3", "CG10"],
     "The deployed build is identified by a stamp the running service returns, and "
     "every checker is required to have a caller."),
    ("R18", "Fail-closed definition exactly once", "ratchet", "ported", ["CG7"],
     "A blocking list declared twice and kept equal by hand is the twin case."),
    ("R19", "Could-not-look is not refusal", "ratchet", "ported", ["CG5"],
     "Carried whole: a missing PyMuPDF is reported as blindness, not as a clean read "
     "over four unreadable PDFs."),
    ("R20", "One gate cannot silence the others", "ratchet", "refused", [],
     "There is no gate orchestrator with per-gate exception containment. pytest reports "
     "each test independently, so one exception cannot suppress the rest."),
    ("R21", "Has-this-ever-fired tri-state", "ratchet", "adapted", ["CG5"],
     "CG5's two states are looked and could-not-look. The third, ran-and-did-not-fire, "
     "is not carried: nothing in this repository keeps a durable firing record that "
     "could be confused with never having run."),
    ("R22", "A check that did not run is not a finding", "ratchet", "ported",
     ["CG1", "CG5"],
     "An unreadable report is refused rather than reported clean, and a guard that "
     "cannot look says which state it is in."),
    ("R23", "Correct-app false-positive family", "ratchet", "ported",
     ["CG1", "CG5", "CG6", "CG7", "CG11"],
     "Every new guard carries a negative control: the correct form must pass, or the "
     "guard is asserting nothing."),
    ("R24", "Deferred behaviour asserted as absence", "ratchet", "already_present", ["CG13"],
     "The drift guard's `claims` list retires statements that stop being true and "
     "fails if one comes back."),
    ("R25", "Invented-credential detector with supplied-key and wiring controls",
     "ratchet", "adapted", ["CG8"],
     "The method transfers: one planted sample per detector, a supplied-value "
     "exclusion, and a clean-tree control. The specimens do not: this application "
     "issues no browser API keys."),
    ("R26", "Provider-key pattern widened to the user base", "ratchet", "adapted",
     ["CG8"],
     "The method transfers. The key shapes do not: there is no user base holding "
     "third-party credentials, only the operator's own .env."),
    ("R27", "Pre-push scanner has a red proof", "ratchet", "ported", ["CG8"],
     "Each detector is driven by a planted sample, the scanner refuses an empty file "
     "set rather than reporting it clean, and a token-shaped value it cannot read "
     "fails closed."),
    ("R28", "Secrets gate has a clean control and one planted violation per rule",
     "ratchet", "ported", ["CG8"],
     "The clean-tree control and the planted-violation table are carried whole."),
    ("R29", "Gate coverage distinguishes skipped files from skipped checks", "ratchet",
     "adapted", ["CG8"],
     "CG8 reports which files it read and which it could not decode, beside the "
     "verdict, rather than folding them into the result."),
    ("R30", "A gate can name every rule it can emit, in both directions", "ratchet",
     "ported", ["CG8"],
     "The declared rule set and the rules the code can emit are compared both ways."),

    ("C1", "Full-history checkout and no path filters", "ci", "ported", ["CG12"],
     "tests.yml now fetches full history and carries no path filter. The two deploy "
     "workflows keep theirs, by name and with a stated reason, and the exemption is "
     "asserted to still be needed."),
    ("C2", "One always-running job and safe concurrency", "ci", "ported", ["CG12"],
     "CG12 requires a job with no `if:` in tests.yml. A concurrency group was added so "
     "a dispatch cannot cancel the authoritative push run."),
    ("C3", "Full dependency installation and explicit type/build steps", "ci",
     "already_present", [],
     "tests.yml installs requirements.txt and says why. No typechecker or bundler is "
     "configured for the backend, so there is no such step to add."),
    ("C4", "The test runner is allowed to finish", "ci", "adapted", ["CG1"],
     "There is no timeout to remove. A truncated run is caught from the other side: a "
     "report with fewer cases than the floor is refused."),
    ("C5", "A declared skip must be absent from a security-critical report", "ci",
     "ported", ["CG1"],
     "Any skipped testcase in the CI report is refused, and the report reader lives "
     "outside tests/ so the suite carries no skip of its own."),
    ("C6", "Static SQL rules must execute and fire on a plant", "ci", "refused", [],
     "There is no static SQL rule set; the store issues prepared statements through "
     "SQLAlchemy and there is no schema to police."),
    ("C7", "Isolation gate and its negative controls", "ci", "refused", [],
     "No tenant isolation exists to gate. The container is bound to loopback and the "
     "deploy asserts that binding, which is the isolation property this app has."),
    ("C8", "Per-run identity, never a pasted credential", "ci", "already_present", [],
     "There is no CI identity provider. The deploy mints a per-run SSH key from a "
     "secret, refuses when the secret is absent, and deletes the key with `if: "
     "always()`. That is the property this family protects."),
    ("C9", "Identity service pre-created, started, and probed", "ci", "already_present",
     [], "No identity service runs in CI. The container is started and probed by "
     "polling /health with an exit check, which is the same property for this "
     "deployment."),
    ("C10", "Migrations rebuild and replay; schema completeness is verified", "ci",
     "refused", [], "No schema and no migrations. Storage is a derived SQLite cache of provider responses, rebuilt by re-running a paper query rather than replayed forward."),
    ("C11", "CI must not be production, in either spelling", "ci", "adapted", ["CG9"],
     "APP_ENV is pinned to production only in the deploy's .env. CG9 makes that value "
     "load-bearing: production refuses to start on a missing api_key or a wildcard "
     "CORS origin, which is what running the wrong environment would produce."),
    ("C12", "No QA worker may hold the suite's database", "ci", "refused", [],
     "There is no QA worker and no shared database; the tests use respx and a "
     "temporary SQLite file."),
    ("C13", "Requirements ledger, both directions", "ci", "ported", ["CG2"],
     "Carried as the documented-field ledger: every field the models declare appears "
     "in the docs, and every field the docs promise exists in the models."),
    ("C14", "The coverage baseline is committed, and a drop must be deliberate", "ci",
     "adapted", ["CG4"],
     "There is no code-coverage baseline. The thesis record is committed, and a drop "
     "in it must now be named as a fall with its reason."),
    ("C15", "Deployment refuses a missing credential, then proves the domain serves "
     "the build", "ci", "ported", ["CG3"],
     "The deploy already refuses a missing SSH key. CG3 adds the second half: the "
     "domain must serve a build that is a known ancestor of the branch tip."),
    ("C16", "Running services must be current and stamped", "ci", "ported", ["CG3"],
     "GET /version returns the build stamp, and check_deployed_build.py refuses when "
     "it is unstamped, unknown, unreachable, or behind."),
    ("C17", "Backup is unconditional, non-empty, private, restore-target-checked",
     "ci", "refused", [],
     "There is no backup workflow. The only persistent state is a SQLite cache of "
     "provider responses, which is rebuilt by re-running a paper query."),
    ("C18", "Unwired and dated guard instruments", "ci", "ported", ["CG10"],
     "Every checker script is required to have a caller in a workflow or a test."),

    ("B1", "Aggregate environment refusal", "runtime", "ported", ["CG9"],
     "Settings.problems() collects every fault and the app refuses once, rather than "
     "reporting them one at a time across restarts."),
    ("B2", "Same-server identity", "runtime", "refused", [],
     "One host, one process, no cross-server identity to confuse with another."),
    ("B3", "No hidden model default; unrecognised endpoint refuses", "runtime",
     "ported", ["CG9"],
     "enable_grobid defaulted to True on a box that runs no GROBID service, so the "
     "deploy had to force it off. The default is now False and a GROBID URL that is "
     "pointed somewhere unreachable is a reported problem rather than a silent stall."),
    ("B4", "Endpoint-matched key names and redacted representation", "runtime",
     "refused", [],
     "There are no per-endpoint API keys to name, and no credential is read from "
     "anywhere but .env, so there is nothing to redact at a call site."),
    ("B5", "Command-prefix and far-side directory coherence", "runtime", "adapted",
     ["CG4"],
     "The write is bound to the plan that was read: --apply must carry the token the "
     "dry run printed, recomputed rather than trusted."),
    ("B6", "Limit sentinels, cross-key invariants, and template refusal", "runtime",
     "ported", ["CG9"],
     "Cross-setting invariants are checked as a set: neo4j enabled requires a "
     "password, production requires an api_key and a non-wildcard CORS origin."),
    ("B7", "Refuse before binding; lifespan refuses rather than falls back", "runtime",
     "ported", ["CG9", "CG3"],
     "A misconfigured production refuses to start rather than serving an open API on "
     "the public domain, and the served build is identifiable rather than anonymous."),
    ("B8", "Posture: degrade if absent, refuse if wrong; behavioural probe",
     "runtime", "ported", ["CG5", "CG9"],
     "A check that cannot run is not a red wall (CG5 reports blindness); a known-wrong "
     "configuration refuses (CG9)."),
    ("B9", "Assert the argv actually built", "runtime", "ported", ["CG4"],
     "The apply mode recomputes the plan token and compares, rather than reading a "
     "stored flag."),
    ("B10", "Measure capacity before allocating it", "runtime", "refused", [],
     "No capacity is allocated. default_max_total_papers bounds a traversal that is "
     "already in-process and already bounded per hop."),
    ("B11", "Mutation gate chokepoint", "runtime", "refused", [],
     "There is no mutating tool surface and no approver, so there is nothing for a "
     "gate to stand in front of."),
    ("B12", "Snapshot before irreversible mutation", "runtime", "adapted", ["CG4"],
     "The dry run prints the additions and the removals, and names a fall as a fall, "
     "before anything is written."),
    ("B13", "Patch safety with terminal/retryable split", "runtime", "refused", [],
     "No subsystem applies patches, so there is no format error to distinguish from a "
     "safety refusal."),
    ("B14", "Validate dependencies before fetching them", "runtime", "refused", [],
     "There is no manifest to validate before fetching: pip resolves from "
     "requirements.txt, which is itself the committed list."),
    ("B15", "Free-endpoint refusal, provider pin, pause ceiling, effort floor",
     "runtime", "adapted", ["CG9"],
     "The analogue is the provider toggles and the OpenAlex contact address. An unset "
     "openalex_email is reported as a problem in production rather than silently using "
     "the anonymous pool."),
    ("B16", "Rate is dated, unpriced is refused", "runtime", "refused", [],
     "There is no billing, no priced pair and no rate table to go stale, so there is nothing here for that family to protect."),
    ("B17", "Tenancy: allow-list tables, constrainable role, least privilege",
     "runtime", "refused", [],
     "The API is single-tenant with an optional shared api_key; there is no role, no "
     "per-tenant schema, and no 404-before-403 surface to protect."),
    ("B18", "Erasure completeness and positive record for deletion", "runtime",
     "refused", [],
     "There is no user data to erase. A run is a cached provider response plus a graph, "
     "both reproducible from the paper query."),
    ("B19", "Workspace containment and executor fail-closed", "runtime", "refused", [],
     "There is no agent executor and no workspace concept in the product. Nothing here runs a model or a command on a caller behalf, so there is nothing to contain."),
    ("B20", "Fixed tool surface; unknown tool mutates", "runtime", "refused", [],
     "There is no tool surface. The API surface is fixed and enumerated instead, and "
     "CG2 holds the documentation to it."),
    ("B21", "Prompt scrubbing, untrusted framing, cache-boundary refusal", "runtime",
     "refused", [],
     "No model is called by the product. scripts/second_annotator.py calls one, but it "
     "is an offline evidence tool that publishes open-access figures and sends no user "
     "data."),
    ("B22", "Locks, exit codes, template history, bundle refusal", "runtime",
     "already_present", [],
     "The SQLite store classifies lock errors from other errors, retries only the lock, "
     "and backs off with jitter. tests/test_sqlite_store.py drives it."),
    ("B23", "Apply only the migrations that were gated, to the named project",
     "runtime", "refused", [],
     "There is no migration runner and no second project on the box to confuse it "
     "with. The deploy does write to a named REMOTE_DIR and refuses rather than "
     "defaulting when it is not set."),
    ("B24", "Publishable key and config-globals contract", "runtime", "adapted", ["CG8"],
     "There is no publishable key. The config-globals half is carried: CG8 asserts "
     "that .env.example declares every setting Settings reads, and carries no value "
     "that is not a placeholder."),
    ("B25", "Credential scope, authenticated cipher, real-key and log-redaction refusals",
     "runtime", "refused", [],
     "The application holds no credential of its own; they arrive from .env through "
     "pydantic-settings and are never written to a store. The encrypted salvage "
     "archive that does hold credentials belongs to another project and is not in this "
     "repository."),
    ("B26", "OAuth state, PKCE, browser binding, single-use provider token", "runtime",
     "refused", [],
     "There is no OAuth flow. The API authenticates with a static optional api_key "
     "header, which is a weaker scheme and is not claimed to be this."),
    ("B27", "Ask the database whether the app can do its own job, for both roles",
     "runtime", "refused", [],
     "There is no second role and no database the application must prove it can reach."),
    ("B28", "Configuration contract: what the writer publishes and what the reader reads",
     "runtime", "ported", ["CG2", "CG8"],
     "Carried as the documented-field ledger in both directions, and as the "
     ".env.example / Settings contract."),

    ("P1", "Push-line stamper refuses while unpushed", "process", "ported", ["CG8"],
     "A scan that cannot see the range it was asked about refuses rather than "
     "reporting the range clean."),
    ("P2", "Report persistence refuses while unpushed", "process", "ported", ["CG8"],
     "The same property on the report side: an unreadable input is a refusal, not an "
     "empty result."),
    ("P3", "Pre-push wrapper refuses on scan failure or empty range", "process",
     "ported", ["CG8"], "Carried whole: the scanner fails closed on a decode error rather than counting the file as clean, which is the property the wrapper exists to provide."),
    ("P4", "Report-number checker treats not-found as failure", "process",
     "already_present", ["CG13"],
     "A quoted number that cannot be found in the PDF or the evidence file fails the "
     "drift guard rather than being skipped."),
    ("P5", "PRD delta merge is all-or-nothing", "process", "refused", [],
     "There is no PRD and no delta merge. build_thesis.py assembles the chapters, and "
     "the drift guard fails if the assembled document is not what the builder emits."),
    ("P6", "Purge requires the dry-run plan token", "process", "ported", ["CG4"],
     "rebaseline_thesis.py writes nothing without --apply carrying the token the dry "
     "run printed."),
    ("P7", "Rebaseline requires a reason", "process", "ported", ["CG4"],
     "And a reason of at least thirty characters, recorded in an append-only history."),
    ("P8", "Reachability from process entrypoints; tests are not roots", "process",
     "refused", [],
     "No entrypoint-rooted reachability sweep is implemented. The API's entrypoints are "
     "its routes and tests/test_api_comprehensive.py exercises them, but that is not "
     "the same claim and this ledger does not pretend it is."),
    ("P9", "Tracked files are the authority", "process", "already_present", ["CG13"],
     "The drift guard asserts the thesis record is git-tracked, so the committed file "
     "rather than a regenerated one is what is compared."),
    ("P10", "Coverage ledger, two directions and two owner classes", "process",
     "ported", ["CG2"],
     "The documented-field ledger is compared in both directions, with a non-empty "
     "floor on each side."),
    ("P11", "Same-box discipline tools refuse the wrong target", "process",
     "already_present", [],
     "deploy-backend.yml already refuses a Docker binding that is not 127.0.0.1:18030 "
     "and an nginx upstream that does not proxy to that port."),
    ("P12", "Positive record of deletable assets; sentinels on limits", "process",
     "adapted", ["CG9"],
     "The traversal limits are checked as sentinels: a non-positive depth or paper "
     "ceiling is a reported problem rather than a silent default."),

    ("G1", "Gate orchestration and fail-closed parsing", "gate", "refused", [],
     "There is no gate_runner. Design review, security review and design audit are "
     "people's jobs here, not a runner's."),
    ("G2", "Security / tenant isolation", "gate", "refused", [],
     "No tenant isolation exists to gate. The store is one SQLite file, and the isolation property this app does have -- the container bound to loopback -- is asserted by the deploy."),
    ("G3", "Secrets, XSS, and CSP", "gate", "adapted", ["CG8"],
     "Only the secrets third is carried. There is no server-rendered HTML to carry a "
     "CSP, and the frontend is a static bundle with no injection surface."),
    ("G4", "Code review", "gate", "refused", [],
     "No review gate. The equivalent control is the test suite plus the drift guard, "
     "which is a different thing and is not claimed as this."),
    ("G5", "Design audit", "gate", "refused", [],
     "No design-audit gate. The rendered PDFs and their page counts are checked, but "
     "that is a layout check, not an audit of the design."),
    ("G6", "Vision judgement layer", "gate", "refused", [],
     "No vision judgement layer with blocking authority. The flow-diagram reader is "
     "measured and reported in the thesis and holds no blocking authority anywhere."),
    ("G7", "Exposure probe and advisory surface", "gate", "adapted", ["CG5"],
     "The transferable half is that a probe which could not authenticate must not read "
     "as an empty exposure list, which is CG5's blindness state applied to a network "
     "probe. There is no exposure surface here to probe."),
]

KIND_LABEL = {"ratchet": "Ratchets and property tests", "ci": "CI and release guards",
              "runtime": "Boot and runtime refusals", "process": "Process guards",
              "gate": "Product gates"}

families = [{"id": i, "name": n, "kind": k, "status": s, "guards": g, "reason": r}
            for i, n, k, s, g, r in ROWS]
guards = [{"id": i, "path": p, "incident": inc, "families": f, "also": a}
          for i, p, inc, f, a in GUARDS]

WANT = {f"{p}{n}" for p, count in (("R", 30), ("C", 18), ("B", 28), ("P", 12), ("G", 7))
        for n in range(1, count + 1)}
assert len(families) == 95, f"expected 95 families, have {len(families)}"
assert {f["id"] for f in families} == WANT, \
    f"id set differs from R1-30 C1-18 B1-28 P1-12 G1-7: " \
    f"{sorted(WANT ^ {f['id'] for f in families})}"
known = {g["id"] for g in guards}
for family in families:
    for carried in family["guards"]:
        assert carried in known, f"{family['id']} names {carried}, which is not a guard here"
for guard in guards:
    for family in guard["families"]:
        assert family in WANT, f"{guard['id']} names {family}, which is not a Terminux family"
    assert len(guard["incident"]) >= 80, f"{guard['id']} has no incident worth reading"

carried = {f for family in families for f in family["guards"]}
for guard in guards:
    assert guard["id"] in carried or guard["id"] in {"CG2"}, \
        f"{guard['id']} is listed as a guard but no family names it"

ledger = {
    "_source": SOURCE,
    "_method": ("Read from _mining/TERMINUX_GUARDS.md. Every family is accounted for. A "
                "family with no guard is recorded as refused with the reason, so the "
                "count is never mistaken for absence. tests/"
                "test_the_guard_ledger_matches_what_is_on_disk.py holds this file, "
                "guards/LEDGER.md and the guards on disk in agreement, both directions."),
    "_counts": {status: sum(1 for f in families if f["status"] == status)
                for status in ("ported", "adapted", "already_present", "refused")},
    "families": families,
    "guards": guards,
    "ordinary": [{"path": f"tests/{name}", "why": why} for name, why in sorted(ORDINARY.items())],
}

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "ledger.json").write_text(json.dumps(ledger, indent=1) + "\n", encoding="utf-8", newline="\n")

lines = [
    "# Guard ledger", "",
    f"Every one of the **{len(families)}** guard families catalogued in the Terminux pass,",
    "and what happened to each one here. Generated by `scripts/build_guard_ledger.py`;",
    "`tests/test_the_guard_ledger_matches_what_is_on_disk.py` keeps this file,",
    "`ledger.json` and the guards on disk in agreement.", "",
    f"Source: {SOURCE}", "",
    "| | families |", "|---|---:|",
]
for status, count in ledger["_counts"].items():
    lines.append(f"| {status} | {count} |")
lines += [f"| **total** | **{len(families)}** |", "",
          "`ported` means a guard in this repository carries it. `adapted` means the",
          "method carries but the specimens or the surface do not. `already_present`",
          "means this repository had it before the port. `refused` means porting it would",
          "have produced a check that passes because nothing can violate it, which is the",
          "failure this whole exercise exists to remove.", "",
          "## The guards", "",
          "| id | file | answers | families |", "|---|---|---|---|"]
for guard in guards:
    also = "".join(f"<br>`{a}`" for a in guard["also"])
    lines.append(f"| {guard['id']} | `{guard['path']}`{also} | {guard['incident']} | "
                 f"{', '.join(guard['families'])} |")
lines += ["", "## Not guards", "",
          "Every other file in `tests/`, classified so the count above cannot be read as",
          "the size of `tests/`. Adding a test file means adding a line here or a guard",
          "above; `tests/test_the_guard_ledger_matches_what_is_on_disk.py` fails until one",
          "of the two happens.", "",
          "| file | what it does |", "|---|---|"]
for entry in ledger["ordinary"]:
    lines.append(f"| `{entry['path']}` | {entry['why']} |")
lines.append("")
for kind in ("ratchet", "ci", "runtime", "process", "gate"):
    group = [f for f in families if f["kind"] == kind]
    lines += [f"## {KIND_LABEL[kind]} ({len(group)})", "",
              "| id | family | status | guard | why |", "|---|---|---|---|---|"]
    for f in group:
        by = ", ".join(f"`{g}`" for g in f["guards"]) or "—"
        lines.append(f"| {f['id']} | {f['name']} | {f['status']} | {by} | "
                     f"{f['reason'].replace(chr(10), ' ')} |")
    lines.append("")

(OUT / "LEDGER.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")

# The rendered table is recorded by hash, so the guard that checks it is current
# can compare 64 characters instead of re-running this script. It used to `exec`
# the builder, which assembled the whole thesis and took the test suite from 47
# seconds to 168.
import hashlib  # noqa: E402

ledger["_ledger_md_sha256"] = hashlib.sha256(
    (OUT / "LEDGER.md").read_bytes()).hexdigest()
(OUT / "ledger.json").write_text(json.dumps(ledger, indent=1) + "\n",
                                 encoding="utf-8", newline="\n")

print("wrote ledger.json and LEDGER.md")
print("families:", len(families), "guards:", len(guards))
print("counts:", ledger["_counts"])
