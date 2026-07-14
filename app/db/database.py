"""SQLAlchemy engine, session factory and FastAPI dependency.

Defaults to MySQL (PyMySQL driver). SQLite is still supported via
DATABASE_URL for lightweight local runs and is used by the test suite.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    # Recycle connections before MySQL's default wait_timeout closes them
    pool_recycle=3600,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()