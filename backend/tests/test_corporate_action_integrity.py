from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.corporate_actions import (
    apply_reconciled_actions_at_ingestion,
    assess_adjustment_integrity,
    reconcile_corporate_actions,
)
from trendforge_api.models import OHLCVCandle
from trendforge_api.main import app
from trendforge_api.parsers.bse_offers_parser import parse_bse_offer_index
from trendforge_api.parsers.corporate_events_parser import parse_corporate_events
from trendforge_api.scanner_scheduler import ScannerScheduler
from trendforge_api.source_resolver import direct_download_candidates, request_headers


BASE = datetime(2026, 6, 1, 9, 15, tzinfo=timezone.utc)


def candle(
    day: int, price: float, *, adjustment_status: str = "UNKNOWN"
) -> OHLCVCandle:
    timestamp = BASE + timedelta(days=day)
    return OHLCVCandle(
        symbol="SPLITCO",
        timeframe="1d",
        source="official_fixture",
        timestamp=timestamp.isoformat(),
        open=price,
        high=price + 1,
        low=price - 1,
        close=price,
        volume=1_000,
        trustLevel="OFFICIAL_FREE_EOD",
        fetchedAt=(timestamp + timedelta(hours=1)).isoformat(),
        adjustmentStatus=adjustment_status,
    )


def split_row(
    *,
    event_id: int,
    source: str,
    numerator: float = 2,
    denominator: float = 1,
    revision: str = "ORIGINAL",
) -> dict:
    return {
        "id": event_id,
        "source_key": source,
        "symbol": "SPLITCO",
        "action_type": "STOCK SPLIT",
        "ex_date": "2026-06-04",
        "record_date": "2026-06-05",
        "announcement_date": "2026-05-20",
        "ratio_numerator": numerator,
        "ratio_denominator": denominator,
        "revision_status": revision,
        "parsed_at": "2026-05-20T12:00:00+00:00",
    }


def cash_action_row(
    *,
    event_id: int,
    action_class: str,
    cash_amount: float | None = None,
    offer_price: float | None = None,
    numerator: float | None = None,
    denominator: float | None = None,
) -> dict:
    return {
        "id": event_id,
        "source_key": "nse_corporate_filings_actions",
        "symbol": "SPLITCO",
        "action_type": action_class,
        "action_class": action_class,
        "ex_date": "2026-06-04",
        "record_date": "2026-06-05",
        "announcement_date": "2026-05-20",
        "ratio_numerator": numerator,
        "ratio_denominator": denominator,
        "cash_amount": cash_amount,
        "offer_price": offer_price,
        "revision_status": "ORIGINAL",
        "parsed_at": "2026-05-20T12:00:00+00:00",
    }


def reconstruction_row(
    *,
    event_id: int,
    action_class: str,
    source: str = "nse_corporate_filings_actions",
    adjustment_factor: float | None = None,
    predecessor_symbol: str = "SPLITCO",
    successor_symbol: str = "SPLITCO",
    continuity_confirmed: bool = False,
) -> dict:
    return {
        "id": event_id,
        "source_key": source,
        "symbol": "SPLITCO",
        "action_type": action_class,
        "action_class": action_class,
        "ex_date": "2026-06-04",
        "record_date": "2026-06-05",
        "announcement_date": "2026-05-20",
        "ratio_numerator": 3,
        "ratio_denominator": 2,
        "adjustment_factor": adjustment_factor,
        "predecessor_symbol": predecessor_symbol,
        "successor_symbol": successor_symbol,
        "continuity_confirmed": continuity_confirmed,
        "revision_status": "ORIGINAL",
        "parsed_at": "2026-05-20T12:00:00+00:00",
    }


def test_parser_extracts_action_ratio_revision_and_cash_amount() -> None:
    content = (
        "symbol,action_type,ex_date,action_ratio,status,dividend_amount\n"
        "SPLITCO,Stock Split,2026-06-04,2:1,Revised,\n"
        "DIVCO,Final Dividend,2026-06-10,,Original,12.5\n"
    ).encode()
    result = parse_corporate_events(content, last_modified="2026-06-01")
    assert result["parser_state"] == "PARSED_STRUCTURED"
    split, dividend = result["output"]["rows"]
    assert split["actionClass"] == "SPLIT"
    assert split["ratioNumerator"] == 2
    assert split["ratioDenominator"] == 1
    assert split["revisionStatus"] == "REVISED"
    assert dividend["actionClass"] == "DIVIDEND"
    assert dividend["cashAmount"] == 12.5


