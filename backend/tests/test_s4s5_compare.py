from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.selection.attention_order import (
    AttentionRowV1,
    InventoryDiscoveryV1,
    persist_attention_order,
)
from trendforge_api.selection.contracts import (
    EvidenceDirection,
    SelectionState,
    StateCeiling,
)
from trendforge_api.selection.inventory_source_bundle import (
    InventorySourceBundleV1,
    StockEvidenceRecordV1,
    persist_inventory_source_bundle,
)
from trendforge_api.selection.r5_live import (
    R5StructureBatchV1,
    R5StructureRowV1,
    persist_r5_structure_batch,
)
from trendforge_api.selection.s4s5_compare import (
    ILLUSTRATION_B,
    ILLUSTRATION_C,
    WITH_FORMULA,
    WITHOUT_FORMULA,
    _kelly,
    _p_min,
    _sigmoid,
    build_s4s5_compare,
)
from trendforge_api.selection.structure import StructureMetrics


TRADING_DATE = date(2026, 8, 14)
DECISION_AT = datetime(2026, 8, 14, 17, 0, tzinfo=UTC)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _persist_lineage(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s4s5.db")
    storage._INITIALIZED_DB_PATHS.clear()
    stock = StockEvidenceRecordV1(
        candidate_id="candidate-ab",
        symbol="S4S5AB",
        instrument_id="NSE:EQ:S4S5AB",
        fact_id="fact-ab",
        public_state=SelectionState.WATCH,
        evidence_direction=EvidenceDirection.BULLISH,
        research_class="CASH_RESEARCH",
        why_visible="Current official cash row.",
        why_not_confirmed=("SOURCE_ACTIVATION_FALSE",),
        attempted_sources=("nse_bhavcopy_eod",),
        completed_sources=("nse_bhavcopy_eod",),
        valid_empty_sources=(),
        failed_sources=(),
        not_attempted_sources=(),
        family_coverage={"PARTICIPATION": "AVAILABLE"},
        dataset_root_ids=("NSE_CASH_EOD",),
        supporting_claims=(),
        opposing_claims=(),
        cheap_features={
            "returnPercentile": 0.9,
            "volumePercentile": 0.9,
            "turnoverPercentile": 0.9,
        },
        source_clock={
            "nse_bhavcopy_eod": {
                "usabilityState": "USABLE_CURRENT",
                "dataDate": TRADING_DATE.isoformat(),
            }
        },
        lineage={"artifactHash": _hash("latest-cash")},
        restriction_state="READY",
        completeness=1.0,
    )
    bundle = InventorySourceBundleV1(
        bundle_id="r1-bundle-ab",
        bundle_hash=_hash("r1-ab"),
        collector_run_id="collector-ab",
        cash_pipeline_run_id="cash-ab",
        cash_pipeline_fingerprint=_hash("pipeline-ab"),
        permission_fingerprint=_hash("permission-ab"),
        snapshot_bundle_id="snapshot-ab",
        trading_date=TRADING_DATE,
        built_at=DECISION_AT,
        registry_sha256=_hash("registry"),
        source_contract_count=0,
        stock_record_count=1,
        stage_states={"C1": "COMPLETED"},
        source_records=(),
        stock_records=(stock,),
    )
    attention = InventoryDiscoveryV1(
        run_id="r2-run-ab",
        run_hash=_hash("r2-ab"),
        r1_bundle_id=bundle.bundle_id,
        r1_bundle_hash=bundle.bundle_hash,
        collector_run_id=bundle.collector_run_id,
        cash_pipeline_run_id=bundle.cash_pipeline_run_id,
        cash_pipeline_fingerprint=bundle.cash_pipeline_fingerprint,
        permission_fingerprint=bundle.permission_fingerprint,
        snapshot_bundle_id=bundle.snapshot_bundle_id,
        trading_date=TRADING_DATE.isoformat(),
        built_at=DECISION_AT,
        universe_count=1,
        watch_count=1,
        wait_count=0,
        reject_count=0,
        rows=(
            AttentionRowV1(
                candidate_id=stock.candidate_id,
                symbol=stock.symbol,
                public_state=SelectionState.WATCH,
                evidence_direction=stock.evidence_direction,
                display_order=1,
                attention_rank=1,
                attention_priority=0.6,
                attention_band="HIGH",
                supporting_families=("CASH_SESSION_ROOT",),
                opposing_claims=(),
                missing_evidence=(),
                conflicts=(),
                completeness=1.0,
                freshness="CURRENT",
                source_quality="OFFICIAL_STRUCTURED",
                restriction_state="READY",
                why_visible=stock.why_visible,
                why_not_confirmed=stock.why_not_confirmed,
                lineage=stock.lineage,
                dataset_root_ids=stock.dataset_root_ids,
            ),
        ),
    )
    structure = R5StructureBatchV1(
        run_id="r5-run-ab",
        run_hash=_hash("r5-ab"),
        r1_bundle_id=bundle.bundle_id,
        r1_bundle_hash=bundle.bundle_hash,
        r2_run_id=attention.run_id,
        r2_run_hash=attention.run_hash,
        collector_run_id=bundle.collector_run_id,
        cash_pipeline_run_id=bundle.cash_pipeline_run_id,
        cash_pipeline_fingerprint=bundle.cash_pipeline_fingerprint,
        permission_fingerprint=bundle.permission_fingerprint,
        trading_date=TRADING_DATE.isoformat(),
        decision_at=DECISION_AT,
        universe_count=1,
        wait_count=1,
        reject_count=0,
        rows=(
            R5StructureRowV1(
                candidate_id=stock.candidate_id,
                symbol=stock.symbol,
                instrument_id=stock.instrument_id,
                r2_public_state=SelectionState.WATCH,
                structure_state=SelectionState.WAIT,
                state_ceiling=StateCeiling.WAIT,
                evidence_direction=EvidenceDirection.BULLISH,
                display_order=1,
                source_mode="OFFICIAL_CASH",
                history_count=22,
                ca_state="NONE",
                index_context_state="READY",
                detected_setups=("BREAKOUT", "NR7"),
                gate_codes=("WAIT_R14_CA_JOIN",),
                why_wait=("R14_NOT_JOINED",),
                metrics=StructureMetrics(
                    reference_level=100.0,
                    accepted=True,
                    relative_volume=2.0,
                    narrow_range=True,
                ),
            ),
        ),
    )
    persist_inventory_source_bundle(bundle)
    persist_attention_order(attention)
    persist_r5_structure_batch(structure)


def test_p_min_is_cost_derived() -> None:
    assert abs(_p_min() - (1 + ILLUSTRATION_C) / (1 + ILLUSTRATION_B)) < 1e-9


def test_compressed_p_hat_is_higher_when_book_is_added() -> None:
    side = 0.6
    book = 0.4
    p_without = _sigmoid(-0.4 + 1.2 * side)
    p_with = _sigmoid(-0.4 + 1.2 * side + 1.2 * book)
    assert p_with > p_without


def test_kelly_illustration_is_capped_and_not_a_live_size() -> None:
    assert _kelly(0.99) <= 0.02
    assert _kelly(0.1) == 0.0


def test_compare_shows_with_and_without_formulas(tmp_path, monkeypatch) -> None:
    _persist_lineage(tmp_path, monkeypatch)
    batch = build_s4s5_compare(limit=5)
    assert batch.can_unlock_confirmed is False
    assert batch.executable is False
    assert batch.calibration == "RESEARCH_PROXY_NOT_CALIBRATED"
    assert batch.with_formula == WITH_FORMULA
    assert batch.without_formula == WITHOUT_FORMULA
    assert batch.row_count == 1
    row = batch.rows[0]
    assert row.symbol == "S4S5AB"
    assert row.research_state is SelectionState.WAIT
    assert row.side_z == 0.6
    assert row.book_z > 0
    assert row.with_s4s5.p_hat > row.without_s4s5.p_hat
    assert row.p_hat_inflation == round(row.with_s4s5.p_hat - row.without_s4s5.p_hat, 4)
    assert "z_book" in row.with_s4s5.formula
    assert "package" in row.without_s4s5.formula.lower() or "B4" in row.without_s4s5.formula
    assert row.without_s4s5.package == "SUPPORT"
    assert row.with_s4s5.would_pass_p_min is True
    assert all(item.research_state is not SelectionState.CONFIRMED for item in batch.rows)


def test_s4s5_compare_api_is_wait_only(tmp_path, monkeypatch) -> None:
    _persist_lineage(tmp_path, monkeypatch)
    client = TestClient(app)
    response = client.get("/api/v1/selection/s4s5-compare?limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["canUnlockConfirmed"] is False
    assert payload["executable"] is False
    assert payload["withFormula"].startswith("p̂ =")
    assert payload["withoutFormula"].startswith("p̂ =")
    row = payload["rows"][0]
    assert row["withS4S5"]["pHat"] > row["withoutS4S5"]["pHat"]
    assert row["researchState"] == "WAIT"
    assert all(item["researchState"] != "CONFIRMED" for item in payload["rows"])
    assert client.post("/api/v1/selection/s4s5-compare").status_code == 405
