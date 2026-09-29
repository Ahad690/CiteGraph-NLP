"""The daily provider budget.

The shape of the limit is the decision worth defending, so it is tested directly.

It is a DAILY ceiling and not a per-run one. A per-run cap stops a run part-way
and hands back a broken artifact, which is worse than a finished run with a
slightly larger bill. Terminus measured why runaway cost is real rather than
theoretical -- one turn accumulated 1.6M prompt tokens, because every round
re-sends the whole conversation -- and bounds it per turn for the same reason
CiteGraph bounds it per day here: the unit that must always complete is the run.

The ceiling is read from an append-only file rather than from memory, so a
restart does not refill it. A budget that resets on restart has no limit in it.
"""
from __future__ import annotations

import json

import pytest

from citegraph.config import settings
from citegraph.llm import budget


@pytest.fixture(autouse=True)
def isolated_record(tmp_path, monkeypatch):
    """Every test writes to its own file and its own ceiling."""
    record = tmp_path / "cost.jsonl"
    monkeypatch.setattr(settings, "provider_cost_record", str(record))
    monkeypatch.setattr(settings, "provider_daily_budget_usd", 1.00)
    yield record


class TestRecording:
    def test_a_reported_cost_is_believed(self):
        assert budget.record("glm", "m", 100, 50, 0.25) == 0.25

    def test_an_unpriced_call_is_estimated_not_skipped(self):
        """A budget that silently ignored unpriced calls would have a hole in it."""
        cost = budget.record("jev", "jev-latest", 1_000_000, 0, None)
        assert cost > 0

    def test_the_row_records_which_price_was_used(self):
        """A reader cannot otherwise tell a measured price from a guess."""
        budget.record("glm", "m", 10, 10, 0.01)
        budget.record("jev", "j", 10, 10, None)
        rows = [json.loads(l) for l in isolated_rows()]
        assert rows[0]["price_source"] == "reported"
        assert rows[1]["price_source"] == "estimated"

    def test_the_record_survives_being_appended_only(self):
        budget.record("glm", "m", 10, 10, 0.10)
        budget.record("glm", "m", 10, 10, 0.20)
        assert len(isolated_rows()) == 2
        assert budget.spend_today() == pytest.approx(0.30)

    def test_a_row_is_never_rewritten(self):
        """Terminus lost half its ledger to a purge of test accounts. The record
        is a file and is only ever appended to."""
        budget.record("glm", "m", 10, 10, 0.10)
        with open(settings.provider_cost_record, "a", encoding="utf-8") as handle:
            handle.write("not json\n")
        assert budget.spend_today() == pytest.approx(0.10), "a bad line broke the total"

    def test_the_model_served_is_recorded_not_the_one_requested(self):
        """A reproducibility claim that cannot name its model is not a claim."""
        budget.record("glm", "glm-5.3-flash-20260101", 10, 10, 0.01)
        row = json.loads(isolated_rows()[0])
        assert row["model"] == "glm-5.3-flash-20260101"

    def test_no_key_ever_reaches_a_row(self):
        budget.record("glm", "m", 10, 10, 0.01)
        assert "sk-" not in isolated_rows()[0]


def isolated_rows() -> list[str]:
    """The lines in this test's own cost record.

    Named for what it reads, NOT for the `isolated_record` fixture, which it
    shadowed in an earlier version: calling `isolated_rows()` returned the
    fixture function rather than the file contents.
    """
    path = settings.provider_cost_record
    with open(path, encoding="utf-8") as handle:
        return [line for line in handle if line.strip()]


class TestTheCeiling:
    def test_nothing_is_spent_before_anything_is_called(self):
        assert budget.spend_today() == 0.0
        assert budget.budget_exhausted() is False

    def test_it_is_not_exhausted_part_way_through(self):
        budget.record("glm", "m", 10, 10, 0.50)
        assert budget.budget_exhausted() is False
        assert budget.budget_remaining() == pytest.approx(0.50)

    def test_it_is_exhausted_at_the_ceiling(self):
        budget.record("glm", "m", 10, 10, 1.00)
        assert budget.budget_exhausted() is True
        assert budget.budget_remaining() == 0.0

    def test_remaining_never_goes_negative(self):
        budget.record("glm", "m", 10, 10, 5.00)
        assert budget.budget_remaining() == 0.0

    def test_another_day_starts_fresh(self):
        """Otherwise the ceiling stops being a ceiling after one busy day."""
        budget.record("glm", "m", 10, 10, 1.00)
        assert budget.budget_exhausted() is True
        rows = [json.loads(l) for l in isolated_rows()]
        rows[0]["day"] = "1999-01-01"
        with open(settings.provider_cost_record, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(rows[0]) + "\n")
        assert budget.spend_today() == 0.0
        assert budget.budget_exhausted() is False

    def test_a_missing_record_reads_as_zero_rather_than_crashing(self):
        """A fresh deployment has no file yet."""
        import os

        if os.path.exists(settings.provider_cost_record):
            os.remove(settings.provider_cost_record)
        assert budget.spend_today() == 0.0

    def test_the_summary_carries_no_key(self):
        assert "sk-" not in budget.remaining_summary()
