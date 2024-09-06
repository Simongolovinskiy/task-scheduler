from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from punq import Container

from app.application.tasks.schemas import (
    CreateTaskRequestSchema,
    CreateTaskResponseSchema,
    TaskSchema
)

from app.application.api.schemas import ErrorSchema
from app.domain.exceptions.base import ApplicationException
from app.domain.sql.models import Task
from app.infrastructure.repositories.base import BaseTasksRepository
from app.infrastructure.uow.base import BaseUnitOfWork
from app.services.commands.tasks import CreateTaskCommand
from app.services.init import init_container
from app.services.mediator.base import Mediator


# from app.services.init import init_container
# from app.services.mediator.base import Mediator


router = APIRouter(tags=["Tasks Scheduler"])


@router.post(
    "/",
    response_model=CreateTaskResponseSchema,
    status_code=status.HTTP_201_CREATED,
    description="Creating a new unique tasks instance",
    responses={
        status.HTTP_201_CREATED: {"model": CreateTaskRequestSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def create_task_handler(
    schema: CreateTaskRequestSchema,
    container: Container = Depends(init_container),
) -> CreateTaskResponseSchema:
    """Creating new task instance."""
    mediator: Mediator = container.resolve(Mediator)
    try:
        task, *_ = await mediator.handle_command(CreateTaskCommand(description=schema.description))
    except ApplicationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.message},
        )
    return CreateTaskResponseSchema.from_entity(task)


@router.get(
    "/{task_oid}/",
    status_code=status.HTTP_200_OK,
    description="Getting task by oid.",
    responses={
        status.HTTP_200_OK: {"model": TaskSchema},
        status.HTTP_404_NOT_FOUND: {"model": ErrorSchema},
    },
)
async def fetch_task_handler(
    task_oid: str,
    container: Container = Depends(init_container),
) -> TaskSchema:
    uow = container.resolve(BaseUnitOfWork)
    task = uow.get_task_from_cache(task_oid)
    if task:
        return TaskSchema(
            task_oid=task.oid,
            description=task.description,
            status=task.status,
            start_time=task.start_time,
            exec_time=task.exec_time,
            create_time=task.created_at
        )

    try:
        async with uow.transaction() as uow:
            tasks_repo: BaseTasksRepository = uow.repository(Task)
            current_task = await tasks_repo.get(task_oid)
            return TaskSchema(**current_task)
    except ApplicationException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message},
        )
