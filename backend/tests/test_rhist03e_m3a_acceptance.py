"""R-HIST-03E-M3A acceptance proof (TEST DATA ONLY, scratch DBs).

Covers: audit read-only proof, snapshot semantics (uncommitted rows invisible,
PENDING reported as pending — never orphan, never PASS), and deterministic
repeatability. No production database is touched.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import test_rhist03e_source_to_end as source_to_end
from trendforge_api import storage
from trendforge_api.historical_retention import RetentionReference
from trendforge_api.historical_retention import (
    HistoricalRetentionAuthority,
    RetentionReferenceType,
)
from trendforge_api.market_data_registry import load_market_data_registry
from trendforge_api.market_data_service import MarketDataService
from trendforge_api.market_data_store import MarketDataStore
from trendforge_api.nse_eod_ingestion import _persist_fetched_artifact
from trendforge_api.retention_coverage import CoverageStatus, audit_coverage
from trendforge_api.selection import r18_governance as governance
from trendforge_api.selection import r18_store
from trendforge_api.selection.cash_a1_staging import (
    persist_cash_staging,
    stage_cash_last_good,
)
from trendforge_api.selection.cash_a2_identity import (
    build_cash_identity_batch,
    persist_cash_identity,
)
from trendforge_api.selection.cash_a4_history import (
    build_cash_history_batch,
    persist_cash_history,
)
from trendforge_api.selection.cash_post_commit import (
    CashPipelineRunContext,
    run_existing_cash_pipeline,
)
from trendforge_api.selection.r16_store import apply_r16_schema

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


def _set_db(tmp_path: Path, monkeypatch, name: str = "m3a.db") -> Path:
    db_path = tmp_path / name
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    monkeypatch.delenv("TRENDFORGE_MARKET_DATA_DB_PATH", raising=False)
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    apply_r16_schema()
    r18_store.apply_rhist03d_schema()
    return db_path


def _fingerprint(db_path: Path) -> dict[str, str]:
    """Logical content fingerprint: schema + ordered row bytes per table."""
    conn = sqlite3.connect(str(db_path))
    try:
        tables = sorted(
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        )
        digest: dict[str, str] = {}
        for table in tables:
            schema = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()[0]
            cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
            rows = conn.execute(
                f"SELECT * FROM {table} ORDER BY {', '.join(cols)}"
            ).fetchall()
            material = json.dumps(
                {"schema": schema, "rows": [list(r) for r in rows]},
                sort_keys=True,
                default=str,
            )
            digest[table] = hashlib.sha256(material.encode()).hexdigest()
        return digest
    finally:
        conn.close()


def _profile(index: int):
    return governance.build_strategy_profile_version(
        profile_id=f"PRF-M3A-{index}",
        profile_version="1.0.0",
        strategy_id="CONTINUATION",
        strategy_version="1.0.0",
        market="NSE",
        instrument_class="EQUITY",
        horizon="INTRADAY",
        timeframes=("5m",),
        setups=("BREAKOUT_CONTINUATION",),
        directions=("LONG", "SHORT"),
        required_to_calculate=("closed_bars",),
        required_to_qualify=("liquidity",),
        optional_context=(),
        prohibited_for_condition=("future_data",),
        relative_strength_contract="same-time-sector-v1",
        gate_policy="tradability-v1",
        ranking_group="intraday-continuation",
        risk_cost_assumptions=("cost-v1",),
        model_id=None,
        model_version=None,
        model_hash=None,
        research_ceiling="WAIT",
        activation_allowed=False,
        created_at=NOW + timedelta(seconds=index),
        valid_from=NOW,
    )


def test_audit_performs_zero_writes(tmp_path, monkeypatch) -> None:
    db_path = _set_db(tmp_path, monkeypatch)
    for index in range(3):
        profile = _profile(index)
        assert r18_store.persist_strategy_profile(profile) is True
    r18_store.finalize_rhist03d_artifact(
        "STRATEGY_PROFILE", "PRF-M3A-0", "1.0.0", verify_parents=True
    )
    before = _fingerprint(db_path)
    first = audit_coverage(audit_at=NOW)
    mid = _fingerprint(db_path)
    second = audit_coverage(audit_at=NOW + timedelta(hours=1))
    after = _fingerprint(db_path)
    assert before == mid == after
    assert first["reportHash"] == second["reportHash"]
    assert first["findings"] == second["findings"]


def test_uncommitted_artifact_is_invisible_to_audit(tmp_path, monkeypatch) -> None:
    db_path = _set_db(tmp_path, monkeypatch)
    profile = _profile(0)
    assert r18_store.persist_strategy_profile(profile) is True
    baseline = audit_coverage(audit_at=NOW)
    assert baseline["expectedCount"] == 1

    held = sqlite3.connect(str(db_path))
    try:
        held.execute("BEGIN IMMEDIATE")
        held.execute(
            "INSERT INTO strategy_profile_versions(record_id,profile_id,"
            "profile_version,content_hash,publication_state,payload_json,"
            "stored_content_hash,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (
                "PRF-M3A-UNCOMMITTED:1.0.0",
                "PRF-M3A-UNCOMMITTED",
                "1.0.0",
                "0" * 64,
                "PENDING_RETENTION",
                "{}",
                "0" * 64,
                NOW.isoformat(),
            ),
        )
        during = audit_coverage(audit_at=NOW)
        assert during["expectedCount"] == 1
        assert during["findings"] == baseline["findings"]
    finally:
        held.rollback()
        held.close()
    assert audit_coverage(audit_at=NOW)["expectedCount"] == 1


def test_pending_reports_pending_never_orphan_or_pass(
    tmp_path, monkeypatch
) -> None:
    _set_db(tmp_path, monkeypatch)
    profile = _profile(0)
    assert r18_store.persist_strategy_profile(profile) is True
    report = audit_coverage(audit_at=NOW)
    assert report["expectedCount"] == 1
    assert report["coveredCount"] == 0
    assert report["verdict"] == "FAIL"
    statuses = {str(row["status"]) for row in report["findings"]}
    assert CoverageStatus.PENDING_RETENTION.value in statuses
    assert CoverageStatus.RETENTION_ORPHAN.value not in statuses


def _run_paired_pipeline(
    tmp_path: Path, monkeypatch, tag: str
) -> tuple[Path, Path, str]:
    """Research + market stores on separate scratch files (TEST DATA ONLY).

    Uses the product-supported ``TRENDFORGE_MARKET_DATA_DB_PATH`` resolution
    path so S8/R16 authority references land in the market database while the
    outbox stays in the research database — exactly the topology the
    cross-store inverse enumerator must cover.
    """
    research_db = tmp_path / f"research-{tag}.db"
    market_db = tmp_path / f"market-{tag}.db"
    monkeypatch.setattr(storage, "DB_PATH", research_db)
    monkeypatch.setenv("TRENDFORGE_MARKET_DATA_DB_PATH", str(market_db))
    storage._INITIALIZED_DB_PATHS.clear()
    storage.init_db()
    apply_r16_schema()
    r18_store.apply_rhist03d_schema()

    store = MarketDataStore(root=tmp_path / "market-data", db_path=market_db)
    transport = source_to_end._CashSourceTransport()
    service = MarketDataService(
        transport=transport,
        normalizer=source_to_end._cash_normalizer,
        store=store,
    )
    contract = load_market_data_registry().by_key["nse_bhavcopy_eod"]
    final_result = None
    for seq, day in enumerate(
        source_to_end._trading_days(source_to_end.TRADE_DATE, 22)
    ):
        result = asyncio.run(
            service.run_source(
                contract,
                context=source_to_end._context(day),
                run_id=f"source-{tag}-{day.isoformat()}",
                slot="eod",
            )
        )
        assert result.status is not None
        staging = persist_cash_staging(stage_cash_last_good(store))
        identity = persist_cash_identity(build_cash_identity_batch(staging, store=store))
        persist_cash_history(
            build_cash_history_batch(
                identity, decision_at=source_to_end._at_close(day)
            )
        )
        saved = _persist_fetched_artifact(
            {
                "state": "FETCHED",
                "sourceKey": "nse_index_close_eod",
                "date": day,
                "url": (
                    "https://nsearchives.nseindia.com/content/indices/"
                    f"ind_close_all_{day.strftime('%d%m%Y')}.csv"
                ),
                "status": 200,
                "headers": {"content-type": "text/csv"},
                "content": source_to_end._index_csv(day, seq),
            }
        )
        assert saved["parserState"] == "PARSED_STRUCTURED"
        final_result = result
    execution = run_existing_cash_pipeline(
        CashPipelineRunContext(
            store=store,
            collector_run_id=f"paired-{tag}",
            trading_date=source_to_end.TRADE_DATE,
            results={"nse_bhavcopy_eod": final_result},
            trigger_source_keys=("nse_bhavcopy_eod",),
            fingerprint="e" * 64,
            observed_at=source_to_end._at_close(source_to_end.TRADE_DATE),
        )
    )
    assert execution.s8_run_id is not None
    states = {stage.stage_id: stage for stage in execution.stages}
    assert states["R16"].state == "COMPLETED"
    return research_db, market_db, str(execution.s8_run_id)


def _market_object_hashes(market_db: Path) -> dict[str, str]:
    conn = sqlite3.connect(str(market_db))
    try:
        return {
            str(row[0]): str(row[1])
            for row in conn.execute(
                "SELECT content_hash, object_path FROM market_data_objects"
            ).fetchall()
        }
    finally:
        conn.close()


def test_paired_stores_pass_and_external_orphan_fails_closed(
    tmp_path, monkeypatch
) -> None:
    research_db, market_db, _ = _run_paired_pipeline(tmp_path, monkeypatch, "pair")
    assert research_db.resolve() != market_db.resolve()

    authority_rows = sqlite3.connect(str(market_db)).execute(
        "SELECT COUNT(*) FROM historical_retention_references"
    ).fetchone()[0]
    assert int(authority_rows) > 0

    single = audit_coverage(db_path=research_db, audit_at=NOW)
    assert single["verdict"] == "PASS"
    paired = audit_coverage(
        db_path=research_db, market_db_paths=[market_db], audit_at=NOW
    )
    assert paired["verdict"] == "PASS"
    assert paired["expectedCount"] == single["expectedCount"]
    assert paired["coveredCount"] == single["coveredCount"]
    self_scan = audit_coverage(
        db_path=research_db, market_db_paths=[research_db], audit_at=NOW
    )
    assert self_scan["verdict"] == "PASS"
    assert self_scan["coveredCount"] == single["coveredCount"]

    intruder_hash = next(iter(_market_object_hashes(market_db)))
    authority = HistoricalRetentionAuthority(db_path=market_db)
    intruder = RetentionReference(
        reference_id="intruder-external-orphan-01",
        reference_type=RetentionReferenceType.DECISION_VERSION,
        content_hash=intruder_hash,
        created_at=NOW,
    )
    authority.register(intruder)
    try:
        flagged = audit_coverage(
            db_path=research_db, market_db_paths=[market_db], audit_at=NOW
        )
        assert flagged["verdict"] == "FAIL"
        assert flagged["orphanCount"] >= 1
        details = " ".join(
            str(finding.get("detail", "")) for finding in flagged["findings"]
        )
        assert "EXTERNAL_AUTHORITY_REFERENCE" in details
        assert CoverageStatus.RETENTION_ORPHAN.value in {
            str(finding["status"]) for finding in flagged["findings"]
        }
        # The single-store view is unchanged by design: it cannot see the
        # external store, which is exactly why acceptance must declare it.
        blind = audit_coverage(db_path=research_db, audit_at=NOW)
        assert blind["verdict"] == "PASS"
    finally:
        conn = sqlite3.connect(str(market_db))
        try:
            conn.execute(
                "DELETE FROM historical_retention_references WHERE reference_id=?",
                (intruder.reference_id,),
            )
            conn.commit()
        finally:
            conn.close()
    healed = audit_coverage(
        db_path=research_db, market_db_paths=[market_db], audit_at=NOW
    )
    assert healed["verdict"] == "PASS"


def test_missing_external_object_fails_closed(tmp_path, monkeypatch) -> None:
    research_db, market_db, s8_run_id = _run_paired_pipeline(
        tmp_path, monkeypatch, "object"
    )
    conn = sqlite3.connect(str(research_db))
    try:
        publication = conn.execute(
            "SELECT lineage_json FROM historical_retention_publications "
            "WHERE artifact_type='S8_DECISION_VERSION' AND artifact_id=?",
            (s8_run_id,),
        ).fetchone()
    finally:
        conn.close()
    retained = {
        str(root["contentHash"])
        for root in json.loads(publication[0])["evidenceRoots"]
        if root.get("contentHash")
    }
    objects = _market_object_hashes(market_db)
    victim = next(h for h in retained if h in objects)
    victim_path = Path(objects[victim])
    assert victim_path.is_file()
    victim_path.unlink()
    try:
        report = audit_coverage(
            db_path=research_db, market_db_paths=[market_db], audit_at=NOW
        )
        assert report["verdict"] == "FAIL"
        assert {
            str(finding["status"]) for finding in report["findings"]
        } & {
            CoverageStatus.LINEAGE_MISSING.value,
            CoverageStatus.LINEAGE_BROKEN.value,
            CoverageStatus.INCONSISTENT_IDENTITY.value,
        }
    finally:
        assert not victim_path.exists()
