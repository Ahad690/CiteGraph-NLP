"""The test job is wired to prove it ran.

Incidents. Terminus kit item 1 (`.github/workflows/ci.yml:499-517`,
`scripts/ci/assert_tests_ran.py:12-30,59-89`): a recorded run was green while both
the database suites and the guard against them were skipped by the same missing
credential. Terminus R15: a guard that skips under the condition that causes the
skip is a green run having executed nothing -- 2,772 tests had never run in CI.
Terminus 5.6.5: "CI was green having run zero tests".

This repository's `tests.yml` ran `python -m pytest -q` and stopped there, so
nothing downstream could tell a run of 205 tests from a run of none.

Reading the report is `scripts/check_test_report.py`'s job, deliberately not this
file's. The first version put the reader in the suite, reading the report the
suite had just written -- which guaranteed one `<skipped/>` in the very report it
was asserting had none. A guard that polices a set it belongs to is moved out of
the set, not exempted inside it (Terminux 5.2).

So this file checks the two things that need no report and can therefore be checked
everywhere: that the workflow asks for a report at all, and that the step which
asserts on it cannot be switched off. The report's contents are driven as the red
proof of the reader, so this file still fails if the reader stops working.

Ported from Terminus kit item 1, R15 and 5.6.5, catalogued in
`_mining/TERMINUX_GUARDS.md` 2.1 and 4.B. See `guards/ledger.json`.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
READER = ROOT / "scripts" / "check_test_report.py"


def _reader():
    spec = importlib.util.spec_from_file_location("check_test_report", READER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def steps() -> list[dict]:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return [step for job in (document.get("jobs") or {}).values()
            for step in (job or {}).get("steps", []) or []]


def test_the_reader_refuses_every_report_that_does_not_prove_a_run():
    """The red proof, in all five shapes: absent, malformed, empty, failing and
    skipping. A reader that treats any of them as clean is the failure this file
    exists to prevent, so each is driven here rather than assumed."""
    reader = _reader()
    scratch = ROOT / ".pytest_cache" / "g1"
    scratch.mkdir(parents=True, exist_ok=True)

    def write(name: str, text: str) -> Path:
        path = scratch / name
        path.write_text(text, encoding="utf-8")
        return path

    suite = ('<testsuites><testsuite name="pytest">{}</testsuite></testsuites>')
    cases = {
        "absent": None,
        "malformed": "<testsuites><testsuite>",
        "empty": suite.format(""),
        "failing": suite.format('<testcase name="test_c"><failure message="x"/></testcase>'),
        "erroring": suite.format('<testcase name="test_d"><error message="x"/></testcase>'),
        "skipping": suite.format('<testcase name="test_b"><skipped/></testcase>'),
        "healthy": suite.format('<testcase name="test_a"/>'
                                + '<testcase name="test_b"/>'.replace("test_b", "test_z")
                                * (reader.MINIMUM_CASES - 1)),
    }
    try:
        for name, text in cases.items():
            path = scratch / f"{name}.xml"
            if text is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(text, encoding="utf-8")
            problems = reader.verdict(reader.inspect(path))
            if name == "healthy":
                assert not problems, f"a full clean run was refused: {problems}"
            else:
                assert problems, (
                    f"a {name} report produced no refusal, so the reader would treat it as "
                    f"proof that the suite ran"
                )
    finally:
        for name in cases:
            (scratch / f"{name}.xml").unlink(missing_ok=True)


def test_the_workflow_asks_pytest_for_a_report():
    """Without this the reader has nothing to read, and the reader refusing an
    absent report would fail every run for the wrong reason."""
    assert "--junitxml" in WORKFLOW.read_text(encoding="utf-8"), \
        f"{WORKFLOW.name} does not ask pytest for a JUnit report"


def test_the_assertion_step_runs_and_cannot_be_switched_off():
    """Terminus R15: a guard skipped by the same condition that causes the skip.
    The assertion is a step in its own right, with no `if:`, so the pytest step
    being conditional cannot take the proof with it."""
    all_steps = steps()
    assert all_steps, f"{WORKFLOW.name} has no steps"

    readers = [s for s in all_steps if "check_test_report.py" in str(s.get("run", ""))]
    assert readers, (
        f"{WORKFLOW.name} never runs scripts/check_test_report.py, so a green run still "
        f"says nothing about whether anything executed"
    )
    for step in readers:
        assert "if" not in step, (
            f"the step that proves the suite ran is conditional: {step.get('name')}. "
            f"That is how a suite and the guard against it get skipped together"
        )
        assert "continue-on-error" not in step, \
            f"the proof step ignores errors, so it cannot fail: {step.get('name')}"


def test_the_report_is_uploaded_whether_or_not_the_suite_passed():
    """A report that only exists on a green run is a report nobody reads when it
    matters."""
    uploads = [s for s in steps() if "upload-artifact" in str(s.get("uses", ""))]
    assert uploads, f"{WORKFLOW.name} does not upload the report, so a failed run leaves no evidence"
    assert any("always()" in str(s.get("if", "")) for s in uploads), \
        "the report upload is conditional, so a failed suite produces no report to read"


def test_the_reader_is_not_part_of_the_suite_it_polices():
    """The self-reference this file was moved out of. If a future change puts the
    report reader back inside `tests/`, the suite carries a guaranteed skip and
    the report can never be clean."""
    inside = [p.name for p in (ROOT / "scripts").glob("check_test_report*.py")]
    assert inside, "the reader is no longer a script, so the workflow step above is dangling"
    assert READER.parent.name == "scripts", (
        f"the reader lives in {READER.parent.name}/, so it runs inside the suite whose "
        f"report it asserts on; its own skip would be a skip in that report"
    )
