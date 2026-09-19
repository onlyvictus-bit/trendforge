from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from trendforge_api.s8_retention import (
    evidence_roots_from_bundle,
    resolve_market_db_path,
)

CASH_HASH = "a" * 64
INDEX_HASH = "b" * 64


def _bundle(*records):
    return SimpleNamespace(
        collector_run_id="collector-orchestration-id",
        bundle_id="r1-bundle-exact",
        bundle_hash="r1-hash-exact",
        source_records=records,
    )


def _record(source_key: str, digest: str | None):
    return SimpleNamespace(source_key=source_key, last_good_hash=digest)


def test_roots_use_immutable_r1_hashes_not_orchestration_run_id() -> None:
    roots = evidence_roots_from_bundle(
        _bundle(
            _record("nse_bhavcopy_eod", CASH_HASH),
            _record("nse_index_close_eod", INDEX_HASH),
        )
    )

    assert [(root.role, root.content_hash, root.run_id) for root in roots] == [
        ("R1_SOURCE_NSE_BHAVCOPY_EOD", CASH_HASH, None),
        ("R1_SOURCE_NSE_INDEX_CLOSE_EOD", INDEX_HASH, None),
    ]


def test_missing_cash_object_root_fails_closed() -> None:
    with pytest.raises(
        ValueError, match="WAIT_RHIST03_CASH_EVIDENCE_ROOT_REQUIRED"
    ):
        evidence_roots_from_bundle(
            _bundle(_record("nse_index_close_eod", INDEX_HASH))
        )


def test_invalid_r1_hash_fails_closed() -> None:
    with pytest.raises(ValueError, match="WAIT_RHIST03_INVALID_EVIDENCE_HASH"):
        evidence_roots_from_bundle(
            _bundle(_record("nse_bhavcopy_eod", "not-a-hash"))
        )


def test_market_db_resolution_requires_every_exact_content_root(
    tmp_path: Path,
) -> None:
    market_db = tmp_path / "market.db"
    with sqlite3.connect(market_db) as conn:
        conn.execute(
            "CREATE TABLE market_data_objects (content_hash TEXT PRIMARY KEY)"
        )
        conn.executemany(
            "INSERT INTO market_data_objects(content_hash) VALUES (?)",
            [(CASH_HASH,), (INDEX_HASH,)],
        )
        conn.commit()

    roots = evidence_roots_from_bundle(
        _bundle(
            _record("nse_bhavcopy_eod", CASH_HASH),
            _record("nse_index_close_eod", INDEX_HASH),
        )
    )
    resolved = resolve_market_db_path(
        research_db_path=tmp_path / "research.db",
        evidence_roots=roots,
        explicit=market_db,
    )
    assert resolved == market_db.resolve(strict=False)


def test_market_db_resolution_refuses_partial_root_set(tmp_path: Path) -> None:
    market_db = tmp_path / "market.db"
    with sqlite3.connect(market_db) as conn:
        conn.execute(
            "CREATE TABLE market_data_objects (content_hash TEXT PRIMARY KEY)"
        )
        conn.execute(
            "INSERT INTO market_data_objects(content_hash) VALUES (?)", (CASH_HASH,)
        )
        conn.commit()

    roots = evidence_roots_from_bundle(
        _bundle(
            _record("nse_bhavcopy_eod", CASH_HASH),
            _record("nse_index_close_eod", INDEX_HASH),
        )
    )
    with pytest.raises(RuntimeError, match="WAIT_RHIST03_MARKET_LINEAGE_UNBOUND"):
        resolve_market_db_path(
            research_db_path=tmp_path / "research.db",
            evidence_roots=roots,
            explicit=market_db,
        )
