"""Compare sentence splitters for population extraction: speed and output.

The extractor only needs sentence boundaries. This measures what each way of
getting them costs, and whether the choice changes what gets extracted:

  full pipeline   en_core_web_sm with tagger, parser and NER (the old default)
  senter          en_core_web_sm with only its statistical sentence recogniser
  sentencizer     spaCy's rule-based splitter (what the extractor now uses)
  regex           the fallback production ran, because the image had no model

A splitter is only acceptable if it leaves every gold-standard metric and every
full-text candidate unchanged. Speed is measured on identical text, so network
variance cannot inflate the comparison.

    python scripts/benchmark_sentence_splitting.py

Needs network access (abstracts and full text are fetched live) and, for the
two model-based rows, `python -m spacy download en_core_web_sm`. Rows whose
model is missing are skipped rather than failing the run.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
logging.disable(logging.WARNING)

import spacy  # noqa: E402

import run_evaluation as ev  # noqa: E402
import citegraph.nlp.population_extractor as pe  # noqa: E402
from citegraph.evaluation.gold_standard import GOLD_POPULATION  # noqa: E402
from citegraph.providers.base import close_shared_client  # noqa: E402
from citegraph.providers.europe_pmc import EuropePMCProvider  # noqa: E402

# Open-access gold-standard papers whose full text Europe PMC serves.
FULL_TEXT_PMCIDS = [
    "PMC7745181", "PMC7787219", "PMC7445431", "PMC7092819",
    "PMC7159299", "PMC7121484", "PMC7727315", "PMC8371605",
]


class RegexSplitter:
    """Stands in for a spaCy pipeline: what production ran with no model."""

    import re as _re

    class _Sent:
        def __init__(self, text: str):
            self.text = text

    class _Doc:
        def __init__(self, sents):
            self.sents = sents

    def __call__(self, text: str):
        parts = self._re.split(r"(?<=[.!?])\s+", text)
        return self._Doc([self._Sent(p) for p in parts])


def splitters() -> list[tuple[str, object]]:
    rows: list[tuple[str, object]] = []
    try:
        rows.append(("full pipeline", spacy.load("en_core_web_sm")))
        senter = spacy.load("en_core_web_sm", exclude=[
            "parser", "ner", "tagger", "lemmatizer", "attribute_ruler"])
        senter.enable_pipe("senter")
        rows.append(("senter", senter))
    except OSError:
        print("  en_core_web_sm not installed; skipping the two model-based rows")
    rule = spacy.blank("en")
    rule.add_pipe("sentencizer")
    rows.append(("sentencizer (current)", rule))
    rows.append(("regex fallback", RegexSplitter()))
    return rows


async def load_text():
    papers = await ev.fetch_abstracts([g["doi"] for g in GOLD_POPULATION])
    provider = EuropePMCProvider()
    full_text = {}
    for pmcid in FULL_TEXT_PMCIDS:
        full_text[pmcid] = [p for _, p in await provider.get_full_text_sections(pmcid)]
    await close_shared_client()
    return papers, full_text


def numeric_metrics(result: dict) -> dict:
    flat = {}
    for key, value in result.items():
        if isinstance(value, dict):
            flat.update({f"{key}.{k}": v for k, v in value.items()
                         if isinstance(v, (int, float)) and not isinstance(v, bool)})
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            flat[key] = value
    return flat


def measure(nlp, papers, full_text):
    original = pe.PopulationExtractor.__init__
    pe.PopulationExtractor.__init__ = lambda self: setattr(self, "nlp", nlp)
    try:
        start = time.perf_counter()
        metrics = numeric_metrics(ev.evaluate_population(papers))
        abstract_seconds = time.perf_counter() - start

        extractor = pe.PopulationExtractor()
        start = time.perf_counter()
        candidates = {
            pmcid: sorted((c.value, str(c.semantic_type))
                          for paragraph in paragraphs
                          for c in extractor.extract_candidates(pmcid, paragraph))
            for pmcid, paragraphs in full_text.items()
        }
        full_text_seconds = time.perf_counter() - start
    finally:
        pe.PopulationExtractor.__init__ = original
    return metrics, candidates, abstract_seconds, full_text_seconds


def main() -> int:
    papers, full_text = asyncio.run(load_text())
    chars = sum(len(p) for paragraphs in full_text.values() for p in paragraphs)
    paragraphs = sum(len(v) for v in full_text.values())
    print(f"  {len(papers)} gold abstracts; {len(full_text)} full texts, "
          f"{paragraphs} paragraphs, {chars:,} characters\n")

    rows = [(name, *measure(nlp, papers, full_text)) for name, nlp in splitters()]
    base_name, base_metrics, base_candidates, _, base_full = rows[0]

    print(f"  {'splitter':<24} {'abstracts':>10} {'full text':>10} {'speed-up':>9}   output vs {base_name}")
    for name, metrics, candidates, abs_s, full_s in rows:
        changed_metrics = [k for k in metrics if metrics[k] != base_metrics.get(k)]
        changed_papers = [p for p in candidates if candidates[p] != base_candidates[p]]
        verdict = ("identical" if not changed_metrics and not changed_papers else
                   f"metrics changed {changed_metrics}, candidates changed {changed_papers}")
        print(f"  {name:<24} {abs_s:9.2f}s {full_s:9.2f}s {base_full / full_s:8.1f}x   {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
