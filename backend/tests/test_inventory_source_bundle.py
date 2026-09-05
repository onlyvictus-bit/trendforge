from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from trendforge_api import main, storage
from trendforge_api.main import app
from trendforge_api.market_data_registry import load_market_data_registry
from trendforge_api.market_data_service import NormalizedSourceResult
from trendforge_api.market_data_store import ManifestStatus, MarketDataStore
from trendforge_api.selection.cash_a3_discovery import (
    CashDiscoveryBatch,
    CashDiscoveryMetrics,
    CashDiscoveryRow,
    DiscoveryProfile,
    SessionDirection,
)
from trendforge_api.selection.cash_c1_rank import CashRankBatch, CashRankRow
from trendforge_api.selection.contracts import SelectionState
from trendforge_api.selection.inventory_source_bundle import (
    SCHEMA_VERSION,
    SourceFreshnessState,
    SourceUsabilityState,
    _evaluate_freshness,
    build_inventory_source_bundle,
    latest_inventory_source_bundle,
    persist_inventory_source_bundle,
)

TRADE_DATE = date(2026, 8, 14)
NOW = datetime(2026, 8, 14, 16, 5, tzinfo=UTC)


def _result(
    source_key: str,
    status: ManifestStatus,
    *,
    rows: int,
    parser: str = "PARSED_STRUCTURED",
    data_date: date | None = TRADE_DATE,
    fetched_at: datetime = NOW,
) -> NormalizedSourceResult:
    return NormalizedSourceResult(
        source_key=source_key,
        normalized_source_key=source_key,
        status=status,
        parser_state=parser,
        source_url=f"https://example.test/{source_key}",
        http_status=200,
        fetched_at=fetched_at,
        data_date=data_date,
        normalized_row_count=rows,
        normalized_content_hash=(source_key.encode().hex() + "0" * 64)[:64],
    )


def _discovery() -> CashDiscoveryBatch:
    row = CashDiscoveryRow(
        symbol="RELIANCE",
        instrument_id="NSE:EQ:RELIANCE",
        fact_id="fact-reliance",
        public_state=SelectionState.WATCH,
        discovery_profiles=(DiscoveryProfile.MOMENTUM,),
        discovery_reason="Current cash discovery profile matched.",
        metrics=CashDiscoveryMetrics(
            session_return=0.02,
            session_direction=SessionDirection.UP,
            return_percentile=0.9,
            volume_percentile=0.8,
            turnover_percentile=0.7,
        ),
        eligible=True,
    )
    return CashDiscoveryBatch(
        batch_id="discovery-1",
        identity_batch_id="identity-1",
        eligible_count=1,
        watch_count=1,
        rows=(row,),
        persisted=True,
    )


def _rank() -> CashRankBatch:
    return CashRankBatch(
        batch_id="rank-1",
        matrix_id="matrix-1",
        can_rank_cash=True,
        mwpl_state="UNKNOWN",
        row_count=1,
        rows=(
            CashRankRow(
                rank=1,
                symbol="RELIANCE",
                public_state=SelectionState.WATCH,
                attention_score=0.85,
                support=("PRICE", "ACTIVITY"),
                reason="Attention only.",
            ),
        ),
        persisted=True,
    )


def _build(tmp_path, *, built_at=NOW):
    registry = load_market_data_registry()
    store = MarketDataStore(root=tmp_path / "market", db_path=tmp_path / "market.db")
    results = {
        "nse_bhavcopy_eod": _result("nse_bhavcopy_eod", ManifestStatus.SUCCESS_NEW, rows=10),
        "nse_fno_ban": _result("nse_fno_ban", ManifestStatus.VALID_EMPTY, rows=0),
        "nse_fo_bhavcopy": _result("nse_fo_bhavcopy", ManifestStatus.SUCCESS_NEW, rows=0),
    }
    return build_inventory_source_bundle(
        store=store,
        collector_run_id="collector-1",
        cash_pipeline_run_id="cash-collector-1",
        cash_pipeline_fingerprint="f" * 64,
        permission_fingerprint="p" * 64,
        snapshot_bundle_id="snapshot-1",
        trading_date=TRADE_DATE,
        results=results,
        discovery=_discovery(),
        rank=_rank(),
        stage_states={"A1": "COMPLETED", "A5": "COMPLETED", "A6": "SKIPPED", "C1": "COMPLETED"},
        registry=registry,
        built_at=built_at,
    )


