from __future__ import annotations

from datetime import datetime, timezone

from trendforge_api import storage
from trendforge_api.bse_offer_ingestion import refresh_bse_offer_documents
from trendforge_api.evidence_builder import build_symbol_evidence
from trendforge_api.models import SourceParseResult
from trendforge_api.main import app
from trendforge_api.source_monitor import source_catalog_records
from fastapi.testclient import TestClient
from trendforge_api.parsers.bse_offer_xbrl_parser import parse_bse_offer_xbrl


BUYBACK_XML = b"""<?xml version="1.0"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
             xmlns:in-capmkt="https://www.sebi.gov.in/xbrl/2023-03-31/in-capmkt">
  <xbrli:context id="MainI"><xbrli:entity><xbrli:identifier
    scheme="https://www.sebi.gov.in/in-capmkt/ScripCode">507685</xbrli:identifier>
    </xbrli:entity><xbrli:period><xbrli:instant>2026-06-09</xbrli:instant></xbrli:period>
  </xbrli:context>
  <in-capmkt:ISIN>INE075A01022</in-capmkt:ISIN>
  <in-capmkt:NameOfTheCompany>WIPRO LIMITED</in-capmkt:NameOfTheCompany>
  <in-capmkt:ScripCode>507685</in-capmkt:ScripCode>
  <in-capmkt:NSESymbol>WIPRO</in-capmkt:NSESymbol>
  <in-capmkt:PhaseOfBuyback>Pre Issue Stage</in-capmkt:PhaseOfBuyback>
  <in-capmkt:DateOfSubmissionForBuybackTenderRoute>2026-06-09</in-capmkt:DateOfSubmissionForBuybackTenderRoute>
  <in-capmkt:DateOfPublicAnnouncement>2026-05-25</in-capmkt:DateOfPublicAnnouncement>
  <in-capmkt:DateOfRecordOfBuyback>2026-06-05</in-capmkt:DateOfRecordOfBuyback>
  <in-capmkt:DateOfBuybackOpening>2026-06-11</in-capmkt:DateOfBuybackOpening>
  <in-capmkt:DateOfBuybackClosing>2026-06-17</in-capmkt:DateOfBuybackClosing>
  <in-capmkt:NumberOfSharesOfBuybackOffer>600000000</in-capmkt:NumberOfSharesOfBuybackOffer>
  <in-capmkt:BuybackPricePerShare>250</in-capmkt:BuybackPricePerShare>
  <in-capmkt:AmountOfAggregateConsiderationNotExceeding>150000000000</in-capmkt:AmountOfAggregateConsiderationNotExceeding>
</xbrli:xbrl>"""


TAKEOVER_XML = b"""<?xml version="1.0"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
             xmlns:in-capmkt="https://www.sebi.gov.in/xbrl/2023-02-28/in-capmkt">
  <xbrli:context id="MainI"><xbrli:entity><xbrli:identifier
    scheme="https://www.sebi.gov.in/in-capmkt/ISIN">INE0VI201010</xbrli:identifier>
    </xbrli:entity><xbrli:period><xbrli:instant>2026-04-11</xbrli:instant></xbrli:period>
  </xbrli:context>
  <in-capmkt:NameOfTargetCompany>SIMANDHAR IMPEX LIMITED</in-capmkt:NameOfTargetCompany>
  <in-capmkt:ISINOfTargetCompany>INE0VI201010</in-capmkt:ISINOfTargetCompany>
  <in-capmkt:TypeOfOffer>Substantial acquisition</in-capmkt:TypeOfOffer>
  <in-capmkt:NumberOfSharesFullyPaidUpToBeAquired>775310</in-capmkt:NumberOfSharesFullyPaidUpToBeAquired>
  <in-capmkt:OfferPricePerShareFullyPaidUp>30</in-capmkt:OfferPricePerShareFullyPaidUp>
  <in-capmkt:OfferSize>23260000</in-capmkt:OfferSize>
  <in-capmkt:DateOfStartOfTendering>2026-04-20</in-capmkt:DateOfStartOfTendering>
  <in-capmkt:DateOfEndOfTendering>2026-05-04</in-capmkt:DateOfEndOfTendering>
  <in-capmkt:DateOfSubmissionForTakeoverPreTenderingPhase>2026-04-11</in-capmkt:DateOfSubmissionForTakeoverPreTenderingPhase>
  <in-capmkt:NameOfAcquirer>Farmico International Private Limited</in-capmkt:NameOfAcquirer>
</xbrli:xbrl>"""


