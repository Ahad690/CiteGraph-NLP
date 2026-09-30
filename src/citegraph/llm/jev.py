"""Jev: a typed decision engine, and the thing it is not.

Jev is not a chat model. It has no messages endpoint, no prompt, and no
conversation. It takes a `state` -- any string, object or array describing what
is known -- and a set of typed questions, and answers each one with a
probability distribution and a confidence. Three question types exist:

    choice   one option selected from named criteria, with per-criterion
             probabilities and a confidence
    score    an index into an ordered criteria array, with a distribution
    noul     a probability in [0, 1] for a yes/no question

Wrapping this in a chat interface would be wrong twice over: it would invent an
endpoint the vendor does not have, and it would hide the distributions that make
the answers useful. CiteGraph's whole argument is that a match carries a
confidence score rather than a verdict, so the value here is the distribution and
not the selected label.

TYPESAFE_API_KEY is not yet set. `configured` is False until it is, `enabled` is
False by default, and the deterministic rules remain in charge. Nothing about the
existing pipeline changes until a key exists AND the flag is on.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from citegraph.config import settings
from citegraph.llm.base import HttpProvider, ProviderUnavailable, Usage
from citegraph.llm.cache import cached_post

logger = logging.getLogger(__name__)

ENDPOINT = "/v1/systemone"


class QuestionType(str, Enum):
    """The three question types Jev has. There is no fourth.

    `str, Enum` and NOT `enum.StrEnum`. StrEnum is Python 3.11+, and production
    runs 3.10, so using it makes this module unimportable there. That stayed
    hidden for a commit because nothing imported jev.py from the app -- the
    module existed, and its tests passed, and the image would not start the
    moment a route imported it. The mixin gives the same behaviour for what this
    is used for: the members ARE strings, so f-strings and JSON serialisation
    need no `.value` and no custom encoder.
    """

    CHOICE = "choice"
    SCORE = "score"
    NOUL = "noul"


@dataclass
class Choice:
    """One option must be selected from named criteria."""

    criteria: dict[str, str | None]
    question_id: str = "choice"

    def to_payload(self, instructions: str) -> dict[str, Any]:
        return {
            "type": "choice",
            "instructions": instructions,
            "criteria": self.criteria,
        }


@dataclass
class Score:
    """An ordered scale; the answer is a zero-based index into criteria."""

    criteria: list[str]
    question_id: str = "score"

    def to_payload(self, instructions: str) -> dict[str, Any]:
        return {
            "type": "score",
            "instructions": instructions,
            "criteria": self.criteria,
        }


@dataclass
class Noul:
    """A yes/no question answered as a probability in [0, 1]."""

    question_id: str = "noul"

    def to_payload(self, instructions: str) -> dict[str, Any]:
        return {"type": "noul", "instructions": instructions}


@dataclass
class Decision:
    """One answer, with everything needed to judge it.

    The thresholds are deliberately NOT applied here. A 0.7 cut-off is a decision
    about what a wrong answer costs, which only the call site knows: a
    misclassified trial type should be reviewed, while a link-confidence score
    feeds a ranking and a different number is right. Applying one globally would
    bake one call site's risk into every other.
    """

    question_id: str
    kind: str
    #: The selected option, or the selected index, per `kind`.
    selected: str | int | None
    #: Probability for each option, or each index, as reported.
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float | None = None
    #: The noul probability, for `noul` questions.
    noul: float | None = None

    @property
    def ambiguous(self) -> bool:
        """Whether the top two options are too close to call.

        Reported rather than acted on, for the same reason thresholds are not
        applied here.
        """
        values = sorted(self.probabilities.values(), reverse=True)
        if len(values) < 2:
            return False
        return (values[0] - values[1]) < 0.1


class JevClient(HttpProvider):
    """A client for one decision endpoint."""

    name = "jev"

    def __init__(self) -> None:
        super().__init__(
            base_url=settings.jev_base_url,
            api_key=settings.jev_api_key,
            timeout_s=settings.jev_timeout_s,
            max_retries=settings.jev_max_retries,
        )

    @property
    def enabled(self) -> bool:
        return bool(settings.enable_jev and self.configured)

    def model_id(self) -> str:
        """The pinned model when one is set, otherwise the moving alias.

        `jev-latest` follows the vendor. A published number that came from it
        cannot be reproduced later, so a run records the model the API REPORTS
        and a production deployment is expected to pin one.
        """
        return settings.jev_model_pin or settings.jev_model

    def build_request(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: dict[str, Any],
        model: str | None = None,
    ) -> dict[str, Any]:
        return {
            "model": model or self.model_id(),
            "state": state,
            "questions": questions,
        }

    async def evaluate(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: dict[str, Any],
        model: str | None = None,
    ) -> tuple[dict[str, Decision], Usage]:
        """Ask several questions against one state in a single call.

        Batching is the point: Jev is built to evaluate several decisions against
        the same input, and one call for three questions costs less and is more
        consistent than three calls for one each.
        """
        if not self.enabled:
            raise ProviderUnavailable("jev: disabled or not configured")

        body = self.build_request(state, questions, model)
        payload, from_cache = await cached_post(
            self, ENDPOINT, body, model=self.model_id()
        )

        answers = payload.get("answers") or {}
        if not isinstance(answers, dict):
            raise ProviderUnavailable("jev: response had no answers object")

        usage_block = payload.get("usage") or {}
        usage = Usage(
            provider=self.name,
            # Zero on a cache hit. The payload still carries the ORIGINAL
            # usage, and reporting it again would charge the daily ceiling for
            # tokens that were never re-bought. The budget is a record of real
            # spend, so a hit that inflated it would make the ceiling measure
            # something other than spend.
            input_tokens=0 if from_cache else int(usage_block.get("input_tokens") or 0),
            output_tokens=0 if from_cache else int(usage_block.get("output_tokens") or 0),
            # Jev reports plain token counts with no cache breakdown, so the
            # conservative all-miss default applies.
            cache_breakdown_known=False,
            model_served=payload.get("model"),
        )

        return (
            {qid: _parse_answer(qid, answers.get(qid)) for qid in questions},
            usage,
        )


def _parse_answer(question_id: str, raw: Any) -> Decision:
    if not isinstance(raw, dict):
        return Decision(question_id=question_id, kind="unknown", selected=None)

    kind = str(raw.get("type") or "unknown")
    probabilities = {
        str(k): float(v)
        for k, v in (raw.get("probabilities") or {}).items()
        if isinstance(v, (int, float))
    }
    confidence = raw.get("confidence")
    noul = raw.get("noul")

    if kind == "choice":
        return Decision(
            question_id=question_id,
            kind=kind,
            selected=raw.get("choice"),
            probabilities=probabilities,
            confidence=float(confidence) if isinstance(confidence, (int, float)) else None,
        )

    if kind == "score":
        score = raw.get("score")
        return Decision(
            question_id=question_id,
            kind=kind,
            selected=int(score) if isinstance(score, (int, float)) else None,
            probabilities=probabilities,
            confidence=float(confidence) if isinstance(confidence, (int, float)) else None,
        )

    if kind == "noul":
        return Decision(
            question_id=question_id,
            kind=kind,
            selected=None,
            probabilities=probabilities,
            noul=float(noul) if isinstance(noul, (int, float)) else None,
        )

    return Decision(question_id=question_id, kind=kind, selected=None)


__all__ = [
    "Choice",
    "Decision",
    "JevClient",
    "Noul",
    "QuestionType",
    "Score",
]
