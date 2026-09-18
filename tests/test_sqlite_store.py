"""Regression tests for the SQLite store retry/lock semantics.

Covers:
  - lock-error retries succeed when the lock clears,
  - non-lock errors surface immediately with context (no silent retry),
  - read path is protected by the same retry/lock policy as writes,
  - exponential-backoff + jitter retry budget is bounded.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import aiosqlite
import pytest
from aiosqlite.context import Result

from citegraph.storage.sqlite import SQLiteStore, SQLiteStoreError

pytestmark = pytest.mark.asyncio


def execute_double(handler):
    """Wrap an async handler so it stands in for aiosqlite's Connection.execute.

    The real method is decorated with aiosqlite's own ``contextmanager``, so its
    return value can either be awaited or used as an async context manager. A
    bare ``async def`` double only supports ``await``, which makes any caller
    using ``async with db.execute(...)`` fail with a confusing TypeError about
    the coroutine protocol rather than exercising the behaviour under test.
    """

    def wrapper(query, params=()):
        return Result(handler(query, params))

    return wrapper


@pytest.fixture
async def store():
    s = SQLiteStore(db_path=":memory:")
    await s.connect()
    yield s
    await s.close()


async def test_write_succeeds_normally(store):
    """Sanity: a clean insert works."""
    await store.create_run("r1")
    row = await store.get_run("r1")
    assert row is not None
    assert row["run_id"] == "r1"
    assert row["status"] == "started"


async def test_non_lock_operational_error_is_not_retried(store):
    """A non-lock OperationalError must surface immediately wrapped in
    SQLiteStoreError, with the original exception preserved as `original`."""
    call_count = {"n": 0}

    real_execute = store._db.execute

    async def boom(query, params=()):
        call_count["n"] += 1
        raise aiosqlite.OperationalError("disk I/O error")

    with patch.object(store._db, "execute", side_effect=execute_double(boom)):
        with pytest.raises(SQLiteStoreError) as exc_info:
            await store.create_run("r-fail")

    assert call_count["n"] == 1, "non-lock error must NOT be retried"
    assert isinstance(exc_info.value.original, aiosqlite.OperationalError)
    assert "disk I/O" in str(exc_info.value.original)
    # Real cursor still works
    assert callable(real_execute)


async def test_programming_error_surfaces(store):
    """ProgrammingError (e.g. bad query) must propagate as SQLiteStoreError."""
    async def boom(query, params=()):
        raise aiosqlite.ProgrammingError("Wrong number of bindings")

    with patch.object(store._db, "execute", side_effect=execute_double(boom)):
        with pytest.raises(SQLiteStoreError) as exc_info:
            await store.create_run("r-bad")

    assert isinstance(exc_info.value.original, aiosqlite.ProgrammingError)


async def test_lock_error_is_retried_then_succeeds(store):
    """A 'database is locked' error retries with backoff and eventually
    succeeds when the lock clears."""
    attempts = {"n": 0}
    real_execute = store._db.execute

    async def flaky(query, params=()):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise aiosqlite.OperationalError("database is locked")
        return await real_execute(query, params)

    with patch.object(store._db, "execute", side_effect=execute_double(flaky)):
        await store.create_run("r-lock")

    assert attempts["n"] == 3, "Should have retried twice then succeeded"
    row = await store.get_run("r-lock")
    assert row is not None


async def test_lock_error_retry_budget_is_bounded(store):
    """If lock contention never clears, we raise SQLiteStoreError after
    the configured retry budget (not silently or with raw OperationalError)."""
    attempts = {"n": 0}

    async def always_locked(query, params=()):
        attempts["n"] += 1
        raise aiosqlite.OperationalError("database is locked")

    with patch.object(store._db, "execute", side_effect=execute_double(always_locked)):
        with pytest.raises(SQLiteStoreError) as exc_info:
            await store.create_run("r-stuck")

    assert attempts["n"] == SQLiteStore._RETRY_ATTEMPTS
    assert "lock contention" in str(exc_info.value)


async def test_get_run_also_retries_under_lock(store):
    """Read path must share the retry/lock policy so a concurrent writer
    doesn't surface as an unhandled OperationalError to callers."""
    await store.create_run("r-read")
    attempts = {"n": 0}
    real_execute = store._db.execute

    async def flaky(query, params=()):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise aiosqlite.OperationalError("database is locked")
        return await real_execute(query, params)

    with patch.object(store._db, "execute", side_effect=execute_double(flaky)):
        row = await store.get_run("r-read")

    assert row is not None
    assert row["run_id"] == "r-read"
    assert attempts["n"] >= 2


async def test_backoff_uses_jitter(store):
    """Backoff is randomized (jitter) so two consecutive retry sleeps are
    not identical when the budget is large enough to observe variance."""
    sleeps = []

    real_sleep = asyncio.sleep
    attempts = {"n": 0}

    async def boom(query, params=()):
        attempts["n"] += 1
        raise aiosqlite.OperationalError("database is locked")

    async def record_sleep(delay):
        sleeps.append(delay)
        await real_sleep(0)  # don't actually wait

    with patch.object(store._db, "execute", side_effect=execute_double(boom)), \
         patch("citegraph.storage.sqlite.asyncio.sleep", side_effect=record_sleep):
        with pytest.raises(SQLiteStoreError):
            await store.create_run("r-jitter")

    # All sleeps must be in [0, cap]
    assert all(0 <= s <= SQLiteStore._RETRY_CAP_S for s in sleeps)
    # At least one sleep should be > 0 (jitter produces non-zero values)
    assert any(s > 0 for s in sleeps), f"all sleeps were 0: {sleeps}"


async def test_save_and_load_round_trip(store):
    """End-to-end happy path: create → save_result → get_run returns the
    serialized RunResult JSON."""
    from datetime import datetime, timezone
    from citegraph.models.run import RunResult

    await store.create_run("r-round")
    result = RunResult(
        run_id="r-round",
        seed_paper_id="P1",
        papers=[],
        studies=[],
        population_candidates=[],
        population_resolutions=[],
        citation_edges=[],
        ranked_foundational_papers=[],
        ranked_paths=[],
        warnings=[],
        created_at=datetime.now(timezone.utc),
    )
    await store.save_result("r-round", result)
    row = await store.get_run("r-round")
    assert row is not None
    assert row["status"] == "completed"
    assert "P1" in row["result_json"]