def test_buyback_xbrl_extracts_trade_relevant_terms() -> None:
    result = parse_bse_offer_xbrl(
        BUYBACK_XML,
        url="https://www.bseindia.com/XBRLFILES/BTRUploadDocument/pre.xml",
        last_modified="Tue, 09 Jun 2026 00:47:18 GMT",
    )
    assert result["parser_state"] == "PARSED_STRUCTURED"
    assert result["data_date"] == "2026-06-09"
    row = result["output"]["rows"][0]
    assert row["offerType"] == "BUYBACK_TENDER"
    assert row["symbol"] == "WIPRO"
    assert row["scripCode"] == "507685"
    assert row["offerPrice"] == 250
    assert row["quantity"] == 600_000_000
    assert row["recordDate"] == "2026-06-05"


def test_takeover_xbrl_extracts_acquirer_and_offer_anchor() -> None:
    result = parse_bse_offer_xbrl(
        TAKEOVER_XML,
        url="https://www.bseindia.com/XBRLFILES/TakeoverPreUploadDocument/pre.xml",
        last_modified="2026-04-11T12:00:00+05:30",
    )
    assert result["parser_state"] == "PARSED_STRUCTURED"
    row = result["output"]["rows"][0]
    assert row["offerType"] == "TAKEOVER_OPEN_OFFER"
    assert row["isin"] == "INE0VI201010"
    assert row["offerPrice"] == 30
    assert row["quantity"] == 775_310
    assert row["acquirers"] == ["Farmico International Private Limited"]


def test_xbrl_fails_closed_for_doctype_or_missing_terms() -> None:
    unsafe = b'<!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><x>&xxe;</x>'
    unsafe_result = parse_bse_offer_xbrl(unsafe, url="https://example.test/a.xml")
    assert unsafe_result["parser_state"] == "WAIT_PARSE_ERROR"
    assert unsafe_result["record_count"] == 0

    incomplete = b"<xbrl><NameOfTheCompany>NO TERMS LTD</NameOfTheCompany></xbrl>"
    incomplete_result = parse_bse_offer_xbrl(
        incomplete, url="https://www.bseindia.com/XBRLFILES/BTR/incomplete.xml"
    )
    assert incomplete_result["parser_state"] == "WAIT_EMPTY_PARSE"

    zero_terms = BUYBACK_XML.replace(
        b"<in-capmkt:BuybackPricePerShare>250</in-capmkt:BuybackPricePerShare>",
        b"<in-capmkt:BuybackPricePerShare>0</in-capmkt:BuybackPricePerShare>",
    ).replace(
        b"<in-capmkt:NumberOfSharesOfBuybackOffer>600000000</in-capmkt:NumberOfSharesOfBuybackOffer>",
        b"<in-capmkt:NumberOfSharesOfBuybackOffer>0</in-capmkt:NumberOfSharesOfBuybackOffer>",
    )
    zero_result = parse_bse_offer_xbrl(
        zero_terms,
        url="https://www.bseindia.com/XBRLFILES/BTRUploadDocument/post.xml",
    )
    assert zero_result["parser_state"] == "WAIT_EMPTY_PARSE"
    assert zero_result["record_count"] == 0


