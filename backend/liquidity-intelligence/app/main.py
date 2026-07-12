"""
FastAPI application entrypoint.
Mounts all routers, middleware, and startup/shutdown lifecycle hooks.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import connect_prisma, disconnect_prisma
from app.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    add_exception_handlers,
)
from app.api.v1.routes.snapshot import router as snapshot_router
from app.api.v1.routes.alerts import router as alerts_router
from app.api.v1.routes.users import router as users_router
from app.api.v1.routes.alert_advisory import router as advisory_router
from app.api.v1.routes.transactions import router as transactions_router
from app.api.v1.routes.cases import router as cases_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic."""
    configure_logging()

    # Connect Prisma client to Supabase
    await connect_prisma()

    # Load context calendar for the ContextEngine
    import os
    from app.engines.context_engine import load_calendar
    calendar_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "context_calendar.csv"
    )
    load_calendar(os.path.abspath(calendar_path))

    yield

    # Shutdown: disconnect Prisma client
    await disconnect_prisma()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "MFS Super-Agent AI Decision Support Platform. "
            "Advisory only — never executes financial transactions."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Custom middleware (order matters — added last = outermost = executes first)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # CORS must be outermost to handle error responses too
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    add_exception_handlers(app)

    # Routers
    prefix = settings.api_v1_prefix
    app.include_router(snapshot_router, prefix=prefix)
    app.include_router(alerts_router, prefix=prefix)
    app.include_router(users_router, prefix=prefix)
    app.include_router(advisory_router, prefix=prefix)
    app.include_router(transactions_router, prefix=prefix)
    app.include_router(cases_router, prefix=prefix)

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()
