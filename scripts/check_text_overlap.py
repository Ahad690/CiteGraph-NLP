"""Check the thesis for verbatim reuse from the project's own earlier documents.

This is the similarity check that actually applies to a prose thesis. Code
plagiarism detectors (JPlag, Dolos) parse programming languages and compute
pairwise similarity across a *set* of submissions; neither accepts prose, and
neither produces anything from a single document.

The real risk for this thesis is unattributed reuse from the team's own earlier
submissions -- the proposal, the PRD, the feasibility report, the interim
project report. An institutional checker compares against a student's prior
submissions, so verbatim carry-over is flagged even though it is the authors'
own writing.

    python scripts/check_text_overlap.py
"""

from __future__ import annotations

import io
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

THESIS = os.path.join(ROOT, "thesis", "CiteGraph-NLP-Thesis.md")
SOURCES = [
    "project_proposal.md",
    "citation_lineage_prd.md",
    "deep-research-report_on_citegraph.md",
    "PROJECT_REPORT.md",
    "USER_GUIDE.md",
    "README.md",
    "frontend_Lovable_prompt.md",
    "frontend_LANDING_PAGE_Lovable_prompt.md",
]

NGRAM = 8          # word n-gram; 8 is the common threshold for "verbatim"
REPORT_LIMIT = 15  # longest overlapping passages to print


def normalise(text: str) -> str:
    """Strip markdown furniture so formatting differences do not mask reuse."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)       # code blocks
    text = re.sub(r"^\s*\|.*$", " ", text, flags=re.M)        # tables
    text = re.sub(r"`[^`]*`", " ", text)                      # inline code
    text = re.sub(r"https?://\S+", " ", text)                 # urls
    text = re.sub(r"[^A-Za-z0-9 ]", " ", text)
    return " ".join(text.lower().split())


def ngrams(words: list[str], n: int) -> Counter:
    return Counter(tuple(words[i:i + n]) for i in range(len(words) - n + 1))


def longest_runs(thesis_words: list[str], source_set: set, min_len: int) -> list[str]:
    """Find maximal spans of the thesis whose every n-gram appears in a source."""
    runs, i = [], 0
    n = min_len
    while i <= len(thesis_words) - n:
        if tuple(thesis_words[i:i + n]) in source_set:
            end = i + n
            while (end < len(thesis_words)
                   and tuple(thesis_words[end - n + 1:end + 1]) in source_set):
                end += 1
            runs.append(" ".join(thesis_words[i:end]))
            i = end
        else:
            i += 1
    return runs


def main() -> int:
    if not os.path.exists(THESIS):
        print(f"missing {THESIS}; run scripts/build_thesis.py first")
        return 1

    thesis_words = normalise(io.open(THESIS, encoding="utf-8").read()).split()
    thesis_grams = ngrams(thesis_words, NGRAM)
    total = sum(thesis_grams.values())
    print(f"thesis: {len(thesis_words):,} words, {total:,} {NGRAM}-grams\n")

    all_matched: set = set()
    print(f"{'source document':<44} {'words':>8} {'shared':>8} {'% thesis':>9}")
    for name in SOURCES:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            print(f"{name:<44} {'—':>8} {'—':>8} {'absent':>9}")
            continue
        src_words = normalise(io.open(path, encoding="utf-8", errors="replace").read()).split()
        src_set = set(ngrams(src_words, NGRAM))
        shared = sum(c for g, c in thesis_grams.items() if g in src_set)
        all_matched |= {g for g in thesis_grams if g in src_set}
        pct = shared / total * 100 if total else 0
        print(f"{name:<44} {len(src_words):>8,} {shared:>8,} {pct:>8.2f}%")

    overall = sum(c for g, c in thesis_grams.items() if g in all_matched)
    pct = overall / total * 100 if total else 0
    print(f"\n{'COMBINED against all project documents':<44} {'':>8} {overall:>8,} {pct:>8.2f}%")

    combined_set = set()
    for name in SOURCES:
        path = os.path.join(ROOT, name)
        if os.path.exists(path):
            w = normalise(io.open(path, encoding="utf-8", errors="replace").read()).split()
            combined_set |= set(ngrams(w, NGRAM))

    runs = longest_runs(thesis_words, combined_set, NGRAM)
    runs.sort(key=lambda r: -len(r.split()))
    print(f"\ncontiguous reused passages (>= {NGRAM} words): {len(runs)}")
    if runs:
        print(f"longest {min(REPORT_LIMIT, len(runs))}:\n")
        for r in runs[:REPORT_LIMIT]:
            print(f"  [{len(r.split()):>3} words] {r[:150]}")

    print()
    if pct < 1.0:
        print(f"VERDICT: {pct:.2f}% overlap — negligible; no rewriting needed.")
    elif pct < 5.0:
        print(f"VERDICT: {pct:.2f}% overlap — low. Inspect the passages above.")
    else:
        print(f"VERDICT: {pct:.2f}% overlap — high enough to address before submission.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
