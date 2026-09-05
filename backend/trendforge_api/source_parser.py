from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin

from .artifact_integrity import validate_source_artifact
from .models import SourceParseResult
from .parsers import (
    parse_bse_offer_index,
    parse_amfi_nav,
    parse_amfi_monthly_aum,
    parse_amfi_portfolio,
    parse_cftc_cot_positions,
    parse_mcx_bhavcopy,
    parse_nse_large_deals,
    parse_nse_large_deals_snapshot,
    parse_bse_fii_dii,
    parse_nse_fii_dii,
    parse_nse_fno_ban,
    parse_nse_mwpl_percentages,
    parse_bse_participant_oi,
    parse_nse_participant_oi,
    parse_nse_mto_delivery,
    parse_nse_short_selling,
    parse_bse_fo_bhavcopy,
    parse_nse_preopen_cash,
    parse_bse_insider_trading,
    parse_nse_index_option_chain,
    parse_lbma_fixings,
    parse_eia_natgas_storage,
    parse_usda_wasde_index,
    parse_rbi_usdinr_html,
    parse_nse_fii_derivatives_stats_text,
    parse_dgcis_trade_html,
    parse_yahoo_chart,
    parse_mcx_json_watch,
    parse_amfi_portfolio_directory,
    parse_nse_trade_info,
    parse_nse_bulk_deals_csv,
    parse_nse_bulk_deal_symbol_json,
    parse_generic_table_or_json,
    parse_nse_fo_bhavcopy,
    parse_nse_slb,
    parse_nse_instruments,
    parse_nse_cash_bhavcopy,
    parse_nse_index_close,
    parse_nse_trading_calendar,
    parse_corporate_events,
    parse_sebi_disclosures,
    parse_fred_broad_dollar,
    parse_fred_real_yield,
    parse_eia_petroleum_stocks,
    parse_sge_daily_report,
    parse_sge_benchmark_gold,
    parse_wgc_gold_etf_series,
    parse_wgc_gold_open_interest,
    parse_bse_bhavcopy,
    parse_nse_block_deal_live,
    parse_nse_option_chain,
    parse_nse_pit_current,
    parse_bse_pledge_data,
    parse_cdsl_fpi_fortnightly_sector,
    parse_nsdl_fpi_daily,
    parse_nsdl_fpi_fortnightly,
    parse_nse_asm,
    parse_nse_auction_securities,
    parse_nse_esm,
    parse_nse_gsm,
    parse_nse_oi_spurts,
    parse_nse_pledge_data,
    parse_nse_regulation_disclosure,
    parse_kite_derivatives_contract_master,
    parse_nse_board_meetings,
    parse_nse_ipo_issue_calendar,
    parse_nse_most_active_derivatives,
    parse_nse_pr_market_snapshot,
    parse_nse_trade_to_trade,
    parse_nse_price_bands,
    parse_google_trends_india_rss,
    parse_tradingeconomics_bdi,
    parse_westmetall_lme,
    parse_yahoo_bdry_proxy,
    parse_crisil_ratings,
    parse_icra_ratings,
    parse_care_ratings,
    parse_google_news_rss,
    parse_screener_in_fii_holding_change,
    parse_tickertape_fii_holding_change_3m,
    parse_dhan_fii_holding_change,
    parse_equitymaster_fii_buys_reference,
    parse_angelone_instrument_master,
    parse_dhan_instrument_master,
    parse_nse_market_status,
    parse_rupeevest_mf_flows,
    parse_eia_steo_opec_supply,
    parse_opec_production_adjustment,
    parse_bse_financial_results_index,
    parse_bse_shareholding_index,
    parse_rbi_tbill_yield,
    parse_upstox_company_profile,
    parse_upstox_competitors,
    parse_upstox_corporate_actions,
    parse_upstox_fundamental_history,
    parse_upstox_historical_candles,
    parse_upstox_key_ratios,
    parse_upstox_market_quote,
    parse_upstox_max_pain,
    parse_upstox_open_interest,
    parse_upstox_option_chain,
    parse_upstox_option_greeks,
    parse_upstox_pcr_history,
    parse_upstox_share_holdings,
)
from .source_monitor import canonical_source_key, get_source_descriptor
from .storage import (
    get_latest_populated_source_snapshot,
    get_latest_source_snapshot,
    list_source_parse_results,
    save_source_parse_result,
)


class LinkExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_map = {key.lower(): value for key, value in attrs if value}
        href = attrs_map.get("href")
        if href:
            self._current_href = urljoin(self.base_url, href)
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href:
            text = " ".join(part for part in self._current_text if part).strip()
            self.links.append({"text": text, "url": self._current_href})
            self._current_href = None
            self._current_text = []


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_snapshot_text(raw_path: str | None) -> str:
    if not raw_path:
        return ""
    path = Path(raw_path)
    if not path.exists():
        return ""
    content = path.read_bytes()
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("latin-1", errors="replace")


def read_snapshot_bytes(raw_path: str | None) -> bytes:
    if not raw_path:
        return b""
    path = Path(raw_path)
    if not path.exists():
        return b""
    return path.read_bytes()


def wait_result(
    source_key: str, state: str, summary: str, error: str | None = None
) -> SourceParseResult:
    return SourceParseResult(
        sourceKey=source_key,
        snapshotId=None,
        parserState=state,  # type: ignore[arg-type]
        dataDate=None,
        recordCount=0,
        summary=summary,
        output={},
        error=error,
        parsedAt=now_utc(),
    )


def generic_metadata_parse(source_key: str) -> SourceParseResult:
    descriptor = get_source_descriptor(source_key)
    if descriptor is None:
        return wait_result(source_key, "NO_PARSER", f"Unknown source key: {source_key}")
    snapshot = get_latest_source_snapshot(source_key)
    if snapshot is None:
        return wait_result(
            source_key,
            "WAIT_SOURCE_SNAPSHOT",
            "Run source freshness check before parsing.",
        )
    if snapshot.check_state in {"BROKEN", "SKIPPED"}:
        return SourceParseResult(
            sourceKey=source_key,
            snapshotId=snapshot.id,
            parserState="WAIT_FETCH_REQUIRED"
            if snapshot.check_state == "SKIPPED"
            else "BROKEN",
            dataDate=snapshot.last_modified,
            recordCount=0,
            summary=f"Latest snapshot is {snapshot.check_state}; structured parser not executed.",
            output={
                "source": descriptor.name,
                "snapshotState": snapshot.check_state,
                "url": snapshot.url,
                "lastModified": snapshot.last_modified,
                "contentLength": snapshot.content_length,
            },
            error=snapshot.error,
            parsedAt=now_utc(),
        )

    return SourceParseResult(
        sourceKey=source_key,
        snapshotId=snapshot.id,
        parserState="PARSED_METADATA_ONLY",
        dataDate=snapshot.last_modified,
        recordCount=1,
        summary="Metadata parsed. Full source-specific data parser is pending.",
        output={
            "source": descriptor.name,
            "category": descriptor.category,
            "url": snapshot.url,
            "snapshotState": snapshot.check_state,
            "lastModified": snapshot.last_modified,
            "etag": snapshot.etag,
            "contentHash": snapshot.content_hash,
            "contentLength": snapshot.content_length,
            "rawPath": snapshot.raw_path,
            "limitation": descriptor.limitation,
        },
        error=None,
        parsedAt=now_utc(),
    )