def test_parser_extracts_explicit_reconstruction_terms_without_inference() -> None:
    content = (
        "symbol,action_type,ex_date,action_ratio,price_adjustment_factor,"
        "predecessor_symbol,successor_symbol,continuity_confirmed,status\n"
        "SPLITCO,Demerger,2026-06-04,3:2,0.72,SPLITCO,SPLITCO,true,Original\n"
    ).encode()
    result = parse_corporate_events(content, last_modified="2026-06-01")
    row = result["output"]["rows"][0]
    assert row["actionClass"] == "DEMERGER"
    assert row["priceAdjustmentFactor"] == 0.72
    assert row["predecessorSymbol"] == "SPLITCO"
    assert row["successorSymbol"] == "SPLITCO"
    assert row["continuityConfirmed"] is True


def test_official_nse_json_contract_and_direct_resolver() -> None:
    content = (
        '[{"symbol":"RELIANCE","comp":"Reliance Industries Limited",'
        '"subject":"Dividend - Rs 6 Per Share","exDate":"05-Jun-2026",'
        '"recDate":"05-Jun-2026","caBroadcastDate":"20-May-2026"},'
        '{"symbol":"BONUSCO","comp":"Bonus Co","subject":"Bonus 1:1",'
        '"exDate":"10-Jun-2026","recDate":"10-Jun-2026"}]'
    ).encode()
    result = parse_corporate_events(content, last_modified="2026-06-10")
    assert result["parser_state"] == "PARSED_STRUCTURED"
    dividend, bonus = result["output"]["rows"]
    assert dividend["company"] == "Reliance Industries Limited"
    assert dividend["cashAmount"] == 6
    assert dividend["recordDate"] == "2026-06-05"
    assert bonus["actionClass"] == "BONUS"
    assert bonus["ratioNumerator"] == 1
    assert bonus["ratioDenominator"] == 1

    actions = direct_download_candidates("nse_corporate_filings_actions")
    buybacks = direct_download_candidates("nse_daily_buyback")
    assert actions == [
        "https://www.nseindia.com/api/corporates-corporateActions?index=equities"
    ]
    assert buybacks == ["https://www.nseindia.com/api/corporates-daily-buyback?"]

    future_payload = (
        '[{"symbol":"FUTURE","comp":"Future Co",'
        '"subject":"Dividend - Rs 2 Per Share","exDate":"13-Jul-2026",'
        '"recDate":"13-Jul-2026"}]'
    ).encode()
    future = parse_corporate_events(future_payload, last_modified="2026-07-11")
    assert future["data_date"] == "2026-07-11"

    empty_buyback = parse_corporate_events(
        b'{"data":[]}',
        url="https://www.nseindia.com/api/corporates-daily-buyback?",
        last_modified="2026-07-11T12:00:00+05:30",
    )
    assert empty_buyback["parser_state"] == "PARSED_STRUCTURED"
    assert empty_buyback["record_count"] == 0
    assert empty_buyback["output"]["validEmpty"] is True


def test_bse_offer_index_is_discovery_metadata_until_xbrl_terms_parse() -> None:
    payload = (
        '{"table":[{"Fld_CompanyId":"3483",'
        '"Fld_NameOfCompany":"WIPRO LIMITED",'
        '"predoc":"/XBRLFILES/BTRUploadDocument/pre.xml",'
        '"postdoc":"/XBRLFILES/BTRUploadDocument/post.xml",'
        '"preti":"6/9/2026 6:17:21 AM","postti":"6/26/2026 6:33:35 PM",'
        '"PreStatus":"New","PostStatus":"New"}]}'
    ).encode()
    result = parse_bse_offer_index(
        payload,
        url=(
            "https://api.bseindia.com/BseIndiaAPI/api/"
            "Mkt_Pubissues_FIS_BuybackTenderoffer_isd_ng/w"
        ),
        last_modified="2026-07-11T10:00:00+05:30",
    )
    assert result["parser_state"] == "PARSED_METADATA_ONLY"
    assert result["record_count"] == 1
    row = result["output"]["rows"][0]
    assert row["company"] == "WIPRO LIMITED"
    assert row["offerType"] == "BUYBACK_TENDER"
    assert row["preDocumentUrl"].endswith("/pre.xml")
    assert row["postDocumentUrl"].endswith("/post.xml")
    assert result["output"]["requiresXbrlDetails"] is True
    assert result["data_date"] == "2026-06-26"

    buyback_urls = direct_download_candidates("bse_buyback_tender")
    takeover_urls = direct_download_candidates("bse_takeover_open_offer")
    assert "Mkt_Pubissues_FIS_BuybackTenderoffer_isd_ng" in buyback_urls[0]
    assert "Mkt_Pubissues_FIS_Takeover_isd_ng" in takeover_urls[0]
    headers = request_headers(buyback_urls[0])
    assert headers["Origin"] == "https://www.bseindia.com"
    assert headers["Referer"] == "https://www.bseindia.com/"
    assert "Origin" not in request_headers("https://www.nseindia.com/api/test")


