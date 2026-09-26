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

import re
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


def remote_scripts() -> list[tuple[str, str, str]]:
    """Every `ssh ... bash -s <<'EOF'` body in the workflows, with the environment
    list that precedes it."""
    found = []
    for path in workflow_files():
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if "bash -s" not in line or "<<" not in line:
                continue
            prefix, cursor = line, index
            while cursor > 0 and "=" not in prefix.split("bash -s")[0]:
                cursor -= 1
                prefix = f"{lines[cursor]}\n{prefix}"
            body = []
            for follower in lines[index + 1:]:
                if follower.strip() == "EOF":
                    break
                body.append(follower)
            found.append((path.name, prefix, "\n".join(body)))
    return found


def unbound_variables(prefix: str, body: str) -> set[str]:
    """Variables the body reads that the ssh line does not pass and the body does
    not define. The shell's own names and `for` loop variables are excluded."""
    BUILTIN = {"PATH", "HOME", "USER", "SHELL", "PWD", "IFS", "RANDOM", "SECONDS",
               "LINENO", "BASH", "HOSTNAME", "OSTYPE", "TERM", "DEBIAN_FRONTEND",
               "PYTHONPATH", "REPLY", "PS1"}
    passed = set(re.findall(r"\b([A-Z_][A-Z0-9_]*)=", prefix))
    # Any assignment, not only one at the start of a line: the deploy's
    # `set_env_key()` declares `local key="$1" value="$2"` and the first version of
    # this check reported both as unbound.
    defined = set(re.findall(
        r"(?:^|[\s;&|(])(?:export\s+|local\s+|declare\s+|readonly\s+)?"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*=", body))
    loops = set(re.findall(r"for\s+([a-z_][a-z0-9_]*)\s+in", body))
    used = set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", body))
    return used - passed - defined - loops - BUILTIN


def test_the_remote_script_reader_sees_a_passing_script_and_catches_the_outage():
    """The red proof. A reader that reports nothing for every script would pass the
    sweep below while the deploy was still one unbound variable from an outage."""
    good_prefix = "ssh host \"PORT='$PORT' REMOTE_DIR='$REMOTE_DIR' bash -s\" <<'EOF'"
    good_body = 'set -euo pipefail\ncurl "http://127.0.0.1:${PORT}/health"\nmkdir -p "$REMOTE_DIR"\n'
    assert unbound_variables(good_prefix, good_body) == set(), \
        f"a correctly passed script was reported as unbound: {unbound_variables(good_prefix, good_body)}"

    defined = 'set -u\nTOKEN="local"\necho "$TOKEN"\n'
    assert unbound_variables("", defined) == set(), "a locally defined variable was reported"

    looped = 'set -u\nfor attempt in $(seq 1 3); do echo "${attempt}"; done\n'
    assert unbound_variables("", looped) == set(), "a loop variable was reported as unbound"

    scoped = 'set -u\nset_key() {\n  local key="$1" value="$2"\n  sed -i "s|^${key}=.*|${key}=${value}|" "$3"\n}\n'
    assert unbound_variables("", scoped) == set(), \
        f"a function's own locals were reported as unbound: {unbound_variables('', scoped)}"

    # The shape that took the API down on 2026-09-26.
    outage = 'set -euo pipefail\ndocker run -e "GIT_SHA=${GITHUB_SHA}" "$IMAGE"\n'
    assert unbound_variables("ssh host \"PORT='$PORT' bash -s\"", outage) == {"GITHUB_SHA"}, \
        "the outage's own shape was not reported"


def test_every_variable_the_remote_script_uses_is_passed_to_it():
    """The 2026-09-26 outage, as a check.

    The deploy sends a shell script to the box over ssh and runs it with
    `set -euo pipefail`. A variable the script reads must appear in the environment
    list on the ssh command line, because the heredoc body executes on the box and
    the runner's own variables are not there. `${GITHUB_SHA}` was not in that list,
    so `set -u` killed the script at the `docker run` line -- after the live
    container had been stopped and removed. The API was down until it was started
    by hand.
    """
    scripts = remote_scripts()
    assert scripts, "no ssh heredoc was found; the locator has stopped working"

    problems = {f"{name} ({len(body.splitlines())} line body)": unbound_variables(prefix, body)
                for name, prefix, body in scripts}
    problems = {where: names for where, names in problems.items() if names}
    assert not problems, (
        f"these remote scripts read variables the ssh command does not pass and the script "
        f"does not define: {problems}. With `set -u` the script dies there, and when that "
        f"is after the running container is removed, the service is down"
    )


def test_the_deploy_proves_the_new_image_before_removing_the_running_one():
    """The other half of the same outage. Stopping the old container before the new
    one is proven makes every later failure a downtime; a preflight on a spare port
    makes it a failed deploy instead."""
    workflow = (WORKFLOWS / "deploy-backend.yml").read_text(encoding="utf-8")
    preflight = workflow.find("PREFLIGHT_NAME=")
    remove_old = workflow.find('docker rm "$CONTAINER_NAME"')
    start_new = workflow.find('--name "$CONTAINER_NAME"')

    assert preflight != -1, "the deploy has no preflight, so a bad image is an outage"
    assert start_new != -1, "the deploy no longer starts the container; the locator is stale"
    assert preflight < remove_old < start_new, (
        f"the preflight must come before the old container is removed and the new one "
        f"started: preflight at {preflight}, remove at {remove_old}, start at {start_new}"
    )
    assert "still serving" in workflow, \
        "the failure message does not say the running container was left alone"