def parse_cftc_cot(source_key: str = "cftc_cot") -> SourceParseResult:
    snapshot = get_latest_source_snapshot(source_key)
    if snapshot is None:
        return wait_result(
            source_key, "WAIT_SOURCE_SNAPSHOT", "Run CFTC source check before parsing."
        )
    if snapshot.check_state in {"BROKEN", "SKIPPED"}:
        return SourceParseResult(
            sourceKey=source_key,
            snapshotId=snapshot.id,
            parserState="WAIT_FETCH_REQUIRED"
            if snapshot.check_state == "SKIPPED"
            else "BROKEN",
            dataDate=snapshot.last_modified,
            recordCount=0,
            summary=f"CFTC snapshot is {snapshot.check_state}; cannot parse report links.",
            output={"snapshotState": snapshot.check_state},
            error=snapshot.error,
            parsedAt=now_utc(),
        )

    text = read_snapshot_text(snapshot.raw_path)
    extractor = LinkExtractor(snapshot.url)
    extractor.feed(text)
    report_links = []
    for link in extractor.links:
        combined = link["text"] + " " + link["url"]
        url = link["url"].lower()
        if "#" in url or "exit/index" in url:
            continue
        is_data_link = any(
            token in url
            for token in (
                "/dea/",
                "publicreporting.cftc.gov",
                "historicalcompressed",
                "historicalviewable",
                "releaseschedule",
            )
        )
        is_cot_link = bool(
            re.search(
                r"(cot|commitments?|legacy|disaggregated|futures|options|txt|csv|zip)",
                combined,
                re.I,
            )
        )
        if is_data_link and is_cot_link:
            report_links.append(link)
    unique: dict[str, dict[str, str]] = {}
    for link in report_links:
        unique[link["url"]] = link
    links = list(unique.values())[:100]

    return SourceParseResult(
        sourceKey=source_key,
        snapshotId=snapshot.id,
        parserState="PARSED_METADATA_ONLY",
        dataDate=snapshot.last_modified,
        recordCount=len(links),
        summary="CFTC COT page metadata/report links parsed. Position-level COT file parser still pending.",
        output={
            "lastModified": snapshot.last_modified,
            "contentHash": snapshot.content_hash,
            "contentLength": snapshot.content_length,
            "reportLinks": links,
            "warning": "This does not yet parse Managed Money or Commercial net positions.",
        },
        error=None,
        parsedAt=now_utc(),
    )


