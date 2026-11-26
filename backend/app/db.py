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
        # Schema migration check for SQLite
        if engine.url.drivername.startswith("sqlite"):
            res = conn.execute(text("PRAGMA table_info(users)"))
            cols = {row[1] for row in res.fetchall()}
            if cols:
                if "zone" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN zone VARCHAR NOT NULL DEFAULT 'SWR'"))
                if "division" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN division VARCHAR NOT NULL DEFAULT 'Southern Division'"))
                if "control_area" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN control_area VARCHAR"))
                if "assigned_stations" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN assigned_stations JSON"))
                if "assigned_sections" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN assigned_sections JSON"))
                if "active" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN active BOOLEAN NOT NULL DEFAULT 1"))
                if "token_version" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 1"))
                if "last_login_at" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))
                if "password_changed_at" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN password_changed_at DATETIME"))

            res_dec = conn.execute(text("PRAGMA table_info(decisions)"))
            dec_cols = {row[1] for row in res_dec.fetchall()}
            if dec_cols:
                if "data_quality" not in dec_cols:
                    conn.execute(text("ALTER TABLE decisions ADD COLUMN data_quality JSON"))
                if "three_way_comparison" not in dec_cols:
                    conn.execute(text("ALTER TABLE decisions ADD COLUMN three_way_comparison JSON"))

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
