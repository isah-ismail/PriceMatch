"""SQLAlchemy engine / session wiring.

The schema itself is owned by the database team and lives in
``../database/migrations``. The ORM models in ``models.py`` mirror it; they do
not create tables in production. Tests create tables from the models on SQLite.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str | None = None, echo: bool | None = None):
    settings = get_settings()
    url = url or settings.database_url
    kwargs: dict = {"echo": settings.sql_echo if echo is None else echo, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        kwargs.update(connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return create_engine(url, **kwargs)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
