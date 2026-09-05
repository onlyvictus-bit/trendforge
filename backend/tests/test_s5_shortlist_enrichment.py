"""S5 shortlist enrichment tests (File A SEL-006, WAIT ceiling)."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

import test_s4_structure_pack as s4f
from trendforge_api import storage
from trendforge_api.fii_stock_signals import (
    FIIStockSignalsSnapshot,
    LargeDealSignal,
)
from trendforge_api.main import app
from trendforge_api.selection.attention_order import persist_attention_order
from trendforge_api.selection.inventory_source_bundle import (
    persist_inventory_source_bundle,
)
from trendforge_api.selection.r4_live import build_r4_identity_pin, persist_r4_identity_pin
from trendforge_api.selection.r14_live import build_r14_ca_join, persist_r14_ca_join
from trendforge_api.selection.r5_live import build_r5_structure_batch, persist_r5_structure_batch
from trendforge_api.selection.r6_live import build_r6_enrichment
from trendforge_api.selection.s4_structure_pack import build_s4_structure_pack
from trendforge_api.selection.s5_shortlist_enrichment import build_s5_enrichment
from trendforge_api.selection.top10_research import build_top10_research
from trendforge_api.selection.store import latest_selection_payload


DECISION_AT = s4f.DECISION_AT
IST = ZoneInfo("Asia/Kolkata")


def _signals(*deals) -> FIIStockSignalsSnapshot:
    return FIIStockSignalsSnapshot(generated_at=DECISION_AT, large_deals=list(deals))


def _unnamed_deal():
    return LargeDealSignal(
        symbol="R5TEST",
        side="BUY",
        client=None,
        quantity=100000,
        price=100.0,
        value=10000000.0,
        deal_type="BULK",
        date="2026-08-12",
        source_key="nse_large_deals",
    )


def _seed_amfi() -> None:
    storage.init_db()
    conn = storage.connect()
    try:
        conn.execute(
            """
            INSERT INTO amfi_stock_deltas (
                disclosure_month, stock, isin, schemes_added, schemes_reduced,
                schemes_exited, net_quantity_change, parsed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026-06", "R5TEST", "INE000A01001", 5, 0, 0, 100, DECISION_AT.isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def _pack(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s5.db")
    instrument, identity, history, bundle, attention, staging, context = s4f._fixtures()
    s4f._store_breakout_history(instrument)
    r5 = s4f._build_r5(instrument, identity, history, bundle, attention, staging, context)
    return r5, build_s4_structure_pack(r5=r5)


def _build(pack, **overrides):
    params = dict(
        s4=pack,
        loader=lambda key: None,
        signals=_signals(),
        delivery_history={"R5TEST": [50.0 + i * 0.1 for i in range(24)]},
        shp_rows=[],
        built_at=DECISION_AT,
    )
    params.update(overrides)
    return build_s5_enrichment(**params)


def test_s5_rows_bounded_by_shortlist(tmp_path, monkeypatch) -> None:
    r5, pack = _pack(tmp_path, monkeypatch)
    batch = _build(pack)
    assert batch.shortlist_source == "S4_STRUCTURE_CLAIMS"
    assert batch.shortlist_count == 1
    assert batch.universe_count == 1
    assert batch.universe_count <= len(pack.rows)
    assert batch.confirmed_count == 0
    assert batch.can_unlock_confirmed is False


def test_s5_market_fii_is_chip_not_per_symbol(tmp_path, monkeypatch) -> None:
    _r5, pack = _pack(tmp_path, monkeypatch)
    batch = _build(pack)
    assert batch.market_fii.scope == "MARKET_WIDE_NOT_PER_STOCK"
    blob = batch.model_dump_json(by_alias=True)
    assert '"fiiBought"' not in blob
    assert "FII bought" not in blob


def test_s5_unnamed_deal_is_never_fii(tmp_path, monkeypatch) -> None:
    _r5, pack = _pack(tmp_path, monkeypatch)
    batch = _build(pack, signals=_signals(_unnamed_deal()))
    row = batch.rows[0]
    assert row.named_deal.code == "UNNAMED_DEAL_NOT_FII"
    assert row.named_deal.is_fii_claim is False


def test_s5_delivery_forbidden_on_intraday_horizon(tmp_path, monkeypatch) -> None:
    _r5, pack = _pack(tmp_path, monkeypatch)
    swing = _build(pack)
    assert swing.rows[0].delivery.horizon_guard == "EOD_ONLY"
    assert swing.rows[0].delivery.z is not None
    intraday = _build(pack, horizon="INTRADAY")
    field = intraday.rows[0].delivery
    assert field.status == "FORBIDDEN_ON_INTRADAY"
    assert field.z is None and field.pct is None


