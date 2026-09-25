"""Generate the thesis figures from the real code, not from a hand-drawn sketch.

Eight figures, all derived by running a tool over the source tree:

  architecture_packages.svg  inter-package dependencies      (pyreverse)
  datamodel_extraction.svg   entities, query to population   (Pydantic introspection)
  datamodel_graph.svg        entities, population to result  (Pydantic introspection)
  datamodel_full.svg         all seven, appendix plate       (Pydantic introspection)
  classes_core.svg           class composition, connected    (pyreverse)
  callgraph_pipeline.svg     calls under the orchestrator    (code2flow)
  classes_full.svg           every class, appendix plate     (pyreverse)
  callgraph_full.svg         every call, appendix plate      (code2flow)

Three post-processing steps exist because the raw tool output is unreadable at
A4 width. Legibility at a fixed page width depends only on the ratio of font
size to graph width, so the only way to make a figure readable is to narrow it:

  collapse   52 module nodes become 14 package nodes, with each edge weighted
             by the number of imports it stands for
  filter     the 22 classes that take part in a relationship are kept and the
             ones pyreverse draws floating are dropped
  relayout   rankdir=LR turns a 2435pt-wide strip into an 827pt portrait block

Needs pylint, code2flow and the Graphviz dot binary.

    python scripts/generate_diagrams.py
"""

from __future__ import annotations

import argparse
import collections
import os
import re
import shutil
import subprocess
import sys
import typing

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
FIGURES = os.path.join(ROOT, "thesis", "figures")
WORK = os.path.join(FIGURES, "_dot")
sys.path.insert(0, SRC)


def tool(name: str) -> str:
    return shutil.which(name) or os.path.join(ROOT, ".venv", "Scripts", f"{name}.exe")


def _dimensions(svg_path: str) -> str:
    with open(svg_path, encoding="utf-8") as fh:
        head = fh.read(600)
    found = re.search(r'width="(\d+)pt" height="(\d+)pt"', head)
    return f"{found.group(1)}x{found.group(2)}pt" if found else "?"


def companion_png(stem: str, dot_path: str, *flags: str) -> None:
    """Render a raster copy of a figure for the DOCX path.

    Pandoc cannot place an SVG in a DOCX without rsvg-convert, which is not
    part of a normal Pandoc install, so every figure is written twice. The PDF
    path uses the vector copy and keeps the labels sharp at any zoom; the DOCX
    path falls back to these. 200 dpi is enough that the smallest label in the
    appendix plates is still readable on screen.
    """
    png_path = os.path.join(FIGURES, f"{stem}.png")
    subprocess.run(["dot", *flags, "-Gdpi=200", "-Tpng", dot_path, "-o", png_path],
                   capture_output=True, text=True)


