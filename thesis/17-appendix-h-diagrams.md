# Appendix H: Full-Scale Generated Diagrams

Every figure in this thesis that describes the structure of the system was
produced by running a tool over `src/citegraph`, not by drawing it. The
chapters show reduced views chosen to stay legible at page width. This
appendix carries the complete plates the reductions were taken from, so a
reader can check that nothing material was hidden by the reduction.

## H.1 How the figures are produced

One script generates all eight:

```bash
python scripts/generate_diagrams.py
```

It needs `pylint` (which supplies `pyreverse`), `code2flow`, and the Graphviz
`dot` binary on `PATH`. Output lands in `thesis/figures/` as SVG. The script
prints the node and edge counts for each figure, which is how the counts
quoted in the captions were obtained.

| Figure | Source | Tool |
|--------|--------|------|
| 4.1 Inter-package dependencies | `src/citegraph` imports | `pyreverse`, collapsed to packages |
| 4.2 Object composition | class attributes | `pyreverse -k`, filtered to connected classes |
| 4.3 Data model, extraction half | `models/` Pydantic classes | introspection of `model_fields` |
| 4.4 Data model, graph half | `models/` Pydantic classes | introspection of `model_fields` |
| 5.1 Orchestrator call graph | `pipeline/orchestrator.py` | `code2flow`, depth 2 |
| H.1 Combined data model | `models/` Pydantic classes | introspection of `model_fields` |
| H.2 Complete class diagram | all classes | `pyreverse` |
| H.3 Complete call graph | all functions | `code2flow` |

The data-model figures deserve a note on method. They are not parsed from
source text; the script imports the Pydantic classes and reads
`model_fields`, which is the same structure Pydantic uses to validate incoming
data at runtime. A field renamed in the code changes the next figure without
anyone editing a diagram, and a figure showing a field that no longer exists
is not possible.

## H.2 Why the chapter figures are reduced

Three reductions are applied, each for the same reason. How legible a
Graphviz figure is at a fixed page width depends only on the ratio between its
font size and its total width, and enlarging the font enlarges the boxes by
the same proportion. Narrowing the graph is therefore the only lever
available.

**Collapsing modules to packages** (Figure 4.1). The raw output has 52 module
nodes and 94 import edges, and at page width its labels render at roughly
three points. Collapsing each module to its package leaves 14 nodes and 40
edges, and carries the discarded detail as edge thickness rather than losing
it.

**Filtering unrelated classes** (Figure 4.2). `pyreverse` draws every class it
finds, including the 19 that take part in no association or inheritance
relationship. Those 19 occupy a full column of the canvas and contribute no
structure, so they are dropped from the chapter figure. Plate H.2 below
retains them.

**Splitting the data model** (Figures 4.3 and 4.4). Seven entities carrying 67
fields do not fit one page at a readable size in any orientation. The chapter
uses two overlapping views, one per half of the pipeline, with `Paper`,
`Study` and `PopulationResolution` appearing in both because they are the
entities the two halves share. Plate H.1 below is the combined view.

No reduction removes an entity, a class relationship or a package dependency
without it appearing in a plate here.

## H.3 Plates

![**Plate H.1** The complete data model: all seven Pydantic entities with
every field and type, and all ten relationships. Figures 4.3 and 4.4 are the
two halves of this diagram.](figures/datamodel_full.svg){width=64%}

\newpage

![**Plate H.2** The complete class diagram from `pyreverse`, including the
classes that participate in no relationship. Reproduced at full scale; the
labels are small in print and are intended to be read by zooming the PDF or by
opening `thesis/figures/classes_full.svg`, which is vector and scales without
loss.](figures/classes_full.svg){width=100%}

\newpage

![**Plate H.3** The complete call graph from `code2flow`: 144 functions and
every call between them, grouped by file and class. Figure 5.1 is the subgraph
reachable from `PipelineOrchestrator.run()` within two
levels.](figures/callgraph_full.svg){width=88%}

## H.4 A caveat on the call graphs

`code2flow` resolves calls statically by name, which has two consequences a
reader should keep in mind when using Plate H.3 as a map of control flow.

Calls made through a variable whose type it cannot infer are recorded against
an unknown owner and do not appear as edges. This affects the provider calls
most, because the orchestrator holds providers behind the `MetadataProvider`
protocol; a call to `provider.resolve()` cannot be attributed to
`OpenAlexProvider`, `CrossrefProvider` or `EuropePMCProvider` without running
the program. The three concrete providers therefore appear less connected in
the plate than they are at runtime.

Second, the tool records a call site, not a call count or an execution order.
An edge drawn once may execute once per paper in a graph of several hundred,
and the left-to-right arrangement within a rank carries no meaning. Section
6.6 gives the measured runtime distribution, which is the correct source for
where time is actually spent.

Neither limitation affects the class, package or data-model figures, which are
derived from declarations rather than from call sites.
