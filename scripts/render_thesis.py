"""Render the assembled thesis to PDF and DOCX in the correct page order.

Pandoc places a generated table of contents at the very top of the body when
the title comes from an H1 rather than from metadata. That buried the title
page, the logo and the declaration behind five pages of contents.

So the front matter is rendered separately and injected ahead of the contents
with --include-before-body, which gives the order a thesis needs:

    title page (logo, authors, supervisor)
    declaration, abstract, abbreviations
    table of contents
    chapters and appendices

    python scripts/render_thesis.py [--docx] [--open]
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THESIS = os.path.join(ROOT, "thesis")
ASSEMBLED = os.path.join(THESIS, "CiteGraph-NLP-Thesis.md")
FRONT = os.path.join(THESIS, "00-front-matter.md")
PDF = os.path.join(THESIS, "CiteGraph-NLP-Thesis.pdf")
DOCX = os.path.join(THESIS, "CiteGraph-NLP-Thesis.docx")
CSS = os.path.join(THESIS, "print.css")

# The page-break marker the assembler writes between parts.
NEWPAGE = "\\newpage"

# -f markdown-smart: Pandoc's smart typography otherwise rewrites `--` as an en
# dash and `---` as an em dash, putting dashes in the PDF the source never had.
# No --number-sections: every heading already carries its number, and Pandoc
# adds its own on top rather than replacing it.
COMMON = ["-f", "markdown-smart", f"--resource-path={THESIS}"]


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    noise = ("WARNING: Ignored", "WARNING: Expected a media type",
             "WARNING: Invalid media type", "Warning: `--localstorage")
    for line in (result.stderr or "").splitlines():
        if line.strip() and not any(line.startswith(n) or n in line for n in noise):
            print(f"    {line}")
    if result.returncode != 0:
        raise SystemExit(f"pandoc failed ({result.returncode}): {' '.join(cmd[:4])} ...")


def split_front_matter() -> tuple[str, str]:
    """Return (front matter markdown, body markdown) from the assembled file."""
    text = open(ASSEMBLED, encoding="utf-8").read()
    front_src = open(FRONT, encoding="utf-8").read().rstrip()
    # The assembler joins parts with a page-break marker; the front matter is
    # the first part, so the body is everything after the first marker.
    marker = "\n\n\\newpage\n\n"
    if marker in text:
        head, body = text.split(marker, 1)
        return head, body
    return front_src, text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docx", action="store_true", help="also write a DOCX")
    args = parser.parse_args()

    if not os.path.exists(ASSEMBLED):
        raise SystemExit("run scripts/build_thesis.py first")

    front_md, body_md = split_front_matter()
    print(f"front matter: {len(front_md.split()):,} words")
    print(f"body        : {len(body_md.split()):,} words")

    with tempfile.TemporaryDirectory() as tmp:
        front_html = os.path.join(tmp, "front.html")
        body_path = os.path.join(tmp, "body.md")

        # Render the front matter to a standalone-free HTML fragment, with the
        # logo inlined so it survives being injected into another document.
        front_path = os.path.join(tmp, "front.md")
        with open(front_path, "w", encoding="utf-8") as fh:
            fh.write(front_md)
        run(["pandoc", front_path, "-o", front_html, "--embed-resources", *COMMON])
        with open(front_html, encoding="utf-8") as fh:
            fragment = fh.read()
        with open(front_html, "w", encoding="utf-8") as fh:
            fh.write(f'<div class="frontmatter">\n{fragment}\n</div>\n')

        # \newpage is raw LaTeX: the LaTeX writer honours it and the HTML
        # writer silently drops it, which left chapters starting mid-page
        # whenever the previous one did not happen to fill one. print.css
        # gives the div below the same meaning for the WeasyPrint path.
        breaks = body_md.count(NEWPAGE)
        html_body = body_md.replace(NEWPAGE, '<div class="pagebreak"></div>')
        with open(body_path, "w", encoding="utf-8") as fh:
            fh.write(html_body)
        print(f"page breaks    : {breaks}")

        print("rendering PDF ...")
        run(["pandoc", body_path, "-o", PDF,
             "--pdf-engine=weasyprint",
             "--toc", "--toc-depth=3",
             f"--include-before-body={front_html}",
             "--embed-resources",
             f"--css={CSS}",
             "--metadata", "title=CiteGraph-NLP",
             *COMMON])
        print(f"  {PDF}  ({os.path.getsize(PDF)/1024:.0f} KB)")

        if args.docx:
            print("rendering DOCX ...")
            # Pandoc needs rsvg-convert to put an SVG in a DOCX and drops the
            # image with a warning when it is missing, which is how the first
            # DOCX came out with eight empty figures. generate_diagrams.py
            # writes a PNG beside every SVG for exactly this path.
            docx_md = os.path.join(tmp, "docx.md")
            source = open(ASSEMBLED, encoding="utf-8").read()
            rastered = re.sub(r"\(figures/([\w-]+)\.svg\)", r"(figures/\1.png)", source)
            swapped = len(re.findall(r"\(figures/[\w-]+\.png\)", rastered))
            missing = [m for m in re.findall(r"\(figures/([\w-]+)\.png\)", rastered)
                       if not os.path.exists(os.path.join(THESIS, "figures", f"{m}.png"))]
            with open(docx_md, "w", encoding="utf-8") as fh:
                fh.write(rastered)
            print(f"  {swapped} figures switched to PNG"
                  + (f"; MISSING: {missing}" if missing else ""))
            run(["pandoc", docx_md, "-o", DOCX, "--toc", "--toc-depth=3", *COMMON])
            print(f"  {DOCX}  ({os.path.getsize(DOCX)/1024:.0f} KB)")

    try:
        import fitz
        doc = fitz.open(PDF)
        print(f"\npages: {doc.page_count}")
        for i in range(min(3, doc.page_count)):
            first = next((l.strip() for l in doc[i].get_text().split("\n") if l.strip()), "")
            imgs = len(doc[i].get_images(full=True))
            placed = any(doc[i].get_image_rects(x[0]) for x in doc[i].get_images(full=True))
            tag = "  [logo]" if placed else ""
            print(f"  page {i+1}: {first[:62]}{tag}")
    except ImportError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
