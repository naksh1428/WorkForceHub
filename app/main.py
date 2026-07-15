"""Application entrypoint.

Run locally:
    uvicorn app.main:app --reload
Interactive docs: http://localhost:8000/docs
"""
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from app.api import auth, departments, employees
from app.core.config import settings
from app.db.cache import get_redis
from app.db.database import Base, engine

logger = logging.getLogger(__name__)
MAX_DB_RETRIES = 10


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create database tables on startup, retrying while MySQL boots.

    MySQL in Docker can take a few seconds to accept connections after the
    container starts, so a transient `OperationalError` is retried instead
    of crashing the app immediately.
    """
    for attempt in range(1, MAX_DB_RETRIES + 1):
        try:
            Base.metadata.create_all(bind=engine)
            break
        except OperationalError:
            if attempt == MAX_DB_RETRIES:
                raise
            logger.warning(
                "Database not ready (attempt %s/%s), retrying in 2s...",
                attempt,
                MAX_DB_RETRIES,
            )
            time.sleep(2)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Employee management REST API built with FastAPI, SQLAlchemy and Redis "
        "caching. JWT-secured CRUD for employees and departments with "
        "pagination, filtering and cache invalidation."
    ),
    lifespan=lifespan,
)
app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(departments.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness probe: reports API and Redis status."""
    redis_status = "up" if get_redis() is not None else "down"
    return {"api": "up", "redis": redis_status}