STRUCTURED_PARSERS: dict[str, Callable[..., dict[str, Any]]] = {
    "upstox_company_profile": parse_upstox_company_profile,
    "upstox_key_ratios": parse_upstox_key_ratios,
    "upstox_option_chain": parse_upstox_option_chain,
    "upstox_pcr_history": parse_upstox_pcr_history,
    "upstox_full_market_quote": parse_upstox_market_quote,
    "upstox_historical_candles": parse_upstox_historical_candles,
    "upstox_option_greeks": parse_upstox_option_greeks,
    "upstox_balance_sheet": parse_upstox_fundamental_history,
    "upstox_cash_flow": parse_upstox_fundamental_history,
    "upstox_income_statement": parse_upstox_fundamental_history,
    "upstox_share_holdings": parse_upstox_share_holdings,
    "upstox_corporate_actions": parse_upstox_corporate_actions,
    "upstox_competitors": parse_upstox_competitors,
    "upstox_open_interest": parse_upstox_open_interest,
    "upstox_max_pain": parse_upstox_max_pain,
    "nse_bhavcopy_eod": parse_nse_cash_bhavcopy,
    "nse_trade_to_trade": parse_nse_trade_to_trade,
    "kite_derivatives_contract_master": parse_kite_derivatives_contract_master,
    "nse_board_meetings": parse_nse_board_meetings,
    "nse_most_active_futures": parse_nse_most_active_derivatives,
    "nse_most_active_options": parse_nse_most_active_derivatives,
    "nse_ipo_issue_calendar": parse_nse_ipo_issue_calendar,
    "nse_pr_market_snapshot": parse_nse_pr_market_snapshot,
    "nse_index_close_eod": parse_nse_index_close,
    "nse_trading_calendar": parse_nse_trading_calendar,
    "nse_equity_universe": parse_nse_instruments,
    "nse_nifty500_constituents": parse_nse_instruments,
    "nse_nifty50_constituents": parse_nse_instruments,
    "cftc_cot": parse_cftc_cot_positions,
    "nse_fno_ban": parse_nse_fno_ban,
    "nse_mwpl_percentages": parse_nse_mwpl_percentages,
    "nse_participant_oi": parse_nse_participant_oi,
    "bse_participant_oi": parse_bse_participant_oi,
    "nse_mto_delivery": parse_nse_mto_delivery,
    "nse_short_selling": parse_nse_short_selling,
    "bse_fo_bhavcopy": parse_bse_fo_bhavcopy,
    "nse_preopen_cash": parse_nse_preopen_cash,
    "bse_insider_trading": parse_bse_insider_trading,
    "nse_option_chain_nifty": parse_nse_index_option_chain,
    "nse_option_chain_banknifty": parse_nse_index_option_chain,
    "nse_index_option_chain_v3": parse_nse_index_option_chain,
    "lbma_gold_silver_fix": parse_lbma_fixings,
    "eia_natgas_storage": parse_eia_natgas_storage,
    "usda_wasde_cornell": parse_usda_wasde_index,
    "rbi_fbil_usdinr": parse_rbi_usdinr_html,
    "nse_fii_derivatives_stats": parse_nse_fii_derivatives_stats_text,
    "dgcis_trade_data": parse_dgcis_trade_html,
    "cdsl_fpi_fortnightly": parse_cdsl_fpi_fortnightly_sector,
    "yahoo_cme_proxy": parse_yahoo_chart,
    "yahoo_lme_proxy": parse_yahoo_chart,
    "mcx_market_watch": parse_mcx_json_watch,
    "mcx_option_chain": parse_mcx_json_watch,
    "mcx_warehouse_stocks": parse_generic_table_or_json,
    "mcx_delivery_reports": parse_generic_table_or_json,
    "mcx_top_participants": parse_generic_table_or_json,
    "ncdex_bhavcopy": parse_generic_table_or_json,
    "amfi_portfolio_disclosure": parse_amfi_portfolio_directory,
    "nse_quote_equity_trade_info": parse_nse_trade_info,
    "nse_bulk_deal_symbol": parse_nse_bulk_deal_symbol_json,
    "nse_bulk_deals_today_csv": parse_nse_bulk_deals_csv,
    "nse_large_deals": parse_nse_large_deals,
    "nse_large_deals_snapshot": parse_nse_large_deals_snapshot,
    "nse_fii_dii": parse_nse_fii_dii,
    "bse_fii_dii": parse_bse_fii_dii,
    "amfi_nav": parse_amfi_nav,
    "amfi_monthly_aum": parse_amfi_monthly_aum,
    "tradingeconomics_bdi": parse_tradingeconomics_bdi,
    "yahoo_bdry_shipping_proxy": parse_yahoo_bdry_proxy,
    "google_trends_india_rss": parse_google_trends_india_rss,
    "crisil_ratings": parse_crisil_ratings,
    "icra_ratings": parse_icra_ratings,
    "care_ratings": parse_care_ratings,
    "google_news_rss": parse_google_news_rss,
    "screener_in_fii_holding_change": parse_screener_in_fii_holding_change,
    "tickertape_fii_holding_change_3m": parse_tickertape_fii_holding_change_3m,
    "dhan_fii_holding_change": parse_dhan_fii_holding_change,
    "equitymaster_fii_buys_reference": parse_equitymaster_fii_buys_reference,
    "angelone_instrument_master": parse_angelone_instrument_master,
    "dhan_instrument_master": parse_dhan_instrument_master,
    "nse_market_status": parse_nse_market_status,
    "rupeevest_mf_flows": parse_rupeevest_mf_flows,
    "eia_steo_opec_supply": parse_eia_steo_opec_supply,
    "opec_production_adjustment": parse_opec_production_adjustment,
    "bse_financial_results_xbrl": parse_bse_financial_results_index,
    "bse_shareholding_pattern": parse_bse_shareholding_index,
    "rbi_tbill_yield": parse_rbi_tbill_yield,
    "lme_warehouse_stocks": parse_westmetall_lme,
    "amfi_monthly_portfolio": parse_amfi_portfolio,
    "amfi_scheme_wise": parse_amfi_portfolio,
    "mcx_bhavcopy": parse_mcx_bhavcopy,
    "nse_fo_bhavcopy": parse_nse_fo_bhavcopy,
    "nse_slb": parse_nse_slb,
    "nse_corporate_filings_actions": parse_corporate_events,
    "nse_daily_buyback": parse_corporate_events,
    "bse_buyback_tender": parse_bse_offer_index,
    "bse_takeover_open_offer": parse_bse_offer_index,
    "sebi_pit_sast": parse_sebi_disclosures,
    "fred_real_yield_10y": parse_fred_real_yield,
    "fred_broad_dollar_index": parse_fred_broad_dollar,
    "eia_weekly_petroleum_stocks": parse_eia_petroleum_stocks,
    "world_gold_council_oi": parse_wgc_gold_open_interest,
    "wgc_gold_etf_holdings": parse_wgc_gold_etf_series,
    "wgc_gold_etf_flows": parse_wgc_gold_etf_series,
    "sge_daily_report": parse_sge_daily_report,
    "sge_benchmark_gold": parse_sge_benchmark_gold,
    "bse_bhavcopy_eod": parse_bse_bhavcopy,
    "nse_block_deal_live": parse_nse_block_deal_live,
    "nse_option_chain": parse_nse_option_chain,
    "nse_pit_current": parse_nse_pit_current,
    "nse_asm": parse_nse_asm,
    "nse_esm": parse_nse_esm,
    "nse_gsm": parse_nse_gsm,
    "nse_price_bands": parse_nse_price_bands,
    "nse_auction_securities": parse_nse_auction_securities,
    "nse_pledge_data": parse_nse_pledge_data,
    "bse_pledge_data": parse_bse_pledge_data,
    "nse_oi_spurts": parse_nse_oi_spurts,
    "nsdl_fpi_daily": parse_nsdl_fpi_daily,
    "nsdl_fpi_fortnightly": parse_nsdl_fpi_fortnightly,
    "cdsl_fpi_fortnightly_sector": parse_cdsl_fpi_fortnightly_sector,
    "nse_regulation_29": parse_nse_regulation_disclosure,
    "nse_regulation_31": parse_nse_regulation_disclosure,
}


