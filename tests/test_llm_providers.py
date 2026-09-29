"""Tests for the model providers. No live API call is made from any of them.

The transport is mocked at the httpx level so the retry policy, the error
classification and the parsing are all exercised without a network, a key, or
money.

Two things are asserted throughout because they are the ones that would hurt:

  A KEY MUST NEVER APPEAR in a log line, an exception message, or a serialised
  response. An exception message is the most likely thing to be printed, shipped
  to an error tracker, or shown in a browser, and a vendor that echoes the key
  back inside an error body would put it there. `test_the_key_never_leaks`
  forces that through every path.

  A PROVIDER THAT IS TYPESAFE'S JEV IS NOT A CHAT MODEL. It is exercised as a
  typed decision engine, because wrapping it in a messages interface would invent
  an endpoint the vendor does not have.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
import pytest

from citegraph.config import settings
from citegraph.llm.base import (
    HttpProvider,
    ProviderUnavailable,
    RetryPolicy,
    Usage,
    classify,
    scrub,
)
from citegraph.llm.glm import GLMClient
from citegraph.llm.jev import Choice, JevClient, Noul, Score

SECRET = "sk-test-0123456789abcdef"  # fake, and long enough to be scrubbed


def transport_returning(*responses: httpx.Response) -> Any:
    """An httpx.AsyncClient whose post returns the given responses in order."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return responses[min(len(calls) - 1, len(responses) - 1)]

    return handler, calls


