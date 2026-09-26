"""The documented response fields are the fields the API returns.

Incident, 2026-09-26. `4c982f2` replaced the raw PageRank term with an
`influence` normalised by the largest value among the ranked papers. `README.md`
went on documenting

    score = 0.5 * PageRank + 0.3 * year_score + 0.2 * evidence_score

and a field table saying "Papers ranked by combined PageRank + year + evidence
score". Both were found by grepping, by hand, in the session that made the change,
and corrected by hand in the same sitting. Nothing would have caught them. A
hand-maintained registry that is only updated when somebody remembers is not a
registry.

The registry in the code is read from the AST, resolving inheritance, because the
request model is `RunRequest(PaperQuery)` and lives in `routes.py` rather than in
`models/`: three of its six fields are inherited. A regex over the text would have
missed them, and a reader that quietly returns a subset compares equal to
everything.

Four claims, and each says which direction it can hold:

  * the `RunResult` table in `README.md` against `models/run.py`, both ways;
  * the `Paper` table in `README.md` against `models/paper.py`, one way -- the
    README documents derived fields the model does not carry;
  * the request table in `docs/API.md` against `RunRequest`, both ways;
  * every route the code serves against every route the docs name. This is the
    direction that caught `/version` being added to `main.py` while `docs/API.md`
    went on describing the API as it had been.

A documented row counts as a field only when its second column is a type, so a
table of status *values* is not mistaken for a table of fields.

Ported from Terminus R14, C13, P10 and B28. See `guards/ledger.json`.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "citegraph"
README = ROOT / "README.md"
API_DOC = ROOT / "docs" / "API.md"
APPENDIX = ROOT / "thesis" / "09-appendix-a-api.md"

#: A second column that makes the row a field rather than a value.
FIELD_TYPES = {"string", "int", "integer", "float", "number", "bool", "boolean",
               "array", "object", "dict", "datetime", "null", "any"}

#: Calibrated against this tree. A comparison over an empty set agrees with
#: everything, which is how a locator that stopped early once passed.
FLOOR = {"RunResult": 10, "Paper": 14, "RunRequest": 6, "routes": 9,
         "documented": 6}


def _classes() -> dict[str, dict]:
    """Every class under `src/`, with its own fields and its base names."""
    found: dict[str, dict] = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            fields = {item.target.id for item in node.body
                      if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)}
            bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
            bases += [base.attr for base in node.bases
                      if isinstance(base, ast.Attribute)]
            found[node.name] = {"fields": fields, "bases": bases, "path": path}
    return found


def model_fields(name: str, classes: dict[str, dict] | None = None, _seen: set | None = None) -> set[str]:
    """A model's fields, including the ones it inherits. `RunRequest` gets two
    fields of its own and three from `PaperQuery`; reading only the class body
    would have reported the documented request as half undocumented."""
    classes = classes if classes is not None else _classes()
    _seen = _seen if _seen is not None else set()
    if name in _seen or name not in classes:
        return set()
    _seen.add(name)
    fields = set(classes[name]["fields"])
    for base in classes[name]["bases"]:
        fields |= model_fields(base, classes, _seen)
    return fields


def request_model_fields() -> set[str]:
    """Every field the API accepts on a run request.

    Taken from the annotation of the handler's `request` parameter rather than by
    guessing which class is the request: the first version matched any class whose
    name began with `Run`, which swept in `RunResult`'s twelve response fields and
    made the documented request look six fields short.
    """
    classes = _classes()
    tree = ast.parse((SRC / "api" / "routes.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                   and d.func.attr == "post" for d in node.decorator_list):
            continue
        for argument in node.args.args:
            if argument.annotation is None:
                continue
            name = argument.annotation.id if isinstance(argument.annotation, ast.Name) else None
            if name and name in classes:
                return model_fields(name, classes)
    return set()


def unmodelled_response_fields() -> set[str]:
    """Fields the docs list that no model declares, because the route returns a
    plain dict. Named here so the exemption is visible, and asserted below to
    still be needed."""
    return {"run_id", "status", "error", "service", "version", "git_sha", "built_at"}


def table_after(text: str, anchor: str) -> set[str]:
    """The typed first-column entries of the markdown table that follows `anchor`.
    Blank lines between the anchor and the table are skipped; the first line that
    is not a table row ends it, so it cannot run on into the next table and collect
    that too."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if anchor not in line:
            continue
        fields: set[str] = set()
        started = False
        for row in lines[index + 1:]:
            if not started:
                if not row.strip():
                    continue
                if not row.startswith("|"):
                    break
                started = True
            if not row.startswith("|"):
                break
            cells = [c.strip() for c in row.strip("|").split("|")]
            if len(cells) < 2:
                continue
            name = re.fullmatch(r"`([A-Za-z_]\w*)`", cells[0])
            kind = cells[1].strip("` ").lower()
            if name and kind in FIELD_TYPES:
                fields.add(name.group(1))
        return fields
    return set()


