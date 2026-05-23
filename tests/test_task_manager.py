"""Regression tests for TaskManager shutdown semantics.

Covers:
  - tasks that suppress CancelledError do NOT block shutdown beyond the timeout,
  - stragglers are logged and (optionally) cleared with force_clear=True,
  - shutdown is a no-op on an empty/already-finished task set.
"""

from __future__ import annotations

import asyncio
import pytest

from citegraph.utils.tasks import TaskManager

pytestmark = pytest.mark.asyncio


async def test_empty_shutdown_is_noop():
    tm = TaskManager()
    # Should not raise or hang
    await tm.shutdown(timeout=0.1)


async def test_completed_tasks_drained():
    tm = TaskManager()

    async def quick():
        return "done"

    t = asyncio.create_task(quick())
    tm.register(t)
    await t
    await tm.shutdown(timeout=0.5)
    assert tm._tasks == set()


async def test_cooperative_cancellation_finishes_before_timeout():
    tm = TaskManager()

    async def cooperative():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise

    t = asyncio.create_task(cooperative())
    tm.register(t)

    # Let the task start
    await asyncio.sleep(0.01)

    start = asyncio.get_event_loop().time()
    await tm.shutdown(timeout=1.0)
    elapsed = asyncio.get_event_loop().time() - start

    assert elapsed < 0.5, f"cooperative task should cancel quickly, took {elapsed:.2f}s"
    assert t.cancelled() or t.done()


async def test_uncooperative_task_does_not_hang_past_timeout():
    """A task that suppresses CancelledError must NOT block shutdown beyond
    the configured timeout. This is the key invariant fixed by switching
    from asyncio.wait_for(gather(...)) to asyncio.wait(pending, timeout=)."""
    tm = TaskManager()

    async def uncooperative():
        while True:
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                # Refuse to die — this used to hang shutdown forever.
                continue

    t = asyncio.create_task(uncooperative())
    tm.register(t)
    await asyncio.sleep(0.01)

    start = asyncio.get_event_loop().time()
    await tm.shutdown(timeout=0.3)
    elapsed = asyncio.get_event_loop().time() - start

    assert elapsed < 0.6, (
        f"shutdown took {elapsed:.2f}s but timeout was 0.3s — "
        f"uncooperative task is blocking shutdown"
    )

    # The straggler is preserved (not cleared by default)
    assert any(not t.done() for t in tm._tasks)

    # Clean up — actually cancel for real to avoid leaking into other tests
    t.cancel()
    try:
        await asyncio.wait_for(t, timeout=0.5)
    except (asyncio.CancelledError, asyncio.TimeoutError, BaseException):
        pass


async def test_force_clear_drops_stragglers():
    """force_clear=True must empty the task set even for stragglers, so the
    manager doesn't leak tasks bound to a torn-down loop across lifespan
    cycles or test invocations."""
    tm = TaskManager()

    async def uncooperative():
        while True:
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                continue

    t = asyncio.create_task(uncooperative())
    tm.register(t)
    await asyncio.sleep(0.01)

    await tm.shutdown(timeout=0.2, force_clear=True)
    assert tm._tasks == set(), "force_clear=True must empty _tasks"

    # Cleanup
    t.cancel()
    try:
        await asyncio.wait_for(t, timeout=0.5)
    except (asyncio.CancelledError, asyncio.TimeoutError, BaseException):
        pass