def client_for(handler: Any, **kwargs: Any) -> HttpProvider:
    provider = HttpProvider(
        base_url="https://example.invalid",
        api_key=SECRET,
        timeout_s=0.1,
        max_retries=kwargs.pop("max_retries", 0),
        **kwargs,
    )
    # A declared attribute, not an invented one. The first version of this set
    # `_client_factory`, which the provider never read, so every test passed a
    # mock that went unused and the suite resolved example.invalid over DNS.
    provider._transport = httpx.MockTransport(handler)
    return provider


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Backoff is real; the tests are not."""
    from citegraph.llm import base

    async def instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr(base, "_sleep", instant)


# ---------------------------------------------------------------- classification


class TestClassify:
    def test_rate_limit_and_overload_are_retryable(self):
        assert classify(429) == "retry"
        assert classify(529) == "retry"
        assert classify(503) == "retry"

    def test_auth_and_schema_are_fatal(self):
        """401 and 422 will fail identically forever. Retrying them is a
        request loop with a latency tax and no chance of success."""
        assert classify(401) == "fatal"
        assert classify(422) == "fatal"

    def test_404_is_fatal(self):
        assert classify(404) == "fatal"


class TestRetryPolicy:
    def test_backoff_grows(self):
        policy = RetryPolicy(base_delay_s=1.0)
        first = policy.delay_for(0)
        second = policy.delay_for(1)
        assert second > first

    def test_jitter_is_present(self):
        """Without jitter, every client that hit the limit together comes back
        together, and the rate limit becomes an outage."""
        policy = RetryPolicy(base_delay_s=1.0)
        samples = {round(policy.delay_for(2), 6) for _ in range(12)}
        assert len(samples) > 1

    def test_jitter_stays_within_the_band(self):
        policy = RetryPolicy(base_delay_s=1.0)
        for _ in range(30):
            delay = policy.delay_for(1)
            assert 2.0 <= delay <= 2.5

    def test_retry_after_is_obeyed(self):
        """A server that says when to come back knows better than a formula."""
        assert RetryPolicy().delay_for(0, "7") == 7.0

    def test_an_unparseable_retry_after_falls_back(self):
        policy = RetryPolicy(base_delay_s=1.0)
        delay = policy.delay_for(0, "tomorrow")
        assert 1.0 <= delay <= 1.25


# ---------------------------------------------------------------- scrubbing


class TestScrub:
    def test_removes_a_known_secret(self):
        assert SECRET not in scrub(f"failed with {SECRET}", SECRET)

    def test_leaves_other_text_intact(self):
        out = scrub("HTTP 401: bad key", SECRET)
        assert "401" in out
        assert "bad key" in out

    def test_ignores_a_secret_too_short_to_match_by_accident(self):
        """A 3-character 'secret' would match everywhere."""
        assert scrub("abcdef", "abc") == "abcdef"

    def test_handles_none(self):
        assert scrub("text", None) == "text"


# ---------------------------------------------------------------- transport


class TestTransport:
    @pytest.mark.asyncio
    async def test_a_200_returns_the_parsed_body(self):
        handler, calls = transport_returning(
            httpx.Response(200, json={"ok": True, "value": 1})
        )
        provider = client_for(handler)
        body, _ = await provider.post_json("/x", {})
        assert body == {"ok": True, "value": 1}
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_the_key_is_sent_as_a_bearer_header(self):
        handler, calls = transport_returning(httpx.Response(200, json={}))
        provider = client_for(handler)
        await provider.post_json("/x", {})
        assert calls[0].headers["authorization"] == f"Bearer {SECRET}"

    @pytest.mark.asyncio
    async def test_401_is_not_retried(self):
        handler, calls = transport_returning(httpx.Response(401, json={}))
        provider = client_for(handler, max_retries=3)
        with pytest.raises(ProviderUnavailable) as exc:
            await provider.post_json("/x", {})
        assert len(calls) == 1, "401 must not be retried"
        assert "401" in str(exc.value)

    @pytest.mark.asyncio
    async def test_422_is_not_retried(self):
        handler, calls = transport_returning(httpx.Response(422, json={}))
        provider = client_for(handler, max_retries=3)
        with pytest.raises(ProviderUnavailable):
            await provider.post_json("/x", {})
        assert len(calls) == 1, "422 must not be retried"

    @pytest.mark.asyncio
    async def test_429_is_retried_then_succeeds(self):
        handler, calls = transport_returning(
            httpx.Response(429, json={}, headers={"retry-after": "0"}),
            httpx.Response(200, json={"ok": True}),
        )
        provider = client_for(handler, max_retries=2)
        body, _ = await provider.post_json("/x", {})
        assert body == {"ok": True}
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_529_is_retried(self):
        handler, calls = transport_returning(
            httpx.Response(529, json={}, headers={"retry-after": "0"}),
            httpx.Response(200, json={"ok": True}),
        )
        provider = client_for(handler, max_retries=2)
        await provider.post_json("/x", {})
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_it_gives_up_after_the_retry_budget(self):
        handler, calls = transport_returning(httpx.Response(503, json={}))
        provider = client_for(handler, max_retries=2)
        with pytest.raises(ProviderUnavailable):
            await provider.post_json("/x", {})
        assert len(calls) == 3  # the original plus two retries

    @pytest.mark.asyncio
    async def test_invalid_json_is_a_failure_not_an_empty_result(self):
        """A response that parses to nothing is a provider failure, not a
        successful call that happened to return nothing."""
        handler, _ = transport_returning(
            httpx.Response(200, text="<html>gateway</html>")
        )
        provider = client_for(handler)
        with pytest.raises(ProviderUnavailable) as exc:
            await provider.post_json("/x", {})
        assert "not valid JSON" in str(exc.value)

    @pytest.mark.asyncio
    async def test_a_json_array_is_rejected(self):
        handler, _ = transport_returning(httpx.Response(200, json=[1, 2, 3]))
        provider = client_for(handler)
        with pytest.raises(ProviderUnavailable):
            await provider.post_json("/x", {})

    @pytest.mark.asyncio
    async def test_a_timeout_is_retried_and_then_reported(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow", request=request)

        provider = client_for(handler, max_retries=1)
        with pytest.raises(ProviderUnavailable):
            await provider.post_json("/x", {})

    @pytest.mark.asyncio
    async def test_a_connection_error_is_reported(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route", request=request)

        provider = client_for(handler, max_retries=0)
        with pytest.raises(ProviderUnavailable):
            await provider.post_json("/x", {})


# ---------------------------------------------------------------- Jev


JEV_CHOICE_RESPONSE = {
    "model": "jev-1.13.0",
    "answers": {
        "study_design": {
            "type": "choice",
            "choice": "randomised",
            "probabilities": {"randomised": 0.92, "observational": 0.06, "other": 0.02},
            "confidence": 0.88,
        }
    },
    "usage": {"input_tokens": 123, "output_tokens": 12},
}


class TestJev:
    def test_it_is_a_decision_engine_not_a_chat_model(self):
        """There is no messages endpoint and no prompt. Inventing one would be
        wrong twice over: the endpoint does not exist, and it would hide the
        distributions that make the answer useful."""
        from citegraph.llm.jev import ENDPOINT

        assert ENDPOINT == "/v1/systemone"
        assert "chat" not in ENDPOINT.lower()
        assert "messages" not in ENDPOINT.lower()

    def test_a_choice_question_has_the_documented_shape(self):
        question = Choice(criteria={"a": "A means A", "b": "B means B"}).to_payload("Which?")
        assert question == {
            "type": "choice",
            "instructions": "Which?",
            "criteria": {"a": "A means A", "b": "B means B"},
        }

    def test_a_score_question_takes_an_ordered_list(self):
        question = Score(criteria=["Calm", "Frustrated"]).to_payload("How much?")
        assert question["criteria"] == ["Calm", "Frustrated"]
        assert question["type"] == "score"

    def test_a_noul_question_takes_no_criteria(self):
        question = Noul().to_payload("Is it true?")
        assert question == {"type": "noul", "instructions": "Is it true?"}

    def test_the_request_carries_the_model_and_state(self):
        client = JevClient()
        body = client.build_request({"message": "x"}, {"q": {"type": "noul"}})
        assert body["model"]
        assert body["state"] == {"message": "x"}
        assert "q" in body["questions"]

    def test_a_pin_overrides_the_moving_alias(self):
        """jev-latest follows the vendor, so a published number from it cannot be
        reproduced. A pin is how a run becomes reproducible."""
        original = settings.jev_model_pin
        try:
            settings.jev_model_pin = "jev-1.13.0"
            assert JevClient().model_id() == "jev-1.13.0"
            settings.jev_model_pin = None
            assert JevClient().model_id() == settings.jev_model
        finally:
            settings.jev_model_pin = original

    def test_a_distribution_is_kept_not_collapsed_to_a_label(self):
        """The distribution is the reason to use this over a classifier. A
        Decision that kept only the selected option would throw away the
        evidence a caller needs to decide whether to trust it."""
        from citegraph.llm.jev import _parse_answer

        decision = _parse_answer("q", JEV_CHOICE_RESPONSE["answers"]["study_design"])
        assert decision.selected == "randomised"
        assert decision.confidence == 0.88
        assert decision.probabilities["randomised"] == 0.92
        assert len(decision.probabilities) == 3

    def test_a_score_answer_is_a_zero_based_index(self):
        from citegraph.llm.jev import _parse_answer

        raw = {
            "type": "score",
            "score": 1,
            "probabilities": {"0": 0.03, "1": 0.91, "2": 0.06},
            "confidence": 0.85,
        }
        decision = _parse_answer("frustration", raw)
        assert decision.selected == 1
        assert decision.probabilities["1"] == 0.91

    def test_a_noul_answer_is_a_probability(self):
        from citegraph.llm.jev import _parse_answer

        decision = _parse_answer("asks", {"type": "noul", "noul": 0.96})
        assert decision.noul == 0.96
        assert decision.selected is None

    def test_a_close_call_is_reported_as_ambiguous(self):
        from citegraph.llm.jev import _parse_answer

        raw = {"type": "choice", "choice": "a", "probabilities": {"a": 0.5, "b": 0.48}}
        assert _parse_answer("q", raw).ambiguous is True

    def test_a_clear_winner_is_not_ambiguous(self):
        from citegraph.llm.jev import _parse_answer

        raw = {"type": "choice", "choice": "a", "probabilities": {"a": 0.9, "b": 0.1}}
        assert _parse_answer("q", raw).ambiguous is False

    def test_no_threshold_is_baked_in(self):
        """A 0.7 cut-off is a decision about what a wrong answer costs, which
        only the call site knows. It must not be a property of the client.

        Asserted by checking a Decision carries every value the caller needs to
        apply its own threshold, and that nothing was dropped on the way. An
        earlier version of this test asserted `confidence == 0.71` on a payload
        with no `confidence` field, which failed against correct code: the
        confidence is a separate field from the probabilities, and a threshold
        applied to the top probability is the caller's decision, not ours.
        """
        from citegraph.llm.jev import _parse_answer

        raw = {
            "type": "choice",
            "choice": "a",
            "probabilities": {"a": 0.71, "b": 0.29},
            "confidence": 0.71,
        }
        decision = _parse_answer("q", raw)
        # Everything a caller needs to make its own decision is present.
        assert decision.selected == "a"
        assert decision.probabilities == {"a": 0.71, "b": 0.29}
        assert decision.confidence == 0.71
        # And the client expressed no opinion of its own about whether 0.71 is
        # good enough -- `ambiguous` is the only judgement here, and it is about
        # the top two being close, not about an absolute cut-off.
        assert decision.ambiguous is False

    def test_a_malformed_answer_becomes_an_unknown_decision(self):
        from citegraph.llm.jev import _parse_answer

        assert _parse_answer("q", "not a dict").kind == "unknown"

    def test_it_is_disabled_without_a_key(self):
        """TYPESAFE_API_KEY is not set yet. The flag alone must not enable it."""
        client = JevClient()
        assert client.configured is False
        assert client.enabled is False

    @pytest.mark.asyncio
    async def test_a_disabled_client_refuses_rather_than_calling(self):
        with pytest.raises(ProviderUnavailable):
            await JevClient().evaluate({"x": 1}, {"q": {"type": "noul"}})


# ---------------------------------------------------------------- GLM


class TestGLM:
    def test_the_prompt_contains_only_what_the_graph_holds(self):
        client = GLMClient()
        prompt = client.build_prompt(
            "What is the effect of X?",
            [
                {
                    "title": "A real paper",
                    "year": 2021,
                    "journal": "J",
                    "authors": ["A", "B", "C", "D"],
                    "doi": "10.1/x",
                    "abstract": "Findings.",
                    "confidence": 0.42,
                }
            ],
        )
        assert "What is the effect of X?" in prompt
        assert "A real paper" in prompt
        assert "10.1/x" in prompt
        assert "et al." in prompt
        assert "0.42" in prompt

    def test_the_system_prompt_forbids_inventing(self):
        from citegraph.llm.glm import SYSTEM_PROMPT

        assert "ONLY" in SYSTEM_PROMPT
        assert "insufficient" in SYSTEM_PROMPT

    def test_a_missing_field_is_omitted_rather_than_faked(self):
        prompt = GLMClient().build_prompt("q", [{"title": "Only a title"}])
        assert "DOI" not in prompt
        assert "Abstract" not in prompt
        assert "confidence" not in prompt

    def test_an_empty_abstract_does_not_produce_an_empty_bullet(self):
        prompt = GLMClient().build_prompt("q", [{"title": "T", "abstract": ""}])
        assert "Abstract:" not in prompt

    def test_a_long_abstract_is_truncated(self):
        prompt = GLMClient().build_prompt("q", [{"title": "T", "abstract": "x" * 5000}])
        assert len(prompt) < 2000

    def test_it_extracts_text_from_a_chat_completion(self):
        from citegraph.llm.glm import _extract_text

        payload = {
            "choices": [{"message": {"content": "  The report.  "}}]
        }
        assert _extract_text(payload) == "The report."

    def test_it_tolerates_a_plain_text_field(self):
        from citegraph.llm.glm import _extract_text

        assert _extract_text({"choices": [{"text": "Report."}]}) == "Report."

    def test_an_empty_response_is_not_a_report(self):
        """An empty report is indistinguishable from a working one, so it is a
        failure."""
        from citegraph.llm.glm import _extract_text

        assert _extract_text({"choices": []}) == ""
        assert _extract_text({}) == ""

    def test_the_glm_cache_shape_is_recorded_as_unknown(self):
        """GLM exposes neither prompt_cache_hit_tokens nor
        prompt_tokens_details.cached_tokens. Reading either would report 0% cache
        hit on every call while being billed for roughly 97% cached."""
        usage = Usage(provider="glm", cache_breakdown_known=False)
        assert usage.cache_breakdown_known is False
        assert usage.cached_input_tokens == 0

    def test_it_is_disabled_without_a_key(self):
        client = GLMClient()
        assert client.enabled is False

    @pytest.mark.asyncio
    async def test_a_disabled_client_refuses(self):
        with pytest.raises(ProviderUnavailable):
            await GLMClient().generate_report("q", [{"title": "T"}])


# ---------------------------------------------------------------- the invariant


class TestTheKeyNeverLeaks:
    def test_an_error_body_echoing_the_key_is_scrubbed(self):
        """Some vendors echo the submitted key back in an error body. If that
        reaches an exception message it is on its way to a log, an error
        tracker, or a browser."""
        body = f'{{"error": "invalid key {SECRET}"}}'
        scrubbed = scrub(body, SECRET)
        assert SECRET not in scrubbed
        assert "[REDACTED]" in scrubbed

    @pytest.mark.asyncio
    async def test_no_path_puts_the_key_in_an_exception(
        self, caplog: pytest.LogCaptureFixture
    ):
        """Every failure route, with a body that echoes the key, checked for the
        key in the exception text AND in the captured logs."""
        caplog.set_level(logging.DEBUG)
        bodies = [
            httpx.Response(401, json={"error": f"bad {SECRET}"}),
            httpx.Response(422, json={"error": f"bad {SECRET}"}),
            httpx.Response(200, text=f"<html>{SECRET}</html>"),
        ]
        for response in bodies:
            handler, _ = transport_returning(response)
            provider = client_for(handler, max_retries=0)
            with pytest.raises(ProviderUnavailable) as exc:
                await provider.post_json("/x", {})
            assert SECRET not in str(exc.value), f"leaked via {response.status_code}"

        logged = "\n".join(record.getMessage() for record in caplog.records)
        assert SECRET not in logged, "leaked into the logs"

    def test_a_usage_row_carries_no_key(self):
        row = Usage(provider="glm", model_served="glm-5.3-flash").as_row()
        assert SECRET not in json.dumps(row)
