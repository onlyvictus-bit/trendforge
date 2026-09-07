"""A single real SQLite view must survive concurrent commits and nested readers."""
from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from trendforge_api import storage
from trendforge_api.market_data_store import MarketDataStore
from trendforge_api.read_snapshot import borrow_connection, read_snapshot


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = tmp_path / "snapshot.db"
    monkeypatch.setattr(storage, "DB_PATH", path)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE generations (value TEXT)")
    conn.execute("INSERT INTO generations VALUES ('old')")
    conn.commit()
    conn.close()
    return path


def test_pinned_view_across_both_store_factories_and_concurrent_writer(database, tmp_path):
    market = MarketDataStore(root=tmp_path, db_path=database)
    with read_snapshot(database):
        first = storage.connect()
        assert first.execute("SELECT value FROM generations").fetchone()[0] == "old"
        first.close()  # A nested helper must not end the outer read transaction.

        def writer():
            with sqlite3.connect(database) as conn:
                conn.execute("UPDATE generations SET value='new'")

        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(writer).result(timeout=5)
        with market._connect() as second:
            assert second.execute("SELECT value FROM generations").fetchone()[0] == "old"
        assert storage.connect().execute("SELECT value FROM generations").fetchone()[0] == "old"
    assert borrow_connection(database) is None
    with read_snapshot(database):
        assert storage.connect().execute("SELECT value FROM generations").fetchone()[0] == "new"


@pytest.mark.parametrize("sql", [
    "UPDATE generations SET value='bad'", "DELETE FROM generations", "DROP TABLE generations",
    "COMMIT", "ROLLBACK", "PRAGMA query_only=OFF", "ATTACH ':memory:' AS extra",
])
def test_cannot_write_or_end_transaction(database, sql):
    with read_snapshot(database):
        with pytest.raises(sqlite3.DatabaseError):
            storage.connect().execute(sql)
        assert storage.connect().execute("SELECT value FROM generations").fetchone()[0] == "old"


def test_helpers_cannot_commit_rollback_or_run_scripts(database):
    with read_snapshot(database):
        for operation in [lambda c: c.commit(), lambda c: c.rollback(),
                          lambda c: c.executescript("SELECT 1;")]:
            with pytest.raises(sqlite3.DatabaseError):
                operation(storage.connect())


def test_no_schema_initialization_and_cleanup_after_error(database, monkeypatch):
    monkeypatch.setattr(storage, "_initialize_db", lambda: pytest.fail("snapshot tried to migrate"))
    with pytest.raises(ValueError, match="test error"):
        with read_snapshot(database):
            storage.init_db()
            with read_snapshot(database):
                assert storage.connect().in_transaction
            raise ValueError("test error")
    assert borrow_connection(database) is None


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        with read_snapshot(path):
            pytest.fail("missing database was opened")
    assert not path.exists()


def test_cross_database_read_is_rejected(database, tmp_path):
    with read_snapshot(database):
        with pytest.raises(sqlite3.DatabaseError):
            borrow_connection(tmp_path / "other.db")


def test_deadline_releases_snapshot_and_next_request_can_read(database, monkeypatch):
    import trendforge_api.read_snapshot as module
    clock = [0.0]
    monkeypatch.setattr(module, "monotonic", lambda: clock[0])
    with pytest.raises(module.SnapshotExpired, match="WAIT_RESEARCH_SNAPSHOT_TIMEOUT"):
        with read_snapshot(database, budget_seconds=1):
            clock[0] = 2.0
            storage.connect()
    assert borrow_connection(database) is None
    with read_snapshot(database):
        assert storage.connect().execute("SELECT value FROM generations").fetchone()[0] == "old"