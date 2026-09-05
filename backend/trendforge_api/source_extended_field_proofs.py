"""AMEND-A-001 / TDG-GAP-001 proofs.

Genuine source-specific values go in ``fields`` and may appear on the compiled
contract. Named waivers document a reviewed gap. Waivers are not compiled
field values and cannot unlock GATE_AUTHORIZED.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .parsers.corporate_events_parser import CORPORATE_ACTIONS_SCHEMA_ID
from .parsers.nse_cash_bhavcopy_parser import CASH_BHAV_SCHEMA_ID
from .parsers.nse_fo_bhavcopy_parser import FO_BHAV_SCHEMA_ID
from .parsers.nse_index_close_parser import INDEX_CLOSE_SCHEMA_ID
from .parsers.nse_mwpl_parser import BAN_SCHEMA_ID, MWPL_SCHEMA_ID


ALLOWED_EXTENDED_FIELDS = frozenset(
    {
        "timezone",
        "publication_calendar",
        "session_dependency",
        "entitlement_required",
        "legal_use_mode",
        "rate_budget",
        "retry_policy",
        "circuit_breaker_policy",
        "content_signature",
        "schema_version",
        "correction_policy",
        "event_identity_fields",
        "fallback_authority",
        "watermark_policy",
        "retention_policy",
    }
)

PROOF_VERSION = "TDG-GAP-001-v4"
PROOF_REVIEWED_AT = "2026-08-22"

# Live shared NSE fetch policy. These are proven *shared-domain* controls in
# market_data_service.DomainCircuitBreaker + source_resolver._fetch_with_retry +
# market_data_store.cleanup_retention. They are not per-source unique breakers.
NSE_SHARED_RUNTIME_PROOF = {
    "rate_budget": "SHARED_NSE_DOMAIN_CAP:archives.nseindia.com=1;www.nseindia.com=1",
    "retry_policy": "SHARED_HTTP_RETRY:max_attempts=3;retry_on=408,425,429,500,502,503,504",
    "circuit_breaker_policy": "SHARED_NSE_DOMAIN_BREAKER:failure_threshold=3;cooldown_seconds=900",
    "retention_policy": "SHARED_MARKET_DATA_STORE:detailed_trading_days=5;hash_archive",
}


@dataclass(frozen=True)
class ExtendedFieldProof:
    source_key: str
    fields: dict[str, str]
    evidence: str
    waivers: dict[str, str] = field(default_factory=dict)
    version: str = PROOF_VERSION
    reviewed_at: str = PROOF_REVIEWED_AT

    def __post_init__(self) -> None:
        overlap = set(self.fields) & set(self.waivers)
        if overlap:
            raise ValueError(f"{self.source_key} cannot prove and waive {overlap}")
        unknown = (set(self.fields) | set(self.waivers)) - ALLOWED_EXTENDED_FIELDS
        if unknown:
            raise ValueError(f"{self.source_key} has unknown extended fields {unknown}")


def _nse_public_research(fields: dict[str, str], evidence: str) -> tuple[dict[str, str], dict[str, str]]:
    proven = {
        "timezone": "Asia/Kolkata",
        "entitlement_required": "PUBLIC_WITH_OPTIONAL_SESSION_SEED",
        "legal_use_mode": "RESEARCH_ONLY",
        **NSE_SHARED_RUNTIME_PROOF,
        **fields,
    }
    return proven, {}


def reviewed_extended_field_proofs() -> dict[str, ExtendedFieldProof]:
    ban_fields, ban_waivers = _nse_public_research(
        {
            "publication_calendar": "NSE_FO_TRADING_DAYS",
            "session_dependency": "NSE_FO",
            "content_signature": "fo_secban_header_and_symbol_list",
            "schema_version": BAN_SCHEMA_ID,
            "correction_policy": "NEXT_SESSION_FILE_REPLACES",
            "event_identity_fields": "symbol|data_date",
            "fallback_authority": "NONE_MWPL_CANNOT_SATISFY_BAN",
            "watermark_policy": "DATA_DATE_FROM_ARTIFACT_NOT_FETCH_TIME",
        },
        "parse_nse_fno_ban accepts only the official fo_secban schema, allows valid-empty, and refuses MWPL percentages.",
    )
    mwpl_fields = {
        "timezone": "Asia/Kolkata",
        "legal_use_mode": "RESEARCH_ONLY",
        "fallback_authority": "NONE_BAN_FILE_CANNOT_SATISFY_PERCENTAGES",
        **NSE_SHARED_RUNTIME_PROOF,
    }
    mwpl_waivers = {
        "publication_calendar": "NO_VERIFIED_OFFICIAL_PERCENTAGE_ARTIFACT",
        "session_dependency": "NO_VERIFIED_OFFICIAL_PERCENTAGE_ARTIFACT",
        "entitlement_required": "NO_VERIFIED_OFFICIAL_PERCENTAGE_ARTIFACT",
        "content_signature": "NO_VERIFIED_OFFICIAL_PERCENTAGE_ARTIFACT",
        "schema_version": f"WAIVED_{MWPL_SCHEMA_ID}",
        "correction_policy": "NO_VERIFIED_OFFICIAL_PERCENTAGE_ARTIFACT",
        "event_identity_fields": "NO_VERIFIED_OFFICIAL_PERCENTAGE_ARTIFACT",
        "watermark_policy": "NO_VERIFIED_OFFICIAL_PERCENTAGE_ARTIFACT",
    }
    cash_fields, cash_waivers = _nse_public_research(
        {
            "publication_calendar": "NSE_CM_TRADING_DAYS",
            "session_dependency": "NSE_CM",
            "content_signature": "eq_series_trade_date_close_prevclose",
            "schema_version": CASH_BHAV_SCHEMA_ID,
            "correction_policy": "NEXT_SESSION_FILE_REPLACES",
            "event_identity_fields": "symbol|series|isin|trade_date",
            "fallback_authority": "BSE_BHAV_DISPLAY_ONLY_CANNOT_INHERIT_NSE",
            "watermark_policy": "TRADE_DATE_FROM_ROW_NOT_FETCH_TIME",
        },
        "parse_nse_cash_bhavcopy keeps EQ rows for one trade_date and fails empty or mixed-date files.",
    )
    fo_fields, fo_waivers = _nse_public_research(
        {
            "publication_calendar": "NSE_FO_TRADING_DAYS",
            "session_dependency": "NSE_FO",
            "content_signature": "symbol_close_prevclose_oi_oi_change",
            "schema_version": FO_BHAV_SCHEMA_ID,
            "correction_policy": "NEXT_SESSION_FILE_REPLACES",
            "event_identity_fields": "symbol|instrument|expiry|strike|option_type|trade_date",
            "fallback_authority": "NONE_LIVE_QUOTE_CANNOT_REPLACE_EOD_OI",
            "watermark_policy": "TRADE_DATE_FROM_ARTIFACT_NOT_FETCH_TIME",
        },
        "parse_nse_fo_bhavcopy requires dated derivative columns and refuses missing OI/price fields.",
    )
    index_fields, index_waivers = _nse_public_research(
        {
            "publication_calendar": "NSE_CM_TRADING_DAYS",
            "session_dependency": "NSE_CM",
            "content_signature": "requires_nifty50_and_india_vix",
            "schema_version": INDEX_CLOSE_SCHEMA_ID,
            "correction_policy": "NEXT_SESSION_FILE_REPLACES",
            "event_identity_fields": "index_name|index_date",
            "fallback_authority": "NONE_CONTEXT_ONLY",
            "watermark_policy": "INDEX_DATE_FROM_ROW_NOT_FETCH_TIME",
        },
        "parse_nse_index_close requires one date and both NIFTY 50 and INDIA VIX rows.",
    )
    ca_fields, ca_waivers = _nse_public_research(
        {
            "publication_calendar": "NSE_EVENT_DRIVEN_FILINGS",
            "session_dependency": "NSE_CM_EVENT",
            "content_signature": "symbol_or_company_and_action_type",
            "schema_version": CORPORATE_ACTIONS_SCHEMA_ID,
            "correction_policy": "REVISED_OR_CANCELLED_FROM_FILING_TEXT",
            "event_identity_fields": "symbol|action_type|ex_date|record_date|announcement_date",
            "fallback_authority": "NONE_BSE_FILING_CANNOT_SILENTLY_REPLACE",
            "watermark_policy": "ANNOUNCEMENT_OR_EX_DATE_NOT_FETCH_TIME",
        },
        "parse_corporate_events keeps actor/action dates and marks REVISED/CANCELLED from filing text.",
    )
    return {
        "nse_fno_ban": ExtendedFieldProof(
            source_key="nse_fno_ban",
            fields=ban_fields,
            waivers=ban_waivers,
            evidence="Official fo_secban CSV; valid-empty allowed; MWPL percentages forbidden.",
        ),
        "nse_mwpl_percentages": ExtendedFieldProof(
            source_key="nse_mwpl_percentages",
            fields=mwpl_fields,
            waivers=mwpl_waivers,
            evidence="Separate contract from the ban file; official percentage artifact is not verified.",
        ),
        "nse_bhavcopy_eod": ExtendedFieldProof(
            source_key="nse_bhavcopy_eod",
            fields=cash_fields,
            waivers=cash_waivers,
            evidence="Official cash EOD EQ bhav; one trade_date; empty/mixed dates fail closed.",
        ),
        "nse_fo_bhavcopy": ExtendedFieldProof(
            source_key="nse_fo_bhavcopy",
            fields=fo_fields,
            waivers=fo_waivers,
            evidence="Official FO UDiFF bhav; required OI/price columns; EOD only.",
        ),
        "nse_index_close_eod": ExtendedFieldProof(
            source_key="nse_index_close_eod",
            fields=index_fields,
            waivers=index_waivers,
            evidence="Official all-indices close; NIFTY 50 and INDIA VIX required.",
        ),
        "nse_corporate_filings_actions": ExtendedFieldProof(
            source_key="nse_corporate_filings_actions",
            fields=ca_fields,
            waivers=ca_waivers,
            evidence="Official corporate filings; revision/cancel from text; not a price vote.",
        ),
    }


def proof_for_source(source_key: str) -> ExtendedFieldProof | None:
    return reviewed_extended_field_proofs().get(source_key)
