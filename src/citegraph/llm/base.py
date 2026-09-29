"""The provider interface CiteGraph's two model backends share.

Jev and GLM are not interchangeable and are not presented as though they are.
Jev is a typed decision engine: it answers `choice`, `score` and `noul` questions
with probability distributions and no chat interface. GLM is a conventional chat
model used to write a narrative from the citation graph. One interface exists so
that the CALL SITE does not branch on vendor, not so that the two can be treated
as the same thing.

Everything here is server-side. No key is ever returned to a caller, and the
`Provider` protocol has no method that could return one.

The transport discipline is borrowed from the Terminux project
(`src/terminux/provider/`), whose docstrings record four behaviours that only
appear on a real connection:

  1. An error can arrive with HTTP 200. Once a stream is open the status is
     already sent, so an upstream failure comes back in the body and a client
     that checks only `status_code` reads it as an empty success.
  2. `finish_reason` arrives before the usage chunk. Stopping there loses the
     usage record that billing depends on.
  3. A stalled stream is not a closed stream. It needs a gap watchdog re-armed per
     chunk, not a total-request timeout.
  4. Keepalive comments are not JSON.

None of the four has been observed on these two providers, so they are
documented rather than implemented speculatively. They are recorded because the
cost of discovering them is a production incident, and the alternative is a
comment that says nothing happened.
"""
from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import httpx

logger = logging.getLogger(__name__)


class ProviderUnavailable(RuntimeError):
    """A provider cannot be used right now. Never carries a credential.

    The message is built from the status code and the provider's own error text
    only. If a vendor echoes the key back in an error body -- some do -- the
    body is logged at DEBUG and not attached to the exception, because an
    exception message is the thing most likely to be printed, logged to a third
    party, or shown in a traceback in a browser.
    """


class DecisionUnavailable(ProviderUnavailable):
    """A call failed in a way that means "ask the rules instead"."""


# ---------------------------------------------------------------- usage


@dataclass
class Usage:
    """Token and cost accounting for one call.

    FR-89a, measured in the Terminus project and restated because it is the
    single easiest thing to get wrong: the three cache-accounting shapes are NOT
    interchangeable and summing them naively double-counts.

        DeepSeek direct   prompt_cache_hit_tokens + prompt_cache_miss_tokens are
                          MUTUALLY EXCLUSIVE and sum to prompt_tokens.
        OpenAI direct     prompt_tokens_details.cached_tokens is INCLUSIVE.
        OpenRouter        INCLUSIVE, plus an authoritative usage.cost.

    GLM exposes NEITHER field name. Reading a DeepSeek or OpenAI field name
    against GLM would report 0% cache hit on every call while being billed for
    roughly 97%. So an absent breakdown is recorded as all-miss, which
    OVER-estimates our own cost rather than under, and a provider whose shape has
    not been measured is marked unknown rather than assumed.
    """

    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    #: True only when the provider actually reported a cache breakdown.
    cache_breakdown_known: bool = False
    cached_input_tokens: int = 0
    cost_usd: float | None = None
    #: The model the provider says it served, not the one we asked for. A
    #: reproducibility claim that cannot name its model is not a claim.
    model_served: str | None = None

    def as_row(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_breakdown_known": self.cache_breakdown_known,
            "cached_input_tokens": self.cached_input_tokens,
            "cost_usd": self.cost_usd,
            "model_served": self.model_served,
        }


class Provider(Protocol):
    """What CiteGraph needs from a model backend."""

    name: str

    async def call(self, payload: dict[str, Any]) -> tuple[dict[str, Any], Usage]:
        """Return the parsed response and its usage. Raise ProviderUnavailable."""
        ...


# ---------------------------------------------------------------- retry


#: Statuses worth trying again. Everything else in the 4xx range is a request
#: that will fail identically forever, and retrying it wastes the budget.
RETRYABLE = frozenset({408, 425, 429, 500, 502, 503, 504, 529})