def test_r1_bundle_classifies_every_registry_job_and_aliases(tmp_path) -> None:
    registry = load_market_data_registry()
    bundle = _build(tmp_path)
    assert bundle.schema_version == SCHEMA_VERSION
    assert bundle.freshness_policy_version == "registry-cadence-v1"
    assert bundle.source_contract_count == len(registry.contracts) == 126
    assert len({row.source_key for row in bundle.source_records}) == 126
    assert all(not row.vote_eligible and not row.can_unlock_ready for row in bundle.source_records)
    aliases = [row for row in bundle.source_records if row.alias_of]
    assert aliases
    assert all(not row.evidence_eligible for row in aliases)


def test_r1_distinguishes_usable_empty_and_http_200_without_rows(tmp_path) -> None:
    bundle = _build(tmp_path)
    by_key = {row.source_key: row for row in bundle.source_records}
    assert by_key["nse_bhavcopy_eod"].usability_state is SourceUsabilityState.USABLE_CURRENT
    assert by_key["nse_fno_ban"].usability_state is SourceUsabilityState.VALID_EMPTY_CURRENT
    assert by_key["nse_fo_bhavcopy"].http_status == 200
    assert by_key["nse_fo_bhavcopy"].usability_state is not SourceUsabilityState.USABLE_CURRENT


def test_r1_daily_freshness_uses_expected_session_not_wall_clock_today(tmp_path) -> None:
    sunday = datetime(2026, 8, 16, 8, 0, tzinfo=UTC)
    bundle = _build(tmp_path, built_at=sunday)
    cash = next(row for row in bundle.source_records if row.source_key == "nse_bhavcopy_eod")
    assert cash.usability_state is SourceUsabilityState.USABLE_CURRENT
    assert cash.freshness_state is SourceFreshnessState.CURRENT
    assert cash.expected_trading_date == TRADE_DATE
    assert cash.source_publication_cadence
    assert cash.etl_refresh_interval


def test_r1_old_daily_data_is_visible_but_not_evidence_eligible(tmp_path) -> None:
    registry = load_market_data_registry()
    store = MarketDataStore(root=tmp_path / "market", db_path=tmp_path / "market.db")
    old = _result(
        "nse_bhavcopy_eod",
        ManifestStatus.SUCCESS_NEW,
        rows=10,
        data_date=date(2026, 8, 13),
    )
    bundle = build_inventory_source_bundle(
        store=store,
        collector_run_id="collector-old",
        cash_pipeline_run_id="cash-old",
        cash_pipeline_fingerprint="f" * 64,
        permission_fingerprint="p" * 64,
        snapshot_bundle_id="snapshot-old",
        trading_date=TRADE_DATE,
        results={"nse_bhavcopy_eod": old},
        discovery=_discovery(),
        rank=_rank(),
        stage_states={"A1": "COMPLETED", "A5": "COMPLETED", "A6": "SKIPPED", "C1": "COMPLETED"},
        registry=registry,
        built_at=NOW,
    )
    cash = next(row for row in bundle.source_records if row.source_key == "nse_bhavcopy_eod")
    stock = bundle.stock_records[0]
    assert cash.usability_state is SourceUsabilityState.STALE_DATA
    assert cash.evidence_eligible is False
    assert "nse_bhavcopy_eod" in stock.failed_sources
    assert stock.source_clock["nse_bhavcopy_eod"]["freshnessState"] == "STALE"


