import asyncio
import logging
from typing import Set

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages background task lifecycle for graceful shutdown."""

    def __init__(self):
        self._tasks: Set[asyncio.Task] = set()

    def register(self, task: asyncio.Task):
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def shutdown(self, timeout: float = 10.0, *, force_clear: bool = False):
        """Cancel and await all registered tasks with a bounded timeout.

        Uses ``asyncio.wait(pending, timeout=...)`` (not ``wait_for(gather(...))``)
        so a task that suppresses or delays ``CancelledError`` cannot block the
        shutdown beyond the configured timeout. Tasks that fail to terminate
        in time are logged as stragglers and either kept (default) or cleared
        (``force_clear=True``) so they don't leak across lifespan/test cycles.
        """
        if not self._tasks:
            return

        # Snapshot before cancelling so the done-callback can't mutate the set
        # while we're iterating / waiting on it.
        pending = [t for t in self._tasks if not t.done()]
        if not pending:
            self._tasks.clear()
            return

        logger.info("Shutting down TaskManager: waiting for %d tasks...", len(pending))

        for task in pending:
            task.cancel()

        done, still_pending = await asyncio.wait(pending, timeout=timeout)
        if still_pending:
            logger.warning(
                "%d tasks failed to shut down gracefully within %.1fs: %s",
                len(still_pending),
                timeout,
                [getattr(t, "get_name", lambda: repr(t))() for t in still_pending],
            )
        else:
            logger.info("All %d background tasks shut down successfully", len(done))

        if force_clear:
            # Final-shutdown path: drop everything so the manager doesn't retain
            # tasks bound to a torn-down loop.
            self._tasks.clear()
        else:
            # Drop completed tasks; keep stragglers so the caller can decide.
            self._tasks = {t for t in self._tasks if not t.done()}


# Global task manager instance
task_manager = TaskManager()
