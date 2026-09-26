"""The thesis says what the repository says, and keeps saying it.

On 2026-09-25 three kinds of drift were found in one afternoon, all by hand:

    - the abstract and four chapters said the system "reads abstracts only",
      six days after e2a1759 made it read open-access full text;
    - Figure 5.1, which is generated from the code, predated two of the calls
      it claims to show, and five counts quoted from the figures were stale;
    - the page counts in two READMEs trailed the committed PDFs, and Appendix F
      still counted 102 tests in a suite of 199.

No test failed, because nothing compared the thesis with the things it
describes. This file does, in five groups:

    ratchet   sections, figures and citations may be added freely but not lost
              without a written reason (scripts/rebaseline_thesis.py)
    evidence  headline results match the evaluation output they came from
    code      the generated figures, and counts quoted from them, match the source
    build     the assembled thesis, the PDFs, and the page and test counts quoted
              about them are current
    claims    statements that were once true and are now false stay retired

It is the same shape as Terminux's PRD guard,
tests/test_the_prd_is_never_replaced.py: the baseline is committed, both lists
may grow, and nothing leaves them without a sentence saying why.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THESIS = ROOT / "thesis"
FIGURES = THESIS / "figures"
EVIDENCE = THESIS / "evidence"
SRC = ROOT / "src" / "citegraph"
BASELINE = ROOT / "scripts" / "thesis_baseline.json"
REBASELINE = 'python scripts/rebaseline_thesis.py "why this changed"'

NUMBER_WORDS = {w: i for i, w in enumerate(
    ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
     "fourteen fifteen sixteen seventeen eighteen nineteen twenty").split())}


@lru_cache(maxsize=None)
def _build():
    spec = importlib.util.spec_from_file_location("build_thesis", ROOT / "scripts" / "build_thesis.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=None)
def _chapter(name: str) -> str:
    """A chapter with its hard line wraps undone, so a phrase can be matched
    wherever the editor happened to break the line."""
    return re.sub(r"\s+", " ", (THESIS / name).read_text(encoding="utf-8"))


def _svg_nodes(name: str) -> list[str]:
    svg = (FIGURES / name).read_text(encoding="utf-8")
    return re.findall(r'<g id="node\d+" class="node">\s*<title>([^<]+)</title>', svg)


def _quoted(chapter: str, pattern: str) -> tuple[int, ...]:
    match = re.search(pattern, _chapter(chapter))
    assert match, f"{chapter} no longer says {pattern!r}; update the claim list in this test"
    return tuple(int(g) if g.isdigit() else NUMBER_WORDS[g.lower()] for g in match.groups())


# ---------------------------------------------------------------- ratchet


@pytest.mark.parametrize("kind", ["sections", "figures", "citations"])
def test_nothing_the_thesis_contained_disappears_without_a_stated_reason(kind):
    """Removing a section, figure or citation can be right. Losing one because
    an older copy of a chapter was pasted over the current one is not, and the
    two look identical the next morning. The rebaseline asks for a sentence so
    that somebody has to decide."""
    document, _ = _build().assembled_text()
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    lost = sorted(set(baseline[kind]) - set(_build().inventory(document)[kind]))
    assert not lost, (
        f"{kind} {lost} were in the thesis and are gone. If that is deliberate, "
        f"record why:\n    {REBASELINE}")


def test_the_baseline_is_committed_rather_than_regenerated():
    """A baseline rebuilt from the thesis on every run agrees with it about
    everything it just lost, so it only works as a witness if git holds it."""
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(BASELINE)],
                             cwd=ROOT, capture_output=True, text=True)
    assert tracked.returncode == 0, "scripts/thesis_baseline.json is not tracked"
    assert json.loads(BASELINE.read_text(encoding="utf-8")).get("_why"), \
        "the baseline carries no reason, so nobody decided it"


# ---------------------------------------------------------------- evidence


def test_headline_results_match_the_evaluation_output():
    """The abstract, Chapter 6 and Chapter 8 each restate the gold-standard
    result. Re-running scripts/run_evaluation.py rewrites the JSON, not the
    prose, so any change there has to show up here."""
    results = json.loads((EVIDENCE / "evaluation_results.json").read_text(encoding="utf-8"))
    pop, meta = results["population_extraction"], results["metadata"]
    det = pop["detection"]
    p, r, f1 = (f"{det[k]:.3f}" for k in ("precision", "recall", "f1"))
    claims = [
        ("00-front-matter.md", f"precision {p}, recall {r} and F1 {f1}"),
        ("00-front-matter.md", f"correct for {pop['value_correct']} of {pop['value_total']} positive cases"),
        ("00-front-matter.md", f"correct for {pop['semantic_type_correct']} of {pop['semantic_type_total']}"),
        ("00-front-matter.md", f"succeeded for {meta['papers_resolved']} of {meta['papers_attempted']} papers"),
        ("06-evaluation-results.md", f"| Precision | {p} |"),
        ("06-evaluation-results.md", f"| Recall | {r} |"),
        ("06-evaluation-results.md", f"| F1 | {f1} |"),
        ("08-conclusion.md", f"precision {p} and recall {r} (F1 {f1}"),
        ("08-conclusion.md", f"correct in {pop['value_correct']} of {pop['value_total']} positive cases"),
    ]
    stale = [(chapter, text) for chapter, text in claims if text not in _chapter(chapter)]
    assert not stale, f"these no longer match evaluation_results.json: {stale}"


def test_flow_diagram_results_match_the_held_out_run():
    """Section 6.14 reports one run on 42 held-out diagrams. Its numbers are
    recomputed here from the rows that run wrote, so the section cannot keep
    quoting a result the evidence no longer contains."""
    run = json.loads((EVIDENCE / "flow_diagrams" / "results_heldout.json").read_text(encoding="utf-8"))
    stated = [row for row in run["rows"] if row["vision_outcome"] != "not_stated"]
    decision = [row for row in stated if row["stage"] in ("enrolled", "randomised", "analysed")]
    n = len(decision)
    vision = sum(row["vision_outcome"] == "right" for row in decision)
    text = sum(row["text_outcome"] == "right" for row in decision)
    present = sum(bool(row["text_value_present"]) for row in decision)
    pct = lambda a, b: f"{round(100 * a / b)}%"

    claims = [
        ("06c-flow-diagrams.md", f"| Diagram reader | {vision} / {n} ({pct(vision, n)}) |"),
        ("06c-flow-diagrams.md", f"| Text method, stage-typed | {text} / {n} ({pct(text, n)}) |"),
        ("06c-flow-diagrams.md", f"| Text method, right number under any label | {present} / {n} ({pct(present, n)}) |"),
        ("06c-flow-diagrams.md", f"{len({row['pmcid'] for row in run['rows']})} held-out diagrams give {n} scored"),
        ("00-front-matter.md", f"read {vision} of {n} stated counts correctly against {text} of {n}"),
        ("08-conclusion.md", f"right on {vision} of {n} stated counts where the text method was right on {text}"),
    ]
    for stage in ("screened", "enrolled", "randomised", "analysed"):
        rows = [row for row in stated if row["stage"] == stage]
        v = sum(row["vision_outcome"] == "right" for row in rows)
        t = sum(row["text_outcome"] == "right" for row in rows)
        claims.append(("06c-flow-diagrams.md",
                       f"| {stage.capitalize()} | {v} / {len(rows)} ({pct(v, len(rows))}) "
                       f"| {t} / {len(rows)} ({pct(t, len(rows))}) |"))
    stale = [(chapter, claim) for chapter, claim in claims if claim not in _chapter(chapter)]
    assert not stale, f"these no longer match results_heldout.json: {stale}"

    if "p < 0.0001" in _chapter("06c-flow-diagrams.md"):
        assert run["mcnemar_p"] < 1e-4
    misses = [row for row in decision if row["vision_outcome"] != "right"]
    assert _quoted("06c-flow-diagrams.md", r"(\w+) of the (\w+) held-out misses") == (
        sum(row["vision_outcome"] == "missed" for row in misses), len(misses))


def test_second_reading_matches_its_summary():
    """Section 6.14.7 quotes the blind second reading. Its numbers come from
    second_annotator_summary.json, which scripts/second_annotator.py --summarise
    computes from the raw replies and adjudication.json."""
    summary = json.loads((EVIDENCE / "flow_diagrams" / "second_annotator_summary.json").read_text(encoding="utf-8"))
    pct = lambda a, b: f"{round(100 * a / b)}%"
    rows = [(name.capitalize() if name == "qwen" else "ChatGPT", v["figures"], v["values"], v["agreed"])
            for name, v in sorted(summary["by_provider"].items(), key=lambda kv: kv[0] != "qwen")]
    rows.append(("Both", summary["read"], summary["values"], summary["agreed"]))
    held, dev = summary["rescored"]["heldout"], summary["rescored"]["second_dev"]
    fmt = lambda c: f"{c['vision']} of {c['n']}"
    claims = [f"| {name} | {f} | {n} | {a} ({pct(a, n)}) |" for name, f, n, a in rows] + [
        f"Each of the {summary['disagreements']} disagreements was settled",
        f"from {fmt(held['original_key'])} to {fmt(held['ambiguous_unscored'])}",
        f"right on {held['ambiguous_unscored']['text']} in both",
        f"from {fmt(dev['original_key'])} to {fmt(dev['ambiguous_unscored'])}",
    ]
    stale = [c for c in claims if c not in _chapter("06c-flow-diagrams.md")]
    assert not stale, f"Section 6.14.7 no longer matches second_annotator_summary.json: {stale}"
    assert held["original_key"]["text"] == held["ambiguous_unscored"]["text"]
    assert _quoted("06c-flow-diagrams.md", r"(\w+) were the second reader's errors") == (summary["second_annotator_errors"],)
    assert _quoted("06c-flow-diagrams.md", r"The other (\w+) are cases") == (summary["ambiguous"],)
    assert summary["key_values_contradicted_by_the_image"] == 0 or "none showed" not in _chapter("06c-flow-diagrams.md")


def test_ranking_fix_matches_the_comparison():
    """Section 5.6.4 quotes scripts/compare_rankings.py, which reruns the
    pipeline on the three evaluation seeds. Any later change to the ranking
    rewrites that JSON, and this keeps the table and its summary in step."""
    runs = json.loads((EVIDENCE / "ranking_comparison.json").read_text(encoding="utf-8"))["runs"]
    labels = {"10.1056/NEJMoa2002032": "COVID-19 in China", "10.1038/s41586-021-03819-2": "AlphaFold",
              "10.1056/NEJMoa1911303": "Dapagliflozin in heart failure"}

    def changed(run, variant):
        lost = 10 - run["top10_overlap_with_current"][variant]
        if lost:
            return f"{lost} papers" if lost > 1 else "1 paper"
        return "none" if run["top10_identical_order"][variant] else "order only"

    rows = [f"| {labels[r['seed']]} | {round(100 * r['pagerank_term_share_before_fix']['median'])}% before, "
            f"{round(100 * r['pagerank_term_share_of_top10_score']['median'])}% after | "
            f"{changed(r, 'before_fix')} | {changed(r, 'unweighted_pr')} |" for r in runs]
    stale = [row for row in rows if row not in _chapter("05-implementation.md")]
    assert not stale, f"Section 5.6.4 no longer matches ranking_comparison.json: {stale}"
    moved = sum(r["top10_overlap_with_current"]["unweighted_pr"] < 10 for r in runs)
    for chapter in ("05-implementation.md", "06-evaluation-results.md", "07-discussion.md", "08-conclusion.md"):
        if "one seed in three" in _chapter(chapter):
            assert (moved, len(runs)) == (1, 3), f"{chapter} says one seed in three; the evidence says {moved} of {len(runs)}"


# ---------------------------------------------------------------- code


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(SRC.parent).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


@lru_cache(maxsize=None)
def _import_graph() -> tuple[int, int, frozenset, frozenset]:
    """Modules, module-level imports, and the package graph Figure 4.1 draws.

    Recomputed with ast rather than by running pyreverse, so the check needs no
    Graphviz; on 2026-09-25 it reproduced the generator's 94 imports and 40
    package edges exactly."""
    files = {_module_name(p): p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts}
    edges = set()
    for name, path in files.items():
        package = name if path.name == "__init__.py" else name.rsplit(".", 1)[0]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level:
                base = package.split(".")[: len(package.split(".")) - node.level + 1]
                targets = [".".join(base + ([node.module] if node.module else []))]
            elif isinstance(node, ast.ImportFrom):
                targets = [node.module or ""]
            else:
                continue
            for target in targets:
                while target and target not in files:
                    target = target.rpartition(".")[0]
                if target.startswith("citegraph.") and target != name:
                    edges.add((name, target))
    top = lambda module: "citegraph." + module.split(".")[1]
    packages = {(top(a), top(b)) for a, b in edges
                if a != "citegraph" and top(a) != top(b)}
    return len(files), len(edges), frozenset({p for e in packages for p in e}), frozenset(packages)


def test_figure_4_1_is_the_import_graph_of_the_current_code():
    """The figure is generated, so it can only be wrong by being old. A package
    added since it was drawn (vision, on 2026-09-25) is missing from it."""
    _, _, packages, edges = _import_graph()
    svg = (FIGURES / "architecture_packages.svg").read_text(encoding="utf-8")
    drawn = set(_svg_nodes("architecture_packages.svg"))
    drawn_edges = set(re.findall(r"<title>([\w.]+)&#45;&gt;([\w.]+)</title>", svg))
    assert drawn == packages and drawn_edges == edges, (
        f"Figure 4.1 is stale (missing {sorted(packages - drawn)}, extra {sorted(drawn - packages)}, "
        f"{len(edges ^ drawn_edges)} edges differ). Regenerate: python scripts/generate_diagrams.py")


def test_figure_5_1_shows_every_call_run_makes():
    """Figure 5.1 claims to show the calls under PipelineOrchestrator.run().
    code2flow draws a call only when its target's name is unique in the
    project, so only those are required; `resolve`, defined four times, is
    the kind it cannot place."""
    definitions: dict[str, int] = {}
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions[node.name] = definitions.get(node.name, 0) + 1
    tree = ast.parse((SRC / "pipeline" / "orchestrator.py").read_text(encoding="utf-8"))
    run = next(n for n in ast.walk(tree)
               if isinstance(n, ast.AsyncFunctionDef) and n.name == "run")
    called = set()
    for node in ast.walk(run):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            root = node.func.value
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name) and root.id == "self":
                called.add(node.func.attr)
    # code2flow titles its nodes with hashes; the function names are the labels.
    drawn = " ".join(re.findall(r"<text[^>]*>([^<]+)</text>",
                                (FIGURES / "callgraph_pipeline.svg").read_text(encoding="utf-8")))
    missing = sorted(c for c in called if definitions.get(c) == 1 and f"{c}()" not in drawn)
    assert not missing, f"run() calls {missing}, which Figure 5.1 does not show. Regenerate it."


def test_counts_quoted_from_the_figures_match_them():
    """Prose that quotes a figure goes stale with it: five of these were wrong
    on 2026-09-25, a week after the code they count had changed."""
    modules, imports, packages, package_edges = _import_graph()
    core, full = len(_svg_nodes("classes_core.svg")), len(_svg_nodes("classes_full.svg"))
    tree = ast.parse((SRC / "pipeline" / "orchestrator.py").read_text(encoding="utf-8"))
    init = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    collaborators = sum(isinstance(s, ast.Assign) and isinstance(s.value, ast.Call) for s in init.body)
    checks = [
        ("04-design.md", r"collapsing its (\d+) module nodes to the (\d+) packages", (modules, len(packages))),
        ("04-design.md", r"with the (\d+) unrelated classes removed", (full - core,)),
        ("04-design.md", r"`PipelineOrchestrator` composes (\w+) collaborators", (collaborators,)),
        ("17-appendix-h-diagrams.md", r"raw output has (\d+) module nodes and (\d+) import edges", (modules, imports)),
        ("17-appendix-h-diagrams.md", r"leaves (\d+) nodes and (\d+) edges", (len(packages), len(package_edges))),
        ("17-appendix-h-diagrams.md", r"including the (\d+) that take part in no association", (full - core,)),
        ("17-appendix-h-diagrams.md", r"`code2flow`: (\d+) functions", (len(_svg_nodes("callgraph_full.svg")),)),
        ("figures/README.md", r"(\d+) modules collapsed to (\d+) packages", (modules, len(packages))),
    ]
    stale = [(c, p, _quoted(c, p), want) for c, p, want in checks if _quoted(c, p) != want]
    assert not stale, "\n".join(f"{c}: {p!r} says {got}, the figure has {want}"
                                for c, p, got, want in stale)


# ---------------------------------------------------------------- build


def test_the_assembled_thesis_is_built_from_the_current_chapters():
    """Chapters are edited; CiteGraph-NLP-Thesis.md is what gets rendered.
    Forgetting scripts/build_thesis.py leaves the PDF describing last week."""
    build = _build()
    assert (THESIS / "13-references.md").read_text(encoding="utf-8") == build.build_references()
    assert (THESIS / "12-appendix-d-gold-standard.md").read_text(encoding="utf-8") == \
        build.build_gold_standard_appendix()
    document, missing = build.assembled_text()
    assert not missing, f"CHAPTERS lists files that do not exist: {missing}"
    assert (THESIS / "CiteGraph-NLP-Thesis.md").read_text(encoding="utf-8") == document, \
        "the assembled thesis is stale: python scripts/build_thesis.py"


PDFS = ["CiteGraph-NLP-Thesis.pdf", "renders/1-current-as-committed.pdf",
        "renders/2-academic-serif.pdf", "renders/3-modern-report.pdf"]


@lru_cache(maxsize=None)
def _pdf(name: str) -> tuple[int, str]:
    fitz = pytest.importorskip("fitz")
    with fitz.open(THESIS / name) as document:
        return document.page_count, re.sub(r"\s+", " ", " ".join(p.get_text() for p in document))


@pytest.mark.parametrize("name", PDFS)
def test_every_pdf_carries_every_section(name):
    """A heading is looked for as its number followed by its first word, as
    the renderer prints it. A PDF missing one was rendered before the section
    was written."""
    document, _ = _build().assembled_text()
    headings = re.findall(r"^#{1,4} ((?:\d+|[A-H])(?:\.\d+)+) \W*(\w+)", document, re.M)
    _, text = _pdf(name)
    missing = [f"{number} {word}" for number, word in headings if f"{number} {word}" not in text]
    assert not missing, (f"{name} lacks {missing[:5]}{' ...' if len(missing) > 5 else ''}; "
                         f"re-render: python scripts/render_thesis.py --docx && python scripts/render_variants.py")


def test_page_counts_quoted_in_the_readmes_match_the_pdfs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    renders = (THESIS / "renders" / "README.md").read_text(encoding="utf-8")
    pages = _pdf("CiteGraph-NLP-Thesis.pdf")[0]
    quoted = {
        "README badge": int(re.search(r"thesis-(\d+)%20pages", readme).group(1)),
        "README table": int(re.search(r"The full thesis: (\d+) pages", readme).group(1)),
    }
    wrong = {k: v for k, v in quoted.items() if v != pages}
    for name in PDFS[1:]:
        stated = int(re.search(rf"\| `{re.escape(Path(name).name)}` \| (\d+) \|", renders).group(1))
        if stated != _pdf(name)[0]:
            wrong[name] = stated
    assert not wrong, f"page counts quoted {wrong}; the PDFs have {pages} and the renders " \
                      f"{[_pdf(n)[0] for n in PDFS[1:]]}"


def test_test_counts_quoted_match_the_suite(request):
    """Appendix F said 102 tests in eight files while the suite grew to 199 in
    thirteen. The count is this session's own collection, so it costs nothing
    and counts a parametrised case the way `pytest -q` reports it; it is only
    meaningful when the whole suite was collected, so otherwise it skips."""
    option = request.config.option
    on_disk = {p.name for p in (ROOT / "tests").glob("test_*.py")}
    per_file: dict[str, int] = {}
    for item in request.session.items:
        name = Path(str(item.fspath)).name
        per_file[name] = per_file.get(name, 0) + 1
    if set(per_file) != on_disk or option.keyword or option.markexpr or getattr(option, "deselect", None):
        pytest.skip("test counts are checked only when the whole suite runs, as `pytest -q` does")
    total = sum(per_file.values())

    appendix = (THESIS / "15-appendix-f-tests.md").read_text(encoding="utf-8")
    listed = {name: int(n) for name, n in re.findall(r"^\| `(test_\w+\.py)` \| (\d+) \|", appendix, re.M)}
    quoted = {
        "Appendix F opening": _quoted("15-appendix-f-tests.md", r"(\d+) automated tests across (\w+) files"),
        "Appendix F total": _quoted("15-appendix-f-tests.md", r"\| \*\*Total\*\* \| \*\*(\d+)\*\* \|"),
        "Appendix C.2": _quoted("11-appendix-c-reproducing.md", r"Expected: \*\*(\d+) passed\*\*"),
        "README badge": _quoted("../README.md", r"tests-(\d+)%20passing"),
        "README tree": _quoted("../README.md", r"tests/ +# (\d+) tests"),
    }
    actual = {"Appendix F opening": (total, len(per_file))}
    wrong = {k: v for k, v in quoted.items() if v != actual.get(k, (total,))}
    if listed != per_file:
        wrong["Appendix F table"] = sorted(set(listed.items()) ^ set(per_file.items()))
    assert not wrong, f"the suite has {total} tests in {len(per_file)} files; these say otherwise: {wrong}"


# ---------------------------------------------------------------- claims

# Statements that were true when written and are false now. Each stays here
# with the reason, so a chapter restored from an old copy cannot bring one back.
RETIRED = [
    (r"reads abstracts only", "open-access full text is read as a fallback since e2a1759"),
    (r"does not read full text", "open-access full text is read as a fallback since e2a1759"),
    (r"no PDF parsing is implemented", "arXiv PDFs are parsed for dataset counts"),
    (r"executes nine stages", "the full-text stage made it ten"),
    (r"no comparison against unweighted PageRank was", "run since c3dfdcd; Section 5.6.4"),
    (r"top-ranked foundational paper was Anfinsen", "it ties for first with a 1993 paper"),
]


def test_retired_claims_stay_retired():
    found = [(name, phrase, why) for name in _build().CHAPTERS
             for phrase, why in RETIRED if re.search(phrase, _chapter(name), re.I)]
    assert not found, "\n".join(f"{n}: {p!r} is no longer true ({w})" for n, p, w in found)


def test_every_citation_is_a_verified_reference():
    """The bibliography holds only DOIs that resolved (scripts/verify_references.py).
    A key cited in the text but absent there prints as a bare bracket."""
    verified = {r["key"] for r in json.loads(
        (EVIDENCE / "references_verified.json").read_text(encoding="utf-8"))["verified"]}
    document, _ = _build().assembled_text()
    unknown = sorted(set(_build().inventory(document)["citations"]) - verified)
    assert not unknown, f"cited but not verified: {unknown}"
