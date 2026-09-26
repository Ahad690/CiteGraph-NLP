"""Every checker in this repository has a caller.

Incident, from reading rather than from a failure. Two of the five scripts whose
names announce that they check something --
`scripts/check_reference_links.py` and `scripts/check_text_overlap.py` -- were
named by no workflow, no test and no line of the README. They had no caller at
all. Terminux 5.7 lists this twice: "a correct check with no caller" (the merge
refusal, the CSP check, the erasure plan, the capacity check and the reaper all
existed with no production consumer) and "a correct guard guarding nothing".

A checker nobody runs is worse than no checker, because the file's existence is
the evidence that somebody thought about the question. So every script named
`check_*` or `verify_*` must be reachable from a workflow, a test, or the README,
and the three manual checkers are now listed in the README rather than left
unmentioned.

The bar is higher for the guards than for the tools. A script in
`guards/ledger.json` must have a caller in a workflow or a test: a guard is a
claim about the repository, and a claim nothing runs is a claim nobody is making.

Ported from Terminus C18, R17 and 5.7. See `guards/ledger.json`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
WORKFLOWS = ROOT / ".github" / "workflows"
LEDGER = ROOT / "guards" / "ledger.json"

#: A script whose name announces that it checks something.
CHECKER_PREFIXES = ("check_", "verify_")

#: Calibrated against this tree: five checkers, two of them guards.
CHECKER_FLOOR = 5


def _texts() -> dict[str, str]:
    return {
        "workflow": "\n".join(p.read_text(encoding="utf-8")
                              for p in sorted(WORKFLOWS.glob("*.yml"))),
        "tests": "\n".join(p.read_text(encoding="utf-8")
                           for p in sorted((ROOT / "tests").glob("*.py"))),
        "readme": (ROOT / "README.md").read_text(encoding="utf-8"),
    }


def checkers() -> set[str]:
    return {p.stem for p in SCRIPTS.glob("*.py") if p.stem.startswith(CHECKER_PREFIXES)}


def callers(stem: str, texts: dict[str, str]) -> list[str]:
    """Where this script is mentioned. A workflow or a test is a caller that runs
    it; the README is a caller only for a tool somebody runs by hand, which is why
    the two are counted separately below."""
    return [where for where, body in texts.items() if re.search(rf"\b{re.escape(stem)}\b", body)]


def guard_scripts() -> set[str]:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    found: set[str] = set()
    for guard in ledger["guards"]:
        for path in [guard["path"], *guard.get("also", [])]:
            if path.startswith("scripts/"):
                found.add(Path(path).stem)
    return found


def test_the_caller_reader_finds_a_caller_and_does_not_invent_one():
    """The red proof. A reader that always reported a caller would pass this file
    while every checker went unwired, which is the state it exists to prevent."""
    texts = {"workflow": "run: python scripts/check_thing.py\n",
             "tests": "", "readme": ""}
    assert callers("check_thing", texts) == ["workflow"], \
        f"a workflow reference was not found: {callers('check_thing', texts)}"
    assert callers("check_absent", texts) == [], \
        f"a caller was invented for a script that does not exist: {callers('check_absent', texts)}"
    assert callers("check_thing", {"workflow": "check_thin", "tests": "", "readme": ""}) == [], \
        "a partial name was read as a caller"


def test_every_checker_has_a_caller():
    """The sweep. Workflow or test runs it; the README at least tells a reader it
    exists and when to run it."""
    texts = _texts()
    found = checkers()
    assert len(found) >= CHECKER_FLOOR, (
        f"only {len(found)} checkers were found, below the floor of {CHECKER_FLOOR}; the "
        f"prefix rule has probably stopped matching"
    )
    orphans = {stem: callers(stem, texts) for stem in sorted(found) if not callers(stem, texts)}
    assert not orphans, (
        f"{len(orphans)} script(s) announce that they check something and are named by no "
        f"workflow, no test and no documentation: {sorted(orphans)}. A checker nobody runs "
        f"is worse than no checker, because its existence is the evidence that the question "
        f"was considered"
    )


def test_a_guard_script_is_called_by_a_workflow_or_a_test_and_not_only_by_the_readme():
    """The higher bar. A guard is a claim about this repository, so being listed in
    a README table is not enough: something has to run it."""
    texts = _texts()
    guards = guard_scripts()
    assert guards, "the ledger names no scripts, so this check is comparing nothing"

    documentation_only = {}
    for stem in sorted(guards):
        where = callers(stem, texts)
        if where and not ({"workflow", "tests"} & set(where)):
            documentation_only[stem] = where
        elif not where:
            documentation_only[stem] = []
    assert not documentation_only, (
        f"{sorted(documentation_only)} are guards, or parts of one, and nothing runs them. "
        f"A guard is a claim; a claim nothing runs is not one"
    )


def test_the_readme_does_not_claim_a_checker_runs_in_ci_when_it_cannot():
    """The failure mode of the fix. Listing the two manual checkers in the README is
    correct; listing them as part of `pytest` or of the Tests job would be a lie
    that this file would then be enforcing."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    workflows = "\n".join(p.read_text(encoding="utf-8")
                          for p in sorted(WORKFLOWS.glob("*.yml")))
    for stem in sorted(checkers()):
        if stem in workflows:
            continue
        assert stem not in readme.split("### Guards")[0], (
            f"{stem} is named in the README outside the guards section but no workflow runs "
            f"it; say which job or script runs it, or move the mention"
        )
