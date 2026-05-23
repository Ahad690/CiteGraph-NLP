import asyncio
import logging
from typing import Set

logger = logging.getLogger(__name__)

class TaskManager:
    """ Manages background task lifecycle for graceful shutdown. """
    def __init__(self):
        self._tasks: Set[asyncio.Task] = set()

    def register(self, task: asyncio.Task):
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def shutdown(self, timeout: float = 10.0):
        if not self._tasks:
            return

        # Snapshot the live tasks so the done-callback can't mutate the set
        # while we're iterating / gathering it.
        pending = [t for t in self._tasks if not t.done()]
        if not pending:
            self._tasks.clear()
            return

        logger.info(f"Shutting down TaskManager: waiting for {len(pending)} tasks...")

        for task in pending:
            task.cancel()

        try:
            await asyncio.wait_for(
                asyncio.gather(*pending, return_exceptions=True),
                timeout=timeout,
            )
            logger.info("All background tasks shut down successfully")
        except asyncio.TimeoutError:
            remaining = [t for t in pending if not t.done()]
            logger.warning(
                f"{len(remaining)} tasks failed to shut down gracefully within {timeout}s"
            )

        # Drop any tasks that have actually completed; keep stragglers so the
        # caller can decide what to do next.
        self._tasks = {t for t in self._tasks if not t.done()}

# Global task manager instance
task_manager = TaskManager()
