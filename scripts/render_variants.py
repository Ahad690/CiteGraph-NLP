"""Render the thesis several ways so the layout can be chosen by looking.

Only WeasyPrint is installed on this machine, so the variants differ by
stylesheet rather than by engine. Each one renders the same assembled
markdown and the same figures; what changes is typography and page furniture.

    python scripts/render_variants.py

Output goes to thesis/renders/, which is tracked: all three layouts are kept
so any of them can be handed over without a rebuild. Whichever one wins can
also be promoted into thesis/print.css and rendered by render_thesis.py as
the default.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THESIS = os.path.join(ROOT, "thesis")
RENDERS = os.path.join(THESIS, "renders")
CSS_DIR = os.path.join(RENDERS, "_css")
ASSEMBLED = os.path.join(THESIS, "CiteGraph-NLP-Thesis.md")

NEWPAGE = "\\newpage"
COMMON = ["-f", "markdown-smart", f"--resource-path={THESIS}"]

# (output name, stylesheets, what the reader is looking at)
VARIANTS = [
    ("1-current-as-committed.pdf", [os.path.join(THESIS, "print.css")],
     "What is committed now. Pandoc's default web styling, no page numbers."),
    ("2-academic-serif.pdf",
     [os.path.join(CSS_DIR, "base.css"), os.path.join(CSS_DIR, "academic.css")],
     "Conventional thesis: justified serif, 30mm binding margin, page numbers, "
     "running chapter head."),
    ("3-modern-report.pdf",
     [os.path.join(CSS_DIR, "base.css"), os.path.join(CSS_DIR, "report.css")],
     "Technical report: sans headings in navy, banded tables, page number and "
     "rule in the footer."),
]


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    noise = ("WARNING: Ignored", "WARNING: Expected a media type",
             "WARNING: Invalid media type", "Warning: `--localstorage",
             "rsvg-convert")
    for line in (result.stderr or "").splitlines():
        if line.strip() and not any(n in line for n in noise):
            print(f"      {line}")
    if result.returncode != 0:
        raise SystemExit(f"pandoc failed ({result.returncode})")


def split_front_matter() -> tuple[str, str]:
    text = open(ASSEMBLED, encoding="utf-8").read()
    marker = "\n\n" + NEWPAGE + "\n\n"
    head, body = text.split(marker, 1)
    return head, body


def describe(pdf_path: str) -> str:
    try:
        import fitz
    except ImportError:
        return ""
    doc = fitz.open(pdf_path)
    # A page number in the footer shows up as a short trailing line that is
    # just digits; sample the middle of the document where body text runs.
    numbered = 0
    for i in range(20, min(doc.page_count, 60)):
        tail = doc[i].get_text().strip().split("\n")[-1].strip()
        if tail.isdigit():
            numbered += 1
    body_font = ""
    for block in doc[40].get_text("dict")["blocks"]:
        if block["type"] == 0:
            for line in block["lines"]:
                for span in line["spans"]:
                    if len(span["text"].strip()) > 40:
                        body_font = f'{span["font"]} {span["size"]:.1f}pt'
                        break
                if body_font:
                    break
        if body_font:
            break
    flag = "page numbers" if numbered > 25 else "NO page numbers"
    return f"{doc.page_count} pages, {flag}, body {body_font or 'n/a'}"


def main() -> int:
    if not os.path.exists(ASSEMBLED):
        raise SystemExit("run scripts/build_thesis.py first")
    os.makedirs(RENDERS, exist_ok=True)

    front_md, body_md = split_front_matter()

    with tempfile.TemporaryDirectory() as tmp:
        front_path = os.path.join(tmp, "front.md")
        front_html = os.path.join(tmp, "front.html")
        body_path = os.path.join(tmp, "body.md")

        with open(front_path, "w", encoding="utf-8") as fh:
            fh.write(front_md)
        run(["pandoc", front_path, "-o", front_html, "--embed-resources", *COMMON])
        fragment = open(front_html, encoding="utf-8").read()
        with open(front_html, "w", encoding="utf-8") as fh:
            fh.write(f'<div class="frontmatter">\n{fragment}\n</div>\n')

        with open(body_path, "w", encoding="utf-8") as fh:
            fh.write(body_md.replace(NEWPAGE, '<div class="pagebreak"></div>'))

        for name, sheets, note in VARIANTS:
            out = os.path.join(RENDERS, name)
            print(f"  {name}")
            css_flags = [f"--css={s}" for s in sheets]
            run(["pandoc", body_path, "-o", out,
                 "--pdf-engine=weasyprint",
                 "--toc", "--toc-depth=3",
                 f"--include-before-body={front_html}",
                 "--embed-resources",
                 *css_flags,
                 "--metadata", "title=CiteGraph-NLP",
                 "--metadata", "lang=en-GB",
                 *COMMON])
            print(f"      {os.path.getsize(out)/1024:.0f} KB  {describe(out)}")
            print(f"      {note}")

    # The DOCX comparison from the earlier pipeline test, if it is still there.
    compare = os.path.join(THESIS, "compare")
    if os.path.isdir(compare):
        for name in os.listdir(compare):
            if name.endswith(".docx"):
                shutil.copy2(os.path.join(compare, name), os.path.join(RENDERS, name))
    for name in ("CiteGraph-NLP-Thesis.docx",):
        src = os.path.join(THESIS, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(RENDERS, "4-pandoc-word.docx"))

    print(f"\n  {RENDERS}")
    for name in sorted(os.listdir(RENDERS)):
        path = os.path.join(RENDERS, name)
        if os.path.isfile(path):
            print(f"    {name:<44} {os.path.getsize(path)/1024:>7.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
