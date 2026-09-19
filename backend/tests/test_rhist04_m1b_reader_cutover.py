"""R-HIST-04 M1B — exact-H1 reader cutover (test-first).

Every governed evidence read must resolve immutable semantic identity H1
through one canonical resolver, never a physical locator. Legacy locators
(object_path/objectPath/lastGoodPath) remain provenance only.

Scratch DBs and scratch files only. No live data. No movement, no deletion
of historical evidence, no trading authority change.
"""
from __future__ import annotations

import hashlib
import io
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trendforge_api.market_data_store import MarketDataStore
from trendforge_api.retention_tiering import (
    TIERS,
    RetentionTieringStore,
    apply_tiering_schema,
)


def _store(tmp_path: Path) -> MarketDataStore:
    return MarketDataStore(
        root=tmp_path / "market-data",
        db_path=tmp_path / "market.db",
    )


def _tiering(tmp_path: Path, db_name: str = "market.db") -> RetentionTieringStore:
    return RetentionTieringStore(
        objects_root=tmp_path / "market-data" / "objects",
        db_path=tmp_path / db_name,
    )


def _install(store: MarketDataStore, payload: bytes) -> str:
    ref = store.install_object(
        payload, extension="json", media_type="application/json"
    )
    return ref.content_hash


def _replica_rows(db_path: Path):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "rhist04_replicas" not in tables:
            return []
        return conn.execute("SELECT * FROM rhist04_replicas").fetchall()


# ---------------------------------------------------------------------------
# Legacy compatibility (no replica records yet)
# ---------------------------------------------------------------------------


