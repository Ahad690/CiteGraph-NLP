"""The deployed-build check must be able to say all five answers.

Incident: this deployment was verified by hand, by opening the URL.
`deploy-backend.yml` carried `46.225.8.77` as a fallback after that box was
deleted on 2026-05-31, and a green deploy said only that `/health` answered.
Nothing tied the running container to the commit that was pushed. In Terminux
the same class of hole let a hand-uploaded bundle sit behind the live domain for
nine days through three green CI runs (kit item 12, C15, C16).

`scripts/check_deployed_build.py` is the fix, and it is useless if it collapses
its answers. A check that can only say "not ok" will be muted the first time it
is wrong about the network, and then it will be muted forever. So the five
answers are driven here, and the three that must be distinguished from a refusal
are distinguished:

    unreachable   could not ask -- NOT a proof, and it must read differently
    unstamped     the service answered but does not say what it is
    unknown       it named a commit this repository has never heard of
    behind        a real commit, but not the one deployed
    ok            the expected build, or a known ancestor of the tip

The `git` questions are driven against real commits in this repository, so the
ancestor logic is exercised rather than mocked.

Ported from Terminus kit item 12, C15, C16. See `guards/ledger.json`.
"""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READER = ROOT / "scripts" / "check_deployed_build.py"

#: A commit that exists here, and one that is certainly its ancestor.
TIP = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                     text=True, check=True).stdout.strip()
FIRST = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=ROOT,
                       capture_output=True, text=True, check=True).stdout.strip().splitlines()[0]
#: 40 zeros is not a commit; it is the shape of a sha nothing has ever heard of.
UNKNOWN = "0" * 40


def _reader():
    spec = importlib.util.spec_from_file_location("check_deployed_build", READER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def asked(sha, **extra):
    return {"state": "asked", "reported": {"service": "citegraph-api", "git_sha": sha, **extra}}


def test_every_answer_is_reachable_and_only_one_is_acceptable():
    """The red proof, all five. A reader that answered 'ok' to an unreachable
    service, or to a build it could not place, would make the deploy green in
    exactly the situation it exists for."""
    reader = _reader()

    assert reader.verdict({"state": "unreachable", "detail": "connection refused"}, None)["state"] \
        == "unreachable", "a network failure was read as something other than a failure to look"
    assert reader.verdict({"state": "unstamped", "detail": "not JSON"}, None)["state"] \
        == "unstamped", "a reply that is not JSON was read as an answer"
    assert reader.verdict(asked(None), None)["state"] == "unstamped", \
        "a reply with no git_sha was read as an answer"
    assert reader.verdict(asked("   "), None)["state"] == "unstamped", \
        "a whitespace sha was read as an answer"
    assert reader.verdict(asked(UNKNOWN), None)["state"] == "unknown", \
        "a commit this repository has never heard of was accepted"
    assert reader.verdict(asked(UNKNOWN), TIP)["state"] == "behind", \
        "an expected sha that is not what is served must be behind"
    assert reader.verdict(asked(FIRST), None, tip=TIP)["state"] == "ok", \
        "a real ancestor of the tip was refused"

    # With --expected, only equality is acceptable: a build that is merely an
    # ancestor is behind, because this run deployed something specific.
    assert reader.verdict(asked(TIP), TIP)["state"] == "ok"
    assert reader.verdict(asked(FIRST), TIP)["state"] == "behind"


def test_the_git_questions_are_driven_against_real_commits():
    """Not mocked. `merge-base --is-ancestor` and `cat-file -e` are asked about
    this repository's own history, so a change in git's behaviour or in the
    arguments would show up here rather than in a deploy."""
    reader = _reader()

    assert reader.known(TIP) is True, f"{TIP[:12]} should be a commit here"
    assert reader.known(UNKNOWN) is False, "a zero sha cannot be a commit"
    assert reader.is_ancestor(FIRST, TIP) is True, "the first commit is an ancestor of HEAD"
    assert reader.is_ancestor(TIP, FIRST) is False, "HEAD is not an ancestor of the first commit"
    assert reader.is_ancestor(UNKNOWN, TIP) is None, \
        "git could not place a nonexistent commit, which is not the same as 'behind'"


def test_the_api_reports_which_build_it_is():
    """The stamp has to come from the service, so /version has to exist and has to
    say `git_sha`. An endpoint that answered 404 would make the check refuse every
    deploy, which is the correct failure but not one to discover in production."""
    source = (ROOT / "src" / "citegraph" / "api" / "main.py").read_text(encoding="utf-8")
    assert '@app.get("/version")' in source, "the API has no /version endpoint"
    for field in ("git_sha", "built_at", "version"):
        assert field in source, f"/version does not report {field}"

    config = (ROOT / "src" / "citegraph" / "config.py").read_text(encoding="utf-8")
    for field in ("git_sha", "build_time"):
        assert f"{field}:" in config, f"Settings has no {field}, so the stamp has nowhere to come from"


def test_the_deploy_stamps_the_build_and_asks_the_question():
    """Wiring at the consumer, and the whole chain of it.

    A stamp that nothing sets, or a check nothing runs, is a correct check with no
    caller -- the failure Terminux 5.7 lists. On 2026-09-26 the chain was broken in
    the middle: the container was given `${GITHUB_SHA}`, which is a variable of the
    runner, from inside a script running on the box. So the assertion follows the
    value rather than trusting any one line: `docker run` stamps `DEPLOY_SHA`, the
    ssh line passes it, and the step's env sets it from the pushed commit.
    """
    workflow = (ROOT / ".github" / "workflows" / "deploy-backend.yml").read_text(encoding="utf-8")
    assert "check_deployed_build.py" in workflow, \
        "the deploy never asks whether the build it just shipped is the one being served"

    stamped = [line.strip() for line in workflow.splitlines()
               if line.strip().startswith("-e ") and "GIT_SHA=" in line]
    assert stamped, "GIT_SHA is not passed to `docker run` as an environment variable"
    for line in stamped:
        assert "${DEPLOY_SHA}" in line, (
            f"the stamp is not the value the deploy resolved: {line!r}. A name that exists "
            f"only on the runner is unbound on the box, and `set -u` stops the script there"
        )

    assert "DEPLOY_SHA='$DEPLOY_SHA'" in workflow, \
        "DEPLOY_SHA is not passed to the box in the ssh environment list"
    assert "DEPLOY_SHA: ${{ github.sha }}" in workflow, \
        "DEPLOY_SHA is not the commit that was pushed, so the stamp would not identify it"

    fresh = [line.strip() for line in workflow.splitlines()
             if line.strip().startswith("-e ") and "BUILD_TIME=" in line]
    assert fresh, "the container is not stamped with a build time"
    for line in fresh:
        assert "${DEPLOY_TIME}" in line, f"the build time is not the resolved value: {line!r}"
