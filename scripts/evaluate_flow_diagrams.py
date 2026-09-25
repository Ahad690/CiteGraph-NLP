"""Score the flow-diagram reader against the answer key, beside the text method.

    python scripts/evaluate_flow_diagrams.py --split dev
    python scripts/evaluate_flow_diagrams.py --split test --save

Only stages the diagram actually states a number for are scored: a method is
right when it reports exactly that number for that stage. Where a diagram has
no separate stage (no "Enrolled" box, say), nothing is scored, because an
abstract saying "91 patients were enrolled" is not wrong just because the
diagram folds enrolment into randomisation. Stages the answer key marks
"unscored" are skipped rather than guessed.

Separately, any number the reader reports for a figure that is not a
participant flow at all is counted as a false positive, since there is no
correct number to read from it.

The text method is the one the pipeline uses today: the pattern extractor over
the abstract, taking the first candidate of each semantic type. It is scored
on exactly the same papers and stages, so the comparison is like for like.

Pre-stated decision rule (written before the reader was run on any held-out
diagram): the reader ships only if, on held-out diagrams, it is right on at
least 15 percentage points more of the stated enrolled, randomised and
analysed counts than the text method, that difference holds up under an exact
McNemar test at p < 0.05, and it reports no number for most of the figures
that are not participant flows. Otherwise it is dropped and the result is
reported.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
logging.disable(logging.WARNING)

from citegraph.nlp.population_extractor import PopulationExtractor  # noqa: E402
from citegraph.vision.flow_diagram import STAGES, read_flow_diagram  # noqa: E402

EVIDENCE = os.path.join(ROOT, "thesis", "evidence", "flow_diagrams")
IMAGES = os.path.join(ROOT, "data", "flow_diagrams")
TYPE_TO_STAGE = {
    "SCREENED": "screened",
    "TOTAL_ENROLLED": "enrolled",
    "TOTAL_RANDOMIZED": "randomised",
    "TOTAL_ANALYZED": "analysed",
}
DECISION_STAGES = ("enrolled", "randomised", "analysed")


def text_method(extractor: PopulationExtractor, abstract: str) -> tuple[dict, set]:
    """What the text method says for each stage, plus every number it found.

    The second value supports a lenient score: credit when the right number
    appears among the abstract's candidates under any label, which separates
    "the abstract does not contain it" from "it was found but mislabelled".
    """
    found: dict = {stage: None for stage in STAGES}
    values: set = set()
    for candidate in extractor.extract_candidates("paper", abstract or "", section="abstract"):
        values.add(candidate.value)
        raw = getattr(candidate.semantic_type, "value", candidate.semantic_type)
        stage = TYPE_TO_STAGE.get(str(raw).split(".")[-1])
        if stage and found[stage] is None:
            found[stage] = candidate.value
    return found, values


def outcome(gold, predicted) -> str:
    if gold is None:
        return "not_stated"
    if predicted is None:
        return "missed"
    return "right" if predicted == gold else "wrong"


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p: b = only reader right, c = only text right."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(0, min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="dev")
    parser.add_argument("--manifest", default=os.path.join(EVIDENCE, "manifest.json"))
    parser.add_argument("--gold", default=os.path.join(EVIDENCE, "gold.json"))
    parser.add_argument("--images", default=IMAGES)
    parser.add_argument("--save", action="store_true", help="write the scored rows to evidence")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    manifest = json.load(io.open(args.manifest, encoding="utf-8"))
    gold = json.load(io.open(args.gold, encoding="utf-8"))["papers"]
    papers = [p for p in manifest["papers"] if gold.get(p["pmcid"], {}).get("split") == args.split]
    extractor = PopulationExtractor()

    rows = []
    non_flow = []
    for paper in papers:
        answer = gold[paper["pmcid"]]
        reading = read_flow_diagram(os.path.join(args.images, paper["image"]))
        vision = reading.as_dict()
        text, text_values = text_method(extractor, paper.get("abstract", ""))
        unscored = set(answer.get("unscored", []))
        if not answer.get("is_participant_flow", True):
            reported = {s: vision[s] for s in STAGES if s not in unscored and vision[s] is not None}
            non_flow.append({"pmcid": paper["pmcid"], "reported": reported})
        for stage in STAGES:
            if stage in unscored:
                continue
            rows.append({
                "pmcid": paper["pmcid"], "stage": stage, "gold": answer[stage],
                "vision": vision[stage], "text": text[stage],
                "vision_outcome": outcome(answer[stage], vision[stage]),
                "text_outcome": outcome(answer[stage], text[stage]),
                "text_value_present": answer[stage] is not None and answer[stage] in text_values,
                "vision_evidence": reading.evidence.get(stage),
                "seconds": round(reading.seconds, 2),
            })
        if not args.quiet:
            marks = "  ".join(
                f"{s[:4]} {'-' if answer[s] is None else answer[s]}:"
                f"{'✓' if outcome(answer[s], vision[s]) == 'right' or (answer[s] is None and vision[s] is None) else vision[s]}"
                for s in STAGES if s not in unscored)
            print(f"  {paper['pmcid']}  {reading.seconds:4.1f}s  boxes {reading.drawn_boxes:<3} {marks}")

    def tally(stages, method):
        scored = [r for r in rows if r["stage"] in stages and r["gold"] is not None]
        right = sum(1 for r in scored if r[f"{method}_outcome"] == "right")
        return right, len(scored)

    stated = [r for r in rows if r["gold"] is not None]
    print(f"\n  split: {args.split}   papers: {len(papers)}   stated stage counts scored: {len(stated)}")
    print(f"  {'stage':<12} {'vision':>12} {'text':>12}")
    for stage in STAGES:
        v, n = tally({stage}, "vision")
        t, _ = tally({stage}, "text")
        print(f"  {stage:<12} {v:>5}/{n:<3} {100*v/max(n,1):3.0f}%  {t:>4}/{n:<3} {100*t/max(n,1):3.0f}%")
    v, n = tally(set(DECISION_STAGES), "vision")
    t, _ = tally(set(DECISION_STAGES), "text")
    lenient = sum(1 for r in rows if r["stage"] in DECISION_STAGES and r["text_value_present"])
    decisive = [r for r in rows if r["stage"] in DECISION_STAGES and r["gold"] is not None]
    only_vision = sum(1 for r in decisive if r["vision_outcome"] == "right" and r["text_outcome"] != "right")
    only_text = sum(1 for r in decisive if r["text_outcome"] == "right" and r["vision_outcome"] != "right")
    gap = 100 * (v - t) / max(n, 1)
    p = mcnemar_exact(only_vision, only_text)
    print(f"\n  enrolled + randomised + analysed:  vision {v}/{n} ({100*v/max(n,1):.0f}%)"
          f"   text {t}/{n} ({100*t/max(n,1):.0f}%)   gap {gap:+.0f} points")
    print(f"  text, lenient (right number found under any label): {lenient}/{n} ({100*lenient/max(n,1):.0f}%)")
    print(f"  discordant: vision-only right {only_vision}, text-only right {only_text}"
          f"   exact McNemar p = {p:.4f}")
    clean = sum(1 for f in non_flow if not f["reported"])
    print(f"  figures that are not participant flows: {len(non_flow)}, reader reported nothing for {clean}")
    for f in non_flow:
        if f["reported"]:
            print(f"      {f['pmcid']} reported {f['reported']}")
    unverifiable = sum(1 for r in rows if r["gold"] is None and r["vision"] is not None)
    print(f"  reader numbers for stages a diagram does not state (not scored): {unverifiable}")
    passes = gap >= 15 and p < 0.05 and (not non_flow or clean > len(non_flow) / 2)
    print(f"  pre-stated rule (>= 15 points, p < 0.05, mostly silent on non-flows): {'PASS' if passes else 'FAIL'}")
    times = [r["seconds"] for r in rows]
    if times:
        print(f"  reader time per diagram: median {sorted(times)[len(times)//2]:.1f}s, max {max(times):.1f}s")

    if args.save:
        out = os.path.join(EVIDENCE, f"results_{args.split}.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({"split": args.split, "rows": rows, "non_flow": non_flow, "gap_points": gap,
                       "mcnemar_p": p, "passes_rule": passes}, fh, indent=2, ensure_ascii=False)
        print(f"  saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
