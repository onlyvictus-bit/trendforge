"""Request-scoped, read-only SQLite snapshot over the existing research store.

All nested repository readers borrow this connection. Their close/context-manager
calls cannot commit or release the owner's transaction. Concurrent writers remain
independent; no connection is cached globally or shared across request threads.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from time import monotonic
from typing import Iterator, Literal, cast


class SnapshotExpired(TimeoutError):
    """The bounded snapshot read budget was exhausted."""


class _BorrowedConnection(sqlite3.Connection):
    def close(self) -> None:
        # Only read_snapshot's finally block owns this connection's lifetime.
        pass

    def commit(self) -> None:
        raise sqlite3.ProgrammingError("READ_ONLY_SNAPSHOT_COMMIT_FORBIDDEN")

    def rollback(self) -> None:
        raise sqlite3.ProgrammingError("READ_ONLY_SNAPSHOT_ROLLBACK_FORBIDDEN")

    def executescript(self, sql_script: str, /) -> sqlite3.Cursor:
        # sqlite3.executescript would implicitly release a pending transaction.
        raise sqlite3.ProgrammingError("READ_ONLY_SNAPSHOT_SCRIPT_FORBIDDEN")

    def __enter__(self) -> _BorrowedConnection:
        return self

    def __exit__(self, *args: object) -> Literal[False]:
        return False


_ACTIVE: ContextVar[tuple[Path, _BorrowedConnection, float] | None] = ContextVar(
    "trendforge_read_snapshot", default=None
)
_READ_PRAGMAS = frozenset({
    "table_info", "table_xinfo", "index_list", "index_info", "index_xinfo",
    "foreign_key_list", "database_list", "compile_options",
})


def _authorize(action: int, arg1: str | None, arg2: str | None,
               database: str | None, source: str | None) -> int:
    if action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
                  sqlite3.SQLITE_RECURSIVE}:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA:
        name = (arg1 or "").lower()
        if name in _READ_PRAGMAS or (
            arg2 is None and name in {"user_version", "schema_version", "data_version", "query_only"}
        ):
            return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def borrow_connection(path: Path) -> sqlite3.Connection | None:
    active = _ACTIVE.get()
    if active is None:
        return None
    db_path, conn, deadline = active
    if path.expanduser().resolve() != db_path:
        raise sqlite3.ProgrammingError("READ_ONLY_SNAPSHOT_DATABASE_MISMATCH")
    if monotonic() >= deadline:
        raise SnapshotExpired("WAIT_RESEARCH_SNAPSHOT_TIMEOUT")
    return conn


@contextmanager
def read_snapshot(path: Path, *, budget_seconds: float = 30.0) -> Iterator[None]:
    """Pin one existing database view without initialization or write access."""
    if budget_seconds <= 0:
        raise ValueError("snapshot budget must be positive")
    if _ACTIVE.get() is not None:
        borrow_connection(path)  # Reject cross-database nesting.
        yield
        return
    db_path = path.expanduser().resolve()
    conn = cast(_BorrowedConnection, sqlite3.connect(
        db_path.as_uri() + "?mode=ro", uri=True, timeout=5,
        isolation_level=None, factory=_BorrowedConnection,
    ))
    token = None
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        # BEGIN alone is deferred: the first SELECT establishes the WAL view.
        conn.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
        deadline = monotonic() + budget_seconds
        conn.set_authorizer(_authorize)
        conn.set_progress_handler(lambda: int(monotonic() >= deadline), 10000)
        token = _ACTIVE.set((db_path, conn, deadline))
        yield
        if monotonic() >= deadline:
            raise SnapshotExpired("WAIT_RESEARCH_SNAPSHOT_TIMEOUT")
    finally:
        if token is not None:
            _ACTIVE.reset(token)
        conn.set_progress_handler(None, 0)
        conn.set_authorizer(None)
        sqlite3.Connection.close(conn)
