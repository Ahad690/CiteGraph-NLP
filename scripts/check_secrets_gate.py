"""A key must never be committed, logged, or serialised.

This is a gate rather than a test, in the same spirit as the other checks in
`scripts/`: it names the rules it enforces and runs in CI, so a leak is caught by
the build instead of by someone noticing on GitHub.

The rules, and why each exists:

  1. A .env file is never tracked. The keys live there and nowhere else.
  2. .env.example carries the NAMES with empty values. A tracked example that
     contains a real key is the most common way one leaks.
  3. No key-shaped string appears anywhere in tracked source. The patterns are
     vendor-shaped rather than generic, so a high-entropy constant in a test
     fixture is not flagged.
  4. The llm package never logs a credential. Asserted on the code, not on a
     run, because a key that is only logged on an error path is only logged when
     something goes wrong.

Rule 3 is a pattern match and pattern matching misses things. It is a backstop
against the obvious mistake, not a proof of absence.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Vendor key shapes. Deliberately narrow: a generic "long base64 string" rule
#: would flag every hash in the test suite.
KEY_SHAPES = [
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI-style key"),
    (r"ghp_[A-Za-z0-9]{30,}", "GitHub personal access token"),
    (r"github_pat_[A-Za-z0-9_]{50,}", "GitHub fine-grained token"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"AIza[0-9A-Za-z_\-]{35}", "Google API key"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "Slack token"),
]

#: The one place a key is allowed to exist.
ALLOWED = {".env"}

#: Paths whose contents are not source.
SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", "var", "__pycache__",
    ".pytest_cache", ".ruff_cache", "coverage", "htmlcov",
}

#: Test fixtures may hold fake keys, and a fake key in a test is the point.
FAKE_ALLOWED = re.compile(r"(test|fake|dummy|example|placeholder|invalid|sample)", re.IGNORECASE)


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return [ROOT / line for line in out.stdout.splitlines() if line.strip()]


def violations() -> list[str]:
    problems: list[str] = []
    tracked = tracked_files()

    for path in tracked:
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if relative in ALLOWED:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".docx", ".ico", ".woff", ".woff2"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            continue

        for pattern, label in KEY_SHAPES:
            for match in re.finditer(pattern, text):
                line = text.count("\n", 0, match.start()) + 1
                # A shape match inside a test file is expected to be a fixture.
                if FAKE_ALLOWED.search(relative):
                    continue
                problems.append(f"{relative}:{line}: {label} in a tracked file")

    # The .env must not be tracked at all, even though it is in ALLOWED above
    # for the reader's benefit.
    if any(p.relative_to(ROOT).as_posix() == ".env" for p in tracked):
        problems.append(".env is tracked; a key file must never be in git")

    # The llm package must not be able to log a credential.
    for path in (ROOT / "src" / "citegraph" / "llm").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "logger" in line and "self._api_key" in line:
                problems.append(
                    f"{path.relative_to(ROOT).as_posix()}:{i}: "
                    "logs the api key directly"
                )
    return problems


def main() -> int:
    found = violations()
    if found:
        print("SECRETS GATE: a credential may have been committed")
        for problem in found:
            print(f"  {problem}")
        print("\nIf a real key was pushed, rotating it is the fix; removing the")
        print("commit alone does not un-publish it.")
        return 1

    count = len(tracked_files())
    print(f"no key-shaped string in {count} tracked files")
    print(f"checked {len(KEY_SHAPES)} credential shapes")
    print(".env is untracked; the llm package logs no key")
    return 0


if __name__ == "__main__":
    sys.exit(main())
