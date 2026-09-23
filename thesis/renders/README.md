# Layout comparison

Three renders of the same thesis. Same text, same eight figures, same
assembled markdown. Only the stylesheet differs, so any difference you see is
a layout decision and not a content one.

Only WeasyPrint is installed on this machine, so these are not a comparison of
PDF engines. No LaTeX distribution (`xelatex`, `pdflatex`, `tectonic`) and no
LibreOffice are present, which is why there is no LaTeX-typeset PDF and no
PDF converted from the Word file.

## The three PDFs

| File | Pages | Page numbers | Body type | Character |
|------|-------|--------------|-----------|-----------|
| `1-current-as-committed.pdf` | 110 | **no** | Times New Roman 12pt | Pandoc's default web styling, printed |
| `2-academic-serif.pdf` | 123 | yes | Times New Roman 11.5pt | Conventional university thesis |
| `3-modern-report.pdf` | 120 | yes | Cambria 11pt | Technical report |

**1 — current.** What is committed in `thesis/CiteGraph-NLP-Thesis.pdf`. It is
Pandoc's browser stylesheet sent to a printer: ragged-right text, no page
numbers, no running heads, and code set at body size. It is the shortest of
the three mostly because it is the loosest, not because it is the most
efficient.

**2 — academic.** Justified with hyphenation, a 30mm left margin for binding,
page number centred in the footer, and the current chapter named in the top
right. Code drops to 9pt, tables to 9.5pt. The longest of the three: the
binding margin and the larger leading cost about twelve pages against variant
1, which is the usual trade for looking like a submitted thesis.

**3 — report.** Sans-serif headings in the same navy as the generated figures,
a rule under each chapter title, banded tables with white-on-navy headers,
page number and a running project name in the footer. Serif body for
readability. Reads as an engineering document rather than a dissertation.

## Choosing

Check your department's submission guidelines first, since they usually fix
margins, body size, line spacing and where the page number sits. If they do,
that decides it, and the chosen stylesheet can be edited to match rather than
started again.

Absent a guideline, variant 2 is the safer choice for a supervisor and an
external examiner; variant 3 is better if the document is also going to be
read as a portfolio piece.

Note that variant 1 has no page numbers at all, which makes the table of
contents and every internal cross-reference harder to use. Whichever way you
go, it should not be the one you submit.

## Promoting a winner

The stylesheets live in `_css/`. To make one the default:

```bash
# pick one
cp thesis/renders/_css/academic.css  thesis/print.css   # variant 2
cp thesis/renders/_css/report.css    thesis/print.css   # variant 3

# then append the shared rules it depends on
cat thesis/renders/_css/base.css >> thesis/print.css

python scripts/render_thesis.py --docx
```

`scripts/render_thesis.py` applies `thesis/print.css` and writes the tracked
PDF and DOCX. `scripts/render_variants.py` regenerates this folder.

All three PDFs are kept in the repository rather than treated as throwaway
output, so any of them can be handed over without a rebuild.

The two `*.docx` files are the earlier comparison between Pandoc's DOCX writer
and the handwrite-studio pipeline, kept here for reference.
`4-pandoc-word.docx` is the current full DOCX with all eight figures embedded
as PNG, which is the format to use if the department wants Word.
