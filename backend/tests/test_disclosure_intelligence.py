from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from trendforge_api.disclosure_intelligence import (
    build_disclosure_snapshot,
    latest_disclosure_drilldown,
    save_disclosure_snapshot,
)
from trendforge_api.institutional_sources import EndpointFetchResult, FetchState


NOW = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)


def result(
    endpoint_key: str,
    payload,
    *,
    state: FetchState = FetchState.RAW_ARCHIVED,
    record_count: int = 1,
    content_hash: str = "a" * 64,
) -> EndpointFetchResult:
    return EndpointFetchResult(
        endpoint_key=endpoint_key,
        state=state,
        fetched_at=NOW,
        url=f"https://example.test/{endpoint_key}",
        content_hash=content_hash,
        raw_path=f"/raw/{content_hash}.json",
        media_type="application/json",
        record_count=record_count,
        payload=payload,
        can_score=False,
    )


def test_source_specific_normalizers_preserve_decision_fields() -> None:
    snapshot = build_disclosure_snapshot(
        [
            result(
                "nse_regulation_31",
                [
                    {
                        "symbol": "CENTRUM",
                        "companyName": "Centrum Capital Limited",
                        "mstrSeqNum": "18515",
                        "promoterName": "PROMOTER LLP",
                        "typeOfEvent": "creation",
                        "sr_dateof_creation": "10-JUL-2026",
                        "broadcastDateTime": "14-JUL-2026 02:00",
                        "numofShares": "2300000",
                        "perofShares": "0.47",
                        "pershareAlrdyheldPrmtr": "8.49",
                        "persharesPostevent": "8.96",
                        "reasonForEncumbrance": "Collateral for loan",
                        "nameOfLenderDebenture": "BANK LTD",
                    }
                ],
            ),
            result(
                "bse_bulk_deals",
                {
                    "Table": [
                        {
                            "DEAL_DATE": "2026-07-01T00:00:00",
                            "SCRIP_CODE": 512591,
                            "scripname": "PULSRIN",
                            "CLIENT_NAME": "FUND A",
                            "TRANSACTION_TYPE": "P",
                            "QUANTITY": 1000,
                            "PRICE": 12.5,
                        }
                    ]
                },
            ),
            result(
                "nse_shareholding_pattern",
                [
                    {
                        "recordId": "209982",
                        "symbol": "RELIANCE",
                        "name": "Reliance Industries Limited",
                        "date": "31-MAR-2026",
                        "submissionDate": "21-APR-2026",
                        "pr_and_prgrp": "50",
                        "public_val": "50",
                        "revisedStatus": "-",
                        "revisedData": "N",
                        "xbrl": "https://example.test/shareholding.xml",
                    }
                ],
            ),
            result(
                "bse_pledge_data",
                {
                    "Table": [
                        {
                            "ScripCode": 532609,
                            "CompanyName": "Example Ltd",
                            "MAxDate": "2019-01-31T00:00:00",
                            "SHP_PulishedTime": "2026-04-21T15:11:38.61",
                            "PROMOTEREncum_NoOfshares": 20412281,
                            "PROMOTEREncum_Percof_PromoterShares": 100.0,
                            "PROMOTEREncum_Percof_TotalShares": 40.58,
                            "Percentage_TOTAL_PROMOTER_HOLDING": 40.58,
                        }
                    ]
                },
            ),
        ]
    )

    assert snapshot.state == "RESEARCH_ONLY"
    assert snapshot.can_unlock_ready is False
    assert len(snapshot.events) == 4
    assert all(source.parser_state == "STRUCTURED_OK" for source in snapshot.sources)

    pledge = next(item for item in snapshot.events if item.source_key == "nse_regulation_31")
    assert pledge.event_type == "PLEDGE_CREATE"
    assert pledge.side == "CREATE"
    assert pledge.counterparty == "BANK LTD"
    assert pledge.quantity == 2_300_000
    assert pledge.percent_before == 8.49
    assert pledge.percent_after == 8.96

    deal = next(item for item in snapshot.events if item.source_key == "bse_bulk_deals")
    assert deal.side == "BUY"
    assert deal.actor == "FUND A"
    assert deal.notional == 12_500

    holding = next(
        item for item in snapshot.events if item.source_key == "nse_shareholding_pattern"
    )
    assert holding.promoter_holding_pct == 50
    assert holding.event_date == "2026-03-31"

    pledge_snapshot = next(
        item for item in snapshot.events if item.source_key == "bse_pledge_data"
    )
    assert pledge_snapshot.pledge_pct_promoter == 100
    assert pledge_snapshot.pledge_pct_total == 40.58


