"""Insert the NUTECH letterhead at the top of a generated .docx.

The handwrite-studio pipeline cannot embed this. Its markdown parser rewrites
every image to its alt text before the plan is built

    (re.compile(r"!\\[([^\\]]*)\\]\\(([^)]+)\\)"), r"\\1"),   # image -> alt text

and the only images the builder does embed are formula renders -- PNGs produced
by the LaTeX pass and attached to formula nodes as `image_path`. So a letterhead
in the markdown source is silently dropped rather than refused.

Rather than hand the whole document to a different converter for one image, the
converter stays and its output is fixed: insert the logo as the first block of
the body, sized to the page, and leave every other paragraph untouched.

    python add_letterhead.py <in.docx> <logo.png>
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches

#: Wider than the printed form needs; the NUTECH seal is a round emblem and
#: reads better at logo size than at wordmark size.
LOGO_WIDTH_INCHES = 1.2


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2

    docx_path = Path(argv[1])
    logo_path = Path(argv[2])

    if not docx_path.is_file():
        print(f"no such file: {docx_path}")
        return 2
    if not logo_path.is_file():
        print(f"no such logo: {logo_path}")
        return 2

    document = Document(str(docx_path))

    # Reuse the first paragraph if it is empty so the logo does not push a blank
    # line above the letterhead; otherwise create one at the top of the body.
    first = document.paragraphs[0] if document.paragraphs else None
    if first is not None and not first.text.strip() and not first.runs:
        paragraph = first
    else:
        paragraph = document.add_paragraph()
        body = document.element.body
        body.remove(paragraph._p)
        body.insert(0, paragraph._p)

    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(logo_path), width=Inches(LOGO_WIDTH_INCHES))

    document.save(str(docx_path))
    print(f"letterhead inserted: {logo_path.name} at {LOGO_WIDTH_INCHES}in wide")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
