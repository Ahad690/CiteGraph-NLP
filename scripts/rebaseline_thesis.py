"""Record what the thesis contains, so the drift test can notice a loss.

tests/test_the_thesis_does_not_drift.py fails when a section, figure or
citation in this record is missing from the thesis. Adding one needs nothing;
removing one needs this script, and this script needs a reason. A rebaseline
that costs a sentence is one somebody has to think about.

    python scripts/rebaseline_thesis.py "why this changed"
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_thesis import ROOT, assembled_text, inventory  # noqa: E402

BASELINE = os.path.join(ROOT, "scripts", "thesis_baseline.json")


def main() -> int:
    reason = " ".join(sys.argv[1:]).strip()
    if not reason:
        print(__doc__)
        print("REFUSING: a rebaseline without a reason is what this guards against.")
        return 2

    document, _ = assembled_text()
    current = inventory(document)
    previous = {}
    if os.path.exists(BASELINE):
        with open(BASELINE, encoding="utf-8") as fh:
            previous = json.load(fh)

    with open(BASELINE, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({**current, "_why": reason}, fh, indent=2)
        fh.write("\n")

    for kind, values in current.items():
        lost = sorted(set(previous.get(kind, [])) - set(values))
        print(f"{kind:<10}: {len(values)}" + (f"   REMOVED {lost}" if lost else ""))
    print(f"reason    : {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
