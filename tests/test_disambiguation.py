"""The second-opinion path for CONSORT stage labels.

The point of these tests is the FAILURE cases. A second opinion that can overturn
a working deterministic path is a liability, so every way it can decline to
override is asserted, along with the one case where it is allowed to.
"""
from __future__ import annotations

import pytest

from citegraph.config import settings
from citegraph.llm.base import ProviderUnavailable
from citegraph.llm.jev import Decision
from citegraph.nlp.disambiguation import (
    DISAMBIGUATION_THRESHOLD,
    SecondOpinion,
    resolve_stages,
    second_opinion,
)


def opinion(**kwargs) -> SecondOpinion:
    defaults = {
        "selected": None,
        "probabilities": {},
        "confidence": None,
        "model_served": None,
        "decisive": False,
        "reason": "test",
    }
    defaults.update(kwargs)
    return SecondOpinion(**defaults)


class TestResolveStages:
    def test_an_unavailable_opinion_leaves_the_rule_answer(self):
        assert resolve_stages("Randomised (n=100)", {"randomised"}, None) == {"randomised"}

    def test_a_non_decisive_opinion_leaves_the_rule_answer(self):
        o = opinion(selected="analysed", confidence=0.99, decisive=False)
        assert resolve_stages("Allocated", {"allocated", "randomised"}, o) == {
            "allocated",
            "randomised",
        }

    def test_a_decisive_opinion_replaces_the_rules(self):
        o = opinion(selected="analysed", confidence=0.95, decisive=True)
        assert resolve_stages("Assigned to arm", {"randomised"}, o) == {"analysed"}

    def test_exclusion_is_respected(self):
        o = opinion(selected="excluded", confidence=0.99, decisive=True)
        assert resolve_stages("Screen failures", {"enrolled"}, o) == {"excluded"}


