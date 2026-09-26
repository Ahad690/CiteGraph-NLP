"""Read the JUnit report and refuse when it does not show a real run.

Incidents. Terminus kit item 1 (`.github/workflows/ci.yml:499-517`,
`scripts/ci/assert_tests_ran.py:12-30,59-89`): a recorded run was green while both
the database suites and the guard against them were skipped by the same missing
credential. Terminus R15: a guard that skips under the condition that causes the
skip is a green run having executed nothing -- 2,772 tests had never run in CI.
Terminus 5.6.5: "CI was green having run zero tests", fixed by an always-running
job plus a separate assertion that the report exists, contains tests, and contains
no skipped cases.

This script is that assertion. It lives outside `tests/` on purpose. The first
version of it was a test in the suite, reading the report the suite had just
written -- so the suite contained one guaranteed skip, which is a `<skipped/>` in
the very report it was asserting had no skips. A guard that polices a set it is
a member of has to be moved out of the set, not exempted inside it (Terminux 5.2,
"relocate a self-referential guard; do not exempt it").

    python scripts/check_test_report.py            # uses CITEGRAPH_JUNIT_XML
    python scripts/check_test_report.py path.xml

Exits non-zero on a missing, empty, unreadable, failing or skipping report. A
report it cannot read is refused, never reported clean: "could not look" is not
"found nothing" (Terminus R19).

See `guards/ledger.json`.
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

#: Set by tests.yml.
REPORT_ENV = "CITEGRAPH_JUNIT_XML"

#: A full run of this repository's suite is 220-odd tests. A report with fewer is
#: a report from something else, or a collection that failed.
MINIMUM_CASES = 200


def inspect(report: Path) -> dict:
    """What a JUnit report actually says. A missing file, an empty file and a
    malformed file are three different answers, because a check that cannot read
    the report must not report it clean."""
    if not report.is_file():
        return {"state": "no_report", "cases": 0, "skipped": [], "failures": [], "errors": []}
    try:
        root = ET.parse(report).getroot()
    except ET.ParseError as error:
        return {"state": f"unreadable: {error}", "cases": 0, "skipped": [],
                "failures": [], "errors": []}

    cases = root.findall(".//testcase")
    skipped = [c.get("name", "?") for c in cases if c.find("skipped") is not None]
    failures = [c.get("name", "?") for c in cases if c.find("failure") is not None]
    errors = [c.get("name", "?") for c in cases if c.find("error") is not None]
    return {"state": "read" if cases else "no_cases", "cases": len(cases),
            "skipped": skipped, "failures": failures, "errors": errors}


def verdict(found: dict) -> list[str]:
    """Every reason this report does not prove a real run. Empty means proved."""
    problems: list[str] = []
    if found["state"] != "read":
        return [f"NO REPORT: {found['state']}; the job proved nothing"]
    if found["cases"] < MINIMUM_CASES:
        problems.append(f"NO TESTS: {found['cases']} testcases, below the floor of {MINIMUM_CASES}")
    if found["errors"]:
        problems.append(f"ERRORED: {found['errors'][:10]}")
    if found["failures"]:
        problems.append(f"FAILED: {found['failures'][:10]}")
    if found["skipped"]:
        problems.append(
            f"SKIPPED TESTS: {len(found['skipped'])} did not run: {found['skipped'][:10]}. "
            f"A skip is green, so a suite that skipped everything is green having run nothing")
    return problems


def main(argv: list[str]) -> int:
    named = argv[1] if len(argv) > 1 else os.environ.get(REPORT_ENV, "")
    if not named:
        print(f"REFUSING: no report named. Pass a path or set {REPORT_ENV}.")
        return 2
    found = inspect(Path(named))
    problems = verdict(found)
    if problems:
        for problem in problems:
            print(problem)
        return 1
    print(f"{found['cases']} tests genuinely executed, none skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