def test_official_mirrors_reconcile_and_ratio_conflict_fails_closed() -> None:
    agreeing = reconcile_corporate_actions(
        [
            split_row(event_id=1, source="nse_corporate_filings_actions"),
            split_row(event_id=2, source="bse_corporate_actions"),
        ],
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )
    assert len(agreeing) == 1
    assert agreeing[0].state == "RECONCILED"
    assert agreeing[0].adjustment_factor == 0.5
    assert agreeing[0].source_count == 2

    conflict = reconcile_corporate_actions(
        [
            split_row(event_id=1, source="nse_corporate_filings_actions"),
            split_row(
                event_id=2,
                source="bse_corporate_actions",
                numerator=5,
                denominator=1,
            ),
        ],
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )
    assert conflict[0].state == "CONFLICT"
    assert conflict[0].adjustment_factor is None


def test_split_is_adjusted_during_ingestion_and_integrity_passes() -> None:
    actions = reconcile_corporate_actions(
        [split_row(event_id=1, source="nse_corporate_filings_actions")],
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )
    raw = [candle(day, 200 if day < 3 else 100) for day in range(6)]
    adjusted = apply_reconciled_actions_at_ingestion(raw, actions)
    assert adjusted[0].close == 100
    assert adjusted[0].volume == 2_000
    assert adjusted[0].adjustment_status == "ADJUSTED"
    assert adjusted[0].adjustment_factor == 0.5
    assert adjusted[-1].adjustment_status == "NOT_REQUIRED"

    assessment = assess_adjustment_integrity(adjusted, actions)
    assert assessment.state == "PASS"
    assert assessment.required_action_count == 1

    bonus_row = split_row(
        event_id=3, source="nse_corporate_filings_actions", numerator=1, denominator=1
    )
    bonus_row["action_type"] = "BONUS ISSUE"
    bonus = reconcile_corporate_actions(
        [bonus_row], as_of=datetime(2026, 6, 10, tzinfo=timezone.utc)
    )
    bonus_adjusted = apply_reconciled_actions_at_ingestion(raw, bonus)
    assert bonus[0].action_class == "BONUS"
    assert bonus[0].adjustment_factor == 0.5
    assert bonus_adjusted[0].close == 100
    assert bonus_adjusted[0].volume == 2_000


def test_known_action_with_unadjusted_or_conflicting_history_is_rejected() -> None:
    raw = [candle(day, 200 if day < 3 else 100) for day in range(6)]
    reconciled = reconcile_corporate_actions(
        [split_row(event_id=1, source="nse_corporate_filings_actions")],
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )
    assert assess_adjustment_integrity(raw, reconciled).state == "REJECT_DATA_INTEGRITY"

    conflicting = reconcile_corporate_actions(
        [
            split_row(event_id=1, source="nse_corporate_filings_actions"),
            split_row(event_id=2, source="bse_corporate_actions", numerator=5),
        ],
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )
    assert (
        assess_adjustment_integrity(raw, conflicting).state == "REJECT_DATA_INTEGRITY"
    )


def test_cash_dividend_and_rights_use_reference_price_without_volume_rewrite() -> None:
    raw = [candle(day, 100 if day < 3 else 90) for day in range(6)]
    dividend = reconcile_corporate_actions(
        [cash_action_row(event_id=10, action_class="DIVIDEND", cash_amount=10)],
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )
    assert dividend[0].state == "RECONCILED"
    dividend_adjusted = apply_reconciled_actions_at_ingestion(raw, dividend)
    assert dividend_adjusted[0].close == 90
    assert dividend_adjusted[0].volume == 1_000
    assert dividend_adjusted[0].adjustment_factor == 0.9
    assert assess_adjustment_integrity(dividend_adjusted, dividend).state == "PASS"

    rights = reconcile_corporate_actions(
        [
            cash_action_row(
                event_id=11,
                action_class="RIGHTS",
                offer_price=50,
                numerator=1,
                denominator=4,
            )
        ],
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )
    assert rights[0].state == "RECONCILED"
    rights_adjusted = apply_reconciled_actions_at_ingestion(raw, rights)
    assert rights_adjusted[0].close == 90
    assert rights_adjusted[0].volume == 1_000
    assert rights_adjusted[0].adjustment_factor == 0.9
    assert assess_adjustment_integrity(rights_adjusted, rights).state == "PASS"


