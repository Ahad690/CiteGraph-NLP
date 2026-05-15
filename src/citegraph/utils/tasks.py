import asyncio
import logging
import anyio
from typing import Set, Awaitable

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

        logger.info(f"Shutting down TaskManager: waiting for {len(self._tasks)} tasks...")
        
        # Signal cancellation
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for completion
        async with anyio.move_on_after(timeout):
            await asyncio.gather(*self._tasks, return_exceptions=True)
            
        remaining = [t for t in self._tasks if not t.done()]
        if remaining:
            logger.warning(f"{len(remaining)} tasks failed to shut down gracefully within {timeout}s")
        else:
            logger.info("All background tasks shut down successfully")
            
        self._tasks.clear()

# Global task manager instance
task_manager = TaskManager()
