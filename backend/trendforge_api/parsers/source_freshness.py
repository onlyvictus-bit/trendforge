from __future__ import annotations

from datetime import date, datetime, timedelta


FRESHNESS_WINDOWS = {
    "nse_bhavcopy_eod": timedelta(days=2),
    "nse_trade_to_trade": timedelta(days=2),
    "kite_derivatives_contract_master": timedelta(days=2),
    "nse_board_meetings": timedelta(days=2),
    "nse_most_active_futures": timedelta(days=1),
    "nse_most_active_options": timedelta(days=1),
    "nse_ipo_issue_calendar": timedelta(days=2),
    "nse_pr_market_snapshot": timedelta(days=2),
    "nse_index_close_eod": timedelta(days=2),
    "nse_trading_calendar": timedelta(days=45),
    "nse_equity_universe": timedelta(days=2),
    "nse_nifty500_constituents": timedelta(days=45),
    "nse_nifty50_constituents": timedelta(days=45),
    "cftc_cot": timedelta(days=8),
    "nse_fno_ban": timedelta(days=2),
    "nse_mwpl_ban": timedelta(days=2),
    "nse_mwpl_percentages": timedelta(days=2),
    "nse_participant_oi": timedelta(days=2),
    "nse_large_deals": timedelta(days=2),
    "nse_fii_dii": timedelta(days=2),
    "amfi_nav": timedelta(days=2),
    "bse_bhavcopy_eod": timedelta(days=2),
    "nse_block_deal_live": timedelta(days=2),
    "nse_option_chain": timedelta(days=1),
    "nse_pit_current": timedelta(days=2),
    "nse_asm": timedelta(days=2),
    "nse_gsm": timedelta(days=2),
    "nse_esm": timedelta(days=8),
    "nse_price_bands": timedelta(days=2),
    "nse_auction_securities": timedelta(days=93),
    "nse_pledge_data": timedelta(days=120),
    "nse_oi_spurts": timedelta(days=2),
    "nsdl_fpi_daily": timedelta(days=2),
    "amfi_monthly_portfolio": timedelta(days=45),
    "amfi_scheme_wise": timedelta(days=120),
    "mcx_bhavcopy": timedelta(days=2),
    "nse_fo_bhavcopy": timedelta(days=2),
    "usd_inr": timedelta(days=1),
    "nse_slb": timedelta(days=2),
    "nse_corporate_filings_actions": timedelta(days=3),
    "nse_daily_buyback": timedelta(days=3),
    "bse_buyback_tender": timedelta(days=3),
    "bse_takeover_open_offer": timedelta(days=3),
    "sebi_pit_sast": timedelta(days=3),
    "fred_real_yield_10y": timedelta(days=5),
    "fred_broad_dollar_index": timedelta(days=5),
    "eia_weekly_petroleum_stocks": timedelta(days=10),
    "world_gold_council_oi": timedelta(days=10),
    "wgc_gold_etf_holdings": timedelta(days=10),
    "wgc_gold_etf_flows": timedelta(days=10),
    "sge_daily_report": timedelta(days=3),
    "tradingeconomics_bdi": timedelta(days=4),
    "yahoo_bdry_shipping_proxy": timedelta(days=4),
    "google_trends_india_rss": timedelta(days=1),
    "crisil_ratings": timedelta(days=4),
    "icra_ratings": timedelta(days=4),
    "care_ratings": timedelta(days=4),
    "google_news_rss": timedelta(days=1),
    "usda_wasde_cornell": timedelta(days=40),
    "angelone_instrument_master": timedelta(days=2),
    "dhan_instrument_master": timedelta(days=2),
}

BUSINESS_DAY_SOURCES = {
    "nse_bhavcopy_eod",
    "nse_trade_to_trade",
    "kite_derivatives_contract_master",
    "nse_board_meetings",
    "nse_most_active_futures",
    "nse_most_active_options",
    "nse_ipo_issue_calendar",
    "nse_pr_market_snapshot",
    "nse_index_close_eod",
    "nse_equity_universe",
    "nse_fno_ban",
    "nse_mwpl_ban",
    "nse_mwpl_percentages",
    "nse_participant_oi",
    "nse_large_deals",
    "nse_fii_dii",
    "amfi_nav",
    "bse_bhavcopy_eod",
    "nse_block_deal_live",
    "nse_option_chain",
    "nse_pit_current",
    "nse_asm",
    "nse_gsm",
    "nse_esm",
    "nse_price_bands",
    "nse_oi_spurts",
    "nsdl_fpi_daily",
    "mcx_bhavcopy",
    "nse_fo_bhavcopy",
    "usd_inr",
    "nse_slb",
    "nse_corporate_filings_actions",
    "nse_daily_buyback",
    "bse_buyback_tender",
    "bse_takeover_open_offer",
    "sebi_pit_sast",
    "fred_real_yield_10y",
    "fred_broad_dollar_index",
    "sge_daily_report",
    "tradingeconomics_bdi",
    "yahoo_bdry_shipping_proxy",
    "crisil_ratings",
    "icra_ratings",
    "care_ratings",
}


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None


def is_data_date_fresh(
    source_key: str, data_date: str | None, now: date | None = None
) -> bool:
    parsed = parse_iso_date(data_date)
    if parsed is None:
        return False
    current = now or date.today()
    window = FRESHNESS_WINDOWS.get(source_key.lower())
    if window is None:
        return False
    if parsed > current:
        if source_key.lower() in {"nse_fno_ban", "nse_mwpl_ban"}:
            return _business_days_between(current, parsed) <= 1
        return False
    if source_key.lower() == "cftc_cot":
        return parsed >= _expected_cftc_report_date(current)
    if source_key.lower() in BUSINESS_DAY_SOURCES:
        return _business_days_between(parsed, current) <= window.days
    return current - parsed <= window


def stale_reason(
    source_key: str, data_date: str | None, now: date | None = None
) -> str:
    parsed = parse_iso_date(data_date)
    if parsed is None:
        return "missing or unparseable data_date"
    current = now or date.today()
    window = FRESHNESS_WINDOWS.get(source_key.lower())
    if window is None:
        return "unknown source freshness window"
    if source_key.lower() in {"nse_fno_ban", "nse_mwpl_ban"} and parsed > current:
        lead = _business_days_between(current, parsed)
        return f"ban file applies {lead} business day(s) ahead; maximum allowed is 1"
    if source_key.lower() == "cftc_cot":
        expected = _expected_cftc_report_date(current)
        return (
            f"latest expected CFTC Tuesday report date is {expected.isoformat()}; "
            f"parsed report date is {parsed.isoformat()}"
        )
    if source_key.lower() in BUSINESS_DAY_SOURCES:
        business_age = _business_days_between(parsed, current)
        return f"data_date age {business_age} business day(s), allowed {window.days} business day(s)"
    calendar_age = current - parsed
    return f"data_date age {calendar_age.days} day(s), allowed {window.days} day(s)"


def _business_days_between(start: date, end: date) -> int:
    if end <= start:
        return 0
    count = 0
    cursor = start
    while cursor < end:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            count += 1
    return count


def _expected_cftc_report_date(current: date) -> date:
    """Return the latest Tuesday report expected to be public by IST date.

    CFTC normally publishes Friday afternoon US time, which is Friday night or
    Saturday in India. Through Friday, the prior Tuesday remains authoritative;
    from Saturday, the current week's Tuesday is required.
    """
    current_week_tuesday = current - timedelta(days=(current.weekday() - 1) % 7)
    if current.weekday() <= 4:
        return current_week_tuesday - timedelta(days=7)
    return current_week_tuesday
