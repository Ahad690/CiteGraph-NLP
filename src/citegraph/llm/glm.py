"""GLM: the narrative report writer.

Different job from Jev and a different shape of answer. Jev classifies; GLM
writes. The constraint that matters is not stylistic:

    A generated sentence with no supporting edge in the citation graph is a
    defect, not a stylistic problem.

CiteGraph's claim is that every claim is traceable to a source and carries its
link confidence. A report that reads fluently and asserts something the graph
does not support undermines the whole design, so `build_prompt` hands the model
only what the graph contains, `generate_report` returns the text together with
the papers it was grounded on, and a caller can therefore check the second
against the first. The model is not asked to cite and is not trusted to.

The key is server-side. It is sent in an Authorization header and never leaves
the process; nothing in this module returns it, logs it, or puts it in an
exception.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from citegraph.config import settings
from citegraph.llm.base import HttpProvider, ProviderUnavailable, Usage
from citegraph.llm.budget import budget_exhausted, record

logger = logging.getLogger(__name__)

ENDPOINT = "/chat/completions"

SYSTEM_PROMPT = (
    "You write literature overviews from a citation graph. "
    "Use ONLY the papers provided. Do not introduce a paper that is not listed, "
    "do not invent a finding, a number, or a year, and do not speculate beyond "
    "what the provided titles and abstracts state. "
    "If the provided material does not support a claim, say the evidence is "
    "insufficient rather than filling the gap. "
    "Write plain prose. No bullet lists, no headings, no preamble."
)


class GLMClient(HttpProvider):
    """Narrative report generation from graph evidence."""

    name = "glm"

    def __init__(self) -> None:
        super().__init__(
            base_url=settings.glm_base_url,
            api_key=settings.glm_api_key,
            timeout_s=settings.glm_timeout_s,
            max_retries=settings.glm_max_retries,
        )

    @property
    def enabled(self) -> bool:
        return bool(settings.enable_glm and self.configured)

    def build_prompt(self, question: str, papers: Sequence[dict[str, Any]]) -> str:
        """The user message: the question, then the evidence, then the ask.

        The evidence is a flat list of what the providers actually returned. No
        summary of the graph, no interpretation, no selection made here -- the
        model sees what the graph holds and nothing else.
        """
        lines = [f"RESEARCH QUESTION: {question}", "", "PAPERS FOUND IN THE GRAPH:"]
        for i, paper in enumerate(papers, 1):
            parts = [f"{i}. {paper.get('title', 'Untitled')}"]
            if paper.get("year"):
                parts.append(f"({paper['year']})")
            if paper.get("journal"):
                parts.append(f"- {paper['journal']}")
            authors = paper.get("authors") or []
            if authors:
                shown = ", ".join(authors[:3])
                if len(authors) > 3:
                    shown += " et al."
                parts.append(f"- {shown}")
            if paper.get("doi"):
                parts.append(f"DOI: {paper['doi']}")
            abstract = paper.get("abstract")
            if abstract:
                parts.append(f"- Abstract: {str(abstract)[:600]}")
            if paper.get("confidence") is not None:
                parts.append(
                    f"- Link confidence to the seed paper: {paper['confidence']:.2f}"
                )
            lines.append(" ".join(parts))
        lines.append("")
        lines.append("Write the overview using only these papers.")
        return "\n".join(lines)

    async def generate_report(
        self, question: str, papers: Sequence[dict[str, Any]]
    ) -> tuple[str, Usage]:
        """Return the report text and the usage for the call.

        The day's budget is checked BEFORE the call, not after. Checking after
        means the call that breaches the ceiling has already been paid for.
        """
        if not self.enabled:
            raise ProviderUnavailable("glm: disabled or not configured")
        if budget_exhausted():
            raise ProviderUnavailable(
                "glm: daily provider budget reached, falling back"
            )
        if not papers:
            raise ProviderUnavailable("glm: no papers to write from")

        body = {
            "model": settings.glm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self.build_prompt(question, papers)},
            ],
            "temperature": 0.2,
        }

        payload, _response = await self.post_json(ENDPOINT, body)

        text = _extract_text(payload)
        if not text:
            raise ProviderUnavailable("glm: response contained no text")

        usage_block = payload.get("usage") or {}
        cost = usage_block.get("cost")
        usage = Usage(
            provider=self.name,
            input_tokens=int(usage_block.get("prompt_tokens") or 0),
            output_tokens=int(usage_block.get("completion_tokens") or 0),
            # GLM exposes neither prompt_cache_hit_tokens nor
            # prompt_tokens_details.cached_tokens. Reading either name against it
            # would report 0% cache hit on every call while being billed for
            # roughly 97% of the input as cached. The breakdown is therefore
            # recorded as unknown, and the cost is estimated conservatively.
            cache_breakdown_known=False,
            cost_usd=float(cost) if isinstance(cost, (int, float)) else None,
            model_served=payload.get("model"),
        )

        record(
            provider=self.name,
            model=usage.model_served or settings.glm_model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=usage.cost_usd,
        )
        return text, usage


def _extract_text(payload: dict[str, Any]) -> str:
    """Pull the assistant text out of a chat-completions response.

    Tolerant of the two shapes seen in the wild: `choices[0].message.content` and
    a plain `content` string. A response that parses but yields nothing is
    reported as a failure rather than as an empty report, because an empty
    report is indistinguishable from a working one.
    """
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content.strip()
            text = first.get("text")
            if isinstance(text, str):
                return text.strip()
    content = payload.get("content")
    return content.strip() if isinstance(content, str) else ""


__all__ = ["SYSTEM_PROMPT", "GLMClient"]
