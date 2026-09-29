"""A second-opinion pass over a finished flow-diagram reading.

`vision/flow_diagram.py` is synchronous and its output feeds counts the thesis
pins, so the model is NOT called from inside it. Making that module async would
ripple through every caller and change a code path the drift guard checks --
for a feature that is off by default and would change no number until enabled.

Instead this is a separate async pass over a reading that has already been
produced. Two properties follow:

  THE SYNC PATH IS UNTOUCHED. With the feature disabled, or with the rules
  confident, or with a provider down, this returns the reading it was given,
  identical. Nothing about today's behaviour changes.

  RE-READING IS NOT FREE. Every stage count is a sum over labels, and changing a
  label's stage changes that sum. So a second-opinion pass that revises a label
  must RE-RUN THE AGGREGATION, or the reading would carry a revised label and a
  count that no longer matches it. `apply_second_opinions` therefore re-derives
  the stage counts from the revised labels and reports what changed, rather than
  quietly leaving the two inconsistent.

The threshold lives in `disambiguation`, not here. This module decides when to
ASK, and what to do with the answer; it does not decide what counts as confident.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from citegraph.nlp.disambiguation import resolve_stages, second_opinion

if TYPE_CHECKING:  # pragma: no cover
    from citegraph.vision.flow_diagram import FlowReading

logger = logging.getLogger(__name__)


@dataclass
class Revisions:
    """What a second-opinion pass changed, so a caller can log or record it."""

    labels_asked: int = 0
    labels_revised: int = 0
    #: label -> (before, after) for each revision.
    changes: dict[str, tuple[frozenset[str], frozenset[str]]] = field(default_factory=dict)
    #: Labels where the model was asked and the rules were kept.
    labels_declined: int = 0
    model_served: str | None = None

    def summary(self) -> str:
        return (
            f"second opinion: asked {self.labels_asked}, revised {self.labels_revised}, "
            f"declined {self.labels_declined}"
        )


async def apply_second_opinions(reading: FlowReading) -> Revisions:
    """Revise stage labels on a reading where the regexes were unsure.

    Returns the revisions made. When a label is revised the stage TOTALS are
    re-derived, because a stage count is a sum over labels: revising a label
    without re-running the aggregation would leave a reading whose labels and
    counts disagree, which looks like a working reading and is not.
    """
    revisions = Revisions()
    counts = list(getattr(reading, "counts", []) or [])

    if not counts:
        return revisions

    # Collect the labels the rules were unsure about. A label with exactly one
    # stage is confident and is never sent anywhere.
    uncertain: list[tuple[Any, str, frozenset[str]]] = []
    for count in counts:
        stages = frozenset(count.stages or ())
        if len(stages - {"excluded"}) == 1:
            continue
        uncertain.append((count, count.label, stages))

    if not uncertain:
        return revisions

    for count, label, stages in uncertain:
        revisions.labels_asked += 1
        opinion = await second_opinion(label, set(stages))
        if opinion.model_served:
            revisions.model_served = opinion.model_served

        if not opinion.decisive:
            revisions.labels_declined += 1
            continue

        revised = frozenset(resolve_stages(label, set(stages), opinion))
        if revised != stages:
            count.stages = set(revised)
            revisions.labels_revised += 1
            revisions.changes[label] = (stages, revised)

    if revisions.labels_revised:
        # Re-derive the totals from the revised labels. Without this the reading
        # would carry a label that says "analysed" and a randomised count that
        # still includes it.
        from citegraph.vision.flow_diagram import _aggregate

        recomputed = _aggregate(counts)
        for stage in ("screened", "enrolled", "randomised", "analysed"):
            setattr(reading, stage, getattr(recomputed, stage))
        reading.evidence = dict(recomputed.evidence)
        reading.counts = counts
        logger.info("second opinion revised %d label(s) and re-derived totals",
                    revisions.labels_revised)

    return revisions


__all__ = ["Revisions", "apply_second_opinions"]
