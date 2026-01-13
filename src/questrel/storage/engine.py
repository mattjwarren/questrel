"""Async engine/session helpers.

SQLite is the initial backend (aiosqlite). Postgres can be adopted later by
switching to `postgresql+asyncpg://...` without changing repository code.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


def create_engine(db_url: str, *, echo: bool = False) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    For SQLite we also apply pragmas to enforce foreign keys.
    """

    kwargs = {
        "echo": echo,
        "future": True,
    }

    # SQLite: avoid long-lived pooled connections which can amplify locking.
    if db_url.startswith("sqlite+"):
        kwargs["poolclass"] = NullPool
        kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_async_engine(db_url, **kwargs)

    if db_url.startswith("sqlite+"):
        _install_sqlite_pragmas(engine)

    return engine


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope(session_maker: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """Context manager for a unit-of-work session."""

    async with session_maker() as session:
        async with session.begin():
            yield session


def _install_sqlite_pragmas(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
