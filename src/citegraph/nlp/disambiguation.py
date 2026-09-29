"""Consult Jev where the regexes are unsure, and nowhere else.

The regex path in `vision/flow_diagram.py` is fast, free, deterministic and
already works on most labels. It is also brittle in exactly the way Chapter 6
measures: abstracts and figure captions use "randomised", "enrolled" and
"analysed" loosely, often for the same number, and the thesis records the
result -- six of ten cases, 60%.

So the model is NOT a replacement. It is a SECOND OPINION, asked only where the
first one is unsure. Three properties make that safe:

  1. THE RULES STILL RUN. Every call is made with their answer already in hand.
     A provider failure, a disabled provider, a spent budget or a low-confidence
     answer all leave the regex verdict standing. Nothing that works today stops
     working.

  2. THE QUESTION IS TYPED, NOT PROMPTED. Jev is asked which of the named stages
     a label denotes, and answers with a distribution. There is no text to
     misread as an instruction and no prompt to inject.

  3. THE DISTRIBUTION IS KEPT. The caller can see how close the call was. A
     `choice` answer that is 0.51 versus 0.49 is a different thing from one that
     is 0.95 versus 0.05, and collapsing both to a label would discard the only
     reason to ask.

The threshold lives HERE, at the call site, because it is a decision about what a
wrong answer costs in this specific pipeline. It is not a property of the Jev
client, and it is not global.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from citegraph.config import settings
from citegraph.llm.base import ProviderUnavailable
from citegraph.llm.budget import budget_exhausted
from citegraph.llm.jev import JevClient

logger = logging.getLogger(__name__)

#: The stages a label can denote, named for the answer so Jev returns a key we
#: can use rather than prose we would have to map back.
STAGE_CRITERIA: dict[str, str] = {
    "screened": "people assessed for eligibility, or screened",
    "enrolled": "people admitted to the study or enrolled",
    "randomised": "people assigned to study arms at random",
    "allocated": "people assigned to a study arm, by any method",
    "analysed": "people included in the final analysis",
    "excluded": "people who did not proceed past a stage",
}

INSTRUCTIONS = (
    "Which CONSORT participant-flow stage does this figure label denote? "
    "The labels come from a clinical trial diagram and are often terse."
)

#: Below this the model is not confident enough to overturn a rule, so the rule
#: stands. This is the "only below a confidence bar" rule: the cheap path is the
#: default and the paid path is the exception.
DISAMBIGUATION_THRESHOLD = 0.70


@dataclass
class SecondOpinion:
    """What the model said, and whether it was allowed to change anything."""

    selected: str | None
    probabilities: dict[str, float]
    confidence: float | None
    model_served: str | None
    #: False whenever the answer must not overturn the rules: unavailable, below
    #: the threshold, too close to call, or not a stage we know.
    decisive: bool
    reason: str


def _regex_agree(stages: set[str]) -> bool:
    """Whether the regexes were confident: exactly one stage, and not excluded."""
    non_exclusion = stages - {"excluded"}
    return len(non_exclusion) == 1


async def second_opinion(
    label: str,
    regex_stages: set[str],
    *,
    client: JevClient | None = None,
) -> SecondOpinion:
    """Ask Jev what a figure label denotes, if the rules were unsure.

    Returns a decision with `decisive=False` in every case where the caller must
    keep the regex answer. Never raises: a provider problem degrades to the
    deterministic path rather than failing the run.
    """
    unavailable = SecondOpinion(None, {}, None, None, False, "unavailable")

    if not settings.enable_jev:
        return SecondOpinion(None, {}, None, None, False, "disabled")
    if budget_exhausted():
        return SecondOpinion(None, {}, None, None, False, "budget")
    if _regex_agree(regex_stages):
        # The rules were sure, so there is nothing to ask about. This check runs
        # before the client is touched, which is also why the default path costs
        # nothing.
        return SecondOpinion(None, {}, None, None, False, "rules were confident")

    jev = client or JevClient()
    if not jev.enabled:
        return unavailable

    try:
        answers, usage = await jev.evaluate(
            state={"label": label, "regex_suggested": sorted(regex_stages)},
            questions={
                "stage": {
                    "type": "choice",
                    "instructions": INSTRUCTIONS,
                    "criteria": STAGE_CRITERIA,
                }
            },
        )
    except ProviderUnavailable as exc:
        logger.info("jev unavailable, keeping the rule verdict: %s", exc)
        return SecondOpinion(None, {}, None, None, False, "provider error")
    except Exception:
        # A provider bug must not fail a run. Log the type, not the payload, in
        # case the payload carries anything from the request.
        logger.exception("unexpected error consulting jev; keeping the rule verdict")
        return SecondOpinion(None, {}, None, None, False, "unexpected error")

    decision = answers.get("stage")
    if decision is None:
        return SecondOpinion(None, {}, None, None, False, "no answer")

    confidence = decision.confidence
    selected = decision.selected if isinstance(decision.selected, str) else None

    if selected is None or selected not in STAGE_CRITERIA:
        return SecondOpinion(None, decision.probabilities, confidence,
                             usage.model_served, False, "unknown stage")
    if decision.ambiguous:
        # Two options within 0.1 of each other. The model is aware of its own
        # uncertainty here, and overriding a rule on a coin-flip is worse than
        # keeping the rule.
        #
        # Checked BEFORE the threshold, because a close call is the more
        # informative reason and would otherwise be reported as merely "below
        # threshold" -- an answer of 0.52/0.48 and one of 0.10/0.02 are both
        # under the bar, and only the first is a near-miss worth naming.
        return SecondOpinion(selected, decision.probabilities, confidence,
                             usage.model_served, False, "ambiguous")
    if confidence is None or confidence < DISAMBIGUATION_THRESHOLD:
        return SecondOpinion(selected, decision.probabilities, confidence,
                             usage.model_served, False, "below threshold")

    return SecondOpinion(selected, decision.probabilities, confidence,
                         usage.model_served, True, "decisive")


def resolve_stages(
    label: str,
    regex_stages: set[str],
    opinion: SecondOpinion | None,
) -> set[str]:
    """Apply a second opinion to a regex verdict.

    Kept separate from the call so the decision is testable without a provider,
    and so "what happens when the model disagrees" is a pure function of its two
    arguments.
    """
    if opinion is None or not opinion.decisive:
        return regex_stages
    if opinion.selected is None:
        # decisive without a selection is not a contradiction, but it is not an
        # answer either. Keeping the regexes is the only safe reading.
        return regex_stages
    if opinion.selected == "excluded":
        return {"excluded"}
    return {opinion.selected}


__all__ = [
    "DISAMBIGUATION_THRESHOLD",
    "STAGE_CRITERIA",
    "SecondOpinion",
    "resolve_stages",
    "second_opinion",
]
