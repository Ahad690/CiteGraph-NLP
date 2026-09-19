# Thesis figures

Every figure here is generated from the source tree by
`scripts/generate_diagrams.py`. None is drawn by hand, so none can drift from
the implementation it describes.

```bash
python scripts/generate_diagrams.py
```

Needs `pylint` (which supplies `pyreverse`), `code2flow`, and the Graphviz
`dot` binary on `PATH`.

---

## Thesis figure to source file

| Figure | Subject | File | Derived from |
|--------|---------|------|--------------|
| **4.1** | Inter-package dependencies | `architecture_packages.svg` | `pyreverse`, 46 modules collapsed to 13 packages |
| **4.2** | Object composition | `classes_core.svg` | `pyreverse -k`, connected classes only |
| **4.3** | Data model, query to population | `datamodel_extraction.svg` | Pydantic `model_fields` introspection |
| **4.4** | Data model, population to result | `datamodel_graph.svg` | Pydantic `model_fields` introspection |
| **5.1** | Orchestrator call graph | `callgraph_pipeline.svg` | `code2flow`, depth 2 from `run()` |
| **H.1** | Combined data model | `datamodel_full.svg` | all seven entities |
| **H.2** | Complete class diagram | `classes_full.svg` | every class `pyreverse` finds |
| **H.3** | Complete call graph | `callgraph_full.svg` | every call `code2flow` finds |

Each figure exists twice. The `.svg` is vector and is what the PDF uses, so
labels stay sharp at any zoom. The `.png` is rendered at 200 dpi from the same
DOT source and exists only because Pandoc cannot place an SVG in a DOCX
without `rsvg-convert`, which is not part of a normal Pandoc install. Do not
edit either by hand; both are regenerated together.

---

## Why the chapter figures are reduced

Raw tool output is unreadable at A4 width. How legible a Graphviz figure is
depends only on the ratio between its font size and its total width, and
enlarging the font enlarges the boxes by the same proportion, so narrowing
the graph is the only lever. The raw class diagram came out 7612pt wide, which
at page width renders 10pt labels at about 3pt.

Three reductions are applied:

- **Collapse** — module nodes become package nodes, with the discarded detail
  carried as edge thickness rather than lost.
- **Filter** — the classes that take part in no relationship are dropped from
  the chapter figure; they occupy a full column and contribute no structure.
- **Relayout** — `rankdir=LR` turns a 2435pt-wide strip into an 827pt portrait
  block.

Appendix H of the thesis documents every reduction and carries the full-scale
plates, so nothing is hidden by one.

---

## Caveat on the call graphs

`code2flow` resolves calls statically by name. Calls made through a variable
whose type it cannot infer are recorded against an unknown owner and do not
appear as edges. This affects the providers most, because the orchestrator
holds them behind the `MetadataProvider` protocol: a call to
`provider.resolve()` cannot be attributed to `OpenAlexProvider`,
`CrossrefProvider` or `EuropePMCProvider` without running the program. The
three concrete providers therefore look less connected than they are at
runtime.

The tool also records a call site, not a call count or an execution order. An
edge drawn once may execute hundreds of times in a single run. Section 6.6 of
the thesis gives the measured runtime distribution, which is the right source
for where time is actually spent.

Neither limitation affects the class, package or data-model figures, which
come from declarations rather than from call sites.

---

## Other assets

`../assets/nutech-logo.png` is the university crest used on the title page. It
is not generated.
