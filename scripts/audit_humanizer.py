"""Audit thesis prose for the 25 humanizer patterns. Detection only.

Rewrites nothing. The thesis is guarded: scripts/thesis_baseline.json keys every
section heading, figure and citation, and tests/test_the_thesis_does_not_drift.py
pins exact phrases with `assert match, f"{chapter} no longer says {pattern!r}"`.
A pattern that is merely stylistic in a normal document can delete a baseline
key here, so the census has to exist before any edit does.

Each pattern is tagged with whether it is safe to apply:

    prose   the fix touches sentence prose only; baseline keys and pinned
            phrases survive
    struct  the fix changes headings, labels or block structure, which is what
            the baseline indexes. Needs rebaseline_thesis.py with a reason.

Usage:
    python scripts/audit_humanizer.py [--verbose]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THESIS = ROOT / "thesis"

#: Chapter sources, in assembly order. The assembled CiteGraph-NLP-Thesis.md is a
#: build product of these and is deliberately not scanned: fixing prose in a
#: generated file would be overwritten by the next render.
SOURCES = sorted(
    p for p in THESIS.glob("*.md")
    if re.fullmatch(r"\d{2}[a-z]?-.+\.md", p.name)
)

#: pattern number -> (short name, tag, compiled pattern)
PATTERNS: dict[int, tuple[str, str, re.Pattern[str]]] = {
    # "rather than" is deliberately NOT matched here. The skill lists the reversed
    # form as a watch-for, but it also says to keep a contrast when both halves
    # carry information. This corpus uses "rather than" functionally -- "stores a
    # confidence score rather than a bare integer" states the alternative that was
    # rejected, which is a fact, not staging. Counting it produced 102 of the 103
    # hits on this pattern and hid the single real instance, which is the opposite
    # of what a census is for.
    1: ("Not X but Y", "prose", re.compile(
        r"\b(?:it(?:'s| is) not (?:just|only|merely|simply)\b"
        r"|not (?:just|only|merely) (?:about|a|an|the)\b[^.]{0,60}\bbut\b"
        r"|this does not mean\b"
        r"|\bis not (?:a|an|the)\b[^.]{0,40}\bbut (?:a|an|the)\b)", re.I)),
    2: ("One-line closer", "prose", re.compile(
        r"^(?:That is the real win|Let that sink in|Read that again|"
        r"This is the (?:real )?(?:win|point|key))\b", re.M | re.I)),
    3: ("Saying that sounds deep", "prose", re.compile(
        r"\b(?:at its core\b|what really matters\b|at the heart of the matter\b"
        r"|the real (?:question|issue|challenge) is\b"
        r"|\bis the language of\b)", re.I)),
    4: ("Staged run-up", "prose", re.compile(
        r"(?:^|\.\s)(?:Let's (?:dive in|explore|break this down)|"
        r"Here's what you need to know|Without further ado|"
        r"Now let's look at|Let's be honest|Real talk)\b", re.I)),
    5: ("Arguing with no one", "prose", re.compile(
        r"\b(?:This isn't (?:mainly )?about|To be clear|Don't get me wrong|"
        r"This is not to say|Some might say|A tempting approach would be|"
        r"One might be tempted to|An obvious approach would be|"
        r"You might think, but|It would be easy to just)\b", re.I)),
    6: ("Forced triad", "prose", re.compile(
        r"\b\w+,\s+\w+,\s+and\s+\w+\b")),
    7: ("Repeated sentence opening", "prose", re.compile(r"^(\b\w+)\s+\w+.*\n\1\s+\w+", re.M)),
    8: ("Dash as connector", "prose", re.compile(
        # A numeric range (0–3, 10–200) is an en dash doing en-dash work, and the
        # skill exempts dashes that grammar needs. Requiring whitespace on both
        # sides and a non-digit on the right keeps ranges out; the earlier version
        # reported all 28 range dashes in this corpus as connector tells.
        r"\s(?:\u2014|\u2013|--)\s(?![-\w]*[\"'\)\]]?\s*$)"
        r"(?<!\d\s)(?<!\d(?=\s))")),
    9: ("Stacked qualifiers", "prose", re.compile(
        r"\b(?:to be fair|it's also possible|could potentially\b|might arguably"
        r"|in some cases it may|this is an inference)\b", re.I)),
    10: ("Hyphenated pairs everywhere", "prose", re.compile(
        r"\b(?:third-party|cross-functional|client-facing|data-driven|"
        r"decision-making|well-known|high-quality|real-time|end-to-end)\b", re.I)),
    11: ("Passive / missing subject", "prose", re.compile(
        r"\b(?:is|are|was|were|be|been)\s+\w+(?:ed|en)\s+by\b", re.I)),
    12: ("Overused AI word", "prose", re.compile(
        r"\b(?:Additionally|bolstered|crucial|deep dive|delve|emphasizing|enduring"
        r"|enhance|fostering|garner|interplay|intricate|intricacies|landscape"
        r"|meticulous|meticulously|pivotal|showcase|tapestry|testament"
        r"|underscore|vibrant)\b")),
    13: ("Inflated significance", "prose", re.compile(
        r"\b(?:stands as a testament|marks a pivotal|plays a key role|"
        r"marking the|underscores (?:its|the) importance|setting the stage for|"
        r"evolving landscape|continues to thrive|Challenges and Legacy|"
        r"Future Outlook|exciting times ahead|the future looks bright)\b", re.I)),
    14: ("Vague connection", "prose", re.compile(
        r"\b(?:associated with|in association with|in connection with|"
        r"linked to|tied to)\b", re.I)),
    15: ("Shallow -ing rider", "prose", re.compile(
        r",\s+(?:highlighting|underscoring|emphasizing|ensuring|reflecting|"
        r"symbolizing|contributing to|cultivating|fostering|encompassing|"
        r"showcasing)\b", re.I)),
    16: ("Sales language", "prose", re.compile(
        r"\b(?:boasts|vibrant|nestled|in the heart of the|groundbreaking|"
        r"renowned|breathtaking|must-visit|stunning)\b", re.I)),
    17: ("Borrowed authority", "prose", re.compile(
        r"\b(?:[Ee]xperts (?:believe|argue|say)|[Oo]bservers have cited|"
        r"industry reports|[Ss]ome critics|several publications)\b")),
    # "features" is only the tell when it is the verb. As a noun it is the
    # accurate word: "Rather than implementing new features" and "features such
    # as pattern identity" are both nouns, and the earlier version counted both.
    18: ("Avoiding is/are/has", "prose", re.compile(
        r"\b(?:serves as|stands as|functions as|operates as)\b"
        r"|\b(?:boasts|offers|refers to)\b"
        r"|(?<![a-z])(?<!new )(?<!such )\bfeatures\b(?!\s+such)"
        r"|(?<!that )(?<!which )\bmaintains\b", re.I)),
    19: ("Bold as decoration", "prose", re.compile(r"\*\*[^*\n]{1,40}\*\*\s*:")),
    # Decorative headings capitalise *interior* words, so that is the only thing
    # worth matching. Two earlier versions were wrong here. The first matched any
    # heading containing a capitalised article or preposition and reported 16
    # findings in a document that has none. The second forgot to anchor the tail
    # to the end of the line, so it ran past the heading into the paragraph below
    # and manufactured two more. Both now require the match to finish on the
    # heading line, and at least two interior words to be capitalised.
    20: ("Decorative heading", "struct", re.compile(
        r"^#{1,6}[ \t]+(?:\d+(?:\.\d+)*[ \t]+)?\w+[ \t]+(?:[A-Z][a-z]{2,}[ \t]+){2,}"
        r"[A-Z][a-z]{2,}[^\n]*$", re.M)),
    21: ("Curly quotes", "prose", re.compile(r"[\u201c\u201d\u2018\u2019]")),
    22: ("Chatbot residue", "prose", re.compile(
        r"\b(?:I hope this helps|Of course!|Certainly!|Great question!|"
        r"let me know|Would you like|Want me to)\b", re.I)),
    23: ("Knowledge-limit disclaimer", "prose", re.compile(
        r"\b(?:as of \d|up to my last training|while (?:specific )?details are"
        r"|based on available information|not publicly available"
        r"|not widely documented|it is believed that)\b", re.I)),
    24: ("Heading repeated in first line", "prose", re.compile(r"^#\s+.+\n\n\w[^\n]{0,60}$", re.M)),
    25: ("Writing about previous version", "prose", re.compile(
        r"\b(?:was added to replace|previously used to|used to call|"
        r"the old (?:approach|version|implementation))\b", re.I)),
}


def scan(verbose: bool) -> int:
    totals: dict[int, int] = {}
    hits: dict[int, list[tuple[str, int, str]]] = {}

    # Inline code, code fences and link targets are exempt per the skill: they are
    # commands, paths and identifiers, not prose. Strip them before counting.
    fence = re.compile(r"```.*?```", re.S)
    inline = re.compile(r"`[^`\n]*`")
    link_target = re.compile(r"(\]\()[^)]*(\))")

    for path in SOURCES:
        raw = path.read_text(encoding="utf-8")
        text = link_target.sub(r"\1\2", inline.sub(" ", fence.sub(" ", raw)))
        for number, (_name, _tag, rx) in PATTERNS.items():
            for m in rx.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                snippet = " ".join(m.group(0).split())[:70]
                hits.setdefault(number, []).append((path.name, line, snippet))
                totals[number] = totals.get(number, 0) + 1

    name_width = max(len(n) for _n, n, _ in PATTERNS.values())
    prose_hits = struct_hits = 0
    for number in sorted(PATTERNS):
        name, tag, _rx = PATTERNS[number]
        count = totals.get(number, 0)
        if tag == "struct":
            struct_hits += count
        else:
            prose_hits += count
        flag = "" if count == 0 else ("  [struct]" if tag == "struct" else "")
        print(f"  {number:>2}. {name:<{name_width}}  {count:>4}{flag}")
        if verbose:
            for fname, line, snippet in hits.get(number, [])[:8]:
                print(f"        {fname}:{line}  {snippet}")

    print(f"\n  prose-tagged findings : {prose_hits}")
    print(f"  struct-tagged findings: {struct_hits}  (needs rebaseline, not a style fix)")
    print(f"  files scanned         : {len(SOURCES)}")
    print("\n  Detection only. Nothing was written.")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verbose", action="store_true", help="show file:line per hit")
    args = ap.parse_args(argv[1:])
    if not SOURCES:
        print("no chapter sources found", file=sys.stderr)
        return 2
    return scan(args.verbose)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