def parse_source_content(
    source_key: str,
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
    response_headers: dict[str, str] | None = None,
    expected_sha256: str | None = None,
) -> SourceParseResult:
    key = canonical_source_key(source_key)
    parser = STRUCTURED_PARSERS.get(key)
    descriptor = get_source_descriptor(key)
    if parser is None:
        return wait_result(key, "NO_PARSER", f"No structured parser for {key}.")
    # Endpoint-only adapters (for example, disabled credentialed research
    # sources) intentionally do not belong to SOURCE_CATALOG: putting them
    # there would make the anonymous source monitor try to fetch them.  They
    # can still use the shared integrity/normalization path when an endpoint
    # contract supplies the URL and credentials.
    descriptor_name = descriptor.name if descriptor is not None else key
    descriptor_category = (
        descriptor.category if descriptor is not None else "credentialed_read_only"
    )
    descriptor_url = descriptor.url if descriptor is not None else (url or "")
    headers = {name.lower(): value for name, value in (response_headers or {}).items()}
    integrity = validate_source_artifact(
        content,
        url=url,
        response_content_length=headers.get("content-length"),
        expected_sha256=expected_sha256,
    )
    if integrity.state != "PASS":
        monitored_no_data = key in {
            "bse_bhavcopy_eod",
            "nse_option_chain",
            "nse_pit_current",
            "nse_block_deal_live",
        }
        return SourceParseResult(
            sourceKey=key,
            snapshotId=None,
            parserState=integrity.state,
            dataDate=None,
            recordCount=0,
            summary=f"{descriptor_name} artifact integrity check failed: {integrity.reason}",
            output={
                "source": descriptor_name,
                "category": descriptor_category,
                "url": url or descriptor_url,
                "artifactIntegrity": integrity.as_dict(),
                "endpointConnected": monitored_no_data,
                "noDataNow": monitored_no_data,
            },
            error=integrity.reason,
            parsedAt=now_utc(),
        )
    try:
        parsed = parser(content, url=url, last_modified=last_modified)
    except Exception as exc:
        return SourceParseResult(
            sourceKey=key,
            snapshotId=None,
            parserState="WAIT_PARSE_ERROR",
            dataDate=None,
            recordCount=0,
            summary=f"{descriptor_name} parser raised {type(exc).__name__}; fail-closed.",
            output={
                "source": descriptor_name,
                "category": descriptor_category,
                "url": url or descriptor_url,
                "artifactIntegrity": integrity.as_dict(),
            },
            error=str(exc),
            parsedAt=now_utc(),
        )
    return SourceParseResult(
        sourceKey=key,
        snapshotId=None,
        parserState=parsed["parser_state"],
        dataDate=parsed.get("data_date"),
        recordCount=parsed.get("record_count", 0),
        summary=parsed.get("summary", "Structured parser completed."),
        output={
            "source": descriptor_name,
            "category": descriptor_category,
            "url": url or descriptor_url,
            "artifactIntegrity": integrity.as_dict(),
            **parsed.get("output", {}),
        },
        error=parsed.get("error"),
        parsedAt=now_utc(),
    )


