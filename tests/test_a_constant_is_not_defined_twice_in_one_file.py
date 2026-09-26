"""A constant is not defined twice in one file.

Incident, Terminux R13 (`tests/test_a_constant_is_not_defined_twice_in_one_file.py`):
a fail-closed list of blocking gates was declared once as a module constant and
then redeclared as a dataclass field, and the two were kept equal by hand. A
floor written against one of them stops matching the moment the other is edited,
and nothing says which one the program reads.

Two shapes are checked here, because the incident is the second one:

  * the same UPPER_CASE name bound twice in the same scope of one file, which is
    a dead copy or a hand-kept twin;
  * a module constant redeclared as a dataclass field in the same file, which is
    the recorded incident and is invisible to the first check.

A clean tree is not evidence that either check works, so this file carries the
planted defect as its own red proof, the correct forms as its negative controls,
and the number of files and constants it read as a floor.

Ported from Terminux R13, catalogued in `_mining/TERMINUX_GUARDS.md` 4.A. See
`guards/ledger.json`.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
G6 = ROOT / "tests" / "test_no_source_file_carries_a_control_character.py"

#: Calibrated against this tree: 78 Python files carrying 176 module and class
#: level constants. A walk that finds materially fewer has stopped looking.
FILE_FLOOR = 60
CONSTANT_FLOOR = 120


def _source_files() -> list[Path]:
    """Reuse the control-character guard's pruned walk rather than keeping a
    second, slightly different definition of what this repository's source is."""
    spec = importlib.util.spec_from_file_location("g6_walk", G6)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return sorted(f for f in module.source_files() if f.suffix == ".py")


def _targets(node: ast.stmt) -> list[ast.Name]:
    if isinstance(node, ast.Assign):
        return [t for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target]
    return []


def constant_bindings(tree: ast.Module) -> dict[str, list[int]]:
    """Every UPPER_CASE name bound at module or class scope, with its lines."""
    found: dict[str, list[int]] = {}

    def record(prefix: str, body: list[ast.stmt]) -> None:
        for node in body:
            for target in _targets(node):
                if target.id.isupper():
                    key = f"{prefix}{target.id}"
                    found.setdefault(key, []).append(target.lineno)

    record("", list(tree.body))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            record(f"{node.name}.", list(node.body))
    return found


def dataclass_fields(tree: ast.Module) -> set[str]:
    """Field names declared on a dataclass, however it is spelled: an annotated
    assignment, a `field(...)` default, or a bare AnnAssign in a decorated class.
    """
    fields: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        decorated = any(
            (isinstance(d, ast.Name) and d.id == "dataclass")
            or (isinstance(d, ast.Attribute) and d.attr == "dataclass")
            or (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass")
            for d in node.decorator_list
        )
        if not decorated:
            continue
        for statement in node.body:
            for target in _targets(statement):
                fields.add(target.id)
    return fields


def duplicates(tree: ast.Module) -> dict[str, list[int]]:
    """Names bound more than once in the same scope."""
    return {name: lines for name, lines in constant_bindings(tree).items() if len(lines) > 1}


def shadowed_fields(tree: ast.Module) -> dict[str, int]:
    """Module constants whose name is also a dataclass field: the R13 incident.
    Class-scoped constants are recorded as `Class.CONST` and are left out, since a
    class attribute and a module constant of the same name are not the confusion
    this incident was."""
    fields = dataclass_fields(tree)
    return {name: lines[0] for name, lines in constant_bindings(tree).items()
            if "." not in name and name in fields}


def test_the_detector_catches_a_planted_twin_and_ignores_the_correct_forms():
    """The red proof, the recorded incident, and the negative controls. Without
    this, a clean tree in the sweep below would be worth nothing."""
    twin = ast.parse("BLOCKING = ['a']\nBLOCKING = ['b']\n")
    assert duplicates(twin) == {"BLOCKING": [1, 2]}, \
        "the detector missed a constant defined twice, so it cannot be trusted on the tree"

    dataclass_twin = ast.parse(
        "from dataclasses import dataclass\n"
        "BLOCKING = ('a', 'b')\n"
        "@dataclass\n"
        "class Config:\n"
        "    BLOCKING: tuple = ()\n"
    )
    assert shadowed_fields(dataclass_twin) == {"BLOCKING": 2}, \
        "the detector missed a constant redeclared as a dataclass field, which is the incident"

    reads = ast.parse("LIMIT = 5\nresult = LIMIT + LIMIT\nprint(LIMIT)\n")
    assert duplicates(reads) == {}, "reading a constant twice is not a duplicate definition"

    inner_scope = ast.parse("LIMIT = 5\ndef f():\n    LIMIT = 6\n    return LIMIT\n")
    assert duplicates(inner_scope) == {}, \
        "a function-local binding of the same name is a different scope, not a twin"

    lowercase = ast.parse("total = 0\ntotal = 1\n")
    assert duplicates(lowercase) == {}, "lower_case locals are not constants"


def test_no_python_file_defines_a_constant_twice():
    """The sweep, over every Python file in the pruned tree."""
    files = _source_files()
    assert len(files) >= FILE_FLOOR, f"only {len(files)} Python files were read; the floor is {FILE_FLOOR}"

    found: dict[str, int] = {}
    constants = 0
    for relative in files:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        bindings = constant_bindings(tree)
        constants += len(bindings)
        for name, lines in duplicates(tree).items():
            found[f"{relative.as_posix()}:{name}"] = lines[0]

    assert constants >= CONSTANT_FLOOR, (
        f"only {constants} constants were seen, below the floor of {CONSTANT_FLOOR}; "
        f"the detector is not reading this tree"
    )
    assert not found, (
        f"{len(found)} constants are defined more than once in the same scope, so one of "
        f"each pair is dead or hand-kept: {found}"
    )


def test_no_module_constant_is_redeclared_as_a_dataclass_field():
    """The recorded R13 incident, swept. A floor written against the constant
    stops matching when the field is the one the program reads."""
    files = _source_files()
    found: dict[str, str] = {}
    for relative in files:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for name, line in shadowed_fields(tree).items():
            found[f"{relative.as_posix()}:{name}"] = f"line {line}"

    assert not found, (
        f"{len(found)} names are both a module constant and a dataclass field in the same "
        f"file, which is how the fail-closed list came to be kept equal by hand: {found}"
    )