def all_typed_fields(text: str) -> set[str]:
    """Every typed field row in a document, wherever it sits. Used where the claim
    is about the whole document rather than one table."""
    fields: set[str] = set()
    for row in text.splitlines():
        if not row.startswith("|"):
            continue
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) < 2:
            continue
        name = re.fullmatch(r"`([A-Za-z_]\w*)`", cells[0])
        if name and cells[1].strip("` ").lower() in FIELD_TYPES:
            fields.add(name.group(1))
    return fields


def declared_routes() -> set[str]:
    found: set[str] = set()
    for path in sorted((SRC / "api").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                target = decorator.func if isinstance(decorator, ast.Call) else decorator
                if not isinstance(target, ast.Attribute) or target.attr not in (
                        "get", "post", "put", "patch", "delete"):
                    continue
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    found.add(str(decorator.args[0].value))
    return found


def named_in_docs(path: str) -> bool:
    """Whether a route path appears in either document. `{run_id}` is matched
    loosely, so renaming a path parameter does not make the route undocumented."""
    pattern = re.escape(path)
    pattern = re.sub(r"\\\{[^{}]*\\\}", r"[^/\\s`]+", pattern)
    for document in (API_DOC, APPENDIX):
        if re.search(pattern, document.read_text(encoding="utf-8")):
            return True
    return False


def test_the_readers_find_what_they_are_looking_for_and_nothing_else():
    """The red proof. A locator that stopped early once passed by comparing an
    empty set against everything, so every reader is driven against text it must
    find, text it must skip, and text it must not invent."""
    sample = (
        "When completed - returns full `RunResult` object:\n\n"
        "| Field | Type | Description |\n"
        "| `run_id` | `string` | id |\n"
        "| `papers` | `array` | papers |\n"
        "| `untyped` | some prose | not a field row |\n\n"
        "**Paper model:**\n"
        "| `paper_id` | `string` | id |\n"
    )
    assert table_after(sample, "returns full `RunResult` object") == {"run_id", "papers"}, \
        "the table reader did not skip the blank line, or collected a row with no type"
    assert table_after(sample, "**Paper model:**") == {"paper_id"}, \
        "the table reader ran past the end of the table it was asked for"
    assert table_after(sample, "a heading that is not in the text") == set(), \
        "the table reader invented a table"

    classes = _classes()
    assert model_fields("RunRequest", classes) >= {"query_type", "value", "pdf_path",
                                                  "backward_depth", "forward_depth",
                                                  "max_total_papers"}, (
        f"RunRequest resolved to {sorted(model_fields('RunRequest', classes))}; inherited "
        f"fields are not being read"
    )
    assert model_fields("NoSuchModel", classes) == set(), "the model reader invented a model"
    assert declared_routes() >= {"/health", "/runs"}, \
        f"only {sorted(declared_routes())} were read from the decorators"


def test_the_runresult_table_in_the_readme_is_the_model():
    """Both directions. This is the table that carried the old formula."""
    documented = table_after(README.read_text(encoding="utf-8"), "returns full `RunResult` object")
    declared = model_fields("RunResult")
    assert len(declared) >= FLOOR["RunResult"], f"only {len(declared)} RunResult fields were read"
    assert len(documented) >= FLOOR["RunResult"], (
        f"only {len(documented)} RunResult fields were documented; the locator has probably "
        f"stopped working and the comparison below would agree with everything"
    )
    assert documented == declared, {
        "only_documented": sorted(documented - declared),
        "only_declared": sorted(declared - documented),
    }


def test_the_paper_table_documents_every_field_the_model_declares():
    """One way. The README's Paper table also carries derived fields the model
    does not hold, so equality would be the wrong claim; what must hold is that
    nothing the model declares is undocumented."""
    documented = table_after(README.read_text(encoding="utf-8"), "**Paper model:**")
    declared = model_fields("Paper")
    assert len(declared) >= FLOOR["Paper"], f"only {len(declared)} Paper fields were read"
    assert len(documented) >= 10, f"only {len(documented)} Paper fields were documented"
    assert not declared - documented, (
        f"Paper declares {sorted(declared - documented)}, which the README does not document"
    )


def test_the_documented_request_fields_are_the_fields_the_api_accepts():
    """docs/API.md's request table against `RunRequest`, which inherits three of its
    six fields from `PaperQuery`."""
    documented = table_after(API_DOC.read_text(encoding="utf-8"), "### Request")
    declared = request_model_fields()
    assert len(declared) >= FLOOR["RunRequest"], f"only {len(declared)} request fields were read"
    assert len(documented) >= FLOOR["RunRequest"], (
        f"only {len(documented)} request fields are documented in docs/API.md; the locator "
        f"may have stopped working"
    )
    assert documented == declared, {
        "only_documented": sorted(documented - declared),
        "only_declared": sorted(declared - documented),
    }


def test_every_documented_field_exists_in_the_code():
    """One direction over the whole of docs/API.md: a field the docs promise that
    no request or response model declares is a promise the API does not keep.

    The exempted names are the fields two routes return as a plain dict rather
    than a model -- `POST /runs`, `/health` and `/version` -- and the exemption is
    asserted still to be needed below, so it cannot quietly absorb a real field.
    """
    classes = _classes()
    declared: set[str] = set()
    for name, entry in classes.items():
        if "BaseModel" in entry["bases"] or any(
                model_fields(base, classes) for base in entry["bases"]):
            declared |= model_fields(name, classes)

    documented = all_typed_fields(API_DOC.read_text(encoding="utf-8"))
    assert len(documented) >= FLOOR["documented"], (
        f"only {len(documented)} typed field rows were read from docs/API.md"
    )
    invented = sorted(documented - declared - unmodelled_response_fields())
    assert not invented, (
        f"docs/API.md documents {invented}, which no model declares. Either the field was "
        f"renamed or removed and the documentation was not updated"
    )


def test_the_unmodelled_fields_exemption_is_still_needed():
    """Terminus 5.8 item 7. If those routes start returning models, the exemption
    has become a loophole; if the fields leave the documentation, it is a phantom."""
    routes = (SRC / "api" / "routes.py").read_text(encoding="utf-8")
    main = (SRC / "api" / "main.py").read_text(encoding="utf-8")
    assert "response_model=Dict[str, str]" in routes, (
        "POST /runs now returns a model, so `run_id` and `status` no longer need the "
        "unmodelled exemption"
    )
    assert '@app.get("/health")' in main and '@app.get("/version")' in main, (
        "an app-level route has changed; the unmodelled exemption may no longer cover it"
    )
    documented = all_typed_fields(API_DOC.read_text(encoding="utf-8"))
    unused = sorted(unmodelled_response_fields() - documented)
    assert len(unused) <= 3, (
        f"{unused} are in the unmodelled exemption but are documented nowhere; the list has "
        f"drifted from the document it exists to excuse"
    )


def test_every_route_the_api_serves_is_named_in_the_documentation():
    """The direction that caught `/version`. A route added to the code and not to
    the docs is invisible to everyone who reads the docs."""
    routes = declared_routes()
    assert len(routes) >= FLOOR["routes"], f"only {len(routes)} routes were read from the code"
    missing = sorted(route for route in routes if not named_in_docs(route))
    assert not missing, (
        f"the API serves {missing}, which neither docs/API.md nor the thesis appendix names. "
        f"An endpoint nobody has documented is an endpoint nobody knows exists"
    )


def test_the_thesis_appendix_documents_fields_that_still_exist():
    """One direction on purpose. The appendix deliberately documents a subset of
    docs/API.md -- the request fields rather than every response field -- so
    demanding equality would be demanding a different document. What must hold is
    that everything it names still exists."""
    classes = _classes()
    declared: set[str] = set()
    for name, entry in classes.items():
        if "BaseModel" in entry["bases"] or any(model_fields(b, classes) for b in entry["bases"]):
            declared |= model_fields(name, classes)

    documented = all_typed_fields(APPENDIX.read_text(encoding="utf-8"))
    assert len(documented) >= 6, f"only {len(documented)} typed field rows were read from Appendix A"
    invented = sorted(documented - declared - unmodelled_response_fields())
    assert not invented, (
        f"Appendix A documents {invented}, which no model declares. The appendix is "
        f"generated for the sections it owns, so a field named here has usually been renamed"
    )
