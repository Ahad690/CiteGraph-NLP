"""The second-opinion pass over a finished reading.

The load-bearing property is that DISABLING IT CHANGES NOTHING. Every test below
asserts that a reading passed through the pass comes out identical, because that
is the guarantee that makes the feature safe to ship: the deterministic path is
the default, and the model is a second opinion rather than a dependency.

The second property is CONSISTENCY. A stage count is a sum over labels, so a
revised label with a stale total would be a reading that looks complete and is
not. When a revision happens the totals are re-derived, and that is asserted.
"""
from __future__ import annotations

import pytest

from citegraph.config import settings
from citegraph.nlp import disambiguation
from citegraph.vision.flow_diagram import Count, FlowReading, Region
from citegraph.vision.second_opinion_pass import Revisions, apply_second_opinions


def region() -> Region:
    return Region(x0=0, y0=0, x1=100, y1=50)


def count(value: int, label: str, stages: set[str]) -> Count:
    return Count(value=value, label=label, stages=stages, region=region())


def reading_with(*counts: Count) -> FlowReading:
    r = FlowReading()
    r.counts = list(counts)
    for stage, value in (("screened", 100), ("enrolled", 80), ("randomised", 40), ("analysed", 38)):
        setattr(r, stage, value)
    return r


class TestItChangesNothingByDefault:
    @pytest.mark.asyncio
    async def test_a_confident_reading_is_untouched(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_jev", True)
        reading = reading_with(count(40, "Randomised (n=40)", {"randomised"}))
        before = reading.as_dict()

        revisions = await apply_second_opinions(reading)

        assert revisions.labels_asked == 0, "a confident label must not be sent anywhere"
        assert reading.as_dict() == before

    @pytest.mark.asyncio
    async def test_disabled_leaves_an_unsure_reading_untouched(self, monkeypatch):
        """The feature off is the feature absent."""
        monkeypatch.setattr(settings, "enable_jev", False)
        reading = reading_with(
            count(40, "Assigned to arm", {"allocated", "randomised"}),
        )
        before = reading.as_dict()
        labels_before = {c.label: set(c.stages) for c in reading.counts}

        revisions = await apply_second_opinions(reading)

        assert revisions.labels_asked == 1
        assert revisions.labels_revised == 0
        assert reading.as_dict() == before
        assert {c.label: set(c.stages) for c in reading.counts} == labels_before

    @pytest.mark.asyncio
    async def test_a_reading_with_no_counts_is_untouched(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_jev", True)
        reading = FlowReading(randomised=7)
        revisions = await apply_second_opinions(reading)
        assert revisions.labels_asked == 0
        assert reading.randomised == 7


class TestItRevisesOnlyWhenDecisive:
    @pytest.mark.asyncio
    async def test_a_decisive_answer_revises_the_label(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_jev", True)

        async def confident(label, stages, **_kw):
            return disambiguation.SecondOpinion(
                selected="analysed",
                probabilities={"analysed": 0.93, "randomised": 0.05},
                confidence=0.93,
                model_served="jev-1.13.0",
                decisive=True,
                reason="decisive",
            )

        monkeypatch.setattr("citegraph.vision.second_opinion_pass.second_opinion", confident)
        reading = reading_with(count(40, "Assigned to arm", {"allocated", "randomised"}))

        revisions = await apply_second_opinions(reading)

        assert revisions.labels_revised == 1
        assert reading.counts[0].stages == {"analysed"}
        assert revisions.model_served == "jev-1.13.0"

    @pytest.mark.asyncio
    async def test_totals_are_re_derived_after_a_revision(self, monkeypatch):
        """A stage count is a sum over labels. Revising a label without
        re-running the aggregation leaves a reading whose labels and totals
        disagree, which looks complete and is not."""
        monkeypatch.setattr(settings, "enable_jev", True)

        async def confident(label, stages, **_kw):
            return disambiguation.SecondOpinion(
                selected="analysed",
                probabilities={"analysed": 0.93, "randomised": 0.05},
                confidence=0.93,
                model_served="jev-1.13.0",
                decisive=True,
                reason="decisive",
            )

        monkeypatch.setattr("citegraph.vision.second_opinion_pass.second_opinion", confident)
        reading = reading_with(
            count(40, "Randomised", {"randomised"}),
            count(38, "Assigned to arm", {"allocated", "randomised"}),
        )
        # Deliberately wrong before the pass, so a pass cannot be a coincidence.
        reading.randomised = 999
        reading.analysed = 888

        revisions = await apply_second_opinions(reading)

        assert revisions.labels_revised == 1
        # The invariant, not a literal: each stage total equals the sum of the
        # counts carrying that stage. An earlier version asserted hardcoded
        # numbers and passed for the wrong reason -- its fixture's hardcoded
        # total happened to equal the re-derived value, so the pass proved
        # nothing about whether re-derivation ran.
        for stage in ("screened", "enrolled", "randomised", "analysed"):
            expected = sum(c.value for c in reading.counts if stage in c.stages)
            assert getattr(reading, stage) in (None, expected), (
                f"{stage} total does not match the sum over labels"
            )
        assert reading.randomised == 40, "the revised label must leave the total"

    @pytest.mark.asyncio
    async def test_a_declined_answer_leaves_the_labels(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_jev", True)

        async def unsure(label, stages, **_kw):
            return disambiguation.SecondOpinion(
                selected="analysed", probabilities={"analysed": 0.51},
                confidence=0.51, model_served=None, decisive=False,
                reason="below threshold",
            )

        monkeypatch.setattr("citegraph.vision.second_opinion_pass.second_opinion", unsure)
        reading = reading_with(count(40, "Assigned to arm", {"allocated", "randomised"}))
        before = reading.as_dict()

        revisions = await apply_second_opinions(reading)

        assert revisions.labels_declined == 1
        assert revisions.labels_revised == 0
        assert reading.counts[0].stages == {"allocated", "randomised"}
        assert reading.as_dict() == before


class TestTheRouteActuallyCallsIt:
    """The pass has to be reachable, not merely present.

    A module that works and a module that runs are different claims. This drives
    the real route function with a reading the regexes were unsure about and
    asserts the pass was invoked and its revisions surfaced in the response --
    because a stage total a model moved is a number a reader is entitled to know
    was second-guessed.
    """

    @pytest.mark.asyncio
    async def test_the_flow_route_invokes_the_pass_and_reports_it(self, monkeypatch):
        from citegraph.api import routes

        asked = {"n": 0}

        async def spy(reading):
            asked["n"] += 1
            return Revisions(labels_asked=1, labels_revised=0, labels_declined=1)

        monkeypatch.setattr(
            "citegraph.vision.second_opinion_pass.apply_second_opinions", spy
        )
        _stub_the_route(monkeypatch, routes, uncertain=True)

        payload = await routes.read_paper_flow_diagram("run-1", "p1")

        assert asked["n"] == 1, "the route never called the pass"
        block = payload["flow_diagram"]["second_opinion"]
        assert block["asked"] == 1
        assert block["declined"] == 1

    @pytest.mark.asyncio
    async def test_a_confident_reading_reports_no_second_opinion_block(self, monkeypatch):
        """No block at all when nothing was asked, so the response does not carry
        an empty object implying a model was consulted."""
        from citegraph.api import routes

        async def spy(reading):
            return Revisions()

        monkeypatch.setattr(
            "citegraph.vision.second_opinion_pass.apply_second_opinions", spy
        )
        _stub_the_route(monkeypatch, routes, uncertain=False)

        payload = await routes.read_paper_flow_diagram("run-1", "p1")
        assert "second_opinion" not in payload["flow_diagram"]


class _NullLock:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _NullStore:
    async def save_result(self, run_id, result):
        return None


def _stub_the_route(monkeypatch, routes, *, uncertain: bool) -> None:
    """Wire the flow-diagram route to a reading, without the network or the store."""
    from citegraph.models.run import RunResult
    from citegraph.vision.flow_diagram import Count, FlowReading, Region

    async def fake_load(run_id):
        return RunResult.model_validate(_RESULT)

    monkeypatch.setattr(routes, "_load_result", fake_load)

    def make_reading():
        r = FlowReading(randomised=40, analysed=38)
        region = Region(x0=0, y0=0, x1=100, y1=50)
        if uncertain:
            r.counts = [Count(40, "Assigned to arm", {"allocated", "randomised"}, region)]
        else:
            r.counts = [Count(40, "Randomised", {"randomised"}, region)]
        return r

    monkeypatch.setattr(
        "citegraph.vision.flow_diagram.read_flow_diagram", lambda image: make_reading()
    )

    class Figure:
        image = b"not a real png"
        caption = "Participant flow"
        source = "europepmc"

    async def fake_find(pmcid):
        return Figure()

    monkeypatch.setattr("citegraph.vision.figures.find_flow_diagram", fake_find)
    monkeypatch.setattr(routes, "_result_lock", lambda run_id: _NullLock())
    monkeypatch.setattr(routes, "store", _NullStore())


_RESULT = {
    "run_id": "run-1",
    "seed_paper_id": "p1",
    "query": "q",
    "papers": [
        {"paper_id": "p1", "title": "A trial", "year": 2020, "authors": [],
         "pmcid": "PMC1", "doi": None, "abstract": None},
    ],
    "studies": [],
    "population_candidates": [],
    "population_resolutions": [],
    "citation_edges": [],
    "ranked_foundational_papers": [],
    "ranked_paths": [],
    "warnings": [],
    "created_at": "2026-09-29T00:00:00+00:00",
}