def test_r1_event_source_uses_recent_check_not_event_date() -> None:
    registry = load_market_data_registry()
    contract = next(item for item in registry.contracts if item.cadence_class.value == "EVENT_DRIVEN")
    state, _, _ = _evaluate_freshness(
        contract,
        data_date=date(2025, 1, 1),
        fetched_at=NOW,
        trading_date=TRADE_DATE,
        now=NOW,
    )
    assert state is SourceFreshnessState.CURRENT


def test_r1_closed_day_publisher_is_not_forced_to_nse_session_date() -> None:
    registry = load_market_data_registry()
    contract = registry.by_key["amfi_nav"]
    sunday = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
    state, _, _ = _evaluate_freshness(
        contract,
        data_date=date(2026, 8, 16),
        fetched_at=sunday,
        trading_date=TRADE_DATE,
        now=sunday,
    )
    assert state is SourceFreshnessState.CURRENT


def test_r1_release_and_empty_freshness_fail_closed() -> None:
    registry = load_market_data_registry()
    weekly = next(item for item in registry.contracts if item.cadence_class.value == "WEEKLY_RELEASE")
    stale_weekly, _, _ = _evaluate_freshness(
        weekly,
        data_date=date(2026, 8, 3),
        fetched_at=NOW,
        trading_date=TRADE_DATE,
        now=NOW,
    )
    valid_empty_contract = registry.by_key["nse_fno_ban"]
    stale_empty, _, _ = _evaluate_freshness(
        valid_empty_contract,
        data_date=None,
        fetched_at=datetime(2026, 8, 1, tzinfo=UTC),
        trading_date=TRADE_DATE,
        now=NOW,
        valid_empty=True,
    )
    assert stale_weekly is SourceFreshnessState.STALE
    assert stale_empty is SourceFreshnessState.STALE


def test_r1_future_data_never_becomes_current() -> None:
    registry = load_market_data_registry()
    contract = registry.by_key["nse_bhavcopy_eod"]
    state, _, _ = _evaluate_freshness(
        contract,
        data_date=date(2026, 8, 15),
        fetched_at=NOW,
        trading_date=TRADE_DATE,
        now=NOW,
    )
    assert state is SourceFreshnessState.FUTURE


def test_r1_stock_record_is_pit_research_only_and_has_no_geometry(tmp_path) -> None:
    stock = _build(tmp_path).stock_records[0]
    assert stock.public_state is SelectionState.WATCH
    assert stock.entry is stock.target is stock.stop is stock.risk_reward is None
    assert "SOURCE_ACTIVATION" in stock.why_not_confirmed
    assert stock.lineage["collectorRunId"] == "collector-1"
    assert stock.dataset_root_ids
    assert stock.tradability == "RESEARCH_ONLY"


def test_r1_hash_is_deterministic_and_persistence_is_profile_isolated(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "selection.db")
    storage._INITIALIZED_DB_PATHS.clear()
    first = _build(tmp_path / "one")
    second = _build(tmp_path / "two")
    assert first.bundle_hash == second.bundle_hash
    stored = persist_inventory_source_bundle(first)
    assert stored.persisted is True
    loaded = latest_inventory_source_bundle()
    assert loaded is not None
    assert loaded.bundle_id == first.bundle_id
    assert loaded.stock_records[0].symbol == "RELIANCE"

def test_r1_evidence_api_returns_only_persisted_bundle(tmp_path, monkeypatch) -> None:
    bundle = _build(tmp_path)
    monkeypatch.setattr(main, "latest_inventory_source_bundle", lambda: bundle)
    response = TestClient(app).get("/api/v1/selection/evidence")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schemaVersion"] == SCHEMA_VERSION
    assert payload["sourceContractCount"] == 126
    assert payload["stockRecords"][0]["publicState"] == "WATCH"
    assert payload["sourceActivationReady"] is False


def test_r1_evidence_api_fails_closed_when_bundle_missing(monkeypatch) -> None:
    monkeypatch.setattr(main, "latest_inventory_source_bundle", lambda: None)
    response = TestClient(app).get("/api/v1/selection/evidence")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "R1_EVIDENCE_NOT_READY"