def test_legacy_hot_h1_resolves_before_backfill_without_writing_state(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    payload = b'{"h1": "legacy-hot"}'
    content_hash = _install(store, payload)
    tiering = _tiering(tmp_path)

    assert tiering.read_object_exact(content_hash) == payload
    assert tiering.exact_object_available(content_hash) is True
    # Read-only: no replica rows may appear as a side effect of reading.
    assert _replica_rows(tmp_path / "market.db") == []


def test_missing_h1_with_valid_h2_present_stays_unavailable(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    present = _install(store, b'{"h2": "present"}')
    missing = hashlib.sha256(b'{"h1": "missing"}').hexdigest()
    assert missing != present
    tiering = _tiering(tmp_path)

    with pytest.raises(OSError, match="EXACT_H1_UNAVAILABLE"):
        tiering.read_object_exact(missing)
    assert tiering.exact_object_available(missing) is False
    # The valid H2 itself still resolves; availability is H1-specific.
    assert tiering.exact_object_available(present) is True


def test_corrupt_legacy_bytes_are_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    content_hash = _install(store, b'{"h1": "intact-legacy"}')
    tiering = _tiering(tmp_path)
    assert tiering.read_object_exact(content_hash) is not None

    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.row_factory = sqlite3.Row
        object_path = Path(
            conn.execute(
                "SELECT object_path FROM market_data_objects WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()["object_path"]
        )
    object_path.write_bytes(b'{"h1": "damaged!!"}')
    with pytest.raises(OSError, match="REPLICA_INTEGRITY_FAILED"):
        tiering.read_object_exact(content_hash)
    assert tiering.exact_object_available(content_hash) is False


def test_legacy_locator_outside_root_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.initialize_schema()
    outside = tmp_path / "outside-evil.json"
    outside.write_bytes(b'{"h1": "outside"}')
    evil_hash = hashlib.sha256(b'{"h1": "outside"}').hexdigest()
    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.execute(
            "INSERT INTO market_data_objects("
            "content_hash, object_path, size_bytes, media_type, created_at"
            ") VALUES (?, ?, ?, ?, ?)",
            (
                evil_hash,
                str(outside),
                outside.stat().st_size,
                "application/json",
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
    tiering = _tiering(tmp_path)
    with pytest.raises(OSError, match="LEGACY_LOCATOR_REJECTED"):
        tiering.read_object_exact(evil_hash)


def test_legacy_symlink_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    content_hash = _install(store, b'{"h1": "link-target"}')
    tiering = _tiering(tmp_path)
    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.row_factory = sqlite3.Row
        object_path = Path(
            conn.execute(
                "SELECT object_path FROM market_data_objects WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()["object_path"]
        )
    smuggled = tmp_path / "smuggled.json"
    smuggled.write_bytes(b'{"h1": "link-target"}')
    try:
        object_path.unlink()
        os.symlink(smuggled, object_path)
    except OSError:
        pytest.skip("platform forbids symlink creation here")
    with pytest.raises(OSError, match="LEGACY_LOCATOR_REJECTED"):
        tiering.read_object_exact(content_hash)


def test_bounded_read_size_is_enforced(tmp_path: Path) -> None:
    store = _store(tmp_path)
    content_hash = _install(store, b"x" * 200)
    tiering = _tiering(tmp_path)
    assert tiering.read_object_exact(content_hash) == b"x" * 200
    with pytest.raises(OSError, match="OBJECT_TOO_LARGE"):
        tiering.read_object_exact(content_hash, max_bytes=100)


# ---------------------------------------------------------------------------
# Replica catalog: byte-proven backfill, replica-first resolution, states
# ---------------------------------------------------------------------------


def test_verified_hot_replica_resolves(tmp_path: Path) -> None:
    store = _store(tmp_path)
    payload = b'{"h1": "hot-replica"}'
    content_hash = _install(store, payload)
    tiering = _tiering(tmp_path)

    replica_id = tiering.adopt_legacy_as_replica(
        content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-1",
    )
    assert tiering.read_object_exact(content_hash) == payload
    assert tiering.exact_object_available(content_hash) is True
    assert replica_id in {row.replica_id for row in tiering.list_replicas(content_hash)}


def test_verified_warm_serves_after_hot_disappears(tmp_path: Path) -> None:
    store = _store(tmp_path)
    payload = b'{"h1": "warm-serves"}'
    content_hash = _install(store, payload)
    tiering = _tiering(tmp_path)

    warm_dir = tmp_path / "warm-mirror"
    warm_dir.mkdir()
    warm_path = warm_dir / "object.bin"
    warm_path.write_bytes(payload)
    tiering.adopt_legacy_as_replica(
        content_hash,
        tier="WARM",
        backend_id="local-warm",
        failure_domain="test-fd-2",
        locator=warm_path,
    )

    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.row_factory = sqlite3.Row
        hot_path = Path(
            conn.execute(
                "SELECT object_path FROM market_data_objects WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()["object_path"]
        )
    hot_path.unlink()
    assert tiering.read_object_exact(content_hash) == payload


def test_verified_cold_tier_resolves_where_backend_available(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    payload = b'{"h1": "cold-tier"}'
    content_hash = _install(store, payload)
    tiering = _tiering(tmp_path)

    cold_dir = tmp_path / "cold-mirror"
    cold_dir.mkdir()
    cold_path = cold_dir / "object.bin"
    cold_path.write_bytes(payload)
    tiering.adopt_legacy_as_replica(
        content_hash,
        tier="COLD",
        backend_id="local-cold",
        failure_domain="test-fd-3",
        locator=cold_path,
    )
    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.execute(
            "DELETE FROM market_data_objects WHERE content_hash = ?",
            (content_hash,),
        )
        conn.commit()
    assert tiering.read_object_exact(content_hash) == payload


def test_removed_replica_cannot_resolve(tmp_path: Path) -> None:
    store = _store(tmp_path)
    content_hash = _install(store, b'{"h1": "removal"}')
    tiering = _tiering(tmp_path)
    replica_id = tiering.adopt_legacy_as_replica(
        content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-1",
    )
    assert tiering.set_replica_state(
        replica_id, expected_state="VERIFIED", new_state="REMOVED"
    ) is True
    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.execute(
            "DELETE FROM market_data_objects WHERE content_hash = ?",
            (content_hash,),
        )
        conn.commit()
    with pytest.raises(OSError, match="EXACT_H1_UNAVAILABLE"):
        tiering.read_object_exact(content_hash)


def test_quarantined_replica_cannot_resolve(tmp_path: Path) -> None:
    store = _store(tmp_path)
    content_hash = _install(store, b'{"h1": "quarantine"}')
    tiering = _tiering(tmp_path)
    replica_id = tiering.adopt_legacy_as_replica(
        content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-1",
    )
    assert tiering.set_replica_state(
        replica_id,
        expected_state="VERIFIED",
        new_state="QUARANTINED",
        quarantine_reason="test-quarantine",
    ) is True
    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.execute(
            "DELETE FROM market_data_objects WHERE content_hash = ?",
            (content_hash,),
        )
        conn.commit()
    with pytest.raises(OSError, match="REPLICA_QUARANTINED"):
        tiering.read_object_exact(content_hash)


def test_broken_replica_falls_through_to_valid_replica(tmp_path: Path) -> None:
    store = _store(tmp_path)
    payload = b'{"h1": "redundant"}'
    content_hash = _install(store, payload)
    tiering = _tiering(tmp_path)

    warm_dir = tmp_path / "warm-good"
    warm_dir.mkdir()
    warm_path = warm_dir / "object.bin"
    warm_path.write_bytes(payload)
    tiering.adopt_legacy_as_replica(
        content_hash,
        tier="WARM",
        backend_id="local-warm",
        failure_domain="test-fd-2",
        locator=warm_path,
    )
    tiering.adopt_legacy_as_replica(
        content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-1",
    )
    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.row_factory = sqlite3.Row
        hot_path = Path(
            conn.execute(
                "SELECT object_path FROM market_data_objects WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()["object_path"]
        )
    hot_path.write_bytes(b'{"h1": "broken!!"}')
    assert tiering.read_object_exact(content_hash) == payload


def test_shadow_compare_proves_legacy_replica_identity(tmp_path: Path) -> None:
    store = _store(tmp_path)
    payload = b'{"h1": "shadow"}'
    content_hash = _install(store, payload)
    tiering = _tiering(tmp_path)
    replica_id = tiering.adopt_legacy_as_replica(
        content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-1",
    )
    report = tiering.shadow_compare_legacy_and_replica(content_hash)
    assert report.equal is True
    assert report.legacy_hash == content_hash
    assert report.replica_hash == content_hash
    assert report.replica_id == replica_id


def test_duplicate_replicas_resolve_deterministically(tmp_path: Path) -> None:
    store = _store(tmp_path)
    payload = b'{"h1": "deterministic"}'
    content_hash = _install(store, payload)
    tiering = _tiering(tmp_path)
    tiering.adopt_legacy_as_replica(
        content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-1",
    )
    warm_dir = tmp_path / "warm-dup"
    warm_dir.mkdir()
    warm_path = warm_dir / "object.bin"
    warm_path.write_bytes(payload)
    tiering.adopt_legacy_as_replica(
        content_hash,
        tier="WARM",
        backend_id="local-warm",
        failure_domain="test-fd-2",
        locator=warm_path,
    )
    first = tiering.verify_exact(content_hash)
    second = tiering.verify_exact(content_hash)
    assert first.available is True
    assert first.replica_id == second.replica_id
    assert tiering.read_object_exact(content_hash) == payload


def test_same_length_mutation_cannot_escape_as_trusted_bytes(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    content_hash = _install(store, b"A" * 64)
    tiering = _tiering(tmp_path)
    assert tiering.read_object_exact(content_hash) == b"A" * 64

    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.row_factory = sqlite3.Row
        object_path = Path(
            conn.execute(
                "SELECT object_path FROM market_data_objects WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()["object_path"]
        )
    object_path.write_bytes(b"B" * 64)
    with pytest.raises(OSError, match="REPLICA_INTEGRITY_FAILED"):
        tiering.read_object_exact(content_hash)


def test_open_compatible_returns_pinned_bytes_not_a_live_handle(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    payload = b'{"h1": "pinned"}'
    content_hash = _install(store, payload)
    tiering = _tiering(tmp_path)
    handle = tiering.open_compatible_exact(content_hash)
    assert isinstance(handle, io.BytesIO)
    assert handle.getvalue() == payload


# ---------------------------------------------------------------------------
# Store facade + R16 proof + cash availability
# ---------------------------------------------------------------------------


def test_store_facade_read_and_availability(tmp_path: Path) -> None:
    store = _store(tmp_path)
    payload = b'{"h1": "facade"}'
    content_hash = _install(store, payload)
    assert store.read_object_exact(content_hash) == payload
    assert store.exact_object_available(content_hash) is True

    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.row_factory = sqlite3.Row
        object_path = Path(
            conn.execute(
                "SELECT object_path FROM market_data_objects WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()["object_path"]
        )
    object_path.unlink()
    assert store.exact_object_available(content_hash) is False
    with pytest.raises(OSError, match="EXACT_H1_UNAVAILABLE"):
        store.read_object_exact(content_hash)


def test_r16_object_proof_rejects_missing_bytes(tmp_path: Path) -> None:
    from trendforge_api.r16_retention import _verify_objects
    from trendforge_api.retention_publication import RetentionEvidenceRoot

    store = _store(tmp_path)
    payload = b'{"h1": "r16-proof"}'
    content_hash = _install(store, payload)
    with sqlite3.connect(tmp_path / "market.db") as market:
        market.row_factory = sqlite3.Row
        roots = (
            RetentionEvidenceRoot(
                role="R1_SOURCE_NSE_BHAVCOPY_EOD", content_hash=content_hash
            ),
        )
        _verify_objects(market, roots)
        object_path = Path(
            market.execute(
                "SELECT object_path FROM market_data_objects WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()["object_path"]
        )
    object_path.unlink()
    with sqlite3.connect(tmp_path / "market.db") as market:
        market.row_factory = sqlite3.Row
        with pytest.raises(RuntimeError, match="EVIDENCE_OBJECT_DAMAGED"):
            _verify_objects(market, roots)


def test_tiering_schema_is_additive_and_versioned(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh.db"
    with sqlite3.connect(db_path) as conn:
        apply_tiering_schema(conn)
        conn.commit()
        version = conn.execute(
            "SELECT description FROM schema_migrations WHERE version = ?",
            ("0024_rhist04_replica_catalog",),
        ).fetchone()[0]
    assert "replica" in version.casefold()
    tables = set()
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "rhist04_replicas" in tables
    assert "rhist04_store_meta" in tables
    # Repeated application converges.
    with sqlite3.connect(db_path) as conn:
        apply_tiering_schema(conn)
        conn.commit()


def test_unknown_tier_and_state_inputs_are_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    content_hash = _install(store, b'{"h1": "typed"}')
    tiering = _tiering(tmp_path)
    with pytest.raises(ValueError, match="tier"):
        tiering.adopt_legacy_as_replica(
            content_hash,
            tier="GLACIER",
            backend_id="x",
            failure_domain="test-fd-1",
        )
    replica_id = tiering.adopt_legacy_as_replica(
        content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-1",
    )
    assert tiering.set_replica_state(
        replica_id, expected_state="DISCOVERED", new_state="VERIFIED"
    ) is False
    with pytest.raises(ValueError, match="state"):
        tiering.set_replica_state(
            replica_id, expected_state="VERIFIED", new_state="ARCHIVED"
        )


def test_invalid_hash_inputs_are_rejected(tmp_path: Path) -> None:
    tiering = _tiering(tmp_path)
    with pytest.raises(ValueError, match="SHA-256"):
        tiering.read_object_exact("not-a-hash")
    # The availability probe never raises and never substitutes.
    assert tiering.exact_object_available("xyz") is False


def test_tier_ordering_is_hot_warm_cold() -> None:
    assert list(TIERS) == ["HOT", "WARM", "COLD"]


def test_cash_dispatch_blocks_when_exact_hot_bytes_vanish(tmp_path: Path) -> None:
    """M1B cash safety: metadata saying H1 exists is not enough.

    After the HOT object file disappears (no replica backfill), dispatch must
    stay BLOCKED_INPUT via exact_object_available(H1) instead of progressing
    into a later FAILED_STAGE.
    """
    import json as _json
    from datetime import date as _date
    from datetime import datetime as _datetime

    from trendforge_api.market_data_service import NormalizedSourceResult
    from trendforge_api.selection.cash_post_commit import (
        CashPipelineExecution,
        CashPostCommitOrchestrator,
    )

    trade_date = _date(2026, 8, 14)
    now = _datetime(2026, 8, 14, 16, 5, tzinfo=UTC)
    store = _store(tmp_path)
    payload = {
        "sourceKey": "nse_bhavcopy_eod",
        "parserState": "PARSED_STRUCTURED",
        "dataDate": trade_date.isoformat(),
        "records": [
            {
                "tradeDate": trade_date.isoformat(),
                "symbol": "RELIANCE",
                "series": "EQ",
                "open": 1400,
                "high": 1440,
                "low": 1390,
                "close": 1430,
                "volume": 1000000,
            }
        ],
    }
    store.commit_success(
        run_id="collector-cash-hot-loss",
        source_key="nse_bhavcopy_eod",
        trading_date=trade_date,
        slot="eod",
        attempted_at=now,
        fetched_at=now,
        data_date=trade_date,
        source_url="https://example.test/cash.csv",
        http_status=200,
        media_type="application/vnd.trendforge.normalized+json",
        content=_json.dumps(payload, sort_keys=True).encode(),
        extension="json",
        normalized_row_count=1,
        retry_count=0,
    )

    calls: list = []

    def _runner(context):
        calls.append(context)
        return CashPipelineExecution(stages=(), permission_fingerprint="p")

    orchestrator = CashPostCommitOrchestrator(
        store=store,
        state_path=tmp_path / "cash-pipeline-state.json",
        runner=_runner,
    )
    results = {
        "nse_bhavcopy_eod": NormalizedSourceResult(
            source_key="nse_bhavcopy_eod",
            normalized_source_key="nse_bhavcopy_eod",
            status="SUCCESS_NEW",
            parser_state="PARSED_STRUCTURED",
            http_status=200,
            fetched_at=now,
            data_date=trade_date,
            normalized_row_count=1,
            normalized_content_hash="a" * 64,
            stored_attempt_id=1,
        )
    }
    first = orchestrator.process(
        collector_run_id="run-cash-healthy",
        trading_date=trade_date,
        results=results,
    )
    assert calls, "healthy baseline must dispatch through exact-H1 reads"
    assert first.latest_dispatch.decision == "DISPATCHED"

    with sqlite3.connect(tmp_path / "market.db") as conn:
        conn.row_factory = sqlite3.Row
        hot_path = Path(
            conn.execute(
                "SELECT object_path FROM market_data_objects "
                "WHERE content_hash = (SELECT content_hash FROM market_data_latest "
                "WHERE source_key = 'nse_bhavcopy_eod')"
            ).fetchone()["object_path"]
        )
    hot_path.unlink()
    calls.clear()
    second = orchestrator.process(
        collector_run_id="run-cash-hot-lost",
        trading_date=trade_date,
        results=results,
    )
    assert calls == []
    assert second.latest_run is not None
    assert second.latest_run.state == "BLOCKED_INPUT"
