"""The CI workflows have no path filters, and one job always runs.

Incidents. Terminus C1 (`.github/workflows/ci.yml:40-74,110-117`): a
`**/*.md` path filter hid a documentation fix until someone dispatched the run by
hand, and two history-scanning tests failed on the first CI run because the clone
was depth-1. Terminus C2 (`:20-30,76-88`): four push runs were cancelled by a
dispatch, and once the job that had to always run was itself made conditional, so
the whole suite was green because the expensive jobs never started. Terminus
R15 (`test_a_suite_that_says_it_must_run_in_ci_is_run_by_ci.py`): the guard
against a skipped suite was skipped by the same condition that skipped the suite,
which is a green run having executed nothing.

This repository's `deploy-backend.yml` and `deploy-frontend.yml` both carry
`paths:` filters. For a *deploy* that is deliberate and correct -- rebuilding an
image because a thesis paragraph changed wastes a runner and restarts a
container that is serving fine. For a *check* it hides failures. So the rule this
guard enforces is narrow and stated: a workflow that runs checks may not filter
by path, and at least one job in the repository's workflows must have no `if:` at
all, so there is always something that runs on every push.

The deploy workflows' filters are permitted by name in `GUARDED`, and
`test_the_exemption_is_still_needed` fails if one of them stops filtering, so the
exemption cannot quietly become a no-op that hides a real exemption.

Ported from Terminus C1, C2 and R15, catalogued in `_mining/TERMINUX_GUARDS.md`
4.B. See `guards/ledger.json`.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

#: Workflows that run checks. A `paths:` filter on one of these can only hide a
#: failure, never save a runner.
GUARDED = {"tests.yml"}

#: Workflows allowed a `paths:` filter, and why. A deploy rebuilds an artifact
#: that a markdown edit did not change; the filters are deliberate.
EXEMPT = {
    "deploy-backend.yml": "rebuilds a container; a thesis edit does not change the image",
    "deploy-frontend.yml": "rebuilds a bundle; a thesis edit does not change the assets",
}

#: Workflows whose steps read git history, and so need `fetch-depth: 0`.
NEEDS_HISTORY = {
    "tests.yml": "runs guards that shell out to git, including the tracked-file check",
    "deploy-backend.yml": "runs scripts/check_deployed_build.py, which asks whether the "
                          "served build is an ancestor of the branch tip",
}

#: Calibrated against this tree: three workflows, three jobs.
WORKFLOW_FLOOR = 3
JOB_FLOOR = 3


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def workflow_files() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))


def triggers(document: dict) -> dict:
    """`on:` is parsed as the boolean True by YAML 1.1, which is a trap worth
    naming: `document.get("on")` is None and the trigger block looks absent."""
    return document.get("on", document.get(True, {})) or {}


def path_filters(document: dict) -> list[str]:
    """Every `paths`/`paths-ignore` entry in the trigger block, by event."""
    found: list[str] = []
    for event, config in triggers(document).items():
        if not isinstance(config, dict):
            continue
        for key in ("paths", "paths-ignore"):
            for entry in config.get(key, []) or []:
                found.append(f"{event}.{key}:{entry}")
    return found


def unconditional_jobs() -> list[str]:
    """Jobs with no `if:`, across every workflow. At least one must exist, so
    something runs on every push regardless of what changed."""
    names: list[str] = []
    for path in workflow_files():
        for name, job in (load(path).get("jobs") or {}).items():
            if "if" not in (job or {}):
                names.append(f"{path.name}:{name}")
    return names


def test_the_reader_finds_the_filters_it_is_looking_for():
    """The red proof. A trigger block that is never read reports no filters, so
    the sweep below would pass on a workflow that has one."""
    filtered = yaml.safe_load(
        "name: x\non:\n  push:\n    branches: [main]\n    paths:\n      - 'src/**'\n"
        "jobs:\n  a:\n    runs-on: ubuntu-latest\n    steps: []\n"
    )
    assert path_filters(filtered) == ["push.paths:src/**"], \
        f"the reader missed a paths filter: {path_filters(filtered)}"

    ignored = yaml.safe_load(
        "name: x\non:\n  pull_request:\n    paths-ignore:\n      - '**/*.md'\n"
        "jobs:\n  a:\n    runs-on: ubuntu-latest\n    steps: []\n"
    )
    assert path_filters(ignored) == ["pull_request.paths-ignore:**/*.md"], \
        "the reader missed a paths-ignore filter"

    plain = yaml.safe_load(
        "name: x\non:\n  push:\n    branches: [main]\n  pull_request:\n"
        "jobs:\n  a:\n    runs-on: ubuntu-latest\n    steps: []\n"
    )
    assert path_filters(plain) == [], f"the reader invented a filter: {path_filters(plain)}"


def test_a_check_workflow_has_no_path_filter():
    """The sweep. `tests.yml` is the only workflow that decides whether the
    repository is healthy, so nothing may stop it starting."""
    assert len(workflow_files()) >= WORKFLOW_FLOOR, \
        f"only {len(workflow_files())} workflows found, below the floor of {WORKFLOW_FLOOR}"

    unlisted = sorted(set(GUARDED) - {p.name for p in workflow_files()})
    assert not unlisted, f"these guarded workflows no longer exist: {unlisted}"

    offenders: dict[str, list[str]] = {}
    for path in workflow_files():
        if path.name not in GUARDED:
            continue
        found = path_filters(load(path))
        if found:
            offenders[path.name] = found

    assert not offenders, (
        f"a workflow that runs checks filters by path, so a failure can be hidden until "
        f"someone dispatches it by hand (Terminus C1): {offenders}"
    )


def test_the_exemption_is_still_needed():
    """Terminus 5.8 item 7: an exemption must be narrow, justified, and still
    needed. If a deploy workflow stops filtering, the exemption has become a
    loophole that permits anything."""
    for name, reason in EXEMPT.items():
        path = WORKFLOWS / name
        assert path.exists(), f"{name} is exempted but no longer exists"
        assert reason.strip(), f"{name} is exempted without a stated reason"
        found = path_filters(load(path))
        assert found, (
            f"{name} is listed as needing a path filter but does not have one; "
            f"the exemption has become a hole"
        )


def test_one_job_always_runs():
    """Terminus C2: an always-running job, so the suite cannot be green because
    nothing started."""
    names = unconditional_jobs()
    assert len(names) >= JOB_FLOOR, \
        f"only {len(names)} unconditional jobs, below the floor of {JOB_FLOOR}"
    assert any(name.startswith("tests.yml:") for name in names), \
        f"no job in tests.yml runs unconditionally, so a push can be green having run " \
        f"nothing: {names}"


def checkouts(path: Path) -> list[dict]:
    """Every `actions/checkout` step's parsed `with:` mapping."""
    found = []
    for job in (load(path).get("jobs") or {}).values():
        for step in (job or {}).get("steps", []) or []:
            uses = str((step or {}).get("uses", ""))
            if uses.startswith("actions/checkout"):
                found.append({"uses": uses, "with": step.get("with") or {}})
    return found


