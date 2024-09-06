from contextlib import asynccontextmanager

from app.services.init import init_container


@asynccontextmanager
async def lifespan(*_):
    init_container()
    yield
    # здесь можно сделать что-то при завершении работы приложения