def structured_parse(source_key: str) -> SourceParseResult:
    descriptor = get_source_descriptor(source_key)
    if descriptor is None:
        return wait_result(source_key, "NO_PARSER", f"Unknown source key: {source_key}")
    snapshot = get_latest_source_snapshot(source_key)
    latest_fetch_state = snapshot.check_state if snapshot else None
    retained_after_fetch_failure = False
    retain_last_populated_keys = {
        "nse_bhavcopy_eod",
        "nse_trade_to_trade",
        "kite_derivatives_contract_master",
        "nse_board_meetings",
        "nse_most_active_futures",
        "nse_most_active_options",
        "nse_ipo_issue_calendar",
        "nse_pr_market_snapshot",
        "tradingeconomics_bdi",
        "yahoo_bdry_shipping_proxy",
        "google_trends_india_rss",
        "crisil_ratings",
        "icra_ratings",
        "care_ratings",
        "google_news_rss",
        "screener_in_fii_holding_change",
        "tickertape_fii_holding_change_3m",
        "dhan_fii_holding_change",
        "equitymaster_fii_buys_reference",
        "usda_wasde_cornell",
        "angelone_instrument_master",
        "dhan_instrument_master",
        "nse_market_status",
        "nse_esm",
        "nse_price_bands",
        "nse_auction_securities",
        "rupeevest_mf_flows",
    }
    if (
        snapshot is not None
        and snapshot.check_state in {"BROKEN", "SKIPPED"}
        and source_key in retain_last_populated_keys
    ):
        populated = get_latest_populated_source_snapshot(source_key)
        if populated is not None:
            snapshot = populated
            retained_after_fetch_failure = True
    if snapshot is None and source_key == "nse_fno_ban":
        snapshot = get_latest_source_snapshot("nse_mwpl_ban")
    if snapshot is None:
        return wait_result(
            source_key,
            "WAIT_SOURCE_SNAPSHOT",
            "Run source freshness check before structured parsing.",
        )
    if snapshot.check_state in {"BROKEN", "SKIPPED"}:
        return SourceParseResult(
            sourceKey=source_key,
            snapshotId=snapshot.id,
            parserState="WAIT_FETCH_REQUIRED"
            if snapshot.check_state == "SKIPPED"
            else "BROKEN",
            dataDate=snapshot.last_modified,
            recordCount=0,
            summary=f"Latest snapshot is {snapshot.check_state}; structured parser not executed.",
            output={
                "source": descriptor.name,
                "snapshotState": snapshot.check_state,
                "url": snapshot.url,
                "lastModified": snapshot.last_modified,
                "contentLength": snapshot.content_length,
            },
            error=snapshot.error,
            parsedAt=now_utc(),
        )
    content = read_snapshot_bytes(snapshot.raw_path)
    if not content:
        return SourceParseResult(
            sourceKey=source_key,
            snapshotId=snapshot.id,
            parserState="WAIT_SOURCE_SNAPSHOT",
            dataDate=snapshot.last_modified,
            recordCount=0,
            summary="Raw snapshot file is missing or empty.",
            output={
                "source": descriptor.name,
                "url": snapshot.url,
                "rawPath": snapshot.raw_path,
            },
            error="raw snapshot missing or empty",
            parsedAt=now_utc(),
        )
    try:
        parsed_result = parse_source_content(
            source_key,
            content,
            url=snapshot.url,
            last_modified=snapshot.last_modified or snapshot.checked_at,
        )
    except (
        Exception
    ) as exc:  # pragma: no cover - defensive catch for fail-closed source parsing
        parsed_result = wait_result(
            source_key,
            "WAIT_PARSE_ERROR",
            f"{descriptor.name} parser raised {type(exc).__name__}; fail-closed.",
            str(exc),
        )
    return SourceParseResult(
        sourceKey=source_key,
        snapshotId=snapshot.id,
        parserState=parsed_result.parser_state,
        dataDate=parsed_result.data_date,
        recordCount=parsed_result.record_count,
        summary=parsed_result.summary,
        output={
            "source": descriptor.name,
            "category": descriptor.category,
            "url": snapshot.url,
            "snapshotState": snapshot.check_state,
            "contentHash": snapshot.content_hash,
            "rawPath": snapshot.raw_path,
            "latestFetchState": latest_fetch_state,
            "retainedSnapshotAfterFetchFailure": retained_after_fetch_failure,
            **parsed_result.output,
        },
        error=parsed_result.error,
        parsedAt=now_utc(),
    )


