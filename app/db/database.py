"""Sets up the connection to the database."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    # Open a fresh connection every hour, before MySQL closes idle ones
    pool_recycle=3600,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Every database table class builds on this."""


def get_db() -> Generator[Session, None, None]:
    """Open a database connection for one request and close it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