class TestItDeclinesToOverride:
    @pytest.mark.asyncio
    async def test_when_disabled(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_jev", False)
        result = await second_opinion("Allocated", {"allocated", "randomised"})
        assert result.decisive is False
        assert result.reason == "disabled"

    @pytest.mark.asyncio
    async def test_when_the_rules_were_already_sure(self, monkeypatch):
        """The cheap path is the default. When the regexes found exactly one
        stage there is nothing to ask, and no provider is touched."""
        monkeypatch.setattr(settings, "enable_jev", True)
        result = await second_opinion("Randomised", {"randomised"})
        assert result.decisive is False
        assert result.reason == "rules were confident"

    @pytest.mark.asyncio
    async def test_when_the_provider_is_down(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_jev", True)

        class Broken:
            enabled = True

            async def evaluate(self, *_a, **_k):
                raise ProviderUnavailable("jev: HTTP 500")

        result = await second_opinion(
            "Assigned", {"allocated", "randomised"}, client=Broken()
        )
        assert result.decisive is False
        assert result.reason == "provider error"

    @pytest.mark.asyncio
    async def test_when_the_provider_raises_something_unexpected(self, monkeypatch):
        """A provider bug must not fail a run."""
        monkeypatch.setattr(settings, "enable_jev", True)

        class Exploding:
            enabled = True

            async def evaluate(self, *_a, **_k):
                raise ValueError("unexpected shape")

        # Two candidate stages, so the rules are unsure and the client is asked.
        # A single stage would short-circuit before the client is reached, and
        # this test passed for the wrong reason once already.
        result = await second_opinion(
            "Assigned", {"allocated", "randomised"}, client=Exploding()
        )
        assert result.decisive is False
        assert result.reason == "unexpected error"

    @pytest.mark.asyncio
    async def test_when_the_budget_is_spent(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_jev", True)
        monkeypatch.setattr(
            "citegraph.nlp.disambiguation.budget_exhausted", lambda: True
        )
        result = await second_opinion("Assigned", {"allocated", "randomised"})
        assert result.decisive is False
        assert result.reason == "budget"

    @pytest.mark.asyncio
    async def test_below_the_threshold(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_jev", True)

        class Weak:
            enabled = True

            async def evaluate(self, *_a, **_k):
                return (
                    {"stage": Decision("stage", "choice", "analysed", {"analysed": 0.55}, 0.55)},
                    type("U", (), {"model_served": "jev-latest"})(),
                )

        result = await second_opinion("Assigned", {"allocated", "randomised"}, client=Weak())
        assert result.decisive is False
        assert result.reason == "below threshold"

    @pytest.mark.asyncio
    async def test_when_ambiguous(self, monkeypatch):
        """Two options within 0.1. Overriding a rule on a coin-flip is worse
        than keeping the rule."""
        monkeypatch.setattr(settings, "enable_jev", True)

        class Close:
            enabled = True

            async def evaluate(self, *_a, **_k):
                decision = Decision(
                    "stage", "choice", "analysed", {"analysed": 0.52, "randomised": 0.48}, 0.52
                )
                return {"stage": decision}, type("U", (), {"model_served": "jev-latest"})()

        result = await second_opinion("Assigned", {"allocated", "randomised"}, client=Close())
        assert result.decisive is False
        assert result.reason == "ambiguous"

    @pytest.mark.asyncio
    async def test_when_the_answer_is_not_a_known_stage(self, monkeypatch):
        """An invented stage name is a hallucination, not a classification."""
        monkeypatch.setattr(settings, "enable_jev", True)

        class Inventive:
            enabled = True

            async def evaluate(self, *_a, **_k):
                decision = Decision("stage", "choice", "consented", {"consented": 0.99}, 0.99)
                return {"stage": decision}, type("U", (), {"model_served": "jev-latest"})()

        result = await second_opinion("Assigned", {"allocated", "randomised"}, client=Inventive())
        assert result.decisive is False
        assert result.reason == "unknown stage"

    @pytest.mark.asyncio
    async def test_when_there_is_no_answer(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_jev", True)

        class Silent:
            enabled = True

            async def evaluate(self, *_a, **_k):
                return {}, type("U", (), {"model_served": None})()

        result = await second_opinion("Assigned", {"allocated", "randomised"}, client=Silent())
        assert result.decisive is False
        assert result.reason == "no answer"


class TestItCanOverride:
    @pytest.mark.asyncio
    async def test_a_confident_unambiguous_answer_is_decisive(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_jev", True)

        class Confident:
            enabled = True

            async def evaluate(self, *_a, **_k):
                decision = Decision(
                    "stage", "choice", "analysed", {"analysed": 0.93, "randomised": 0.05}, 0.93
                )
                return {"stage": decision}, type("U", (), {"model_served": "jev-1.13.0"})()

        result = await second_opinion(
            "Assigned to arm", {"allocated", "randomised"}, client=Confident()
        )
        assert result.decisive is True
        assert result.selected == "analysed"
        assert result.model_served == "jev-1.13.0", "the served model must be recorded"


class TestTheThresholdLivesHere:
    def test_it_is_a_pipeline_decision_not_a_client_property(self):
        """0.7 is about what a wrong stage label costs in CONSORT arithmetic,
        which is this module's business and not the Jev client's."""
        assert 0 < DISAMBIGUATION_THRESHOLD < 1

    def test_no_threshold_literal_in_the_client(self):
        """The client must not carry a cut-off of its own.

        Checked against the CODE, not the whole file: an earlier version read the
        entire module and failed on a DOCSTRING that explains why the threshold
        is not in the client. A test that fails on its own documentation is a
        test that will be 'fixed' by deleting the explanation.
        """
        from citegraph.llm import jev

        source = __import__("pathlib").Path(jev.__file__).read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.split("\n") if not line.strip().startswith("#")
        )
        # Strip the module and class docstrings before looking for a number.
        import ast

        tree = ast.parse(source)
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                doc = ast.get_docstring(node, clean=False)
                if doc:
                    docstrings.add(doc)
        for doc in docstrings:
            code = code.replace(doc, "")
        assert "0.7" not in code
        assert "DISAMBIGUATION_THRESHOLD" not in code