def test_s5_options_unknown_needs_r12_and_cash_only_not_punished(
    tmp_path, monkeypatch
) -> None:
    _r5, pack = _pack(tmp_path, monkeypatch)
    batch = _build(pack)
    row = batch.rows[0]
    assert row.options_package.status == "UNKNOWN_NEEDS_R12"
    assert row.options_package.can_support_confirmed is False
    assert row.options_package.score_contribution == 0
    # Cash-only name: missing FO package never penalizes; state stays WAIT.
    assert row.research_state.value == "WAIT"
    assert row.fo_package.can_support_confirmed is False
    blob = batch.model_dump_json(by_alias=True)
    assert '"winProbability"' not in blob
    assert '"quantity"' not in blob


def test_s5_shp_delta_null_and_amfi_delayed(tmp_path, monkeypatch) -> None:
    _r5, pack = _pack(tmp_path, monkeypatch)
    _seed_amfi()
    batch = _build(pack)
    row = batch.rows[0]
    assert row.shp_context.fii_delta is None
    assert row.delayed_mf is not None
    assert row.delayed_mf.code.startswith("DELAYED_MF_")
    assert row.delayed_mf.delayed is True


def test_s5_fo_missing_not_a_penalty(tmp_path, monkeypatch) -> None:
    _r5, pack = _pack(tmp_path, monkeypatch)
    batch = _build(pack, fo=None)
    row = batch.rows[0]
    assert row.fo_package.status in {
        "UNKNOWN_MISSING_SOURCE",
        "NOT_IN_A6_SHORTLIST_CASH_ONLY_NOT_PUNISHED",
    }
    assert row.research_state.value == "WAIT"


def test_s5_read_only_hashes_unchanged_and_no_persist(tmp_path, monkeypatch) -> None:
    r5, pack = _pack(tmp_path, monkeypatch)
    batch = _build(pack)
    assert batch.source_activation_ready is False
    assert batch.can_unlock_confirmed is False
    assert batch.r2_run_hash == pack.r2_run_hash == s4f._hash("r2")
    assert batch.r14_run_hash == r5.r14_run_hash
    # Read-only: S5 persists nothing into the selection artifact store.
    assert latest_selection_payload("PRF-S5-ENRICH-WAIT") is None


def test_s5_row_without_structure_claim_excluded(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s5-excl.db")
    instrument, identity, history, bundle, attention, staging, context = s4f._fixtures()
    s4f._store_breakout_history(instrument)
    mid_session = datetime.combine(s4f.TRADING_DATE, time(10, 0), tzinfo=IST)
    r5 = s4f._build_r5(
        instrument, identity, history, bundle, attention, staging, context,
        decision_at=mid_session,
    )
    pack = build_s4_structure_pack(r5=r5)
    batch = _build(pack)
    # The only fixture row has no structure claim mid-session, so it is excluded.
    assert batch.universe_count == 0


def test_s5_api_route(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s5-api.db")
    instrument, identity, history, bundle, attention, staging, context = s4f._fixtures()
    s4f._store_breakout_history(instrument)
    persist_inventory_source_bundle(bundle)
    persist_attention_order(attention)
    pin = persist_r4_identity_pin(
        build_r4_identity_pin(bundle=bundle, attention=attention, identity=identity)
    )
    join = persist_r14_ca_join(
        build_r14_ca_join(
            bundle=bundle,
            attention=attention,
            identity=identity,
            pin=pin,
            observations=[],
            vintages=[],
            decision_at=DECISION_AT,
        )
    )
    persist_r5_structure_batch(
        build_r5_structure_batch(
            bundle=bundle,
            attention=attention,
            identity=identity,
            history=history,
            staging=staging,
            context=context,
            ca_join=join,
            decision_at=DECISION_AT,
        )
    )
    client = TestClient(app)
    response = client.get("/api/v1/selection/s5-enrichment")
    assert response.status_code == 200
    body = response.json()
    assert body["acceptanceCeiling"] == "LIVE_S5_ENRICH_WAIT_ONLY"
    assert body["confirmedCount"] == 0
    assert client.post("/api/v1/selection/s5-enrichment").status_code == 405


def test_s6_regression_r6_top10_still_pass(tmp_path, monkeypatch) -> None:
    """Light smoke: R6 + top10 builders still run on the same fixture spine."""
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s5-r6smoke.db")
    instrument, identity, history, bundle, attention, staging, context = s4f._fixtures()
    s4f._store_breakout_history(instrument)
    join = s4f._ca_join(bundle, attention, identity)
    r5 = s4f._build_r5(instrument, identity, history, bundle, attention, staging, context)
    enrichment = build_r6_enrichment(
        bundle=bundle, attention=attention, r14=join, r5=r5, loader=None, signals=_signals()
    )
    board = build_top10_research(enrichment=enrichment)
    assert enrichment.rows[0].research_state.value == "WAIT"
    assert board is not None