def test_offer_document_and_event_storage_is_idempotent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "bse-offers.db")
    parsed = parse_bse_offer_xbrl(
        BUYBACK_XML,
        url="https://www.bseindia.com/XBRLFILES/BTRUploadDocument/pre.xml",
        last_modified="Tue, 09 Jun 2026 00:47:18 GMT",
    )
    artifact = {
        "parent_source_key": "bse_buyback_tender",
        "company_id": "3483",
        "offer_type": "BUYBACK_TENDER",
        "phase": "PRE",
        "document_url": "https://www.bseindia.com/XBRLFILES/BTRUploadDocument/pre.xml",
        "published_date": "2026-06-09",
        "revision_status": "NEW",
        "fetched_at": "2026-07-11T12:00:00+00:00",
        "status_code": 200,
        "content_hash": "abc123",
        "raw_path": "data/raw/pre.xml",
        "parser_state": parsed["parser_state"],
        "data_date": parsed["data_date"],
        "payload": parsed["output"],
        "error": None,
    }
    first = storage.save_bse_offer_document(artifact)
    second = storage.save_bse_offer_document(artifact)
    assert first == second
    documents = storage.list_bse_offer_documents()
    events = storage.list_corporate_offer_events(symbol="WIPRO")
    assert len(documents) == 1
    assert len(events) == 1
    assert events[0]["offer_price"] == 250
    assert events[0]["document_hash"] == "abc123"
    assert "0007_bse_offer_xbrl_lineage" in {
        row["version"] for row in storage.list_schema_migrations()
    }
    claims = build_symbol_evidence(
        "WIPRO", as_of=datetime(2026, 7, 12, tzinfo=timezone.utc)
    )
    offer_claims = [
        claim for claim in claims if claim.signal_type == "FORCED_CORPORATE_FLOW"
    ]
    assert len(offer_claims) == 1
    assert offer_claims[0].layer == "CAUSE"
    assert "INR 250" in offer_claims[0].explanation

    revised_payload = parsed["output"].copy()
    revised_payload["rows"] = [dict(parsed["output"]["rows"][0])]
    revised_payload["rows"][0]["offerPrice"] = 260
    revised = {
        **artifact,
        "document_url": "https://www.bseindia.com/XBRLFILES/BTRUploadDocument/revised.xml",
        "published_date": "2026-06-10",
        "revision_status": "REVISED",
        "content_hash": "def456",
        "data_date": "2026-06-10",
        "payload": revised_payload,
    }
    storage.save_bse_offer_document(revised)
    current = storage.list_corporate_offer_events(symbol="WIPRO")
    history = storage.list_corporate_offer_events(symbol="WIPRO", current_only=False)
    assert len(current) == 1
    assert current[0]["offer_price"] == 260
    assert len(history) == 2
    assert sum(row["is_current"] for row in history) == 1


def test_bounded_refresh_uses_saved_index_and_skips_same_version(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "refresh.db")
    storage.save_source_parse_result(
        SourceParseResult(
            sourceKey="bse_buyback_tender",
            snapshotId=1,
            parserState="PARSED_METADATA_ONLY",
            dataDate="2026-06-09",
            recordCount=1,
            summary="fixture index",
            output={
                "rows": [
                    {
                        "company": "WIPRO LIMITED",
                        "bseCompanyId": "3483",
                        "scripCode": "507685",
                        "offerType": "BUYBACK_TENDER",
                        "preDocumentUrl": "https://example.test/pre.xml",
                        "postDocumentUrl": None,
                        "prePublishedAt": "2026-06-09",
                        "preRevisionStatus": "NEW",
                    }
                ]
            },
            parsedAt="2026-07-11T12:00:00+00:00",
        )
    )
    calls: list[str] = []

    def fake_fetch(url: str, timeout_seconds: int):
        calls.append(url)
        assert timeout_seconds == 5
        return 200, {"last-modified": "Tue, 09 Jun 2026 00:47:18 GMT"}, BUYBACK_XML

    first = refresh_bse_offer_documents(
        "bse_buyback_tender",
        max_documents=1,
        timeout_seconds=5,
        fetcher=fake_fetch,
    )
    assert first["state"] == "STRUCTURED_OK"
    assert first["saved"] == 1
    assert len(calls) == 1

    second = refresh_bse_offer_documents(
        "bse_buyback_tender",
        max_documents=1,
        timeout_seconds=5,
        fetcher=fake_fetch,
    )
    assert second["attempted"] == 0
    assert second["skipped"] == 1
    assert second["state"] == "STRUCTURED_OK"
    assert len(calls) == 1


