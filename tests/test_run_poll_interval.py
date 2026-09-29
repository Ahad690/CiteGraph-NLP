"""The poll interval the server asks for.

AnswerThis returns `retry_after_ms` with its job state and the client obeys it.
CiteGraph previously hardcoded 2 seconds in `useRun.ts`, so a slow run was polled
90 times a minute whether the server was idle or overloaded.

These assert the backend half. The client half is covered by
`frontend/src/lib/runNormalization.test.ts` and the `serverPollMs` function in
`useRun.ts`, which clamps anything implausible back to the default.
"""
from __future__ import annotations

from citegraph.api.routes import RunStatus, _retry_after_ms


class TestRetryAfter:
    def test_a_running_run_uses_the_existing_default(self):
        """2s is what the client used unconditionally before, so nothing changes
        for the common case and the change is purely additive."""
        assert _retry_after_ms("running") == 2000

    def test_a_just_started_run_is_backed_off(self):
        """A run that has barely begun is the least likely to be ready, and the
        one most wasteful to poll hard."""
        assert _retry_after_ms("started") == 4000

    def test_a_terminal_run_returns_soon(self):
        """The client is about to stop regardless. This exists so a client that
        asks once more is not made to wait on an answer it already has."""
        assert _retry_after_ms("completed") == 1000
        assert _retry_after_ms("failed") == 1000

    def test_every_status_returns_a_positive_interval(self):
        """A zero or negative interval would become a request loop on the client."""
        for s in ("started", "running", "completed", "failed", "unknown"):
            assert _retry_after_ms(s) > 0, s


class TestRunStatusCarriesIt:
    def test_the_field_is_present_with_the_default(self):
        status = RunStatus(run_id="r1", status="running")
        assert status.retry_after_ms == 2000

    def test_an_explicit_value_is_kept(self):
        status = RunStatus(run_id="r1", status="running", retry_after_ms=5000)
        assert status.retry_after_ms == 5000

    def test_it_survives_serialisation(self):
        """The field is only useful if it reaches the client."""
        payload = RunStatus(run_id="r1", status="running", retry_after_ms=4000).model_dump()
        assert payload["retry_after_ms"] == 4000
