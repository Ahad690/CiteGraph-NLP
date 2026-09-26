"""Refuse when the deployed build is not the build being served.

Incident, 2026-09-19 and before it: this deployment was verified by hand, by
opening the URL. `deploy-backend.yml` carried `46.225.8.77` as a fallback host
after that box was deleted on 2026-05-31, and a green deploy said only that
`/health` answered. Nothing tied the container that was running to the commit
that had been pushed, so a stale image behind a live domain would have stayed
there indefinitely. In Terminux the same class of hole let a hand-uploaded bundle
sit behind the live domain for nine days through three green CI runs (kit item 12,
C15, C16).

So the running service identifies itself: `GET /version` returns the `GIT_SHA`
the deploy passed to `docker run`. This script asks, and refuses unless the
answer is a build it can place in this repository's history.

Five answers, kept distinct on purpose, because collapsing them is how a stale
deploy stays invisible:

    ok           the served build is the expected one, or a known ancestor of the
                 branch tip
    unreachable  could not ask -- a network failure is NOT a proof
    unstamped    the service answered but does not say what it is
    unknown      it named a commit this repository has never heard of
    behind       it is a real commit, but not the one deployed and not an
                 ancestor of the tip

    python scripts/check_deployed_build.py
    python scripts/check_deployed_build.py --expected "$GITHUB_SHA"
    python scripts/check_deployed_build.py --base http://127.0.0.1:18030

See `guards/ledger.json`, family C16.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BASE = "https://citegraph-api.penora.us"
TIMEOUT = 20

#: The ref the served build must be reachable from. A build that is an ancestor of
#: the branch tip is current enough; a build that is not is behind.
DEFAULT_TIP = "origin/main"

STATES = ("ok", "unreachable", "unstamped", "unknown", "behind")


def ask(base: str, timeout: int = TIMEOUT) -> dict:
    """What the service says it is. A network failure is its own answer, never an
    empty one."""
    url = f"{base.rstrip('/')}/version"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, TimeoutError) as error:
        return {"state": "unreachable", "detail": f"{url}: {error}"}
    try:
        reported = json.loads(body)
    except json.JSONDecodeError as error:
        return {"state": "unstamped", "detail": f"{url} did not return JSON: {error}"}
    if not isinstance(reported, dict):
        return {"state": "unstamped", "detail": f"{url} returned {type(reported).__name__}"}
    return {"state": "asked", "reported": reported}


def is_ancestor(candidate: str, tip: str = DEFAULT_TIP) -> bool | None:
    """Whether `candidate` is reachable from `tip`. None when git cannot answer,
    which is a different answer from False and must not be read as "behind"."""
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", candidate, tip],
        cwd=ROOT, capture_output=True, text=True,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    return None


def known(candidate: str) -> bool:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{candidate}^{{commit}}"],
        cwd=ROOT, capture_output=True, text=True,
    )
    return completed.returncode == 0


def verdict(found: dict, expected: str | None, tip: str = DEFAULT_TIP) -> dict:
    """The five answers. Pure, so tests/test_the_deployed_build_reads_its_reply.py
    can drive every one of them without a network."""
    if found["state"] == "unreachable":
        return {"state": "unreachable",
                "detail": f"could not ask what is deployed: {found['detail']}"}
    if found["state"] == "unstamped":
        return {"state": "unstamped", "detail": found["detail"]}

    reported = found.get("reported") or {}
    served = (reported.get("git_sha") or "").strip()
    if not served:
        return {"state": "unstamped",
                "detail": f"/version answered but git_sha is {reported.get('git_sha')!r}"}

    if expected:
        if served == expected:
            return {"state": "ok", "detail": f"serving the deployed build {served[:12]}"}
        return {"state": "behind",
                "detail": f"deployed {expected[:12]} but serving {served[:12]}"}

    if not known(served):
        return {"state": "unknown",
                "detail": f"serving {served[:12]}, which is not a commit in this repository; "
                          f"a fetch may be needed, or the build was stamped wrongly"}
    answer = is_ancestor(served, tip)
    if answer is None:
        return {"state": "unknown",
                "detail": f"git could not place {served[:12]} against {tip}"}
    if answer:
        return {"state": "ok", "detail": f"serving {served[:12]}, an ancestor of {tip}"}
    return {"state": "behind",
            "detail": f"serving {served[:12]}, which is not an ancestor of {tip}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--base", default=DEFAULT_BASE,
                        help=f"the API root to ask (default {DEFAULT_BASE})")
    parser.add_argument("--expected", default="",
                        help="the commit that was deployed; the served build must equal it")
    parser.add_argument("--tip", default=DEFAULT_TIP,
                        help=f"the ref the served build must be an ancestor of (default {DEFAULT_TIP})")
    arguments = parser.parse_args(argv)

    expected = arguments.expected.strip() or None
    if expected is None:
        subprocess.run(["git", "fetch", "--quiet", "origin"], cwd=ROOT, check=False)

    answer = verdict(ask(arguments.base), expected, arguments.tip)
    if answer["state"] == "ok":
        print(answer["detail"])
        return 0
    print(f"REFUSING [{answer['state']}]: {answer['detail']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
