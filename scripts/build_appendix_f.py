"""Regenerate the Appendix F per-file table from a real collection run.

Hand-counting a table of 33 files is how a table goes wrong: a test added in one
file and the total updated in another is exactly the drift the guard exists to
catch, and doing it by hand is doing the thing the guard is against.

So the counts come from pytest's own collector, and the descriptions are carried
over from the ledger so the two cannot disagree about what a file is.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APX = ROOT / "thesis" / "15-appendix-f-tests.md"

DESCRIPTIONS = {
    "test_api_comprehensive.py": "Endpoints, validation, clamping, auth, CORS, exports, pipeline",
    "test_query_detection.py": "Identifier auto-detection and the title matching behind run acceptance",
    "test_the_thesis_does_not_drift.py": "This thesis against its evidence, its figures, its PDFs",
    "test_flow_diagram.py": "Stage and layout rules of the flow-diagram reader (Section 6.14)",
    "test_technical_evidence.py": "Research-field detection, arXiv links and dataset-size extraction",
    "test_the_config_refuses_every_problem_at_once.py": "Configuration faults gathered in one pass",
    "test_the_documented_response_fields_are_the_fields_the_api_returns.py": "The documented fields",
    "test_no_secret_is_committed_to_this_tree.py": "Credential shapes, each driven by a planted sample",
    "test_nothing_needs_a_newer_python.py": (
        "That nothing in src/ needs a Python newer than the image runs, after a "
        "3.10 deploy failed on enum.StrEnum"
    ),
    "test_the_guard_ledger_matches_what_is_on_disk.py": "All 95 catalogued families accounted for",
    "test_sqlite_store.py": "Persistence, lock retry policy, backoff jitter, error classification",
    "test_the_ci_workflows_have_no_path_filters_and_one_always_runs.py": "No path filter on a workflow, and one that always runs",
    "test_the_test_job_proves_it_ran.py": "That the Tests job emits a JUnit report and asserts on it",
    "test_the_baseline_is_not_stale_in_either_direction.py": "The thesis record equal to the thesis",
    "test_every_guard_checker_has_a_caller.py": "Every `check_*` and `verify_*` script reachable from CI or a test",
    "test_the_deployed_build_reads_its_reply.py": "That the domain serves the build just deployed",
    "test_ranking.py": "Foundational scoring and path ranking",
    "test_add_citegraph_route.py": "Deployment route-insertion helper",
    "test_population_patterns.py": "Extraction patterns and ignore-span behaviour",
    "test_full_text_population.py": "The open-access full-text fallback of Section 5.2",
    "test_a_constant_is_not_defined_twice_in_one_file.py": "A constant bound twice in one scope",
    "test_a_guard_that_cannot_look_does_not_report_clean.py": "That the PDF checks in the drift guard can read",
    "test_no_source_file_carries_a_control_character.py": "Invisible control bytes",
    "test_task_manager.py": "Background task lifecycle and shutdown semantics",
    "test_url_resolver.py": "URL identifier extraction, DOI view-segment trimming",
    "test_input_normalizer.py": "Identifier canonicalisation",
    # Added with the two model providers.
    "test_config_env_alias.py": "The environment variable an operator sets is the one the code reads",
    "test_disambiguation.py": "A Jev answer is used only above the confidence bar",
    "test_evaluation_metrics.py": "The Wilson interval and the metrics the thesis quotes",
    "test_graph_exporters.py": "The JSON and GraphML exporters emit the real edges",
    "test_llm_providers.py": "The Jev and GLM request shapes, retries, and key redaction",
    "test_provider_budget.py": "The daily ceiling, its UTC day, and its append-only record",
    "test_provider_cache.py": "The content-hash cache key, and that a hit spends nothing",
    "test_report_route.py": "The report route's fallback when no provider is configured",
    "test_run_poll_interval.py": "That RunStatus carries the server's retry interval",
    "test_second_opinion_pass.py": "That the second-opinion pass changes nothing when disabled",
}


def counts() -> dict[str, int]:
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--collect-only"],
        cwd=ROOT, capture_output=True, text=True,
    )
    found: dict[str, int] = {}
    for line in out.stdout.splitlines():
        m = re.match(r"^tests/(test_\w+)\.py::", line.strip())
        if m:
            name = m.group(1) + ".py"
            found[name] = found.get(name, 0) + 1
    if not found:
        raise SystemExit("collected nothing; refusing to write a table of zeros")
    return found


def main() -> int:
    found = counts()
    total = sum(found.values())

    missing = sorted(set(found) - set(DESCRIPTIONS))
    if missing:
        raise SystemExit(
            f"no description for {missing}. A new test file forces a decision "
            f"about what it asserts, which is the point of the table."
        )

    rows = sorted(found.items(), key=lambda kv: (-kv[1], kv[0]))
    table = ["| File | Tests | Covers |", "|------|------:|--------|"]
    for name, n in rows:
        table.append(f"| `{name}` | {n} | {DESCRIPTIONS[name]} |")
    table.append(f"| **Total** | **{total}** | |")

    text = APX.read_text(encoding="utf-8")
    new_table = "\n".join(table)

    # Replace the existing table, from the header row to the Total row.
    replaced, count = re.subn(
        r"\| File \| Tests \| Covers \|\n\|------\|------:\|--------\|\n(?:\|.*\n)*\| \*\*Total\*\* \| \*\*\d+\*\* \| \|",
        new_table, text,
    )
    if count != 1:
        raise SystemExit(f"replaced {count} tables; expected exactly 1")
    APX.write_text(replaced, encoding="utf-8")

    print(f"wrote {len(found)} files, {total} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
