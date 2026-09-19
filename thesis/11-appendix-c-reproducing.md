# Appendix C: Reproducing the Results

Every quantitative claim in Chapter 6 is produced by a script committed to the
repository. This appendix gives the commands.

## C.1 Environment

```bash
git clone https://github.com/Ahad690/CiteGraph-NLP.git
cd CiteGraph-NLP
python -m venv .venv
# Windows:      .venv\Scripts\Activate.ps1
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set OPENALEX_EMAIL
```

Setting `OPENALEX_EMAIL` is not optional in practice. OpenAlex serves
identified callers from a faster "polite pool"; without it, request latency,
which Section 6.6 shows dominates runtime, is materially worse.

## C.2 Test suite

```bash
pytest -q
```

Expected: **102 passed**. The suite mocks all HTTP at transport level with
`respx`, so it requires no network access and no API keys.

## C.3 Evaluation (Chapter 6)

```bash
python scripts/run_evaluation.py --out thesis/evidence --max-papers 40
```

Writes `thesis/evidence/evaluation_results.json` and prints a summary.
Requires network access; takes roughly three to five minutes, most of it in the
three live traversals.

To reproduce only the extraction and metadata results (Sections 6.2–6.4) and
skip the traversals:

```bash
python scripts/run_evaluation.py --skip-graph --out thesis/evidence
```

The JSON artifact contains a `per_paper` array with the prediction, gold label,
confidence and abstract source for every gold-standard paper, which is the
source for the failure analysis in Sections 6.4.2 to 6.4.4.

## C.4 Reference verification (Section 6.7)

```bash
python scripts/verify_references.py --out thesis/evidence
```

Resolves every candidate DOI against Crossref, falling back to OpenAlex, and
writes `references_verified.json` and `references.bib`. Any candidate that
fails to resolve is printed as UNVERIFIED and excluded from the bibliography.

## C.5 Rebuilding the thesis

```bash
python scripts/build_thesis.py
```

Regenerates the reference list and the gold-standard appendix from the verified
artifacts, then concatenates all chapters into
`thesis/CiteGraph-NLP-Thesis.md`. The reference list is *generated*, not
hand-maintained, so it cannot drift from the verification record.

## C.6 Rendering to PDF

Two engines work. WeasyPrint needs no LaTeX installation and is what the
page counts in this thesis were measured with:

```bash
pandoc thesis/CiteGraph-NLP-Thesis.md \
  -o thesis/CiteGraph-NLP-Thesis.pdf \
  --pdf-engine=weasyprint \
  -f markdown-smart \
  --toc --toc-depth=3
```

Do not add `--number-sections`. Every section in this thesis already carries
its number in the heading text, and the cross-references throughout the body
point at those numbers. Pandoc's automatic numbering is added on top rather
than replacing them, so headings render with two numbers ("2.1 1.1 Background
and Motivation"), and its count is offset by one because it treats the front
matter as the first chapter.

`-f markdown-smart` matters. Pandoc's smart typography rewrites `--` as an en
dash and `---` as an em dash, so the rendered PDF ends up containing dashes the
source never had. A mechanical pre-submission check run against that PDF then
reports them as prose findings: five of the six em dashes flagged in one such
run came from this conversion rather than from the manuscript.

A DOCX, if the department requires one:

```bash
pandoc thesis/CiteGraph-NLP-Thesis.md \
  -o thesis/CiteGraph-NLP-Thesis.docx \
  -f markdown-smart \
  --toc --toc-depth=3
```

With a LaTeX distribution instead:

```bash
pandoc thesis/CiteGraph-NLP-Thesis.md \
  -o thesis/CiteGraph-NLP-Thesis.pdf \
  -f markdown-smart \
  --toc --toc-depth=3 \
  -V documentclass=report \
  -V papersize=a4 \
  -V fontsize=11pt \
  -V geometry:margin=1in \
  -V linkcolor=blue
```

`\newpage` markers between chapters are inserted by the assembly script and are
honoured by the LaTeX writer.

## C.7 Running the system

Locally:

```bash
uvicorn citegraph.api.main:app --reload     # API on :8000
cd frontend && npm install && npm run dev   # dashboard on :5173
```

Or the whole stack:

```bash
docker compose up --build
```

The deployed instance is documented in the project README.

## C.8 A caveat on exact reproduction

The evaluation queries live scholarly APIs. OpenAlex and Crossref revise
records continuously, abstracts are added, reference lists are corrected,
citation counts change daily. A rerun may therefore differ from the figures in
Chapter 6, particularly the traversal statistics in Section 6.5, which depend
on what the providers hold at query time.

The gold-standard labels are fixed and committed, so the extraction metrics in
Section 6.4 are stable provided the abstracts remain retrievable. Section 8.2.7
proposes snapshotting the corpus to remove this dependency entirely.