@dataclass
class RetryPolicy:
    """Backoff schedule.

    Jitter is not optional. Without it, every client that hit a rate limit at the
    same moment retries at the same moment, which is how a rate limit becomes an
    outage.
    """

    max_retries: int = 3
    base_delay_s: float = 1.0
    timeout_s: float = 10.0

    def delay_for(self, attempt: int, retry_after: str | None = None) -> float:
        """Seconds to wait before attempt N+1.

        A `Retry-After` header is obeyed when it parses; a server that tells you
        when to come back knows better than a formula.
        """
        if retry_after:
            try:
                return min(float(retry_after), 60.0)
            except ValueError:
                logger.debug("Retry-After header was not a number; using backoff")
        exponential = self.base_delay_s * (2**attempt)
        return exponential + random.uniform(0, exponential * 0.25)


def classify(status: int) -> Literal["retry", "fatal"]:
    """Whether a status is worth another attempt."""
    return "retry" if status in RETRYABLE else "fatal"


# ---------------------------------------------------------------- protocol glue


def scrub(text: str, *secrets: str | None) -> str:
    """Remove any known secret from a string before it is logged or raised.

    Belt and braces for the case this is guarding: a vendor echoing the key back
    inside an error body. The length is the only thing that must survive, so a
    redacted message stays useful.
    """
    out = text
    for secret in secrets:
        if secret and len(secret) >= 8:
            out = out.replace(secret, "[REDACTED]")
    return out


class HttpProvider:
    """Shared HTTP behaviour for both providers."""

    name = "http"

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        timeout_s: float,
        max_retries: int,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.timeout_s = timeout_s
        self.retry = RetryPolicy(
            max_retries=max_retries, base_delay_s=1.0, timeout_s=timeout_s
        )
        self._headers = headers or {}
        #: Overridden by tests with an httpx.MockTransport. Set here rather than
        #: read from an attribute that does not exist, because a test that sets an
        #: undeclared hook passes silently and then talks to the real network --
        #: which is what happened: the first run of this suite tried to resolve
        #: example.invalid and failed on DNS.
        self._transport: httpx.AsyncBaseTransport | None = None

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def _request_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self._headers}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def post_json(
        self, path: str, body: dict[str, Any]
    ) -> tuple[dict[str, Any], httpx.Response]:
        """POST with the retry policy, returning parsed JSON and the response.

        The response is returned as well as the parsed body because the model id
        and the usage block often live in headers or in fields the caller reads
        separately.
        """
        url = f"{self.base_url}{path}"
        last: Exception | None = None

        async with httpx.AsyncClient(
            timeout=self.timeout_s, transport=self._transport
        ) as client:
            for attempt in range(self.retry.max_retries + 1):
                try:
                    response = await client.post(
                        url, json=body, headers=self._request_headers()
                    )
                except httpx.TimeoutException as exc:
                    last = exc
                    logger.warning("%s: request timed out", self.name)
                except httpx.HTTPError as exc:
                    last = exc
                    logger.warning("%s: connection error", self.name)
                else:
                    if response.status_code < 400:
                        return self._parse(response), response

                    verdict = classify(response.status_code)
                    detail = scrub(
                        response.text[:400], self._api_key
                    )
                    if verdict == "retry" and attempt < self.retry.max_retries:
                        delay = self.retry.delay_for(
                            attempt, response.headers.get("retry-after")
                        )
                        logger.warning(
                            "%s: HTTP %s, retrying in %.1fs",
                            self.name,
                            response.status_code,
                            delay,
                        )
                        await _sleep(delay)
                        continue
                    # 401 and 422 land here: never retried, and the body is
                    # scrubbed because it is the likeliest place for a key to
                    # come back.
                    raise ProviderUnavailable(
                        f"{self.name}: HTTP {response.status_code}: {detail}"
                    ) from None

                if attempt >= self.retry.max_retries:
                    break
                delay = self.retry.delay_for(attempt)
                await _sleep(delay)

        raise DecisionUnavailable(
            f"{self.name}: gave up after {self.retry.max_retries + 1} attempts"
        ) from last

    def _parse(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except (json.JSONDecodeError, ValueError):
            body = scrub(response.text[:200], self._api_key)
            raise ProviderUnavailable(
                f"{self.name}: response was not valid JSON: {body}"
            ) from None
        if not isinstance(payload, dict):
            raise ProviderUnavailable(f"{self.name}: response was not a JSON object")
        return payload


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)


__all__ = [
    "RETRYABLE",
    "DecisionUnavailable",
    "HttpProvider",
    "Provider",
    "ProviderUnavailable",
    "RetryPolicy",
    "Usage",
    "classify",
    "scrub",
]
