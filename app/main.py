from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR, get_settings
from app.repository import calculate_age
from app.routes import router, templates


def create_app() -> FastAPI:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Employee Registry")
    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
    app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
    templates.env.filters["age"] = calculate_age
    app.include_router(router)

    return app


app = create_app()
