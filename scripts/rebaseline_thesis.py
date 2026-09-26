"""Record what the thesis contains, so the drift test can notice a loss.

tests/test_the_thesis_does_not_drift.py fails when a section, figure or
citation in this record is missing from the thesis. This script writes that
record, and this script needs a reason. A rebaseline that costs a sentence is
one somebody has to think about.

    python scripts/rebaseline_thesis.py "why this changed"

The record must equal the thesis, not merely be a subset of it. It used to be
allowed to lag: adding a section needed nothing, so §5.6.4 and §6.14.7 were
written on 2026-09-26 and sat outside the record, which meant deleting either
one would have gone unnoticed until some later removal forced a rebaseline. A
guard that protects only what somebody remembered to register is not a guard, so
tests/test_the_baseline_is_not_stale_in_either_direction.py now requires exact
equality, and this script is what brings the record back into line.

Every run appends to `history`, so a fall -- a count that went down -- keeps the
reason it happened instead of overwriting the last one. That is the Terminux R8
lesson: a re-baseline costs a written reason, and a later fall preserves the
reason rather than replacing it with a bare number.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_thesis import ROOT, assembled_text, inventory  # noqa: E402

BASELINE = os.path.join(ROOT, "scripts", "thesis_baseline.json")
KINDS = ("sections", "figures", "citations")

#: A reason shorter than this is a word, not a decision. The drift guard does not
#: police the prose; this is the floor.
MINIMUM_REASON = 30


def plan(current: dict[str, list[str]], previous: dict) -> dict:
    """What this rebaseline would do, before it does it: the new counts, what was
    added, what was removed, and whether the change is a fall. `--apply` is given
    the token this prints, so the write cannot happen on a plan nobody read."""
    import hashlib

    added = {kind: sorted(set(current[kind]) - set(previous.get(kind, []))) for kind in KINDS}
    removed = {kind: sorted(set(previous.get(kind, [])) - set(current[kind])) for kind in KINDS}
    counts = {kind: len(current[kind]) for kind in KINDS}
    was = {kind: len(previous.get(kind, [])) for kind in previous if kind in KINDS}
    falls = sorted(kind for kind in KINDS
                   if kind in was and counts[kind] < was[kind])
    token = hashlib.sha256(
        "\n".join(f"{kind}={counts[kind]}" for kind in KINDS).encode("utf-8")
    ).hexdigest()[:12]
    return {"counts": counts, "was": was, "added": added, "removed": removed,
            "falls": falls, "token": token}


def apply_plan(plan_result: dict, reason: str, when: str) -> dict:
    """The record as it will be written. Kept separate from the write so the
    guard can call it and compare, without touching the file."""
    document, _ = assembled_text()
    current = inventory(document)
    previous = {}
    if os.path.exists(BASELINE):
        with open(BASELINE, encoding="utf-8") as fh:
            previous = json.load(fh)
    history = list(previous.get("history", []))
    history.append({
        "date": when,
        "reason": reason,
        "counts": plan_result["counts"],
        "removed": {kind: plan_result["removed"][kind] for kind in KINDS
                    if plan_result["removed"][kind]},
        "fell": plan_result["falls"],
    })
    return {**current, "_why": reason,
            # The reason the record was first taken, preserved. Carried from
            # `_why` when an older record has no `_first_why` yet: the first
            # version of this script read `previous.get("_first_why", reason)`,
            # which overwrote the original reason with the first new one and lost
            # "First baseline, taken after the full-text wording fix and the
            # 2026-09-25 figure regeneration" on its first run.
            "_first_why": previous.get("_first_why") or previous.get("_why") or reason,
            "history": history}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("reason", nargs="*", help="why this rebaseline is happening")
    parser.add_argument("--apply", metavar="TOKEN",
                        help="the token the dry run printed; without it nothing is written")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="recorded in history, for reproducing a run")
    args = parser.parse_args()

    reason = " ".join(args.reason).strip()
    document, _ = assembled_text()
    current = inventory(document)
    previous = {}
    if os.path.exists(BASELINE):
        with open(BASELINE, encoding="utf-8") as fh:
            previous = json.load(fh)

    planned = plan(current, previous)

    if not reason:
        print(__doc__)
        print("REFUSING: a rebaseline without a reason is what this guards against.")
        return 2
    if len(reason) < MINIMUM_REASON:
        print(f"REFUSING: {len(reason)} characters is not a reason; "
              f"this needs at least {MINIMUM_REASON}.")
        return 2

    if args.apply != planned["token"]:
        print("Dry run. Nothing has been written.\n")
        for kind in KINDS:
            line = f"  {kind:<10} {planned['was'].get(kind, 0):>4} -> {planned['counts'][kind]:<4}"
            if planned["added"][kind]:
                line += f"  add {planned['added'][kind]}"
            if planned["removed"][kind]:
                line += f"  REMOVE {planned['removed'][kind]}"
            print(line)
        if planned["falls"]:
            print(f"\n  this is a FALL in {', '.join(planned['falls'])}: "
                  f"the thesis now holds less than the record claimed.")
        print(f"\n  to apply: python scripts/rebaseline_thesis.py \"{reason}\" "
              f"--apply {planned['token']}")
        return 0

    record = apply_plan(planned, reason, args.date)
    with open(BASELINE, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")
    for kind in KINDS:
        lost = planned["removed"][kind]
        print(f"{kind:<10}: {planned['counts'][kind]}" + (f"   REMOVED {lost}" if lost else ""))
    if planned["falls"]:
        print(f"FALL      : {', '.join(planned['falls'])}")
    print(f"reason    : {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
