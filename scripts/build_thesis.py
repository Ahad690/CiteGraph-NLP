"""Generate the thesis appendices and assemble the final document.

The reference list and the gold-standard appendix are generated from the
verified artifacts rather than typed by hand, so they cannot drift from the
evidence they describe.

    python scripts/build_thesis.py
"""

from __future__ import annotations

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THESIS = os.path.join(ROOT, "thesis")
EVIDENCE = os.path.join(THESIS, "evidence")
sys.path.insert(0, os.path.join(ROOT, "src"))

CHAPTERS = [
    "00-front-matter.md",
    "01-introduction.md",
    "02-literature-review.md",
    "03-requirements-methodology.md",
    "03b-project-management.md",
    "04-design.md",
    "04b-algorithms.md",
    "05-implementation.md",
    "05b-frontend.md",
    "06-evaluation-results.md",
    "06b-extended-analysis.md",
    "06c-flow-diagrams.md",
    "07-discussion.md",
    "08-conclusion.md",
    "09-appendix-a-api.md",
    "10-appendix-b-config.md",
    "11-appendix-c-reproducing.md",
    "12-appendix-d-gold-standard.md",
    "14-appendix-e-traceability.md",
    "15-appendix-f-tests.md",
    "16-appendix-g-listings.md",
    "17-appendix-h-diagrams.md",
    "13-references.md",
]


def format_authors(authors: list[str]) -> str:
    authors = [a for a in (authors or []) if a]
    if not authors:
        return "Anon."
    if len(authors) > 6:
        return f"{authors[0]} et al."
    if len(authors) == 1:
        return authors[0]
    return ", ".join(authors[:-1]) + f", and {authors[-1]}"


def build_references() -> str:
    path = os.path.join(EVIDENCE, "references_verified.json")
    data = json.load(io.open(path, encoding="utf-8"))
    verified = sorted(data["verified"], key=lambda r: (r.get("authors") or [""])[0].split()[-1:] or [""])
    verified = sorted(data["verified"], key=lambda r: r["key"])

    lines = [
        "# References", "",
        "Every entry below was resolved against Crossref (with OpenAlex as a",
        "fallback) by `scripts/verify_references.py` before being cited. Entries",
        "that failed to resolve were removed rather than cited from memory; see",
        "Section 6.7 for the three identifiers this process corrected.", "",
        f"All {len(verified)} entries resolve as of the verification run.", "",
    ]
    for i, r in enumerate(verified, 1):
        authors = format_authors(r.get("authors"))
        title = r.get("title") or "[untitled]"
        container = r.get("container")
        year = r.get("year")
        doi = r.get("doi")
        parts = [f"**[{i}]** `{r['key']}`. {authors}."]
        parts.append(f'"{title}."')
        if container:
            parts.append(f"*{container}*,")
        if year:
            parts.append(f"{year}.")
        if doi:
            parts.append(f"DOI: [{doi}](https://doi.org/{doi})")
        lines.append(" ".join(parts))
        if r.get("why_cited"):
            lines.append(f"  <br/>*Cited for:* {r['why_cited']}")
        lines.append("")

    if data.get("unverified"):
        lines += ["## Unverified candidates (not cited)", ""]
        for r in data["unverified"]:
            lines.append(f"- `{r['key']}` ({r['doi']}) : did not resolve; excluded.")
        lines.append("")
    return "\n".join(lines)


def build_gold_standard_appendix() -> str:
    from citegraph.evaluation.gold_standard import GOLD_POPULATION

    results_path = os.path.join(EVIDENCE, "evaluation_results.json")
    per_paper = {}
    if os.path.exists(results_path):
        res = json.load(io.open(results_path, encoding="utf-8"))
        per_paper = {r["doi"]: r for r in res["population_extraction"]["per_paper"]}

    lines = [
        "# Appendix D: Gold Standard Annotations", "",
        "The complete annotated set used in Chapter 6. Each label was assigned by",
        "reading the abstract retrieved through the same providers the pipeline",
        "uses; the supporting sentence is quoted so every label is auditable.", "",
        "`n_eff` is the total number of human subjects the paper's primary analysis",
        "rests on, as stated in the abstract. A dash means no human study",
        "population is stated and the correct behaviour is to extract nothing.", "",
        "## D.1 Summary", "",
        "| # | DOI | Design | Gold n_eff | Predicted | Match |",
        "|--:|-----|--------|-----------:|----------:|:-----:|",
    ]
    for i, g in enumerate(GOLD_POPULATION, 1):
        pred = per_paper.get(g["doi"], {})
        p = pred.get("predicted_n_eff")
        gold = g["n_eff"]
        mark = "n/a"
        if per_paper:
            mark = "ok" if p == gold else "**miss**"
        lines.append(
            f"| {i} | `{g['doi']}` | {g['design']} | "
            f"{gold if gold is not None else 'none'} | "
            f"{p if p is not None else 'none'} | {mark} |"
        )

    lines += ["", "## D.2 Annotations with supporting evidence", ""]
    for i, g in enumerate(GOLD_POPULATION, 1):
        lines += [
            f"### D.2.{i} `{g['doi']}`", "",
            f"- **Design:** {g['design']}",
            f"- **Gold n_eff:** {g['n_eff'] if g['n_eff'] is not None else 'none (negative case)'}",
            f"- **Gold semantic type:** {g['semantic_type'] or 'n/a'}",
            f"- **Supporting evidence:** {g['evidence']}",
            "",
        ]
    return "\n".join(lines)


def assemble() -> None:
    parts = []
    missing = []
    for name in CHAPTERS:
        path = os.path.join(THESIS, name)
        if not os.path.exists(path):
            missing.append(name)
            continue
        parts.append(io.open(path, encoding="utf-8").read().rstrip())

    document = "\n\n\\newpage\n\n".join(parts) + "\n"
    out = os.path.join(THESIS, "CiteGraph-NLP-Thesis.md")
    io.open(out, "w", encoding="utf-8").write(document)

    words = len(re.findall(r"\b[\w'-]+\b", document))
    table_rows = document.count("\n|")
    code_fences = len(re.findall(r"^```", document, re.M))
    # A words-per-page figure badly understates a table- and code-heavy
    # document. Calibrated against an actual WeasyPrint render: 26,758 words
    # produced 98 A4 pages, i.e. ~273 words/page rather than the ~450 a
    # prose-only document yields.
    est_pages = round(words / 273)
    print(f"assembled {len(parts)} parts -> {out}")
    print(f"  words             : {words:,}")
    print(f"  table rows        : {table_rows:,}")
    print(f"  code fences       : {code_fences}")
    print(f"  estimated A4 pages: ~{est_pages}  (calibrated against a real render)")
    print("  verify with the Pandoc + WeasyPrint command in Appendix C.7")
    if missing:
        print(f"  MISSING        : {missing}")


def main() -> int:
    os.makedirs(THESIS, exist_ok=True)
    io.open(os.path.join(THESIS, "13-references.md"), "w", encoding="utf-8").write(build_references())
    io.open(os.path.join(THESIS, "12-appendix-d-gold-standard.md"), "w", encoding="utf-8").write(
        build_gold_standard_appendix()
    )
    print("generated: 13-references.md, 12-appendix-d-gold-standard.md")
    assemble()
    return 0


if __name__ == "__main__":
    sys.exit(main())
