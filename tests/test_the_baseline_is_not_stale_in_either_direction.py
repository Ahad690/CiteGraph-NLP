"""The baseline is not stale in either direction.

Incident, 2026-09-26: `tests/test_the_thesis_does_not_drift.py` compares the
committed record one way only -- `set(record) - set(thesis)`, "nothing in the
record has gone". That direction cannot see a record that has been *shortened*.
Deleting an entry from `scripts/thesis_baseline.json` by hand disables protection
for that section, permanently, with no rebaseline, no reason and nothing in `git
log` to say so. The guard guarding nothing is a failure shape the Terminux
catalogue lists twice (5.7, "a correct guard guarding nothing"; R2, "pin-not-above-
reality").

The same hole was open in the other direction without anyone editing anything. The
record was allowed to lag the thesis, so a newly written section was unprotected
from the moment it was written until some later removal forced a rebaseline. On
2026-09-26 that was two live sections: 5.6.4 and 6.14.7. Deleting either would
have passed.

So the record must now *equal* the thesis, exactly, in both directions, and every
fall -- a count that went down -- must carry its own reason in an append-only
history rather than overwriting the last one.

Ported from Terminux R2 (`test_the_unowned_count_does_not_rise_while_you_decide.py:461`)
and R8 (`:471-627`); the lag half is this repository's own. See `guards/ledger.json`.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "scripts" / "thesis_baseline.json"
KINDS = ("sections", "figures", "citations")

#: Calibrated against this tree. A comparison over an empty set agrees with
#: everything, which is how a locator that stopped early once passed (Terminux
#: 5.6.3).
FLOOR = {"sections": 200, "figures": 5, "citations": 30}


def _rebaseline():
    spec = importlib.util.spec_from_file_location("rebaseline", ROOT / "scripts" / "rebaseline_thesis.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build():
    spec = importlib.util.spec_from_file_location("build", ROOT / "scripts" / "build_thesis.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def thesis_now() -> dict[str, list[str]]:
    build = _build()
    document, _ = build.assembled_text()
    return build.inventory(document)


def staleness(committed: dict, actual: dict) -> dict[str, dict[str, list[str]]]:
    """Both directions, per kind. `only_recorded` is the drift guard's direction;
    `only_thesis` is the one it could not see."""
    return {kind: {
        "only_recorded": sorted(set(committed.get(kind, [])) - set(actual.get(kind, []))),
        "only_thesis": sorted(set(actual.get(kind, [])) - set(committed.get(kind, []))),
    } for kind in KINDS}


def test_the_comparison_catches_a_hand_edited_record_in_both_directions():
    """The red proof. Deleting an entry is the incident; adding one is the pin
    sitting above reality. Both must be visible, and an untouched record must be
    silent, or the sweep below is decoration."""
    committed = {"sections": ["1.1", "1.2"], "figures": ["Figure 1.1"], "citations": []}
    actual = {"sections": ["1.1", "1.2"], "figures": ["Figure 1.1"], "citations": []}
    assert staleness(committed, actual) == {k: {"only_recorded": [], "only_thesis": []} for k in KINDS}, \
        "the comparison reports staleness when there is none"

    deleted = {**committed, "sections": ["1.1"]}
    assert staleness(deleted, actual)["sections"]["only_thesis"] == ["1.2"], \
        "a section removed from the record by hand is invisible, which is the incident"

    invented = {**committed, "sections": ["1.1", "1.2", "9.9"]}
    assert staleness(invented, actual)["sections"]["only_recorded"] == ["9.9"], \
        "a section invented in the record is invisible, so a pin can sit above reality"


def test_the_record_equals_the_thesis_in_both_directions():
    """The sweep. Every section, figure and citation in the thesis is in the
    record, and every entry in the record is in the thesis."""
    committed, actual = record(), thesis_now()
    for kind, floor in FLOOR.items():
        assert len(actual.get(kind, [])) >= floor, (
            f"only {len(actual.get(kind, []))} {kind} were found, below the floor of {floor}; "
            f"a comparison over an empty extraction agrees with everything"
        )

    stale = {kind: hits for kind, hits in staleness(committed, actual).items()
             if hits["only_recorded"] or hits["only_thesis"]}
    assert not stale, (
        "the record and the thesis disagree, so part of the thesis is unguarded. "
        f"`only_recorded` is the drift guard's direction; `only_thesis` is the direction "
        f"it could not see. Fix with: python scripts/rebaseline_thesis.py \"why\" --apply "
        f"<token from the dry run>. Offending: {stale}"
    )


def test_every_fall_in_the_history_carries_its_own_reason():
    """Terminus R8: a re-baseline costs a written reason, and a later fall keeps
    the reason rather than overwriting it with a bare number."""
    committed = record()
    history = committed.get("history")
    assert history, "the record carries no history, so a fall leaves no trace of why"
    assert committed.get("_first_why"), "the record does not say why it was first taken"
    assert committed.get("_why"), "the record does not say why it was last written"

    previous = {kind: len(committed[kind]) for kind in KINDS}
    for index, entry in enumerate(history):
        assert entry.get("reason"), f"history[{index}] has no reason"
        assert len(entry["reason"]) >= 30, f"history[{index}]'s reason is {len(entry['reason'])} characters"
        assert entry.get("date"), f"history[{index}] has no date, so a reviewer cannot place it"
        assert set(entry.get("counts", {})) == set(KINDS), f"history[{index}] does not count every kind"
        fell = [kind for kind in KINDS if entry["counts"][kind] < previous[kind]]
        assert fell == entry.get("fell", fell), (
            f"history[{index}] records a fall in {fell} but its `fell` says {entry.get('fell')}"
        )
        for kind in fell:
            assert entry.get("removed", {}).get(kind), (
                f"history[{index}] claims {kind} fell but does not say what was removed"
            )
        previous = entry["counts"]

    assert previous == {kind: len(committed[kind]) for kind in KINDS}, (
        "the last history entry does not describe the record as it stands, so the history "
        "is not a record of what happened"
    )


def test_the_apply_token_is_the_only_way_to_write():
    """Terminus P6: a destructive step must be handed the plan it read. A reason
    alone prints a plan and writes nothing."""
    import io
    import contextlib
    import sys

    rebaseline = _rebaseline()
    committed = record()
    actual = thesis_now()
    planned = rebaseline.plan(actual, committed)
    assert planned["token"] and len(planned["token"]) == 12, "the plan carries no token"

    before = BASELINE.read_text(encoding="utf-8")
    argv = sys.argv
    sys.argv = ["rebaseline_thesis.py", "a reason long enough to be accepted here"]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            code = rebaseline.main()
    finally:
        sys.argv = argv
    assert code == 0, f"the dry run exited {code}"
    assert BASELINE.read_text(encoding="utf-8") == before, \
        "a dry run wrote to the record; the plan token is not the only way through"