PARSER_MAP = {
    "nse_bhavcopy_eod": structured_parse,
    "nse_trade_to_trade": structured_parse,
    "kite_derivatives_contract_master": structured_parse,
    "nse_board_meetings": structured_parse,
    "nse_most_active_futures": structured_parse,
    "nse_most_active_options": structured_parse,
    "nse_ipo_issue_calendar": structured_parse,
    "nse_pr_market_snapshot": structured_parse,
    "nse_index_close_eod": structured_parse,
    "nse_trading_calendar": structured_parse,
    "nse_equity_universe": structured_parse,
    "nse_nifty500_constituents": structured_parse,
    "nse_nifty50_constituents": structured_parse,
    "cftc_cot": structured_parse,
    "nse_fno_ban": structured_parse,
    "nse_mwpl_percentages": structured_parse,
    "nse_participant_oi": structured_parse,
    "bse_participant_oi": structured_parse,
    "nse_mto_delivery": structured_parse,
    "nse_short_selling": structured_parse,
    "bse_fo_bhavcopy": structured_parse,
    "nse_preopen_cash": structured_parse,
    "bse_insider_trading": structured_parse,
    "nse_option_chain_nifty": structured_parse,
    "nse_option_chain_banknifty": structured_parse,
    "nse_index_option_chain_v3": structured_parse,
    "lbma_gold_silver_fix": structured_parse,
    "eia_natgas_storage": structured_parse,
    "usda_wasde_cornell": structured_parse,
    "rbi_fbil_usdinr": structured_parse,
    "nse_fii_derivatives_stats": structured_parse,
    "dgcis_trade_data": structured_parse,
    "cdsl_fpi_fortnightly": structured_parse,
    "yahoo_cme_proxy": structured_parse,
    "yahoo_lme_proxy": structured_parse,
    "mcx_market_watch": structured_parse,
    "mcx_option_chain": structured_parse,
    "mcx_warehouse_stocks": structured_parse,
    "mcx_delivery_reports": structured_parse,
    "mcx_top_participants": structured_parse,
    "ncdex_bhavcopy": structured_parse,
    "amfi_portfolio_disclosure": structured_parse,
    "nse_quote_equity_trade_info": structured_parse,
    "nse_bulk_deal_symbol": structured_parse,
    "nse_bulk_deals_today_csv": structured_parse,
    "nse_large_deals": structured_parse,
    "nse_large_deals_snapshot": structured_parse,
    "nse_fii_dii": structured_parse,
    "bse_fii_dii": structured_parse,
    "amfi_nav": structured_parse,
    "amfi_monthly_aum": structured_parse,
    "tradingeconomics_bdi": structured_parse,
    "yahoo_bdry_shipping_proxy": structured_parse,
    "google_trends_india_rss": structured_parse,
    "crisil_ratings": structured_parse,
    "icra_ratings": structured_parse,
    "care_ratings": structured_parse,
    "google_news_rss": structured_parse,
    "screener_in_fii_holding_change": structured_parse,
    "tickertape_fii_holding_change_3m": structured_parse,
    "dhan_fii_holding_change": structured_parse,
    "equitymaster_fii_buys_reference": structured_parse,
    "angelone_instrument_master": structured_parse,
    "dhan_instrument_master": structured_parse,
    "nse_market_status": structured_parse,
    "rupeevest_mf_flows": structured_parse,
    "eia_steo_opec_supply": structured_parse,
    "opec_production_adjustment": structured_parse,
    "bse_financial_results_xbrl": structured_parse,
    "bse_shareholding_pattern": structured_parse,
    "rbi_tbill_yield": structured_parse,
    "lme_warehouse_stocks": structured_parse,
    "amfi_monthly_portfolio": structured_parse,
    "amfi_scheme_wise": structured_parse,
    "mcx_bhavcopy": structured_parse,
    "nse_fo_bhavcopy": structured_parse,
    "nse_slb": structured_parse,
    "nse_corporate_filings_actions": structured_parse,
    "nse_daily_buyback": structured_parse,
    "bse_buyback_tender": structured_parse,
    "bse_takeover_open_offer": structured_parse,
    "sebi_pit_sast": structured_parse,
    "fred_real_yield_10y": structured_parse,
    "fred_broad_dollar_index": structured_parse,
    "eia_weekly_petroleum_stocks": structured_parse,
    "world_gold_council_oi": structured_parse,
    "wgc_gold_etf_holdings": structured_parse,
    "wgc_gold_etf_flows": structured_parse,
    "sge_daily_report": structured_parse,
    "sge_benchmark_gold": structured_parse,
    "bse_bhavcopy_eod": structured_parse,
    "nse_block_deal_live": structured_parse,
    "nse_option_chain": structured_parse,
    "nse_pit_current": structured_parse,
    "nse_asm": structured_parse,
    "nse_gsm": structured_parse,
    "nse_pledge_data": structured_parse,
    "bse_pledge_data": structured_parse,
    "nse_oi_spurts": structured_parse,
    "nsdl_fpi_daily": structured_parse,
    "nsdl_fpi_fortnightly": structured_parse,
    "cdsl_fpi_fortnightly_sector": structured_parse,
    "nse_regulation_29": structured_parse,
    "nse_regulation_31": structured_parse,
}


