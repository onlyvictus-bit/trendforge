from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.demo_data import generate_demo_daily_candles
from trendforge_api.evidence_builder import (
    build_symbol_evidence,
    persist_symbol_evidence,
)
from trendforge_api.main import app
from trendforge_api.scanner_scheduler import ScannerScheduler


AS_OF = datetime.now(timezone.utc).replace(microsecond=0)


def seed_evidence_rows() -> None:
    storage.init_db()
    parsed = (AS_OF - timedelta(hours=1)).isoformat()
    future = (AS_OF + timedelta(hours=1)).isoformat()
    data_date = AS_OF.date().isoformat()
    event_date = (AS_OF - timedelta(days=1)).date().isoformat()
    disclosure_month = (AS_OF - timedelta(days=30)).strftime("%Y-%m")
    with storage.connect() as conn:
        conn.execute(
            """
            INSERT INTO bulk_block_deals
            (data_date, symbol, deal_type, buyer, quantity, price, value, premium_pct, parsed_at)
            VALUES (?, 'EVIDENCE', 'BULK', 'ALPHA FUND', 100000, 500, 50000000, 2.0, ?)
            """,
            (data_date, parsed),
        )
        conn.execute(
            """
            INSERT INTO amfi_stock_deltas
            (disclosure_month, stock, schemes_added, schemes_reduced, schemes_exited, net_quantity_change, parsed_at)
            VALUES (?, 'EVIDENCE', 3, 0, 0, 125000, ?)
            """,
            (disclosure_month, parsed),
        )
        conn.execute(
            """
            INSERT INTO sebi_disclosures
            (data_date, symbol, entity, relationship, transaction_type, event_date,
             disclosure_date, quantity, price, parsed_at)
            VALUES (?, 'EVIDENCE', 'PROMOTER A', 'PROMOTER', 'OPEN MARKET BUY',
                    ?, ?, 50000, 498, ?)
            """,
            (data_date, event_date, data_date, parsed),
        )
        conn.execute(
            """
            INSERT INTO sebi_disclosures
            (data_date, symbol, entity, relationship, transaction_type, event_date,
             disclosure_date, quantity, price, parsed_at)
            VALUES (?, 'EVIDENCE', 'DIRECTOR B', 'DIRECTOR', 'ESOP EXERCISE',
                    ?, ?, 1000, 10, ?)
            """,
            (data_date, event_date, data_date, parsed),
        )
        conn.execute(
            """
            INSERT INTO corporate_events
            (source_key, data_date, symbol, company, action_type, announcement_date, offer_price, parsed_at)
            VALUES ('nse_daily_buyback', ?, 'EVIDENCE', 'Evidence Ltd', 'BUYBACK',
                    ?, 550, ?)
            """,
            (data_date, data_date, parsed),
        )
        conn.execute(
            """
            INSERT INTO corporate_events
            (source_key, data_date, symbol, company, action_type, announcement_date, offer_price, parsed_at)
            VALUES ('nse_daily_buyback', ?, 'EVIDENCE', 'Evidence Ltd', 'OPEN OFFER',
                    ?, 600, ?)
            """,
            (data_date, data_date, future),
        )
        conn.commit()


def test_structured_rows_become_point_in_time_typed_evidence(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "evidence.db")
    seed_evidence_rows()
    claims = build_symbol_evidence("EVIDENCE", as_of=AS_OF)
    assert len(claims) == 6
    assert {claim.layer.value for claim in claims} == {"CAUSE", "SPONSOR"}
    assert {claim.sponsor_actor.value for claim in claims if claim.sponsor_actor} == {
        "DII",
        "NAMED_INVESTOR",
        "PROMOTER_INSIDER",
    }
    assert {claim.cause_type.value for claim in claims if claim.cause_type} == {
        "FORCED_MANDATORY_FLOW",
        "INFORMATION_ASYMMETRY",
    }
    assert not any("ESOP" in claim.signal_type for claim in claims)
    assert not any(
        claim.source_row_id == 2 and claim.source_key == "nse_daily_buyback"
        for claim in claims
    )
    assert all(
        claim.source_key and claim.source_row_id and claim.source_date <= AS_OF
        for claim in claims
    )


def test_evidence_claim_persistence_is_hash_deduplicated(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "evidence-persist.db")
    seed_evidence_rows()
    assert persist_symbol_evidence("EVIDENCE", as_of=AS_OF) == 6
    assert persist_symbol_evidence("EVIDENCE", as_of=AS_OF) == 0
    rows = storage.list_evidence_claims(symbol="EVIDENCE")
    assert len(rows) == 6
    assert all(row["claim_hash"] for row in rows)


def test_evidence_api_exposes_source_dated_claims(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "evidence-api.db")
    seed_evidence_rows()
    response = TestClient(app).get(
        "/api/evidence/EVIDENCE",
        params={"asOf": AS_OF.isoformat(), "persist": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "EVIDENCE"
    assert payload["claimCount"] == 6
    assert payload["savedCount"] == 6
    assert all(item["sourceKey"] for item in payload["claims"])


def test_scanner_attaches_normalized_cause_and_sponsor_claims(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "evidence-scanner.db")
    seed_evidence_rows()
    storage.save_ohlcv_candles(
        generate_demo_daily_candles(symbol="EVIDENCE", sessions=80)
    )
    summary = ScannerScheduler().run_once(
        universe="WATCHLIST_ONLY", fetch=False, trigger="evidence-test"
    )
    assert summary["status"] == "COMPLETE"
    rows = storage.list_scanner_candidates(run_id=summary["runId"], limit=10)
    candidate = next(row["payload"] for row in rows if row["symbol"] == "EVIDENCE")
    assert candidate["harmonicLifecycle"]["status"] in {
        "TRACKED",
        "NOT_APPLICABLE",
    }
    assert candidate["harmonicLifecycle"]["executable"] is False
    causal = candidate["causalEvaluation"]
    attached = {item["sourceKey"] for item in causal["evidence"] if item["sourceKey"]}
    assert {
        "nse_large_deals",
        "amfi_monthly_portfolio",
        "sebi_pit_sast",
        "nse_daily_buyback",
    } <= attached
    layer_scores = {item["layer"]: item["finalScore"] for item in causal["layerScores"]}
    assert layer_scores["CAUSE"] >= 2
    assert layer_scores["SPONSOR"] >= 4
    assert causal["finalState"] != "READY"
