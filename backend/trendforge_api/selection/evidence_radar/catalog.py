"""Slot catalog: every live R1 source contract becomes exactly one typed job slot.

Built from the persisted R1 bundle plus the Hybrid A19.2 decision-job specs in
`source_inventory_compiler.DECISION_JOB_SPECS`. This is NOT a handwritten list
of ~140 links and never turns a slot into a vote: `canSupportConfirmed` is
always False.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ..inventory_source_bundle import InventorySourceBundleV1

SCHEMA_VERSION = "trendforge.evidence-radar-catalog.v1"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class Grain(str, Enum):
    SYMBOL = "SYMBOL"
    MARKET = "MARKET"
    SECTOR = "SECTOR"
    CONTRACT = "CONTRACT"
    MACRO = "MACRO"
    COMPANION = "COMPANION"


class Authority(str, Enum):
    OFFICIAL = "OFFICIAL"
    DELAYED_OFFICIAL = "DELAYED_OFFICIAL"
    CALCULATED = "CALCULATED"
    SECONDARY = "SECONDARY"
    UNOFFICIAL = "UNOFFICIAL"


class Horizon(str, Enum):
    INTRADAY = "INTRADAY"
    SWING = "SWING"
    POSITION = "POSITION"
    COMMODITY = "COMMODITY"

    @classmethod
    def all(cls) -> tuple["Horizon", ...]:
        return (cls.INTRADAY, cls.SWING, cls.POSITION, cls.COMMODITY)


# Keyword classification rules. First match wins; unmatched keys still get a
# slot with UNKNOWN_FAMILY / NOT_NORMALIZED so nothing is ever skipped.
_RULES: tuple[dict, ...] = (
    {
        "keys": ("index_close", "nifty50"),
        "grain": Grain.COMPANION,
        "jobs": ("J05",),
        "family": "MARKET_AND_SECTOR_CONTEXT",
        "authority": Authority.OFFICIAL,
        "calculate": "INDEX_CONTEXT_READ",
        "horizons": (Horizon.INTRADAY, Horizon.SWING, Horizon.POSITION),
        "wrong_grain": True,
    },
    {
        "keys": ("vix",),
        "grain": Grain.MARKET,
        "jobs": ("J05",),
        "family": "MARKET_AND_SECTOR_CONTEXT",
        "authority": Authority.OFFICIAL,
        "calculate": "VIX_LEVEL_CONTEXT",
        "horizons": (Horizon.INTRADAY, Horizon.SWING, Horizon.POSITION),
        "wrong_grain": True,
    },
    {
        "keys": ("participant_oi",),
        "grain": Grain.MARKET,
        "jobs": ("J06",),
        "family": "DERIVATIVES_FUTURES",
        "authority": Authority.OFFICIAL,
        "calculate": "PARTICIPANT_OI_CONTEXT",
        "horizons": (Horizon.SWING, Horizon.POSITION),
        "wrong_grain": True,
    },
    {
        "keys": ("fii_dii",),
        "grain": Grain.MARKET,
        "jobs": ("J05", "J06"),
        "family": "MARKET_AND_SECTOR_CONTEXT",
        "authority": Authority.OFFICIAL,
        "calculate": "MARKET_FII_NET_CHIP",
        "horizons": (Horizon.INTRADAY, Horizon.SWING, Horizon.POSITION),
        "wrong_grain": True,
    },
    {
        "keys": ("mto",),
        "grain": Grain.SYMBOL,
        "jobs": ("J03",),
        "family": "DELIVERY",
        "authority": Authority.OFFICIAL,
        "calculate": "DELIVERY_Z_PIT20",
        "horizons": (Horizon.SWING, Horizon.POSITION),
        "wrong_grain": False,
    },
    {
        "keys": ("preopen", "pre_open"),
        "grain": Grain.SYMBOL,
        "jobs": ("J04",),
        "family": "STRUCTURE",
        "authority": Authority.OFFICIAL,
        "calculate": "PREOPEN_GAP_FTR001",
        "horizons": (Horizon.INTRADAY,),
        "wrong_grain": False,
    },
    {
        "keys": ("bulk_deal", "block_deal", "large_deal"),
        "grain": Grain.SYMBOL,
        "jobs": ("J08",),
        "family": "EVENT_AND_SPONSOR",
        "authority": Authority.OFFICIAL,
        "calculate": "NAMED_DEAL_SIDE",
        "horizons": (Horizon.INTRADAY, Horizon.SWING, Horizon.POSITION),
        "wrong_grain": False,
    },
    {
        "keys": (
            "announcements",
            "filings_actions",
            "corporate_filings",
            "financial_results",
            "board_meet",
            "buyback",
            "order_win",
            "regulation_29",
            "regulation_31",
            "nse_pit_symbol",
            "nse_pit_current",
            "nse_pit_annual",
        ),
        "grain": Grain.SYMBOL,
        "jobs": ("J09",),
        "family": "EVENT_AND_SPONSOR",
        "authority": Authority.OFFICIAL,
        "calculate": "OFFICIAL_EVENT_AVAILABLE_AT",
        "horizons": (Horizon.SWING, Horizon.POSITION),
        "wrong_grain": False,
    },
    {
        "keys": ("most_active", "volume_gainer", "market_turnover", "variations_"),
        "grain": Grain.SYMBOL,
        "jobs": ("J03",),
        "family": "PARTICIPATION",
        "authority": Authority.OFFICIAL,
        "calculate": "ACTIVITY_SESSION_JOIN_NOT_SECOND_VOTE",
        "horizons": (Horizon.INTRADAY, Horizon.SWING),
        "wrong_grain": False,
    },
    {
        "keys": ("all_indices", "market_status", "pr_market", "fii_derivatives"),
        "grain": Grain.MARKET,
        "jobs": ("J05",),
        "family": "MARKET_AND_SECTOR_CONTEXT",
        "authority": Authority.OFFICIAL,
        "calculate": "INDEX_CONTEXT_READ",
        "horizons": (Horizon.INTRADAY, Horizon.SWING, Horizon.POSITION),
        "wrong_grain": True,
    },
    {
        "keys": ("live_equity_derivatives",),
        "grain": Grain.CONTRACT,
        "jobs": ("J06", "J07"),
        "family": "DERIVATIVES_FUTURES",
        "authority": Authority.OFFICIAL,
        "calculate": "FO_OI_PACKAGE_A6",
        "horizons": (Horizon.INTRADAY, Horizon.SWING),
        "wrong_grain": False,
    },
    {
        "keys": ("lme_warehouse", "warehouse_stock"),
        "grain": Grain.MACRO,
        "jobs": ("J12",),
        "family": "GLOBAL_CONTEXT",
        "authority": Authority.DELAYED_OFFICIAL,
        "calculate": "GLOBAL_DELAYED_Z_CONTEXT",
        "horizons": (Horizon.COMMODITY,),
        "wrong_grain": True,
    },
    {
        "keys": ("cdsl_fpi",),
        "grain": Grain.MARKET,
        "jobs": ("J10",),
        "family": "SPONSOR_DELAYED",
        "authority": Authority.DELAYED_OFFICIAL,
        "calculate": "DELAYED_FPI_CONTEXT_NOT_STOCK_TAPE",
        "horizons": (Horizon.POSITION,),
        "wrong_grain": True,
    },
    {
        "keys": ("ratings",),
        "grain": Grain.SYMBOL,
        "jobs": ("J09",),
        "family": "EVENT_AND_SPONSOR",
        "authority": Authority.SECONDARY,
        "calculate": "INFO_ZERO_SCORE",
        "horizons": (Horizon.SWING, Horizon.POSITION),
        "wrong_grain": False,
    },
    {
        "keys": ("news", "trends"),
        "grain": Grain.SYMBOL,
        "jobs": (),
        "family": "SECONDARY_DISCOVERY",
        "authority": Authority.SECONDARY,
        "calculate": "INFO_ZERO_SCORE",
        "horizons": (Horizon.SWING,),
        "wrong_grain": False,
    },
    {
        "keys": ("amfi",),
        "grain": Grain.SYMBOL,
        "jobs": ("J10",),
        "family": "SPONSOR_DELAYED",
        "authority": Authority.DELAYED_OFFICIAL,
        "calculate": "AMFI_DELTA_DELAYED",
        "horizons": (Horizon.SWING, Horizon.POSITION),
        "wrong_grain": False,
    },
    {
        "keys": ("shareholding", "sast", "insider", "nsdl_fpi"),
        "grain": Grain.SYMBOL,
        "jobs": ("J10", "J08"),
        "family": "SPONSOR_DELAYED",
        "authority": Authority.DELAYED_OFFICIAL,
        "calculate": "SHP_PROMOTER_PUBLIC_CONTEXT",
        "horizons": (Horizon.POSITION,),
        "wrong_grain": False,
    },
    {
        "keys": ("pledge", "surveillance", "asm", "gsm", "t2t", "trade_to_trade", "short_selling", "slb", "ban", "mwpl"),
        "grain": Grain.SYMBOL,
        "jobs": ("J02",),
        "family": "TRADABILITY_AND_SAFETY",
        "authority": Authority.OFFICIAL,
        "calculate": "VETO_SLOT_NO_SCORE",
        "horizons": Horizon.all(),
        "wrong_grain": False,
    },
    {
        "keys": ("mcx",),
        "grain": Grain.CONTRACT,
        "jobs": ("J11",),
        "family": "MCX_LOCAL",
        "authority": Authority.OFFICIAL,
        "calculate": "MCX_LOCAL_CLOSE_OI_CHANGE",
        "horizons": (Horizon.COMMODITY,),
        "wrong_grain": False,
    },
    {
        "keys": (
            "cftc", "eia", "wgc", "usda", "fred", "lbma", "usdinr", "fbil",
            "rainfall", "trade_data", "rig_count", "sge", "petroleum",
            "natgas", "gold_physical", "world_gold", "opec", "tbill",
            "tradingeconomics", "baltic",
        ),
        "grain": Grain.MACRO,
        "jobs": ("J12",),
        "family": "GLOBAL_CONTEXT",
        "authority": Authority.DELAYED_OFFICIAL,
        "calculate": "GLOBAL_DELAYED_Z_CONTEXT",
        "horizons": (Horizon.COMMODITY,),
        "wrong_grain": True,
    },
    {
        "keys": ("option_chain", "max_pain", "pcr", "option_oi"),
        "grain": Grain.SYMBOL,
        "jobs": ("J07",),
        "family": "DERIVATIVES_OPTIONS",
        "authority": Authority.OFFICIAL,
        "calculate": "OPTIONS_PACKAGE_UNKNOWN_NEEDS_R12",
        "horizons": (Horizon.INTRADAY, Horizon.SWING),
        "wrong_grain": False,
    },
    {
        "keys": ("fo_bhavcopy", "oi_spurt", "rollover"),
        "grain": Grain.CONTRACT,
        "jobs": ("J06",),
        "family": "DERIVATIVES_FUTURES",
        "authority": Authority.OFFICIAL,
        "calculate": "FO_OI_PACKAGE_A6",
        "horizons": (Horizon.SWING, Horizon.POSITION),
        "wrong_grain": False,
    },
    {
        "keys": (
            "calendar",
            "holiday",
            "instrument_master",
            "contract_master",
            "equity_universe",
            "constituents",
        ),
        "grain": Grain.COMPANION,
        "jobs": ("J01",),
        "family": "IDENTITY",
        "authority": Authority.OFFICIAL,
        "calculate": "IDENTITY_READ_NO_VOTE",
        "horizons": Horizon.all(),
        "wrong_grain": True,
    },
    {
        "keys": ("pk_", "q5_pk"),
        "grain": Grain.SYMBOL,
        "jobs": (),
        "family": "PK_SHADOW",
        "authority": Authority.SECONDARY,
        "calculate": "ZERO_VOTE_DIGEST",
        "horizons": (Horizon.SWING,),
        "wrong_grain": False,
    },
    {
        "keys": (
            "screener_",
            "tickertape_",
            "dhan_",
            "equitymaster_",
            "rupeevest",
            "yahoo_",
        ),
        "grain": Grain.SYMBOL,
        "jobs": (),
        "family": "SECONDARY_DISCOVERY",
        "authority": Authority.SECONDARY,
        "calculate": "INFO_ZERO_SCORE",
        "horizons": (Horizon.SWING, Horizon.POSITION),
        "wrong_grain": False,
    },
    {
        "keys": ("quote_equity", "trade_info"),
        "grain": Grain.SYMBOL,
        "jobs": ("J03",),
        "family": "PARTICIPATION",
        "authority": Authority.OFFICIAL,
        "calculate": "ACTIVITY_SESSION_JOIN_NOT_SECOND_VOTE",
        "horizons": (Horizon.INTRADAY, Horizon.SWING),
        "wrong_grain": False,
    },
    {
        "keys": ("bhavcopy",),
        "grain": Grain.SYMBOL,
        "jobs": ("J03",),
        "family": "PARTICIPATION",
        "authority": Authority.OFFICIAL,
        "calculate": "R2_ATTENTION_READ",
        "horizons": (Horizon.INTRADAY, Horizon.SWING, Horizon.POSITION),
        "wrong_grain": False,
    },
)


class SourceSlotCatalogEntry(BaseModel):
    model_config = MODEL_CONFIG

    source_key: str
    canonical_root: str
    alias_of: str | None = None
    decision_jobs: tuple[str, ...] = ()
    evidence_family: str
    correlation_group: str
    grain: Grain
    horizons_allowed: tuple[Horizon, ...]
    can_support_confirmed: bool = False
    authority: Authority
    calculate: str
    wrong_grain_if_copied_to_symbol: bool

    @model_validator(mode="after")
    def slot_is_never_a_vote(self) -> "SourceSlotCatalogEntry":
        if self.can_support_confirmed:
            raise ValueError("a catalog slot can never support CONFIRMED")
        return self


class SlotCatalog(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    bundle_id: str
    bundle_hash: str
    built_at: datetime
    total_slots: int = Field(ge=0)
    companion_count: int = Field(ge=0, default=0)
    entries: tuple[SourceSlotCatalogEntry, ...]

    @model_validator(mode="after")
    def counts_match(self) -> "SlotCatalog":
        if self.total_slots != len(self.entries):
            raise ValueError("slot catalog total does not match entries")
        return self


def _classify(source_key: str) -> dict:
    lowered = source_key.lower()
    for rule in _RULES:
        if any(keyword in lowered for keyword in rule["keys"]):
            return rule
    return {
        "grain": Grain.SYMBOL,
        "jobs": (),
        "family": "UNKNOWN_FAMILY",
        "authority": Authority.SECONDARY,
        "calculate": "NOT_NORMALIZED",
        "horizons": (),
        "wrong_grain": False,
    }


def _compiler_jobs(record) -> tuple[str, ...]:
    try:
        from ...source_inventory_compiler import infer_decision_jobs
    except Exception:
        return ()
    inferred = infer_decision_jobs(
        source_keys=[record.source_key, record.normalized_source_key or ""],
        purpose_jobs=None,
        url=record.canonical_url or "",
        source_role=None,
    )
    return tuple(str(job) for job in inferred)


def build_slot_catalog(
    bundle: InventorySourceBundleV1, *, built_at: datetime | None = None
) -> SlotCatalog:
    entries: list[SourceSlotCatalogEntry] = []
    companions = 0
    for record in bundle.source_records:
        rule = _classify(record.source_key)
        if rule["grain"] is Grain.COMPANION:
            companions += 1
        jobs = tuple(dict.fromkeys((*rule["jobs"], *_compiler_jobs(record))))
        entries.append(
            SourceSlotCatalogEntry(
                source_key=record.source_key,
                canonical_root=record.dataset_root_id or record.normalized_source_key,
                alias_of=record.alias_of,
                decision_jobs=jobs,
                evidence_family=rule["family"],
                correlation_group=record.correlation_group,
                grain=rule["grain"],
                horizons_allowed=tuple(rule["horizons"]),
                can_support_confirmed=False,
                authority=rule["authority"],
                calculate=rule["calculate"],
                wrong_grain_if_copied_to_symbol=bool(rule["wrong_grain"]),
            )
        )
    return SlotCatalog(
        bundle_id=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        built_at=built_at or datetime.now(UTC),
        total_slots=len(entries),
        companion_count=companions,
        entries=tuple(entries),
    )


__all__ = [
    "SCHEMA_VERSION",
    "Authority",
    "Grain",
    "Horizon",
    "SlotCatalog",
    "SourceSlotCatalogEntry",
    "build_slot_catalog",
]

