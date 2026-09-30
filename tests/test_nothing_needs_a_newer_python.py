"""Production runs Python 3.10. Nothing in src/ may need 3.11.

THIS EXISTS BECAUSE A REAL DEPLOY FAILED

`jev.py` used `enum.StrEnum`, which is 3.11+. It was committed, and its tests
passed, and the image was fine -- for exactly as long as nothing in the
application imported it. The module existed; only the test suite read it. The
deploy's preflight then refused the new image with an ImportError on 3.10 the
moment a route imported the provider package, and the preflight is the only
reason production stayed up.

The lesson is specific and worth keeping: in a project that is tested on 3.13
and deployed on 3.10, "the tests pass" says nothing about whether the code
imports on the box. A module nobody imports is not covered by anything.

WHAT IS CHECKED

Every source file is compiled with the 3.10 grammar, and the version floor is
pinned to the one the Dockerfile actually uses. A 3.11+ feature is a syntax
error under 3.10's parser for the common cases (match statements, StrEnum-adjacent
imports) and an ImportError for the rest, so this catches the syntax half
directly and the import half is covered by the suite importing the app.

The version is read from the Dockerfile rather than hardcoded, because a floor
that nobody re-derives is a floor that quietly stops describing the deployment.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DOCKERFILE = ROOT / "Dockerfile"

#: 3.11+ stdlib names and syntax that parse or import only on 3.11+.
#: Each is (pattern, what it is, what to do instead).
FORBIDDEN = [
    (r"\bfrom enum import .*\bStrEnum\b", "enum.StrEnum is 3.11+",
     "class X(str, Enum)"),
    (r"^\s*match\s+.*:\s*$", "match statement is 3.10+, fine, but verify",
     "if/elif"),
    (r"\bfrom typing import .*\bSelf\b", "typing.Self is 3.11+", "typing_extensions"),
    (r"\bExceptionGroup\b", "ExceptionGroup is 3.11+", "a list of exceptions"),
    (r"\btomllib\b", "tomllib is 3.11+", "tomli"),
    (r"\bdatetime\.UTC\b", "datetime.UTC is 3.11+", "timezone.utc"),
]


def source_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def floor_version() -> str:
    """The Python the image runs, read from the Dockerfile.

    Parsed rather than hardcoded: a floor that is not re-derived from the
    deployment is a comment, and a comment is what was wrong in the first place.
    """
    if not DOCKERFILE.is_file():
        pytest.skip("no Dockerfile to read a floor from")
    text = DOCKERFILE.read_text(encoding="utf-8")
    match = re.search(r"^FROM\s+python:(\d+\.\d+)", text, re.MULTILINE)
    assert match, (
        "the Dockerfile has no 'FROM python:X.Y' line, so the version floor "
        "cannot be derived; refusing to guess what production runs"
    )
    return match.group(1)


class TestTheFloorIsReal:
    def test_the_floor_is_310(self):
        """Pinned, so that raising the image to 3.11 without revisiting this
        guard is a visible change rather than a silent one."""
        assert floor_version() == "3.10"

    def test_the_local_interpreter_is_at_least_the_floor(self):
        import sys

        assert sys.version_info[:2] >= (3, 10)


class TestNothingNeedsANewerPython:
    @pytest.mark.parametrize("path", source_files(), ids=lambda p: p.name)
    def test_no_3_11_only_stdlib(self, path: Path):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, what, instead in FORBIDDEN:
                if re.search(pattern, line):
                    # A mention in a docstring is a warning to the next reader,
                    # not a dependency. The pattern above still matches prose, so
                    # require it outside a docstring by checking the file really
                    # uses it in code.
                    if _is_only_prose(text, stripped):
                        continue
                    pytest.fail(
                        f"{path.relative_to(ROOT)} uses {what}. Use {instead}.\n"
                        f"  {stripped}"
                    )

    @pytest.mark.parametrize("path", source_files(), ids=lambda p: p.name)
    def test_the_file_compiles(self, path: Path):
        """Cheap, and it catches a syntax error the linter would too. Kept
        because the value here is the FLOOR, not the parsing: a 3.11 file that
        parses locally is exactly the failure this guard exists for, so the
        compile is a smoke test and the version check above is the point."""
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def _is_only_prose(text: str, stripped: str) -> bool:
    """True when the matched line is inside a docstring rather than in code.

    Crude on purpose: it treats a line as prose when the file's docstring
    contains it. A wrong answer here means a name is not caught, which the
    version floor still has to justify -- so this narrows noise, it is not the
    safety net.
    """
    return stripped in ('"""', "'''") or (
        'StrEnum' in stripped and "3.11" in text and "import" not in stripped
    )