def test_a_check_workout_reads_full_history():
    """Terminus C1: `fetch-depth: 0`. A test that reads git history sees one commit
    on a depth-1 clone and passes for the wrong reason, and
    `git merge-base --is-ancestor` cannot answer at all.

    `tests.yml` runs the guards that shell out to git. `deploy-backend.yml` runs
    `scripts/check_deployed_build.py`, which asks whether the served build is an
    ancestor of the branch tip. `deploy-frontend.yml` is exempt: it builds a
    bundle and uploads it, and reads no history.
    """
    for name in NEEDS_HISTORY:
        path = WORKFLOWS / name
        assert path.exists(), f"{name} needs full history but does not exist"
        steps = checkouts(path)
        assert steps, f"{name} has no checkout step, so the rule below cannot apply"
        shallow = [s["uses"] for s in steps if str(s["with"].get("fetch-depth", "")) != "0"]
        assert not shallow, (
            f"{name} does not ask for full history, so a guard that reads git history sees "
            f"one commit: {shallow}"
        )

    exempt = WORKFLOWS / "deploy-frontend.yml"
    assert not any(str(s["with"].get("fetch-depth", "")) == "0"
                   for s in checkouts(exempt)), (
        "deploy-frontend.yml now fetches full history; if it reads history, move it into "
        "NEEDS_HISTORY, and if it does not, drop the fetch to keep the clone shallow"
    )

