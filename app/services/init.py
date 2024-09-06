from functools import lru_cache

from punq import Container, Scope

from app.common.factory import session_factory
from app.domain.events.tasks import NewTaskCreatedEvent
from app.domain.sql.models import Task
from app.infrastructure.repositories.sqlalchemy_repository import SQLAlchemyTasksRepository
from app.infrastructure.uow.base import BaseUnitOfWork
from app.infrastructure.uow.sqlalchemy_uow import SQLAlchemyUnitOfWork
from app.services.commands.tasks import (
    CreateTaskCommand,
    CreateTaskCommandHandler,
)
from app.services.events.manager import ThreadTaskQueueManager
from app.services.events.tasks import NewTaskCreatedEventHandler
from app.services.mediator.base import Mediator
from app.services.mediator.event import EventMediator

from app.settings.conf import Config


DOCKER_SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@postgres_db:5432/develop"
SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:8087/develop"


@lru_cache(1)
def init_container() -> Container:
    return _init_container()


def _init_container() -> Container:
    container = Container()
    container.register(Config, instance=Config(), scope=Scope.singleton)
    container.register(CreateTaskCommandHandler)

    def create_sqlalchemy_uow():
        session = session_factory(DOCKER_SQLALCHEMY_DATABASE_URL)
        uow = SQLAlchemyUnitOfWork(session)
        task_repo = SQLAlchemyTasksRepository(session, Task)
        uow.register_repository(Task, task_repo)
        return uow

    container.register(BaseUnitOfWork, factory=create_sqlalchemy_uow, scope=Scope.singleton)
    uow = container.resolve(BaseUnitOfWork)
    container.register(ThreadTaskQueueManager, instance=ThreadTaskQueueManager(uow), scope=Scope.singleton)

    def init_mediator() -> Mediator:
        mediator = Mediator()
        create_task_handler = CreateTaskCommandHandler(
            _mediator=mediator,
        )

        new_task_created_event_handler = NewTaskCreatedEventHandler(
            manager=container.resolve(ThreadTaskQueueManager)
        )
        mediator.register_event(NewTaskCreatedEvent, [new_task_created_event_handler])
        mediator.register_command(CreateTaskCommand, [create_task_handler])
        return mediator

    container.register(Mediator, factory=init_mediator)
    container.register(EventMediator, factory=init_mediator)

    return container
