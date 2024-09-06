from typing import Dict, Type

from app.infrastructure.repositories.base import BaseTasksRepository
from app.infrastructure.uow.base import ModelT, UoWModel, BaseUnitOfWork


class UnitOfWork(BaseUnitOfWork):
    def __init__(self):
        self.dirty: Dict[int, ModelT] = {}
        self.new: Dict[int, ModelT] = {}
        self.deleted: Dict[int, ModelT] = {}
        self.repositories: Dict[Type[ModelT], BaseTasksRepository] = {}

    def register_repository(self, model_class: Type[ModelT], repository: BaseTasksRepository) -> None:
        self.repositories[model_class] = repository

    def register_dirty(self, model: ModelT) -> None:
        model_id = id(model)
        if model_id not in self.new:
            self.dirty[model_id] = model

    def register_deleted(self, model: ModelT) -> None:
        if isinstance(model, UoWModel):
            model = model._model
        model_id = id(model)
        self.new.pop(model_id, None)
        self.dirty.pop(model_id, None)
        self.deleted[model_id] = model

    def register_new(self, model: ModelT) -> 'UoWModel[ModelT]':
        model_id = id(model)
        self.new[model_id] = model
        return UoWModel(model, self)

    async def commit(self) -> None:
        try:
            for model in self.new.values():
                await self.repositories[type(model)].add(model)
            for model in self.dirty.values():
                await self.repositories[type(model)].update(model)
            for model in self.deleted.values():
                await self.repositories[type(model)].remove(model)
        except Exception:
            await self.rollback()
            raise
        finally:
            self.clear()

    async def rollback(self) -> None:
        self.clear()

    def clear(self) -> None:
        self.dirty.clear()
        self.new.clear()
        self.deleted.clear()

    def repository(self, model_class: Type[ModelT]) -> BaseTasksRepository:
        return self.repositories[model_class]
