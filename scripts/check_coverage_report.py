"""Read the coverage report and refuse when it does not describe a real run.

A coverage gate is only as honest as the report behind it, and the default
failure mode is silence rather than noise. `node --test test/*.test.js` with a
glob that matches nothing prints `1..0` and exits 0: green, having measured
nothing. `--cov-fail-under` has the same shape of hazard -- if the report is
absent, or present but describes no statements, there is no percentage to
compare and the gate has proved nothing while appearing to pass.

This script is that assertion, and it sits outside `tests/` for the same reason
`check_test_report.py` does (see its docstring): a guard that polices a set it is
a member of has to be moved out of the set, not exempted inside it.

    python scripts/check_coverage_report.py                # uses CITEGRAPH_COVERAGE_XML
    python scripts/check_coverage_report.py coverage.xml

Exits non-zero on a missing, empty, unreadable, or implausible report -- a report
it cannot read is refused, never reported clean: "could not look" is not "found
nothing" (Terminus R19).

The pass/fail threshold is deliberately NOT decided here. `--cov-fail-under`
belongs to the run that produced the numbers, so the comparison and the
measurement cannot drift apart. This script only answers the prior question:
did anything get measured at all?

See `guards/ledger.json`.
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

#: Set by tests.yml.
REPORT_ENV = "CITEGRAPH_COVERAGE_XML"

#: The package the suite is meant to measure. Coverage is taken with
#: --cov=src/citegraph, so the report's declared source root ends in this name.
#: It is matched against the *basename of the root the report itself declares*,
#: because the absolute root differs on every machine (a hardcoded path checks
#: nothing off-CI) and because measured filenames are relative to that root and so
#: never contain it -- an earlier version matched the substring "citegraph" in the
#: package names and failed every legitimate run.
SOURCE_PACKAGE = "citegraph"

#: A full run measures ~2,700 statements across ~38 modules. Anything an order of
#: magnitude below that is a partial collection, not a measurement of the package.
MINIMUM_STATEMENTS = 500

#: Line coverage outside this band means the report is misparsed, not remarkable.
PLAUSIBLE_LINE_RATE = (0.0, 1.0)


def inspect(report: Path) -> dict:
    """What a Cobertura report actually says. A missing file, an empty file and a
    malformed file are three different answers, because a check that cannot read
    the report must not report it clean."""
    empty = {"state": "no_report", "statements": 0, "files": 0, "line_rate": None,
             "packages": [], "source_root": "", "resolved": 0, "sampled": 0}
    if not report.is_file():
        return empty
    if report.stat().st_size == 0:
        return {**empty, "state": "empty_file"}
    try:
        root = ET.parse(report).getroot()
    except ET.ParseError as error:
        return {**empty, "state": f"unreadable: {error}"}

    if root.tag != "coverage":
        return {**empty, "state": f"not cobertura: root is <{root.tag}>"}

    packages = [p.get("name", "") for p in root.findall("./packages/package")]
    files = root.findall(".//class")

    # Prefer the sum of recorded lines: the header's line-rate is rounded, and a
    # ratchet built on a rounded number is a ratchet that can be rounded under.
    statements = len(root.findall(".//class/./lines/line"))
    if statements == 0:
        # Some emitters omit empty <lines> elements; fall back to the header.
        try:
            statements = int(float(root.get("lines-valid", "0") or 0))
        except ValueError:
            statements = 0

    try:
        line_rate: float | None = float(root.get("line-rate", "") or 0)
    except ValueError:
        line_rate = None

    # Measured filenames are relative to the source root, and the report says
    # what that root is in <sources><source>. Resolve against the report's own
    # root rather than a path guessed here: the absolute root differs on every
    # machine, and a hardcoded one silently checks nothing off-CI.
    source_root = ""
    node = root.find("./sources/source")
    if node is not None and node.text:
        source_root = node.text.strip()

    sampled = [c.get("filename", "") for c in files if c.get("filename")]
    resolved = 0
    if source_root:
        base = Path(source_root)
        resolved = sum(1 for name in sampled if (base / name).is_file())

    return {"state": "read" if files else "no_classes", "statements": statements,
            "files": len(files), "line_rate": line_rate, "packages": packages,
            "source_root": source_root, "resolved": resolved, "sampled": len(sampled)}


def verdict(found: dict) -> list[str]:
    """Every reason this report does not prove a real measurement. Empty means proved."""
    if found["state"] != "read":
        return [f"NO REPORT: {found['state']}; coverage proved nothing"]

    problems: list[str] = []
    if found["files"] == 0:
        problems.append("NO FILES: report describes no measured modules")
    if found["statements"] < MINIMUM_STATEMENTS:
        problems.append(
            f"TOO FEW STATEMENTS: {found['statements']}, below the floor of "
            f"{MINIMUM_STATEMENTS}. This is a partial collection, not a measurement "
            f"of the source tree"
        )
    if not found["source_root"]:
        problems.append(
            "NO SOURCE ROOT: report declares no <sources><source>, so its filenames "
            "cannot be resolved and the measurement cannot be located"
        )
    elif Path(found["source_root"]).name != SOURCE_PACKAGE:
        problems.append(
            f"WRONG PACKAGE: measured {Path(found['source_root']).name!r}, expected "
            f"{SOURCE_PACKAGE!r}"
        )
    elif found["resolved"] == 0:
        problems.append(
            f"WRONG TREE: none of the {found['sampled']} measured files exist under "
            f"the declared source root, so this report describes some other tree"
        )
    rate = found["line_rate"]
    if rate is None or not (PLAUSIBLE_LINE_RATE[0] <= rate <= PLAUSIBLE_LINE_RATE[1]):
        problems.append(f"IMPLAUSIBLE line-rate: {rate!r}")
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
    percent = (found["line_rate"] or 0) * 100
    print(
        f"coverage genuinely measured: {found['statements']} statements across "
        f"{found['files']} modules, {percent:.1f}% lines"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
