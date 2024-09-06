import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from app.domain.entities.tasks import Task
from app.domain.sql.models import Task as TaskModel
from app.infrastructure.uow.base import BaseUnitOfWork
import queue


class ThreadTaskQueueManager:
    def __init__(self, uow: BaseUnitOfWork, max_concurrent_tasks: int = 2):
        self.queue = queue.Queue()
        self.max_concurrent_tasks = max_concurrent_tasks
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)
        self.uow = uow
        self.loop = asyncio.get_event_loop()
        threading.Thread(target=self._process_queue, daemon=True).start()

    async def add_task(self, task: Task):
        self.queue.put(task)

    def _process_queue(self):
        while True:
            if not self.queue.empty() and len(self.uow.cache) < 2:
                task = self.queue.get()
                self.uow.push_to_cache(task)
                self.executor.submit(self._run_task, task)
            time.sleep(0.2)

    def _run_task(self, task: Task):
        updated_task = task.run_task()

        self.uow.remove_task_from_cache(updated_task)
        self._update_task_in_db(updated_task)

    def _update_task_in_db(self, task: Task):
        future = asyncio.run_coroutine_threadsafe(self._async_update_task_in_db(task), self.loop)
        future.result()

    async def _async_update_task_in_db(self, task: Task) -> None:
        async with self.uow.transaction() as uow:
            uow.register_new(TaskModel(
                task_oid=task.oid,
                description=task.description,
                start_time=task.start_time,
                create_time=task.created_at,
                exec_time=task.exec_time,
                status=task.status
            )
            )

