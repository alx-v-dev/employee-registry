from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.repository import calculate_age
from app.routes import router, templates


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Employee Registry", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
    templates.env.filters["age"] = calculate_age
    app.include_router(router)

    return app


app = create_app()
