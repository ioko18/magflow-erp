"""Background task service for handling heavy operations."""

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class BackgroundTask:
    """Represents a background task."""

    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: str | None = None
    priority: int = 1  # Higher number = higher priority

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "priority": self.priority,
        }


class BackgroundTaskService:
    """Service for managing background tasks."""

    def __init__(self, max_concurrent_tasks: int = 5):
        """Initialize the background task service.

        Args:
            max_concurrent_tasks: Maximum number of tasks to run concurrently

        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tasks: dict[str, BackgroundTask] = {}
        self.running_tasks: dict[str, asyncio.Task] = {}
        self._task_queue: list[BackgroundTask] = []
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._running = False
        self._task_lock = asyncio.Lock()

    async def start(self):
        """Start the background task service."""
        self._running = True
        logger.info("Background task service started")

        # Start the task processor
        asyncio.create_task(self._process_tasks())

    async def stop(self):
        """Stop the background task service."""
        self._running = False

        # Cancel all running tasks
        for task_id in list(self.running_tasks.keys()):
            await self.cancel_task(task_id)

        logger.info("Background task service stopped")

    async def add_task(
        self,
        name: str,
        func: Callable,
        priority: int = 1,
        *args,
        **kwargs,
    ) -> str:
        """Add a new task to the queue.

        Args:
            name: Task name for identification
            func: Function to execute
            priority: Task priority (higher = more important)
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function

        Returns:
            Task ID

        """
        task_id = str(uuid4())
        task = BackgroundTask(
            id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
        )

        async with self._task_lock:
            self.tasks[task_id] = task
            # Insert task in priority order (higher priority first)
            self._task_queue.append(task)
            self._task_queue.sort(key=lambda t: t.priority, reverse=True)

        logger.info(f"Added background task: {name} (ID: {task_id})")
        return task_id

    async def get_task(self, task_id: str) -> BackgroundTask | None:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task object or None if not found

        """
        return self.tasks.get(task_id)

    async def get_all_tasks(self) -> list[BackgroundTask]:
        """Get all tasks.

        Returns:
            List of all tasks

        """
        return list(self.tasks.values())

    async def get_pending_tasks(self) -> list[BackgroundTask]:
        """Get all pending tasks.

        Returns:
            List of pending tasks

        """
        return [task for task in self.tasks.values() if task.status == "pending"]

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task.

        Args:
            task_id: Task ID

        Returns:
            True if task was cancelled, False if not found

        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status == "running":
            running_task = self.running_tasks.get(task_id)
            if running_task and not running_task.done():
                running_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await running_task

        task.status = "cancelled"
        logger.info(f"Cancelled task: {task.name} (ID: {task_id})")
        return True

    async def _process_tasks(self):
        """Process tasks in the queue."""
        while self._running:
            try:
                # Get next task from queue
                async with self._task_lock:
                    if not self._task_queue:
                        await asyncio.sleep(1)
                        continue

                    task = self._task_queue.pop(0)

                # Skip if task is no longer pending
                if task.status != "pending":
                    continue

                # Acquire semaphore to limit concurrent tasks
                async with self._semaphore:
                    await self._execute_task(task)

            except Exception as e:
                logger.error(f"Error processing tasks: {e!s}")
                await asyncio.sleep(5)  # Wait before retrying

    async def _execute_task(self, task: BackgroundTask):
        """Execute a single task."""
        logger.info(f"Starting task: {task.name} (ID: {task.id})")

        # Update task status
        task.status = "running"
        self.running_tasks[task.id] = asyncio.current_task()

        try:
            # Execute the task
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                # Run sync function in thread pool using the current event loop
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    task.func,
                    *task.args,
                    **task.kwargs,
                )

            task.status = "completed"
            task.result = result
            logger.info(f"Completed task: {task.name} (ID: {task.id})")

        except asyncio.CancelledError:
            task.status = "cancelled"
            logger.info(f"Cancelled task: {task.name} (ID: {task.id})")
            raise

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            logger.error(f"Failed task: {task.name} (ID: {task.id}): {e!s}")

        finally:
            # Clean up running tasks
            self.running_tasks.pop(task.id, None)

    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed/failed tasks.

        Args:
            max_age_hours: Maximum age of tasks to keep

        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        async with self._task_lock:
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if task.status in ["completed", "failed", "cancelled"]:
                    if task.created_at < cutoff_time:
                        tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                del self.tasks[task_id]

        logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")


# Global background task service instance
background_task_service = BackgroundTaskService()