def test_valid_empty_is_not_misclassified_as_broken() -> None:
    snapshot = build_disclosure_snapshot(
        [
            result(
                "bse_block_deals",
                {"Table": []},
                state=FetchState.NO_DATA_NOW,
                record_count=0,
            )
        ]
    )

    assert snapshot.state == "WAIT_SOURCE"
    assert snapshot.sources[0].parser_state == "VALID_EMPTY"
    assert snapshot.sources[0].rejected_count == 0
    assert snapshot.events == []


def test_schema_mismatch_and_stale_data_fail_closed() -> None:
    malformed = result("nse_regulation_29", [{"unexpected": "value"}])
    stale = result(
        "bse_sast",
        [
            {
                "scrip_code": "500209",
                "Company_Name": "Infosys Ltd",
                "shareholdername": "HOLDER",
                "Acquisition_date": "10/12/2025",
                "Acq_Sale": "SALE",
                "Acq_sale_qty": "542375",
                "Acq_sale_Pct": "0.01",
                "Acquisition_Pct_After": "0.12",
            }
        ],
        state=FetchState.STALE_FALLBACK,
    )

    snapshot = build_disclosure_snapshot([malformed, stale])
    states = {item.endpoint_key: item.parser_state for item in snapshot.sources}

    assert states["nse_regulation_29"] == "SCHEMA_MISMATCH"
    assert states["bse_sast"] == "STALE_FALLBACK"
    assert snapshot.state == "WAIT_SOURCE"
    assert snapshot.can_unlock_ready is False
    assert len(snapshot.events) == 1


def test_event_level_hash_deduplicates_replayed_rows_and_keeps_run_lineage(
    tmp_path: Path,
) -> None:
    payload = {
        "Table": [
            {
                "NEWSID": "abc-123",
                "SCRIP_CD": 500325,
                "SLONGNAME": "Reliance Industries Ltd",
                "NEWSSUB": "Board meeting update",
                "DT_TM": "2026-07-10T17:48:43.49",
                "CATEGORYNAME": "Company Update",
                "ATTACHMENTNAME": "notice.pdf",
            }
        ]
    }
    first = build_disclosure_snapshot([result("bse_corporate_announcements", payload)])
    second = build_disclosure_snapshot([result("bse_corporate_announcements", payload)])
    db_path = tmp_path / "research.sqlite3"

    save_disclosure_snapshot(first, db_path)
    save_disclosure_snapshot(second, db_path)

    with sqlite3.connect(db_path) as connection:
        event_count = connection.execute(
            "SELECT COUNT(*) FROM institutional_disclosure_events"
        ).fetchone()[0]
        run_count = connection.execute(
            "SELECT COUNT(*) FROM institutional_disclosure_runs"
        ).fetchone()[0]
        lineage_count = connection.execute(
            "SELECT COUNT(*) FROM institutional_disclosure_run_events"
        ).fetchone()[0]

    assert event_count == 1
    assert run_count == 2
    assert lineage_count == 2


def test_latest_drilldown_filters_by_nse_symbol(tmp_path: Path) -> None:
    snapshot = build_disclosure_snapshot(
        [
            result(
                "nse_announcements",
                [
                    {
                        "seq_id": "1",
                        "symbol": "RELIANCE",
                        "sm_name": "Reliance Industries Limited",
                        "an_dt": "14-Jul-2026 14:58:21",
                        "desc": "Result",
                        "attchmntText": "Financial result",
                    },
                    {
                        "seq_id": "2",
                        "symbol": "TCS",
                        "sm_name": "Tata Consultancy Services Limited",
                        "an_dt": "14-Jul-2026 14:50:00",
                        "desc": "Order",
                        "attchmntText": "Contract award",
                    },
                ],
                record_count=2,
            )
        ]
    )
    db_path = tmp_path / "research.sqlite3"
    save_disclosure_snapshot(snapshot, db_path)

    drilldown = latest_disclosure_drilldown(
        symbol="reliance", limit=10, db_path=db_path
    )

    assert drilldown.event_count == 2
    assert drilldown.returned_count == 1
    assert drilldown.events[0].symbol == "RELIANCE"
    assert drilldown.can_unlock_ready is False


def test_non_disclosure_context_sources_are_not_forced_into_event_schema() -> None:
    snapshot = build_disclosure_snapshot(
        [
            result("mcx_option_chain", {"Data": [{"Symbol": "GOLD"}]}),
            result("sge_benchmark_gold", {"zp": [[1, 100.0]]}),
        ]
    )

    assert snapshot.sources == []
    assert snapshot.events == []
    assert snapshot.state == "WAIT_SOURCE"
