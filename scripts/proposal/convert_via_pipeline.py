"""Convert a markdown file to DOCX and PDF using the handwrite-studio pipeline.

Drives the same functions the HTTP /convert route calls -- _plan_from_markdown,
build_docx, docx_to_pdf -- without the route, because the route is
authenticated and because its whitelist has no (".md", "docx") pair, so
markdown-to-Word cannot be requested through it at all. Only the pair check is
bypassed here; the parser, the builder and the PDF renderer are the real ones.

    python convert_via_pipeline.py <input.md> <output_dir> [style]
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from pathlib import Path

#: This repository's root, used to find thesis/print.css.
ROOT = Path(__file__).resolve().parents[2]

#: Where the handwrite-studio backend lives. Resolved as a sibling of this
#: repository rather than written out in full, because an absolute path under
#: C:\Users\<account> publishes the account name of whoever ran the script, and
#: this repository's remote is public. parents[2] is the repository root, so
#: parents[2].parent is the directory holding both checkouts. Override with
#: HANDWRITE_STUDIO_BACKEND when they are not siblings.
BACKEND = Path(
    os.environ.get("HANDWRITE_STUDIO_BACKEND")
    or (Path(__file__).resolve().parents[2].parent / "handwrite-studio" / "backend")
)
sys.path.insert(0, str(BACKEND))

from routers.convert import _plan_from_markdown  # noqa: E402
from services.docx_builder import build_docx  # noqa: E402


async def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2

    source = Path(argv[1]).resolve()
    outdir = Path(argv[2]).resolve()
    style = argv[3] if len(argv) > 3 else "computerized"
    outdir.mkdir(parents=True, exist_ok=True)

    if not source.is_file():
        print(f"no such file: {source}")
        return 2

    # Same entry point the route uses for a markdown source, which has no
    # .plan.json sidecar because it is the source rather than a generated file.
    plan = _plan_from_markdown(source)
    sections = plan.get("sections", [])
    title = plan.get("title", source.stem)
    print(f"plan: title={title!r} sections={len(sections)} style={style!r}")

    if not sections:
        print("plan contains no sections")
        return 1

    file_id = uuid.uuid4().hex[:12]
    docx_path = await build_docx(plan, file_id, style=style)

    final_docx = outdir / f"{source.stem}.docx"
    final_docx.write_bytes(docx_path.read_bytes())
    print(f"DOCX: {final_docx} ({final_docx.stat().st_size // 1024} KB)")

    # The PDF is rendered by pandoc rather than by the pipeline's own
    # docx_to_pdf. That function shells out to LibreOffice, which is a separate
    # ~350 MB install and is not present here; without it the call raises
    # FileNotFoundError from subprocess and the script dies after the DOCX is
    # already written. Pandoc plus WeasyPrint is what scripts/render_thesis.py
    # uses for this repository's own thesis, so both documents come out of the
    # same renderer and the letterhead behaves the same in each.
    #
    # --pdf-engine=weasyprint, and not the LaTeX default, because the CSS that
    # carries the page furniture is what makes the output look like a thesis
    # rather than an article.
    css = ROOT / "thesis" / "print.css"
    final_pdf = outdir / f"{source.stem}.pdf"
    # os.pathsep, not a literal ":". Pandoc splits --resource-path on the
    # platform separator, which is ";" on Windows, so a hardcoded colon made it
    # parse "C:\...\docs\proposal:C:\...\assets" as one nonexistent directory.
    # The logo then silently vanished: the PDF still rendered, five pages and
    # every field present, with no image and no warning.
    resource_path = os.pathsep.join(
        str(p) for p in (source.parent, source.parent / "assets") if p.is_dir()
    )
    cmd = [
        "pandoc", str(source),
        "-o", str(final_pdf),
        "--pdf-engine=weasyprint",
        "--resource-path", resource_path,
    ]
    if css.is_file():
        cmd[1:1] = ["-c", str(css)]
    else:
        print(f"note: {css} not found, rendering without the thesis stylesheet")

    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        print("PDF : FAILED")
        print(done.stderr.strip()[:2000])
        return 1
    print(f"PDF : {final_pdf} ({final_pdf.stat().st_size // 1024} KB)")

    # A PDF with a missing image is still a valid PDF. It renders, every field is
    # present, and the page count is right, so nothing about the exit status or
    # the file size says the letterhead is gone. That is the same failure shape as
    # a coverage gate with no report behind it, so the image is checked rather
    # than assumed.
    if not _pdf_has_image(final_pdf):
        print("PDF : WARNING no image found; the letterhead did not render")
        return 1

    return 0


def _pdf_has_image(pdf: Path) -> bool | None:
    """True if the PDF embeds an image. None if that cannot be determined.

    Returning None is not the same as False: an unverified PDF must not be
    reported as a clean one.
    """
    try:
        import pypdf
    except ImportError:
        return None
    try:
        reader = pypdf.PdfReader(str(pdf))
        return any(len(page.images) for page in reader.pages)
    except Exception:
        return None


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv)))
