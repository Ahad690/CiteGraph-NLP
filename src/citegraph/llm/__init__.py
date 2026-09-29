"""External model providers, server-side only.

Two backends, two shapes, one selection point:

    Jev    typed decisions -- choice, score, noul -- with distributions
    GLM    narrative generation from graph evidence

They are not interchangeable and neither is presented as a chat model. The
registry exists so a CALL SITE does not branch on vendor, not to blur the
difference.

Every provider is OFF by default. With no key and no flag, this package changes
nothing about how CiteGraph behaves, and the deterministic rules stay in charge.
"""
from __future__ import annotations

import logging

from citegraph.llm.base import (
    DecisionUnavailable,
    HttpProvider,
    Provider,
    ProviderUnavailable,
    RetryPolicy,
    Usage,
    classify,
    scrub,
)
from citegraph.llm.budget import budget_exhausted, budget_remaining, record, spend_today
from citegraph.llm.glm import GLMClient
from citegraph.llm.jev import Choice, Decision, JevClient, Noul, QuestionType, Score

logger = logging.getLogger(__name__)


def get_jev() -> JevClient:
    return JevClient()


def get_glm() -> GLMClient:
    return GLMClient()


__all__ = [
    "Choice",
    "Decision",
    "DecisionUnavailable",
    "GLMClient",
    "HttpProvider",
    "JevClient",
    "Noul",
    "Provider",
    "ProviderUnavailable",
    "QuestionType",
    "RetryPolicy",
    "Score",
    "Usage",
    "budget_exhausted",
    "budget_remaining",
    "classify",
    "get_glm",
    "get_jev",
    "record",
    "scrub",
    "spend_today",
]