def parse_source(source_key: str, *, save: bool = True) -> SourceParseResult:
    key = canonical_source_key(source_key)
    parser = PARSER_MAP.get(key)
    result = parser(key) if parser else generic_metadata_parse(key)
    if save:
        return save_source_parse_result(result)
    return result


def parse_sources(
    source_keys: list[str] | None = None, *, save: bool = True
) -> list[SourceParseResult]:
    keys = source_keys or [
        "nse_trading_calendar",
        "nse_equity_universe",
        "nse_nifty500_constituents",
        "nse_nifty50_constituents",
        "nse_bhavcopy_eod",
        "nse_trade_to_trade",
        "kite_derivatives_contract_master",
        "nse_board_meetings",
        "nse_most_active_futures",
        "nse_most_active_options",
        "nse_ipo_issue_calendar",
        "nse_pr_market_snapshot",
        "nse_index_close_eod",
        "nse_fii_dii",
        "nse_participant_oi",
        "nse_fno_ban",
        "nse_mwpl_percentages",
        "nse_slb",
        "nse_fo_bhavcopy",
        "nse_large_deals",
        "amfi_nav",
        "amfi_monthly_portfolio",
        "amfi_scheme_wise",
        "sebi_pit_sast",
        "nse_corporate_filings_actions",
        "nse_daily_buyback",
        "bse_buyback_tender",
        "bse_takeover_open_offer",
        "mcx_bhavcopy",
        "cftc_cot",
        "fred_real_yield_10y",
        "fred_broad_dollar_index",
        "eia_weekly_petroleum_stocks",
        "world_gold_council_oi",
        "wgc_gold_etf_holdings",
        "wgc_gold_etf_flows",
        "sge_daily_report",
        "sge_benchmark_gold",
        "bse_bhavcopy_eod",
        "nse_block_deal_live",
        "nse_option_chain",
        "nse_pit_current",
        "nse_asm",
        "nse_gsm",
        "nse_pledge_data",
        "bse_pledge_data",
        "nse_oi_spurts",
        "nsdl_fpi_daily",
        "nsdl_fpi_fortnightly",
    ]
    return [parse_source(key, save=save) for key in keys]


def source_parse_history(
    source_key: str | None = None, limit: int = 100
) -> list[SourceParseResult]:
    return list_source_parse_results(source_key=source_key, limit=limit)
