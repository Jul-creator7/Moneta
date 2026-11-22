from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from .api import router
from .banking_api import router as banking_router
from .community_api import router as community_router
from .config import Settings
from .explore_api import router as explore_router
from .goal_api import router as goal_router
from .intelligence_api import router as intelligence_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    sqlite = settings.database_url.startswith("sqlite")
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if sqlite else {},
    )

    if sqlite:
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

    @asynccontextmanager
    async def lifespan(_app):
        yield
        engine.dispose()

    app = FastAPI(title="Tandem API", lifespan=lifespan)
    app.state.settings = settings
    app.state.sessions = sessionmaker(engine)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Transaction-Id"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError):
        # Validation errors can contain the original submitted password.
        fields = [
            {"field": str(item["loc"][-1]), "message": item["msg"]}
            for item in error.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": fields})

    app.include_router(router, prefix="/api")
    app.include_router(banking_router, prefix="/api")
    app.include_router(goal_router, prefix="/api")
    app.include_router(intelligence_router, prefix="/api")
    app.include_router(community_router, prefix="/api")
    app.include_router(explore_router, prefix="/api")
    return app
