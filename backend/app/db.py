"""Database engine, session handling and append-only protections."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, future=True)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):  # pragma: no cover
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables and append-only triggers."""
    from . import models  # noqa: F401  (register mappings)

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS audit_events_no_update
                BEFORE UPDATE ON audit_events
                BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
                BEFORE DELETE ON audit_events
                BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS decisions_no_update
                BEFORE UPDATE ON decisions
                BEGIN SELECT RAISE(ABORT, 'decisions is append-only'); END;
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS decisions_no_delete
                BEFORE DELETE ON decisions
                BEGIN SELECT RAISE(ABORT, 'decisions is append-only'); END;
                """
            )
        )
        # The chain head must be updatable by appends, but never deleted.
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS audit_chain_head_no_delete
                BEFORE DELETE ON audit_chain_head
                BEGIN SELECT RAISE(ABORT, 'audit_chain_head is append-only'); END;
                """
            )
        )
