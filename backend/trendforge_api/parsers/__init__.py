"""Structured source parsers for official TrendForge data sources.

Parsers in this package are intentionally pure: they parse already-saved raw
snapshots and never fetch the internet themselves. Fetching stays in
source_monitor.py so every source has a raw hash, path, and freshness record.
"""

from .amfi_portfolio_parser import parse_amfi_portfolio
from .amfi_nav_parser import parse_amfi_nav
from .file2_context_parser import (
    parse_amfi_monthly_aum,
    parse_google_trends_india_rss,
    parse_tradingeconomics_bdi,
    parse_westmetall_lme,
    parse_yahoo_bdry_proxy,
)
from .free_recovery_global_parser import (
    parse_eia_steo_opec_supply,
    parse_opec_production_adjustment,
)
from .official_replacement_parser import (
    parse_bse_financial_results_index,
    parse_bse_shareholding_index,
    parse_rbi_tbill_yield,
)
from .upstox_readonly_parser import (
    parse_upstox_competitors,
    parse_upstox_company_profile,
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
from .crisil_ratings_parser import parse_crisil_ratings
from .icra_ratings_parser import parse_icra_ratings
from .care_ratings_parser import parse_care_ratings
from .google_news_rss_parser import parse_google_news_rss
from .third_party_fii_holding_parser import (
    parse_dhan_fii_holding_change,
    parse_equitymaster_fii_buys_reference,
    parse_screener_in_fii_holding_change,
    parse_tickertape_fii_holding_change_3m,
)
from .angelone_instrument_master_parser import parse_angelone_instrument_master
from .dhan_instrument_master_parser import parse_dhan_instrument_master
from .pack5_public_sources_parser import parse_nse_market_status, parse_rupeevest_mf_flows
from .bse_offers_parser import parse_bse_offer_index
from .bse_offer_xbrl_parser import parse_bse_offer_xbrl
from .cftc_cot_parser import parse_cftc_cot_positions
from .mcx_bhavcopy_parser import parse_mcx_bhavcopy
from .nse_large_deals_parser import parse_nse_large_deals, parse_nse_large_deals_snapshot
from .nse_fii_dii_parser import parse_bse_fii_dii, parse_nse_fii_dii
from .nse_mwpl_parser import (
    parse_nse_fno_ban,
    parse_nse_mwpl,
    parse_nse_mwpl_percentages,
)
from .nse_participant_oi_parser import parse_bse_participant_oi, parse_nse_participant_oi
from .nse_mto_short_parser import (
    parse_bse_fo_bhavcopy,
    parse_nse_mto_delivery,
    parse_nse_preopen_cash,
    parse_nse_short_selling,
)
from .phase2_screener_parsers import (
    parse_bse_insider_trading,
    parse_eia_natgas_storage,
    parse_lbma_fixings,
    parse_nse_fii_derivatives_stats_text,
    parse_nse_index_option_chain,
    parse_rbi_usdinr_html,
    parse_usda_wasde_index,
)
from .dgcis_parser import parse_dgcis_trade_html
from .finish_30_parsers import (
    parse_amfi_portfolio_directory,
    parse_generic_table_or_json,
    parse_mcx_json_watch,
    parse_nse_bulk_deal_symbol_json,
    parse_nse_bulk_deals_csv,
    parse_nse_trade_info,
    parse_yahoo_chart,
)
from .nse_fo_bhavcopy_parser import parse_nse_fo_bhavcopy
from .nse_slb_parser import parse_nse_slb
from .nse_instrument_parser import parse_nse_instruments
from .nse_cash_bhavcopy_parser import parse_nse_cash_bhavcopy
from .nse_index_close_parser import parse_nse_index_close
from .nse_trading_calendar_parser import parse_nse_trading_calendar
from .corporate_events_parser import parse_corporate_events
from .sebi_disclosure_parser import parse_sebi_disclosures
from .fred_series_parser import parse_fred_broad_dollar, parse_fred_real_yield
from .eia_petroleum_parser import parse_eia_petroleum_stocks
from .sge_daily_parser import parse_sge_benchmark_gold, parse_sge_daily_report
from .wgc_gold_parser import parse_wgc_gold_etf_series, parse_wgc_gold_open_interest
from .supplemental_market_parser import (
    parse_bse_bhavcopy,
    parse_nse_block_deal_live,
    parse_nse_option_chain,
    parse_nse_pit_current,
)
from .surveillance_pledge_fpi_parser import (
    parse_bse_pledge_data,
    parse_cdsl_fpi_fortnightly_sector,
    parse_nsdl_fpi_daily,
    parse_nsdl_fpi_fortnightly,
    parse_nse_asm,
    parse_nse_esm,
    parse_nse_gsm,
    parse_nse_oi_spurts,
    parse_nse_pledge_data,
    parse_nse_regulation_disclosure,
)
from .nse_inventory_gap_parser import (
    parse_kite_derivatives_contract_master,
    parse_nse_board_meetings,
    parse_nse_ipo_issue_calendar,
    parse_nse_most_active_derivatives,
    parse_nse_pr_market_snapshot,
    parse_nse_trade_to_trade,
)
from .tradability_source_parser import (
    parse_nse_auction_securities,
    parse_nse_price_bands,
)

__all__ = [
    "parse_amfi_portfolio",
    "parse_amfi_nav",
    "parse_amfi_monthly_aum",
    "parse_google_trends_india_rss",
    "parse_tradingeconomics_bdi",
    "parse_westmetall_lme",
    "parse_eia_steo_opec_supply",
    "parse_opec_production_adjustment",
    "parse_bse_financial_results_index",
    "parse_bse_shareholding_index",
    "parse_rbi_tbill_yield",
    "parse_upstox_company_profile",
    "parse_upstox_competitors",
    "parse_upstox_corporate_actions",
    "parse_upstox_fundamental_history",
    "parse_upstox_historical_candles",
    "parse_upstox_key_ratios",
    "parse_upstox_market_quote",
    "parse_upstox_max_pain",
    "parse_upstox_open_interest",
    "parse_upstox_option_chain",
    "parse_upstox_option_greeks",
    "parse_upstox_pcr_history",
    "parse_upstox_share_holdings",
    "parse_yahoo_bdry_proxy",
    "parse_crisil_ratings",
    "parse_icra_ratings",
    "parse_care_ratings",
    "parse_google_news_rss",
    "parse_screener_in_fii_holding_change",
    "parse_tickertape_fii_holding_change_3m",
    "parse_dhan_fii_holding_change",
    "parse_equitymaster_fii_buys_reference",
    "parse_angelone_instrument_master",
    "parse_dhan_instrument_master",
    "parse_nse_market_status",
    "parse_rupeevest_mf_flows",
    "parse_bse_offer_index",
    "parse_bse_offer_xbrl",
    "parse_cftc_cot_positions",
    "parse_mcx_bhavcopy",
    "parse_nse_large_deals",
    "parse_nse_large_deals_snapshot",
    "parse_nse_fii_dii",
    "parse_nse_fno_ban",
    "parse_nse_mwpl",
    "parse_nse_mwpl_percentages",
    "parse_nse_participant_oi",
    "parse_nse_mto_delivery",
    "parse_nse_short_selling",
    "parse_bse_fo_bhavcopy",
    "parse_nse_preopen_cash",
    "parse_bse_insider_trading",
    "parse_nse_index_option_chain",
    "parse_lbma_fixings",
    "parse_eia_natgas_storage",
    "parse_usda_wasde_index",
    "parse_rbi_usdinr_html",
    "parse_nse_fii_derivatives_stats_text",
    "parse_dgcis_trade_html",
    "parse_yahoo_chart",
    "parse_mcx_json_watch",
    "parse_amfi_portfolio_directory",
    "parse_nse_trade_info",
    "parse_nse_bulk_deals_csv",
    "parse_nse_bulk_deal_symbol_json",
    "parse_generic_table_or_json",
    "parse_nse_fo_bhavcopy",
    "parse_nse_slb",
    "parse_nse_instruments",
    "parse_nse_cash_bhavcopy",
    "parse_nse_index_close",
    "parse_nse_trading_calendar",
    "parse_corporate_events",
    "parse_sebi_disclosures",
    "parse_fred_broad_dollar",
    "parse_fred_real_yield",
    "parse_eia_petroleum_stocks",
    "parse_sge_daily_report",
    "parse_sge_benchmark_gold",
    "parse_wgc_gold_etf_series",
    "parse_wgc_gold_open_interest",
    "parse_bse_bhavcopy",
    "parse_nse_block_deal_live",
    "parse_nse_option_chain",
    "parse_nse_pit_current",
    "parse_bse_pledge_data",
    "parse_cdsl_fpi_fortnightly_sector",
    "parse_nsdl_fpi_daily",
    "parse_nsdl_fpi_fortnightly",
    "parse_nse_asm",
    "parse_nse_esm",
    "parse_nse_gsm",
    "parse_nse_oi_spurts",
    "parse_nse_pledge_data",
    "parse_nse_regulation_disclosure",
    "parse_kite_derivatives_contract_master",
    "parse_nse_board_meetings",
    "parse_nse_ipo_issue_calendar",
    "parse_nse_most_active_derivatives",
    "parse_nse_pr_market_snapshot",
    "parse_nse_trade_to_trade",
    "parse_nse_auction_securities",
    "parse_nse_price_bands",
]