def test_merger_or_demerger_ratio_alone_never_authorizes_reconstruction() -> None:
    merger = reconcile_corporate_actions(
        [reconstruction_row(event_id=20, action_class="MERGER")],
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )[0]
    assert merger.state == "WAIT_DETAILS"
    assert merger.adjustment_factor is None
    assert "explicit" in merger.reason.lower()

    cross_symbol = reconcile_corporate_actions(
        [
            reconstruction_row(
                event_id=21,
                action_class="DEMERGER",
                adjustment_factor=0.72,
                successor_symbol="NEWCO",
                continuity_confirmed=True,
            )
        ],
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )[0]
    assert cross_symbol.state == "WAIT_DETAILS"
    assert "cross-symbol" in cross_symbol.reason.lower()


def test_explicit_same_symbol_reconstruction_adjusts_price_not_volume() -> None:
    actions = reconcile_corporate_actions(
        [
            reconstruction_row(
                event_id=22,
                action_class="DEMERGER",
                adjustment_factor=0.72,
                continuity_confirmed=True,
            ),
            reconstruction_row(
                event_id=23,
                action_class="DEMERGER",
                source="bse_corporate_actions",
                adjustment_factor=0.72,
                continuity_confirmed=True,
            ),
        ],
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )
    assert actions[0].state == "RECONCILED"
    assert actions[0].adjustment_factor == 0.72
    raw = [candle(day, 100 if day < 3 else 72) for day in range(6)]
    adjusted = apply_reconciled_actions_at_ingestion(raw, actions)
    assert adjusted[0].close == 72
    assert adjusted[0].volume == 1_000
    assert assess_adjustment_integrity(adjusted, actions).state == "PASS"

    conflict = reconcile_corporate_actions(
        [
            reconstruction_row(
                event_id=24,
                action_class="MERGER",
                adjustment_factor=0.72,
                continuity_confirmed=True,
            ),
            reconstruction_row(
                event_id=25,
                action_class="MERGER",
                source="bse_corporate_actions",
                adjustment_factor=0.75,
                continuity_confirmed=True,
            ),
        ],
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )[0]
    assert conflict.state == "CONFLICT"
    assert conflict.adjustment_factor is None


def test_reconstruction_terms_survive_storage_and_schema_migration(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "reconstruction.db")
    inserted = storage.save_corporate_event_observations(
        "nse_corporate_filings_actions",
        data_date="2026-06-04",
        rows=[
            {
                "symbol": "SPLITCO",
                "company": "Reconstruction Co",
                "actionType": "DEMERGER",
                "actionClass": "DEMERGER",
                "announcementDate": "2026-05-20",
                "exDate": "2026-06-04",
                "recordDate": "2026-06-05",
                "ratioNumerator": 3,
                "ratioDenominator": 2,
                "priceAdjustmentFactor": 0.72,
                "predecessorSymbol": "SPLITCO",
                "successorSymbol": "SPLITCO",
                "continuityConfirmed": True,
                "revisionStatus": "ORIGINAL",
            }
        ],
        parsed_at="2026-05-20T12:00:00+00:00",
    )
    assert inserted == 1
    stored = storage.list_corporate_event_observations(symbol="SPLITCO")[0]
    assert stored["adjustment_factor"] == 0.72
    assert stored["predecessor_symbol"] == "SPLITCO"
    assert stored["successor_symbol"] == "SPLITCO"
    assert stored["continuity_confirmed"] == 1
    assert "0008_corporate_reconstruction_terms" in {
        row["version"] for row in storage.list_schema_migrations()
    }

    actions = reconcile_corporate_actions(
        storage.list_corporate_event_observations(symbol="SPLITCO"),
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )
    assert actions[0].state == "RECONCILED"
    assert actions[0].adjustment_factor == 0.72


def test_non_adjusting_buyback_does_not_contaminate_price_integrity() -> None:
    raw = [candle(day, 100) for day in range(6)]
    buyback = reconcile_corporate_actions(
        [cash_action_row(event_id=12, action_class="BUYBACK", offer_price=120)],
        as_of=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )
    assert buyback[0].action_class == "OTHER"
    assert assess_adjustment_integrity(raw, buyback).state == "PASS"


