"""CROSS-004 / TDG-GAP-014 named source contracts for PRF-001..007.

This registry defines source dependencies only. Registration is not freshness,
usable data, source activation, evidence acceptance, or confirmation.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from ..source_inventory_compiler import compile_default_inventory


class MatchPolicy(StrEnum):
    ALL_OF = "ALL_OF"
    ANY_OF = "ANY_OF"


class SourceGroup(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

    group_id: str = Field(alias="groupId")
    purpose: str
    evidence_family: str = Field(alias="evidenceFamily")
    match_policy: MatchPolicy = Field(alias="matchPolicy")
    source_keys: tuple[str, ...] = Field(alias="sourceKeys")
    registered_keys: tuple[str, ...] = Field(alias="registeredKeys")
    missing_keys: tuple[str, ...] = Field(alias="missingKeys")
    contract_covered: bool = Field(alias="contractCovered")
    live_data_required: bool = Field(alias="liveDataRequired")
    delayed_context_only: bool = Field(default=False, alias="delayedContextOnly")


class StrategySourceProfile(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

    profile_id: str = Field(alias="profileId")
    name: str
    market: str
    horizon: str
    mandatory: tuple[SourceGroup, ...]
    confirmations: tuple[SourceGroup, ...]
    vetoes: tuple[SourceGroup, ...]
    registration_complete: bool = Field(alias="registrationComplete")
    source_activation_ready: bool = Field(default=False, alias="sourceActivationReady")
    can_unlock_confirmed: bool = Field(default=False, alias="canUnlockConfirmed")
    executable: bool = False
    state_ceiling_without_live_acceptance: str = Field(
        default="WAIT", alias="stateCeilingWithoutLiveAcceptance"
    )
    rule: str


class StrategySourceRegistry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

    contract: str = "trendforge.strategy-source-contracts.v1"
    profile_count: int = Field(alias="profileCount")
    source_activation_ready: bool = Field(default=False, alias="sourceActivationReady")
    can_unlock_confirmed: bool = Field(default=False, alias="canUnlockConfirmed")
    executable: bool = False
    profiles: tuple[StrategySourceProfile, ...]
    note: str


def _g(
    group_id: str,
    purpose: str,
    family: str,
    keys: tuple[str, ...],
    *,
    policy: MatchPolicy = MatchPolicy.ALL_OF,
    live: bool = False,
    delayed: bool = False,
) -> dict[str, object]:
    return {
        "group_id": group_id,
        "purpose": purpose,
        "evidence_family": family,
        "match_policy": policy,
        "source_keys": keys,
        "live_data_required": live,
        "delayed_context_only": delayed,
    }


NSE_SAFETY = (
    _g("NSE_IDENTITY", "Instrument identity", "IDENTITY", ("nse_equity_universe",)),
    _g("NSE_CALENDAR", "Trading session calendar", "MARKET", ("nse_trading_calendar",)),
    _g("NSE_CA", "Corporate-action adjustment state", "SAFETY", ("nse_corporate_filings_actions",)),
)

NSE_VETOES = (
    _g("NSE_ASM", "ASM restriction", "SAFETY", ("nse_asm",)),
    _g("NSE_GSM", "GSM restriction", "SAFETY", ("nse_gsm",)),
    _g("NSE_FNO_BAN", "F&O-ban hard veto when derivatives are used", "SAFETY", ("nse_fno_ban",)),
)

MCX_SAFETY = (
    _g("MCX_LOCAL", "Local contract price/OI", "STRUCTURE", ("mcx_bhavcopy",)),
    _g(
        "MCX_MASTER",
        "Contract identity, lot, tick and expiry",
        "IDENTITY",
        ("mcx_market_watch", "mcx_future_prices"),
        policy=MatchPolicy.ANY_OF,
    ),
    _g("MCX_CALENDAR", "Commodity session calendar", "MARKET", ("mcx_trading_holidays",)),
    _g("MCX_FX", "Validated USD/INR context", "MARKET", ("fbil_usdinr_reference", "rbi_fbil_usdinr"), policy=MatchPolicy.ANY_OF),
)

PROFILE_DEFINITIONS: tuple[dict[str, object], ...] = (
    {
        "profile_id": "PRF-001",
        "name": "NSE intraday continuation",
        "market": "NSE",
        "horizon": "INTRADAY",
        "mandatory": NSE_SAFETY + (
            _g("INTRA_BARS", "Fresh quote and closed intraday bars", "STRUCTURE", ("openalgo_intraday_candles",), live=True),
            _g("INTRA_LIQUIDITY", "Spread and trade-quality checks", "PARTICIPATION", ("nse_quote_equity_trade_info",), live=True),
            _g("INTRA_REGIME", "Sector and index regime", "MARKET", ("nse_sector_constituents", "nse_all_indices")),
            _g("INTRA_RVOL", "Time-of-day relative volume discovery", "PARTICIPATION", ("nse_volume_gainers", "nse_most_active_volume"), policy=MatchPolicy.ANY_OF, live=True),
        ),
        "confirmations": (
            _g("INTRA_OI", "Independent OI participation", "DERIVATIVES", ("nse_oi_spurts_contracts", "nse_fo_bhavcopy"), policy=MatchPolicy.ANY_OF),
            _g("INTRA_EVENT", "Material event context", "EVENT", ("nse_announcements", "bse_corporate_announcements"), policy=MatchPolicy.ANY_OF),
        ),
        "vetoes": NSE_VETOES,
        "rule": "Closed intraday structure plus participation and regime; no verified live bars means WAIT.",
    },
    {
        "profile_id": "PRF-002",
        "name": "NSE intraday reversal",
        "market": "NSE",
        "horizon": "INTRADAY",
        "mandatory": NSE_SAFETY + (
            _g("REVERSAL_BARS", "Failed acceptance and closed reclaim bars", "STRUCTURE", ("openalgo_intraday_candles",), live=True),
            _g("REVERSAL_LIQUIDITY", "Spread and trade-quality checks", "PARTICIPATION", ("nse_quote_equity_trade_info",), live=True),
            _g("REVERSAL_REGIME", "Sector/index divergence", "MARKET", ("nse_sector_constituents", "nse_all_indices")),
        ),
        "confirmations": (
            _g("REVERSAL_OI", "Covering or unwinding context", "DERIVATIVES", ("nse_oi_spurts_contracts", "nse_fo_bhavcopy"), policy=MatchPolicy.ANY_OF),
            _g("REVERSAL_AUCTION", "Pre-open auction context", "MARKET", ("nse_preopen_cash", "nse_preopen_fo"), policy=MatchPolicy.ANY_OF),
        ),
        "vetoes": NSE_VETOES,
        "rule": "A large move or gap alone is insufficient; failed acceptance and reclaim must close.",
    },
    {
        "profile_id": "PRF-003",
        "name": "NSE swing continuation",
        "market": "NSE",
        "horizon": "SWING_EOD",
        "mandatory": NSE_SAFETY + (
            _g("SWING_BARS", "Adjusted closed EOD bars", "STRUCTURE", ("nse_bhavcopy_eod",)),
            _g("SWING_RS", "Stock/sector relative strength", "MARKET", ("nse_sector_constituents", "nse_all_indices")),
            _g("SWING_PARTICIPATION", "Delivery or volume participation", "PARTICIPATION", ("nse_mto_delivery", "nse_bhavcopy_eod"), policy=MatchPolicy.ANY_OF),
        ),
        "confirmations": (
            _g("SWING_RESULTS", "Official results/event support", "EVENT", ("nse_financial_results", "bse_financial_results_xbrl"), policy=MatchPolicy.ANY_OF),
            _g("SWING_DEALS", "Large-deal direction and acceptance", "EVENT", ("nse_large_deals", "bse_bulk_deals", "bse_block_deals"), policy=MatchPolicy.ANY_OF),
        ),
        "vetoes": NSE_VETOES,
        "rule": "Closed adjusted EOD acceptance plus one independent family and no unresolved event risk.",
    },
    {
        "profile_id": "PRF-004",
        "name": "NSE event and accumulation",
        "market": "NSE",
        "horizon": "SWING_EVENT",
        "mandatory": NSE_SAFETY + (
            _g("EVENT_BARS", "Post-event adjusted price acceptance", "STRUCTURE", ("nse_bhavcopy_eod",)),
            _g("EVENT_ACTOR", "Official actor-level event", "EVENT", ("nse_pit_current", "nse_pit_symbol", "bse_insider_trading"), policy=MatchPolicy.ANY_OF),
        ),
        "confirmations": (
            _g("EVENT_OWNERSHIP", "Delayed ownership/sponsor context", "OWNERSHIP", ("nse_shareholding_pattern", "amfi_monthly_portfolio", "nsdl_fpi_daily"), policy=MatchPolicy.ANY_OF, delayed=True),
            _g("EVENT_PLEDGE", "Promoter pledge context", "SAFETY", ("nse_pledge_data", "bse_pledge_data"), policy=MatchPolicy.ANY_OF),
            _g("EVENT_DEALS", "Deal direction and later price acceptance", "EVENT", ("nse_large_deals", "bse_bulk_deals", "bse_block_deals"), policy=MatchPolicy.ANY_OF),
        ),
        "vetoes": NSE_VETOES,
        "rule": "Official actor claim plus post-publication price acceptance; aggregate flows cannot satisfy actor identity.",
    },
    {
        "profile_id": "PRF-005",
        "name": "MCX precious metals",
        "market": "MCX",
        "horizon": "INTRADAY_AND_SWING",
        "mandatory": MCX_SAFETY,
        "confirmations": (
            _g("METALS_CFTC", "Weekly positioning context", "MACRO", ("cftc_cot", "cftc_disagg_futures_only"), policy=MatchPolicy.ANY_OF, delayed=True),
            _g("METALS_RATES", "Dollar and real-yield context", "MACRO", ("fred_real_yield_10y", "fred_broad_dollar_index"), delayed=True),
            _g("METALS_GOLD", "Gold inventory/flow context", "MACRO", ("wgc_gold_etf_holdings", "wgc_gold_etf_flows", "sge_benchmark_gold"), policy=MatchPolicy.ANY_OF, delayed=True),
        ),
        "vetoes": (
            _g("MCX_DELIVERY", "Delivery/tender/expiry restriction", "SAFETY", ("mcx_delivery_reports", "mcx_circulars"), policy=MatchPolicy.ANY_OF),
        ),
        "rule": "Local MCX contract evidence leads; CFTC/WGC/SGE are delayed context and never intraday proof.",
    },
    {
        "profile_id": "PRF-006",
        "name": "MCX energy",
        "market": "MCX",
        "horizon": "INTRADAY_AND_SWING",
        "mandatory": MCX_SAFETY,
        "confirmations": (
            _g("ENERGY_EIA", "Released petroleum inventory context", "MACRO", ("eia_weekly_petroleum_stocks",), delayed=True),
            _g("ENERGY_RIGS", "Rig-count supply context", "MACRO", ("baker_hughes_na_rig_count",), delayed=True),
            _g("ENERGY_CFTC", "Weekly positioning context", "MACRO", ("cftc_cot",), delayed=True),
        ),
        "vetoes": (
            _g("ENERGY_DELIVERY", "Delivery/tender/expiry restriction", "SAFETY", ("mcx_delivery_reports", "mcx_circulars"), policy=MatchPolicy.ANY_OF),
        ),
        "rule": "Local price/OI leads; delayed EIA and CFTC context use publication timestamps and revisions.",
    },
    {
        "profile_id": "PRF-007",
        "name": "MCX base metals and agriculture",
        "market": "MCX",
        "horizon": "INTRADAY_AND_SWING",
        "mandatory": MCX_SAFETY,
        "confirmations": (
            _g("BASE_STOCKS", "Exchange warehouse context", "MACRO", ("lme_warehouse_stocks", "shfe_weekly_stock"), policy=MatchPolicy.ANY_OF, delayed=True),
            _g("TRADE_FLOW", "Official trade context", "MACRO", ("dgcis_trade_data",), delayed=True),
            _g("AGRI_WEATHER", "Weather/crop context", "MACRO", ("imd_rainfall_timeseries", "usda_wasde"), policy=MatchPolicy.ANY_OF, delayed=True),
        ),
        "vetoes": (
            _g("MCX_TENDER", "Delivery/tender/expiry restriction", "SAFETY", ("mcx_delivery_reports", "mcx_circulars"), policy=MatchPolicy.ANY_OF),
        ),
        "rule": "Commodity-group rules remain separate; slow context cannot confirm an intraday trigger.",
    },
)


def _resolve_group(raw: dict[str, object], registered: set[str]) -> SourceGroup:
    keys = tuple(raw["source_keys"])
    found = tuple(key for key in keys if key in registered)
    missing = tuple(key for key in keys if key not in registered)
    policy = MatchPolicy(raw["match_policy"])
    covered = bool(found) if policy is MatchPolicy.ANY_OF else not missing
    return SourceGroup(
        groupId=str(raw["group_id"]),
        purpose=str(raw["purpose"]),
        evidenceFamily=str(raw["evidence_family"]),
        matchPolicy=policy,
        sourceKeys=keys,
        registeredKeys=found,
        missingKeys=missing,
        contractCovered=covered,
        liveDataRequired=bool(raw["live_data_required"]),
        delayedContextOnly=bool(raw["delayed_context_only"]),
    )


def build_strategy_source_registry() -> StrategySourceRegistry:
    compiler = compile_default_inventory()
    registered = {item.source_contract_id for item in compiler.source_contracts}
    profiles: list[StrategySourceProfile] = []
    for raw in PROFILE_DEFINITIONS:
        mandatory = tuple(_resolve_group(item, registered) for item in raw["mandatory"])
        confirmations = tuple(_resolve_group(item, registered) for item in raw["confirmations"])
        vetoes = tuple(_resolve_group(item, registered) for item in raw["vetoes"])
        profiles.append(
            StrategySourceProfile(
                profileId=str(raw["profile_id"]),
                name=str(raw["name"]),
                market=str(raw["market"]),
                horizon=str(raw["horizon"]),
                mandatory=mandatory,
                confirmations=confirmations,
                vetoes=vetoes,
                registrationComplete=all(item.contract_covered for item in mandatory),
                rule=str(raw["rule"]),
            )
        )
    return StrategySourceRegistry(
        profileCount=len(profiles),
        profiles=tuple(profiles),
        note=(
            "Registration coverage only. Runtime freshness, usable parsed rows, "
            "lineage, family acceptance and safety gates remain separate."
        ),
    )