def render(dot_source: str, stem: str, *flags: str) -> None:
    """Write DOT to the work directory and render it to SVG beside the figures."""
    dot_path = os.path.join(WORK, f"{stem}.gv")
    svg_path = os.path.join(FIGURES, f"{stem}.svg")
    with open(dot_path, "w", encoding="utf-8") as fh:
        fh.write(dot_source)
    result = subprocess.run(["dot", *flags, "-Tsvg", dot_path, "-o", svg_path],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    {stem}: dot failed: {result.stderr.strip()[:160]}")
        return
    companion_png(stem, dot_path, *flags)
    print(f"    {stem}.svg  {os.path.getsize(svg_path)/1024:>5.0f} KB  "
          f"{_dimensions(svg_path)}")


def pyreverse(project: str, target: str, *extra: str) -> None:
    subprocess.run(
        [tool("pyreverse"), "-o", "dot", "-p", project,
         "--output-directory", WORK, *extra, target],
        cwd=SRC, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": SRC},
    )


def read_dot(name: str) -> str:
    path = os.path.join(WORK, name)
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""


# --------------------------------------------------------------------------
# Figure: inter-package dependencies
# --------------------------------------------------------------------------

def package_graph() -> str:
    """Collapse pyreverse's per-module graph to one node per package."""
    src = read_dot("packages_ALL.dot")

    def pkg(module: str) -> str:
        parts = module.split(".")
        return ".".join(parts[:2]) if len(parts) > 1 else module

    weights: collections.Counter = collections.Counter()
    for a, b in re.findall(r'"([\w.]+)"\s*->\s*"([\w.]+)"', src):
        pa, pb = pkg(a), pkg(b)
        if pa != pb:
            weights[(pa, pb)] += 1

    # Ranked so the figure reads top-down in the order the pipeline runs.
    layers = [
        ("citegraph.api",),
        ("citegraph.pipeline",),
        ("citegraph.input", "citegraph.metadata", "citegraph.citations",
         "citegraph.nlp", "citegraph.graph"),
        ("citegraph.providers", "citegraph.evaluation"),
        ("citegraph.models", "citegraph.storage", "citegraph.utils",
         "citegraph.config"),
    ]
    fill = {0: "#1f4e79", 1: "#2e75b6", 2: "#5b9bd5", 3: "#9dc3e6", 4: "#bdd7ee"}
    rank_of = {name: i for i, row in enumerate(layers) for name in row}

    lines = [
        "digraph packages {",
        '  graph [rankdir=TB, fontname="Helvetica", nodesep=0.35, ranksep=0.75, '
        'splines=polyline, bgcolor="transparent"];',
        '  node  [shape=box, style="filled,rounded", fontname="Helvetica", '
        'fontsize=13, height=0.42, color="#dddddd"];',
        '  edge  [color="#7f7f7f", arrowsize=0.7];',
        "",
    ]
    nodes = {n for e in weights for n in e}
    for name in sorted(nodes):
        depth = rank_of.get(name, 4)
        text = "white" if depth <= 1 else "#10243a"
        short = name.replace("citegraph.", "")
        lines.append(f'  "{name}" [label="{short}", fillcolor="{fill[depth]}", '
                     f'fontcolor="{text}"];')

    lines.append("")
    for row in layers:
        present = [f'"{n}"' for n in row if n in nodes]
        if present:
            lines.append(f"  {{ rank=same; {' '.join(present)} }}")

    lines.append("")
    for (a, b), count in sorted(weights.items()):
        width = min(1.0 + 0.35 * (count - 1), 3.2)
        lines.append(f'  "{a}" -> "{b}" [penwidth={width:.2f}];')
    lines.append("}")
    print(f"    ({len(nodes)} packages, {len(weights)} dependencies, collapsed "
          f"from {src.count('->')} module imports)")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Figure: domain entity relationships
# --------------------------------------------------------------------------

def _type_name(annotation: typing.Any) -> str:
    text = str(annotation)
    text = text.replace("typing.", "").replace("citegraph.models.", "")
    for module in ("paper.", "study.", "population.", "citation.", "run."):
        text = text.replace(module, "")
    text = text.replace("<class '", "").replace("'>", "")
    if text.startswith("Optional["):
        text = text[len("Optional["):].rstrip("]") + " ?"
    text = text.replace("datetime.datetime", "datetime")
    return text if len(text) <= 38 else text[:37] + "…"


ALL_RELATIONS = [
    ("PaperQuery", "Paper", "resolves to"),
    ("Paper", "PopulationCandidate", "abstract yields 0..n"),
    ("PopulationCandidate", "PopulationResolution", "n..1 chosen"),
    ("Paper", "Study", "1..1"),
    ("Paper", "CitationEdge", "source, target"),
    ("PopulationResolution", "CitationEdge", "supplies weight"),
    ("RunResult", "Paper", "collects"),
    ("RunResult", "CitationEdge", "collects"),
    ("RunResult", "PopulationResolution", "collects"),
    ("RunResult", "Study", "collects"),
]


def _models() -> dict:
    from citegraph.models.paper import Paper, PaperQuery
    from citegraph.models.study import Study
    from citegraph.models.population import PopulationCandidate, PopulationResolution
    from citegraph.models.citation import CitationEdge
    from citegraph.models.run import RunResult
    return {m.__name__: m for m in (PaperQuery, Paper, Study, PopulationCandidate,
                                    PopulationResolution, CitationEdge, RunResult)}


def data_model(names: tuple = (), rankdir: str = "LR") -> str:
    """Render an ER view over `names`, or over every entity when empty.

    Seven entities carrying 67 fields will not fit one page legibly, so the
    chapter uses two views that each cover one half of the pipeline and the
    appendix carries the combined plate.
    """
    registry = _models()
    names = names or tuple(registry)
    entities = [registry[n] for n in names]
    relations = [r for r in ALL_RELATIONS if r[0] in names and r[1] in names]

    lines = [
        "digraph datamodel {",
        f'  graph [rankdir={rankdir}, fontname="Helvetica", splines=spline, '
        f'nodesep=0.45, ranksep=1.0, bgcolor="transparent"];',
        '  node  [shape=plaintext, fontname="Helvetica"];',
        '  edge  [fontname="Helvetica", fontsize=11, color="#666666", arrowsize=0.75];',
        "",
    ]
    for model in entities:
        fields = list(model.model_fields.items())
        rows = "".join(
            f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="11">{name}</FONT></TD>'
            f'<TD ALIGN="LEFT"><FONT POINT-SIZE="10" COLOR="#777777">'
            f'{_type_name(field.annotation)}</FONT></TD></TR>'
            for name, field in fields[:13]
        )
        if len(fields) > 13:
            rows += ('<TR><TD COLSPAN="2" ALIGN="LEFT"><FONT POINT-SIZE="10" '
                     f'COLOR="#aaaaaa">and {len(fields)-13} more</FONT></TD></TR>')
        label = (
            '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
            f'<TR><TD COLSPAN="2" BGCOLOR="#1f4e79"><FONT COLOR="white" '
            f'POINT-SIZE="13"><B>{model.__name__}</B></FONT></TD></TR>'
            f'{rows}</TABLE>>'
        )
        lines.append(f"  {model.__name__} [label={label}];")

    lines.append("")
    for a, b, label in relations:
        lines.append(f'  {a} -> {b} [label="{label}"];')
    lines.append("}")
    total = sum(len(m.model_fields) for m in entities)
    print(f"    ({len(entities)} entities, {total} fields, "
          f"{len(relations)} relationships)")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Figures: class diagrams
# --------------------------------------------------------------------------

def class_graph(dot_name: str, connected_only: bool) -> str:
    src = read_dot(dot_name)
    edges = re.findall(r'^\s*"?([\w.]+)"?\s*->\s*"?([\w.]+)"?', src, re.M)
    keep = {n for e in edges for n in e}
    out, dropped = [], 0
    for line in src.splitlines():
        match = re.match(r'^\s*"?([\w.]+)"?\s*\[', line)
        if match and match.group(1) not in ("graph", "node", "edge"):
            if connected_only and match.group(1) not in keep:
                dropped += 1
                continue
        out.append(line)
    if connected_only:
        print(f"    ({len(keep)} classes in {len(edges)} relationships; "
              f"{dropped} unrelated classes dropped)")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Figures: call graphs
# --------------------------------------------------------------------------

def code2flow(stem: str, *extra: str) -> None:
    """Trace calls with code2flow, then render the SVG and PNG from one DOT.

    code2flow assigns edge colours at random on each run, so asking it twice
    for the two formats would give the PDF and the DOCX visibly different
    figures. Writing DOT once and rendering it twice keeps them identical.
    """
    svg_path = os.path.join(FIGURES, f"{stem}.svg")
    dot_path = os.path.join(WORK, f"{stem}.gv")
    traced = subprocess.run(
        [tool("code2flow"), os.path.join(SRC, "citegraph"),
         "--output", dot_path, "--language", "py", *extra],
        capture_output=True, text=True,
    )
    if os.path.exists(dot_path):
        subprocess.run(["dot", "-Tsvg", dot_path, "-o", svg_path],
                       capture_output=True, text=True)
        companion_png(stem, dot_path)
    if not os.path.exists(svg_path):
        print(f"    {stem}: code2flow produced nothing "
              f"({(traced.stderr or '').strip()[:120]})")
        return
    nodes = open(svg_path, encoding="utf-8").read().count('class="node"')
    print(f"    {stem}.svg  {os.path.getsize(svg_path)/1024:>5.0f} KB  "
          f"{_dimensions(svg_path)}  {nodes} nodes")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-dot", action="store_true",
                        help="leave the intermediate DOT sources in place")
    args = parser.parse_args()

    if not shutil.which("dot"):
        raise SystemExit("Graphviz dot is not on PATH")
    os.makedirs(FIGURES, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)

    print("pyreverse")
    pyreverse("ALL", "citegraph")
    pyreverse("KN", "citegraph", "-k")

    print("\nFigure: inter-package dependencies")
    render(package_graph(), "architecture_packages")

    print("\nFigure: data model, extraction half")
    render(data_model(("PaperQuery", "Paper", "Study", "PopulationCandidate",
                       "PopulationResolution"), rankdir="TB"), "datamodel_extraction")

    print("\nFigure: data model, graph half")
    render(data_model(("Paper", "Study", "PopulationResolution",
                       "CitationEdge", "RunResult")), "datamodel_graph")

    print("\nFigure: combined data model (appendix plate)")
    render(data_model(rankdir="TB"), "datamodel_full")

    print("\nFigure: class composition (connected classes)")
    render(class_graph("classes_KN.dot", connected_only=True), "classes_core",
           "-Grankdir=LR", "-Gnodesep=0.14", "-Granksep=0.6",
           "-Gbgcolor=transparent")

    print("\nFigure: full class diagram (appendix plate)")
    render(class_graph("classes_ALL.dot", connected_only=False), "classes_full",
           "-Grankdir=LR", "-Gnodesep=0.12", "-Granksep=0.5",
           "-Gbgcolor=transparent")

    print("\nFigure: call graph under the orchestrator")
    code2flow("callgraph_pipeline", "--target-function", "PipelineOrchestrator.run",
              "--downstream-depth", "2")

    print("\nFigure: full call graph (appendix plate)")
    code2flow("callgraph_full")

    if not args.keep_dot:
        shutil.rmtree(WORK, ignore_errors=True)

    print("\nfigures written:")
    for name in sorted(os.listdir(FIGURES)):
        if name.endswith(".svg"):
            size = os.path.getsize(os.path.join(FIGURES, name)) / 1024
            print(f"  {name:<32} {size:>6.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