def test_offer_evidence_uses_pit_isin_mapping_and_ignores_zero_legacy_rows(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "offer-identity.db")
    storage.init_db()
    conn = storage.connect()
    try:
        conn.execute(
            """
            INSERT INTO nse_instruments (
                data_date, symbol, company, series, isin, active, parsed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2026-07-01",
                "SIMANDHAR",
                "SIMANDHAR IMPEX LIMITED",
                "EQ",
                "INE0VI201010",
                1,
                "2026-07-01T18:00:00+00:00",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    parsed = parse_bse_offer_xbrl(
        TAKEOVER_XML,
        url="https://www.bseindia.com/XBRLFILES/TakeoverPreUploadDocument/pre.xml",
        last_modified="2026-04-11T12:00:00+05:30",
    )
    storage.save_bse_offer_document(
        {
            "parent_source_key": "bse_takeover_open_offer",
            "company_id": "14457",
            "scrip_code": "544662",
            "offer_type": "TAKEOVER_OPEN_OFFER",
            "phase": "PRE",
            "document_url": "https://www.bseindia.com/XBRLFILES/TakeoverPreUploadDocument/pre.xml",
            "published_date": "2026-04-11",
            "revision_status": "NEW",
            "fetched_at": "2026-07-11T12:00:00+00:00",
            "status_code": 200,
            "content_hash": "takeover-positive",
            "raw_path": "data/raw/takeover-pre.xml",
            "parser_state": parsed["parser_state"],
            "data_date": parsed["data_date"],
            "payload": parsed["output"],
            "error": None,
        }
    )
    zero_payload = {
        "scope": "CORPORATE_OFFER_TERMS",
        "rows": [
            {
                "symbol": "ZEROPOST",
                "scripCode": "500000",
                "isin": "INE000X01010",
                "company": "ZERO POST LIMITED",
                "offerType": "BUYBACK_TENDER",
                "phase": "POST",
                "offerPrice": 0,
                "quantity": 0,
                "announcementDate": "2026-07-01",
                "scope": "CORPORATE_OFFER_TERMS",
            }
        ],
    }
    storage.save_bse_offer_document(
        {
            "parent_source_key": "bse_buyback_tender",
            "company_id": "legacy-zero",
            "offer_type": "BUYBACK_TENDER",
            "phase": "POST",
            "document_url": "https://example.test/legacy-zero.xml",
            "published_date": "2026-07-01",
            "revision_status": "NEW",
            "fetched_at": "2026-07-11T12:00:00+00:00",
            "status_code": 200,
            "content_hash": "legacy-zero",
            "raw_path": "data/raw/legacy-zero.xml",
            "parser_state": "PARSED_STRUCTURED",
            "data_date": "2026-07-01",
            "payload": zero_payload,
            "error": None,
        }
    )

    mapped_claims = build_symbol_evidence(
        "SIMANDHAR", as_of=datetime(2026, 7, 12, tzinfo=timezone.utc)
    )
    assert len(mapped_claims) == 1
    assert "INR 30" in mapped_claims[0].explanation
    assert build_symbol_evidence(
        "ZEROPOST", as_of=datetime(2026, 7, 12, tzinfo=timezone.utc)
    ) == []


def test_bse_offer_api_exposes_lineage_without_execution(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "bse-api.db")
    client = TestClient(app)
    waiting = client.post(
        "/api/bse-offers/xbrl/refresh",
        params={"sourceKey": "bse_buyback_tender", "maxDocuments": 1},
    )
    assert waiting.status_code == 200
    assert waiting.json()["state"] == "WAIT_INDEX_METADATA"
    assert waiting.json()["executable"] is False
    assert client.get("/api/bse-offers/xbrl/documents").json() == []
    assert client.get("/api/bse-offers/events").json() == []


def test_source_catalog_does_not_overclaim_unrelated_live_verification() -> None:
    catalog = {row.key: row for row in source_catalog_records()}
    assert "XBRL_DETAIL_LIVE_VERIFIED" in catalog["bse_buyback_tender"].parser_status
    assert (
        "XBRL_DETAIL_LIVE_VERIFIED" in catalog["bse_takeover_open_offer"].parser_status
    )
    assert (
        "OPEN_POSITION_ARTIFACT_LIVE_VERIFIED_2026_07_13"
        in catalog["nse_slb"].parser_status
    )
    assert (
        "LIVE_ARTIFACT_VERIFIED_2026_07_11" in catalog["nse_fo_bhavcopy"].parser_status
    )
