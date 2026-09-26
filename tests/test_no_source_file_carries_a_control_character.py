"""No source file carries a control character.

Incident, Terminux R12 (`tests/test_no_source_file_carries_a_control_character.py`):
two literal BACKSPACE bytes sat where `\\b` was intended, which turned a checker
into a pattern that matched nothing. It reported zero sites and passed green
twice, because a regex built from a byte nobody can see is a regex that cannot
fire. Nothing about the run looked wrong.

The control characters that matter are the ones a human editor cannot see in a
diff: everything below 0x20 except tab, newline and carriage return, plus 0x7f.
Their presence means some string in the tree was written with an escape that was
never interpreted, and any pattern built from it is suspect.

This guard is a code-point test, not a pattern, so it cannot itself be defeated
by an invisible byte. It carries the literal backspace as its own red proof and
counts the files it read, so an empty walk cannot pass as a clean tree.

The exemptions are by name and by suffix, never by proximity to a match, because
Terminux 5.4 records a guard whose exemption was "a refusal nearby" and was
defeated by putting the defect next to the exemption. `test_the_pruned_paths_are
_build_output` keeps the directory list honest.

Ported from Terminux R12, catalogued in `_mining/TERMINUX_GUARDS.md` 4.A. See
`guards/ledger.json`.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Directory names pruned wherever they appear. `node_modules` sits under
#: `frontend/` as well as at the root, and the first version matched pruned names
#: as whole relative paths, so it walked all 33,000 files inside it.
PRUNED_DIR_NAMES = {
    ".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
    "node_modules", ".venv", "venv", "env", "data", "htmlcov", ".idea", ".vscode",
    "dist", "build", "perplexity-reviews", ".opencode", "snapshots", "models",
}

#: Whole subtrees pruned by relative path, where the name alone is not enough.
#: `tests/snapshots` is not here: `snapshots` in PRUNED_DIR_NAMES already covers it.
PRUNED_DIRS = {"thesis/renders", "frontend/dist", "frontend/build"}

#: Suffixes that are binary, generated, or machine-written. The walk still
#: descends into these directories' parents, so a `.log` next to source is read.
SKIP_SUFFIXES = {".pdf", ".docx", ".pptx", ".xlsx", ".mp4", ".mov", ".png", ".jpg",
                 ".jpeg", ".gif", ".webp", ".ico", ".sqlite", ".db", ".enc", ".gz",
                 ".zip", ".7z", ".woff", ".woff2", ".ttf", ".dll", ".pyd", ".onnx",
                 ".pt", ".pth", ".so", ".exe", ".mp3", ".wav", ".log", ".csv"}

#: The file count below which this guard declines to conclude anything. A walk
#: that found a handful of files has not checked this repository.
FILE_FLOOR = 120

#: What a person cannot see in a diff. Tab, newline and carriage return are the
#: three legitimate ones.
FORBIDDEN = {c for c in range(0x20) if c not in (0x09, 0x0A, 0x0D)}
FORBIDDEN.add(0x7F)


def _pruned(relative: Path) -> bool:
    if any(part in PRUNED_DIR_NAMES for part in relative.parts):
        return True
    posix = relative.as_posix()
    return any(posix == name or posix.startswith(name + "/") for name in PRUNED_DIRS)


def source_files(root: Path = ROOT) -> list[Path]:
    """Every hand-written text file in the tree. Pruning happens during the walk
    so the cost is proportional to what is read, not to what is skipped."""
    found: list[Path] = []
    for directory, subdirectories, filenames in root.walk(top_down=True):
        here = Path(directory).relative_to(root)
        subdirectories[:] = sorted(
            name for name in subdirectories
            if not _pruned(here / name if str(here) != "." else Path(name))
        )
        for filename in sorted(filenames):
            relative = here / filename
            if _pruned(relative) or relative.suffix.lower() in SKIP_SUFFIXES:
                continue
            found.append(relative)
    return found


def control_characters(text: str) -> dict[str, list[str]]:
    """The code points a human cannot see, mapped to the lines they occur on.
    Built from integers, so the detector cannot be broken by writing the wrong
    escape -- which is the failure this guard exists to catch."""
    hits: dict[str, list[str]] = {}
    for number, line in enumerate(text.splitlines(), 1):
        for character in line:
            if ord(character) in FORBIDDEN:
                hits.setdefault(f"U+{ord(character):04X}", []).append(f"line {number}")
    return hits


def test_the_detector_finds_a_literal_backspace_and_ignores_ordinary_text():
    """The red proof and its negative control in one place: the Terminux R12
    incident, and the reason a clean tree is not evidence that the detector
    works. The count of occurrences is deliberately not asserted, because a
    detector that reported one hit where there are two would still be detecting;
    the tree sweep below is where multiplicity matters."""
    invisible = "PATTERN = \bFORBIDDEN\b"  # a real BACKSPACE, not an escape
    hits = control_characters(invisible)
    assert set(hits) == {"U+0008"}, f"the detector missed a literal backspace: {hits}"
    assert all(report == "line 1" for report in hits["U+0008"]), hits

    ordinary = "PATTERN = r'\\bFORBIDDEN\\b'  # an escaped word boundary, written correctly"
    assert control_characters(ordinary) == {}, \
        "the detector fired on correctly escaped text"

    assert control_characters("def f():\n\treturn 1\n") == {}, \
        "tabs and newlines are not findings"


def test_no_source_file_carries_a_control_character():
    """The sweep. The file count is asserted first, so a walk that silently
    collected nothing cannot report a clean tree."""
    files = source_files()
    assert len(files) >= FILE_FLOOR, (
        f"the walk read only {len(files)} files, below the floor of {FILE_FLOOR}; "
        f"a pruned tree is not a clean tree"
    )

    dirty: dict[str, dict[str, list[str]]] = {}
    unreadable: list[str] = []
    for relative in files:
        try:
            text = (ROOT / relative).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            unreadable.append(str(relative))
            continue
        hits = control_characters(text)
        if hits:
            dirty[relative.as_posix()] = hits

    assert not unreadable, f"these files are not UTF-8 text and were not read: {unreadable}"
    assert not dirty, (
        f"{len(dirty)} of {len(files)} files carry an invisible control character, so any "
        f"pattern built from them may match nothing: "
        + "; ".join(f"{name} {sorted(hits)}" for name, hits in sorted(dirty.items()))
    )


def test_the_pruned_paths_are_build_output():
    """Terminux 5.8 item 7: an exemption must be narrow, justified, and still
    needed. Each pruned name is asserted to be a build, cache, environment or
    artifact directory, so `src` or `tests` cannot be pruned by accident and left
    the sweep reading almost nothing while still reporting a clean tree."""
    recognisable = {
        ".git", ".pytest_cache", ".ruff_cache", ".mypy_cache", "node_modules", ".venv",
        "venv", "env", "data", "dist", "build", "htmlcov", ".idea", ".vscode",
        "perplexity-reviews", ".opencode", "__pycache__", "snapshots", "models",
        "renders",
    }
    assert PRUNED_DIR_NAMES <= recognisable, \
        f"pruned without a stated justification: {sorted(PRUNED_DIR_NAMES - recognisable)}"
    for name in PRUNED_DIRS:
        assert name.split("/")[-1] in recognisable, \
            f"{name} is pruned but is not recognisably build output"

    files = source_files()
    assert len(files) >= FILE_FLOOR, "the walk is empty after pruning"
    for required in (Path("src/citegraph/api/main.py"), Path("tests/conftest.py"),
                     Path(".github/workflows/tests.yml"), Path("requirements.txt"),
                     Path("scripts/second_annotator.py"), Path("README.md")):
        assert required in files, f"{required.as_posix()} is not being read by the sweep"
