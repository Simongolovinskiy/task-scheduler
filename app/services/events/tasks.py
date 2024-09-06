from dataclasses import dataclass

from app.domain.events.tasks import NewTaskCreatedEvent
from app.services.events.manager import ThreadTaskQueueManager


@dataclass
class NewTaskCreatedEventHandler:
    manager: ThreadTaskQueueManager

    async def handle(self, event: NewTaskCreatedEvent) -> None:
        await self.manager.add_task(event.task)
