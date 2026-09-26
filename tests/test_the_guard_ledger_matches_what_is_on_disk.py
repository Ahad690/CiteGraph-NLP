"""The guard ledger matches what is on disk, in both directions.

Incident, from the catalogue itself. `TERMINUX_GUARDS.md` is explicit that a count
must not be mistaken for absence: it lists thirty-six further guard-shaped files
in an appendix "so the count is not mistaken for absence", and it records 16 gaps
under a heading that says each one is "stated, not invented". The method is the
point. A ledger that lists a guard which does not exist is the same defect in the
other direction, and neither is caught by counting.

So this file compares four sets, each against the filesystem rather than against
another list:

  * every family id in the ledger against R1-30, C1-18, B1-28, P1-12, G1-7;
  * every guard the ledger names against the files on disk;
  * every `tests/test_*.py` on disk against the ledger, which must classify each
    one as a guard or as an ordinary behaviour test -- so adding a test file
    forces a decision rather than slipping past unclassified;
  * every guard in the registry against the families that claim it, both ways, so
    neither a guard nothing carries nor a family nothing carries can sit there.

And it checks that the human-readable `LEDGER.md` was generated from the same
table, because two files describing one judgement will otherwise drift.

Ported from Terminus R14 and kit item 11. See `guards/ledger.json`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDS = ROOT / "guards"
LEDGER = GUARDS / "ledger.json"
MARKDOWN = GUARDS / "LEDGER.md"

KINDS = {"R": 30, "C": 18, "B": 28, "P": 12, "G": 7}
KIND_NAMES = {"R": "ratchet", "C": "ci", "B": "runtime", "P": "process", "G": "gate"}
STATUSES = {"ported", "adapted", "already_present", "refused"}


def ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def all_ids() -> set[str]:
    return {f"{kind}{n}" for kind, count in KINDS.items() for n in range(1, count + 1)}


def test_the_ledger_accounts_for_every_family_and_nothing_else():
    data = ledger()
    families = data["families"]
    assert len(families) == 95, f"the ledger has {len(families)} families, not 95"

    ids = [f["id"] for f in families]
    assert len(ids) == len(set(ids)), f"duplicate family ids: {sorted(i for i in ids if ids.count(i) > 1)}"
    assert set(ids) == all_ids(), (
        f"the ledger's family ids differ from R1-30 C1-18 B1-28 P1-12 G1-7: "
        f"{sorted(all_ids() ^ set(ids))}"
    )

    for family in families:
        assert family["status"] in STATUSES, f"{family['id']} has status {family['status']!r}"
        prefix = family["id"][0]
        assert family["kind"] == KIND_NAMES[prefix], (
            f"{family['id']} is filed as {family['kind']!r}; {prefix} families are "
            f"{KIND_NAMES[prefix]!r}"
        )
        assert len(family["reason"]) >= 40, (
            f"{family['id']} is recorded as {family['status']} with a {len(family['reason'])}-"
            f"character reason, which is not a reason"
        )
        if family["status"] in ("ported", "adapted", "already_present"):
            assert family["guards"] or family["status"] == "already_present", (
                f"{family['id']} is {family['status']} but names no guard"
            )


def test_every_guard_the_ledger_names_exists_on_disk():
    data = ledger()
    assert data["guards"], "the ledger registers no guards"
    for guard in data["guards"]:
        for path in [guard["path"], *guard.get("also", [])]:
            assert (ROOT / path).is_file(), (
                f"{guard['id']} names {path}, which does not exist. Either the guard was "
                f"renamed or the ledger is describing something that is not there"
            )
        assert len(guard["incident"]) >= 80, (
            f"{guard['id']} has no incident worth reading; Terminux 5.8 item 1 says to write "
            f"'not recorded' rather than invent one, and this is neither"
        )
        assert guard["families"], f"{guard['id']} carries no Terminux family"


def test_every_test_file_is_classified_as_a_guard_or_as_an_ordinary_test():
    """The direction that makes the classification exhaustive. A new test file that
    nobody classified is a file whose status -- guard or behaviour -- nobody decided."""
    data = ledger()
    claimed = {guard["path"] for guard in data["guards"]}
    claimed |= {path for guard in data["guards"] for path in guard.get("also", [])}
    ordinary = {entry["path"] for entry in data["ordinary"]}
    for entry in data["ordinary"]:
        assert (ROOT / entry["path"]).is_file(), \
            f"the ledger lists {entry['path']} as an ordinary test, and it is not there"
        assert len(entry["why"]) >= 20, f"{entry['path']} is classified without a reason"

    on_disk = {f"tests/{p.name}" for p in sorted((ROOT / "tests").glob("test_*.py"))}
    assert len(on_disk) >= 20, f"only {len(on_disk)} test files were found; the walk is wrong"

    unclassified = sorted(on_disk - claimed - ordinary)
    assert not unclassified, (
        f"{unclassified} are in tests/ and are in neither the guard registry nor the "
        f"ordinary list. Add it to guards/ledger.json -- one line in ORDINARY, or a guard "
        f"entry -- so its status is a decision rather than an omission"
    )

    missing = sorted((claimed | ordinary) - on_disk - {
        p for p in claimed if not p.startswith("tests/")})
    assert not missing, f"the ledger names {missing}, which are not test files on disk"


def test_every_guard_is_carried_by_a_family_and_every_family_by_a_guard():
    """Both directions, and non-empty on both sides. Two set differences over empty
    sets both pass, which is the recorded incident."""
    data = ledger()
    guard_ids = {g["id"] for g in data["guards"]}
    assert len(guard_ids) >= 10, f"only {len(guard_ids)} guards are registered"

    named = {g for family in data["families"] for g in family["guards"]}
    assert not named - guard_ids, f"families name {sorted(named - guard_ids)}, which are not guards"
    assert not guard_ids - named, (
        f"{sorted(guard_ids - named)} are registered guards that no family claims, so nothing "
        f"records what they are for"
    )

    for guard in data["guards"]:
        unknown = set(guard["families"]) - all_ids()
        assert not unknown, f"{guard['id']} claims {sorted(unknown)}, which are not families"


def test_the_human_readable_ledger_was_generated_from_the_same_table():
    """Two files describing one judgement will drift unless one is generated from
    the other. The builder records the hash of what it wrote; this compares it.

    The first version re-ran the builder here to check, which assembled the whole
    thesis and took the suite from 47 seconds to 168. Comparing the hash is the
    same claim for a fraction of the cost."""
    import hashlib

    data = ledger()
    recorded = data.get("_ledger_md_sha256")
    assert recorded, (
        "guards/ledger.json records no hash of LEDGER.md, so the generated copy cannot be "
        "checked for staleness without rebuilding it"
    )
    actual = hashlib.sha256(MARKDOWN.read_bytes()).hexdigest()
    assert actual == recorded, (
        f"guards/LEDGER.md is stale: it hashes to {actual[:12]}, and the ledger recorded "
        f"{recorded[:12]}. Run python scripts/build_guard_ledger.py"
    )

    before = MARKDOWN.read_text(encoding="utf-8")
    assert "| **total** | **95** |" in before, "LEDGER.md does not state the family total"
    for status, count in data["_counts"].items():
        assert f"| {status} | {count} |" in before, \
            f"LEDGER.md does not carry the {status} count the JSON has ({count})"
    for guard in data["guards"]:
        assert f"`{guard['path']}`" in before, f"LEDGER.md does not mention {guard['path']}"
    for entry in data["ordinary"]:
        assert f"`{entry['path']}`" in before, \
            f"LEDGER.md does not classify {entry['path']}"


def test_the_counts_add_up():
    data = ledger()
    families = data["families"]
    for status, count in data["_counts"].items():
        actual = sum(1 for f in families if f["status"] == status)
        assert actual == count, f"_counts says {status} is {count}; it is {actual}"
    assert sum(data["_counts"].values()) == len(families) == 95, \
        "the four statuses do not account for all 95 families"