def test_storage_applies_known_action_and_persists_lineage(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "corporate-actions.db")
    storage.save_corporate_event_observations(
        "nse_corporate_filings_actions",
        data_date="2026-06-04",
        rows=[
            {
                "symbol": "SPLITCO",
                "company": "Split Co",
                "actionType": "STOCK SPLIT",
                "actionClass": "SPLIT",
                "announcementDate": "2026-05-20",
                "exDate": "2026-06-04",
                "recordDate": "2026-06-05",
                "ratioNumerator": 2,
                "ratioDenominator": 1,
                "revisionStatus": "ORIGINAL",
            }
        ],
        parsed_at="2026-05-20T12:00:00+00:00",
    )
    storage.save_ohlcv_candles(
        [candle(day, 200 if day < 3 else 100) for day in range(6)]
    )
    stored = storage.list_ohlcv_candles("SPLITCO", "1d", source="official_fixture")
    assert stored[0].close == 100
    assert stored[0].adjustment_status == "ADJUSTED"
    assert stored[-1].adjustment_status == "NOT_REQUIRED"
    assessments = storage.list_candle_adjustment_assessments(symbol="SPLITCO")
    assert assessments[-1]["state"] == "PASS"
    assert "0006_corporate_action_adjustment_lineage" in {
        row["version"] for row in storage.list_schema_migrations()
    }
    client = TestClient(app)
    response = client.get(
        "/api/corporate-actions/SPLITCO/reconciliation",
        params={"asOf": "2026-06-10T00:00:00+00:00"},
    )
    assert response.status_code == 200
    assert response.json()["actions"][0]["state"] == "RECONCILED"
    assessments_response = client.get(
        "/api/storage/candle-adjustments", params={"symbol": "SPLITCO"}
    )
    assert assessments_response.status_code == 200
    assert assessments_response.json()[-1]["state"] == "PASS"


def test_late_action_observation_blocks_scanner_before_harmonics(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "late-action.db")
    raw = [candle(day, 200 if day < 3 else 100) for day in range(45)]
    storage.save_ohlcv_candles(raw)
    storage.save_corporate_event_observations(
        "nse_corporate_filings_actions",
        data_date="2026-06-04",
        rows=[
            {
                "symbol": "SPLITCO",
                "company": "Split Co",
                "actionType": "STOCK SPLIT",
                "actionClass": "SPLIT",
                "announcementDate": "2026-05-20",
                "exDate": "2026-06-04",
                "recordDate": "2026-06-05",
                "ratioNumerator": 2,
                "ratioDenominator": 1,
                "revisionStatus": "ORIGINAL",
            }
        ],
        parsed_at="2026-05-20T12:00:00+00:00",
    )

    def harmonic_must_not_run(*args, **kwargs):
        raise AssertionError("harmonic analysis ran before corporate-action integrity")

    monkeypatch.setattr(
        "trendforge_api.scanner_scheduler.analyze_harmonic_advanced",
        harmonic_must_not_run,
    )
    summary = ScannerScheduler().run_once(
        universe="WATCHLIST_ONLY", fetch=False, trigger="late-action-test"
    )
    assert summary["status"] == "COMPLETE"
    candidate = storage.list_scanner_candidates(run_id=summary["runId"], limit=10)[0][
        "payload"
    ]
    assert candidate["state"] == "REJECT_DATA_INTEGRITY"
    assert candidate["corporateActionIntegrity"]["state"] == "REJECT_DATA_INTEGRITY"
    decisions = storage.list_gate_decisions(run_id=str(summary["runId"]))
    assert any(
        row["gate_key"] == "CORPORATE_ACTION_INTEGRITY" and row["symbol"] == "SPLITCO"
        for row in decisions
    )

    reconciled = TestClient(app).post(
        "/api/storage/candle-adjustments/reconcile",
        json={
            "symbol": "SPLITCO",
            "timeframe": "1d",
            "source": "official_fixture",
        },
    )
    assert reconciled.status_code == 200
    assert reconciled.json()["status"] == "PASS"
    assert reconciled.json()["updatedCount"] > 0
    corrected = storage.list_ohlcv_candles("SPLITCO", "1d", source="official_fixture")
    assert corrected[0].close == 100
    assert corrected[0].adjustment_status == "ADJUSTED"
    assert storage.list_candle_revisions(symbol="SPLITCO")
