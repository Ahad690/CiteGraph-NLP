"""A guard that cannot look must not report clean.

Incident, 2026-09-26: `test_the_thesis_does_not_drift.py:344` opens a PDF with
`fitz = pytest.importorskip("fitz")`. That is the only thing standing between a
missing or half-installed PyMuPDF and three PDF checks -- every section present
in every rendered PDF, the page counts quoted in two READMEs, and the
`1-current-as-committed.pdf` page total -- quietly passing without having read a
single page. A skip is green. Nothing in the suite said otherwise.

This file is the guard against that guard. It asserts three things:

  * the PDF engine is importable here, and the drift guard's reader returns real
    text rather than an empty string, so the section checks are not passing over
    an empty gather;
  * when the engine is hidden, the drift guard's reader *refuses* -- the absence
    is reported as "could not look" and is distinguishable from a clean read;
  * the healthy path is not misreported as blind, which is the negative control
    for the detector above.

The drift guard's fourth check, the test counts, skips unless the whole suite was
collected. That skip is legitimate and is not asserted here: refusing a skipped
test in the CI report is `tests/test_the_test_job_proves_it_ran.py`'s job, and a
second guard for one question is the duplication Terminux 5.8 item 15 warns
about.

Ported from Terminux R19 (`test_a_guard_that_cannot_look_is_not_a_guard_that_
refused.py`), R22 (`test_a_check_that_did_not_run_is_not_a_finding.py`) and R3
(`test_an_empty_gather_is_not_a_clean_result.py`), catalogued in
`_mining/TERMINUX_GUARDS.md` 4.A. See `guards/ledger.json`.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRIFT = ROOT / "tests" / "test_the_thesis_does_not_drift.py"

#: Below this many characters a "read" of a 120-page thesis has found nothing,
#: and every "is this section present" check over it passes for the wrong reason.
TEXT_FLOOR = 20_000

#: The two states a check can be in. `BLIND` is the one that used to be silently
#: indistinguishable from `LOOKED`, because pytest records both as a non-failure.
LOOKED = "looked"
BLIND = "could_not_look"

def _load_drift():
    """The drift guard as a module, so this file inspects the code that runs
    rather than a copy of it."""
    spec = importlib.util.spec_from_file_location("drift_guard_under_inspection", DRIFT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hidden_engine(*args, **kwargs):
    """An import hook that makes `import fitz` fail, which is what a broken or
    partially installed PyMuPDF looks like to the drift guard.

    This blocks the module through `sys.meta_path` and evicts it from
    `sys.modules`, rather than patching `builtins.__import__`. The first version
    did the latter and passed on the machine it was written on, then failed in CI
    with the engine hidden and the reader still reporting 126 pages: newer pytest
    imports with `importlib.import_module`, which never calls `builtins.__import__`,
    so the hook was never consulted and the red proof was really a measurement of
    which import mechanism pytest uses. A meta-path finder is consulted by both, and
    is how a genuinely absent module behaves.
    """
    class _Blocker:
        def find_spec(self, fullname, path=None, target=None):
            if fullname == "fitz" or fullname.startswith("fitz."):
                raise ModuleNotFoundError(f"No module named {fullname!r}")
            return None

    blocker = _Blocker()
    saved = {name: module for name, module in sys.modules.items()
             if name == "fitz" or name.startswith(("fitz.", "pymupdf"))}
    for name in saved:
        del sys.modules[name]
    sys.meta_path.insert(0, blocker)
    return blocker, saved


def _restore_engine(blocker, saved) -> None:
    if blocker in sys.meta_path:
        sys.meta_path.remove(blocker)
    for name in list(sys.modules):
        if name == "fitz" or name.startswith(("fitz.", "pymupdf")):
            del sys.modules[name]
    sys.modules.update(saved)


def pdf_guard_state(module) -> tuple[str, str]:
    """Ask the drift guard to read a committed PDF and report which state it is
    in, as `(state, detail)`.

    The reader is `lru_cache`d, so the cache is cleared first: without that, a
    second probe is answered from the first probe's bytes and never touches the
    import hook, which would make the blindness check below pass for the wrong
    reason. That this was the first version, and that it reported `looked` while
    the engine was hidden, is why the assertion is written as a flip in both
    directions rather than as a single expected value.
    """
    module._pdf.cache_clear()
    try:
        pages, text = module._pdf(module.PDFS[0])
    except BaseException as error:  # pytest's Skipped is an OutcomeException
        if type(error).__name__ in ("Skipped", "Skip"):
            return BLIND, str(error) or "fitz is not importable"
        raise
    if pages < 1 or len(text) < TEXT_FLOOR:
        return BLIND, f"opened {module.PDFS[0]} but read {pages} pages and {len(text)} characters"
    return LOOKED, f"{pages} pages, {len(text)} characters"


def test_the_pdf_engine_is_importable_and_the_drift_reader_finds_text():
    """The positive control. If this fails, the three PDF checks in the drift
    guard are not running, and the suite would otherwise have stayed green."""
    module = _load_drift()
    state, detail = pdf_guard_state(module)
    assert state == LOOKED, (
        f"the drift guard cannot read {module.PDFS[0]}: {detail}. PyMuPDF is in "
        f"requirements.txt; without it the PDF checks are not running"
    )


def test_a_hidden_pdf_engine_is_reported_as_blind_not_clean():
    """The red proof: hide PyMuPDF and require the state to change. A detector
    that cannot see its own subject is the failure this file exists to catch, so
    this asserts the flip in both directions rather than one expected value."""
    module = _load_drift()
    healthy, detail = pdf_guard_state(module)
    assert healthy == LOOKED, f"the control run is not healthy, so the flip proves nothing: {detail}"

    blocker, saved = _hidden_engine()
    try:
        blind, why = pdf_guard_state(module)
    finally:
        _restore_engine(blocker, saved)

    assert blind == BLIND, (
        "with fitz unimportable the drift guard's reader did not report blindness, so a "
        f"missing PDF engine would still read as a clean pass (state={blind!r}, detail={why!r})"
    )
    assert "fitz" in why, f"the blindness report does not name the missing engine: {why!r}"

    recovered, _ = pdf_guard_state(module)
    assert recovered == LOOKED, "the engine was still hidden after the import hook was restored"


def test_the_hiding_actually_hides_the_module():
    """The red proof for the hider. Without this, the test above would pass on a
    machine where the block does nothing and the blindness came from somewhere
    else -- which is exactly what happened in CI on 2026-09-26."""
    blocker, saved = _hidden_engine()
    try:
        with pytest.raises(BaseException):
            importlib.import_module("fitz")
    finally:
        _restore_engine(blocker, saved)

    assert importlib.import_module("fitz") is not None, \
        "the module is still unimportable after the block was removed"


def test_every_committed_pdf_yields_text_a_check_can_search():
    """The empty-gather floor. A PDF that opens but yields no extractable text
    would make `test_every_pdf_carries_every_section` pass over every heading
    while reading nothing, which is R3's failure: an empty gather is not a clean
    result."""
    module = _load_drift()
    assert len(module.PDFS) >= 4, f"the drift guard now checks {len(module.PDFS)} PDFs; the floor was 4"
    thin = []
    for name in module.PDFS:
        pages, text = module._pdf(name)
        if pages < 100 or len(text) < TEXT_FLOOR:
            thin.append(f"{name}: {pages} pages, {len(text)} characters")
    assert not thin, f"these PDFs are too thin to check anything against: {thin}"
