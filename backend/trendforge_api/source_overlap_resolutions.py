"""Typed, fail-closed semantic-overlap resolutions for the source compiler."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from urllib.parse import urlparse


REVIEWED_WORKBOOK_SHA256 = (
    "f1abcdce2b451b4ded9d9e9c8eb6bd63fae82853803f60bef60a1651dd52eb0b"
)


class OverlapDisposition(StrEnum):
    SAME_DATASET_ALIAS = "SAME_DATASET_ALIAS"
    TRANSPORT_VARIANT = "TRANSPORT_VARIANT"
    DISTINCT_SHARED_ENDPOINT = "DISTINCT_SHARED_ENDPOINT"
    PARENT_CHILD_CONTRACT = "PARENT_CHILD_CONTRACT"
    QUARANTINED_UNPROVEN = "QUARANTINED_UNPROVEN"


class OverlapResolutionState(StrEnum):
    UNEXPLAINED_OVERLAP = "UNEXPLAINED_OVERLAP"
    EXPLAINED_ALIAS = "EXPLAINED_ALIAS"
    EXPLAINED_TRANSPORT_VARIANT = "EXPLAINED_TRANSPORT_VARIANT"
    EXPLAINED_DISTINCT = "EXPLAINED_DISTINCT"
    EXPLAINED_PARENT_CHILD = "EXPLAINED_PARENT_CHILD"
    QUARANTINED_OVERLAP = "QUARANTINED_OVERLAP"


class EvidenceBasis(StrEnum):
    WORKBOOK_LINEAGE = "WORKBOOK_LINEAGE"
    CONTRACT_REVIEW = "CONTRACT_REVIEW"
    PARSER_CONTRACT = "PARSER_CONTRACT"
    SCHEMA_REVIEW = "SCHEMA_REVIEW"
    SAVED_ARTIFACT = "SAVED_ARTIFACT"
    SOURCE_DOCUMENTATION = "SOURCE_DOCUMENTATION"
    URL_MATCH_ONLY = "URL_MATCH_ONLY"


STRONG_IDENTITY_EVIDENCE = frozenset(
    {
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.PARSER_CONTRACT,
        EvidenceBasis.SCHEMA_REVIEW,
        EvidenceBasis.SAVED_ARTIFACT,
        EvidenceBasis.SOURCE_DOCUMENTATION,
    }
)


DISPOSITION_STATES = {
    OverlapDisposition.SAME_DATASET_ALIAS: OverlapResolutionState.EXPLAINED_ALIAS,
    OverlapDisposition.TRANSPORT_VARIANT: (
        OverlapResolutionState.EXPLAINED_TRANSPORT_VARIANT
    ),
    OverlapDisposition.DISTINCT_SHARED_ENDPOINT: (
        OverlapResolutionState.EXPLAINED_DISTINCT
    ),
    OverlapDisposition.PARENT_CHILD_CONTRACT: (
        OverlapResolutionState.EXPLAINED_PARENT_CHILD
    ),
    OverlapDisposition.QUARANTINED_UNPROVEN: (
        OverlapResolutionState.QUARANTINED_OVERLAP
    ),
}


def resolve_dataset_root_identity(
    *,
    urls: Sequence[str],
    source_keys: Sequence[str],
    overlap_resolutions: Sequence[OverlapResolution] = (),
) -> tuple[str, str, str]:
    """Return (mirror_group_id, resolver_id, fallback_authority_cap).

    Unreviewed or conflicting roots stay UNSPECIFIED and cannot vote.
    """
    url_set = set(urls)
    key_set = set(source_keys)
    hits = [
        item
        for item in overlap_resolutions
        if item.canonical_url in url_set or key_set.intersection(item.contract_ids)
    ]
    if not hits:
        return "UNSPECIFIED", "UNSPECIFIED", "UNSPECIFIED_NO_VOTE"
    if any(
        item.disposition is OverlapDisposition.QUARANTINED_UNPROVEN for item in hits
    ):
        return "UNSPECIFIED", "QUARANTINED_UNPROVEN", "UNSPECIFIED_NO_VOTE"
    roots = {item.canonical_dataset_root_id for item in hits}
    if len(roots) != 1:
        return "UNSPECIFIED", "CONFLICTING_REVIEWED_ROOTS", "UNSPECIFIED_NO_VOTE"
    dispositions = {item.disposition.value for item in hits}
    resolver_id = (
        next(iter(dispositions))
        if len(dispositions) == 1
        else "REVIEWED_MIXED_DISPOSITION"
    )
    return next(iter(roots)), resolver_id, "REVIEWED_NO_GATE"


def normalize_resolution_url(value: str) -> str:
    if "*" in value:
        raise ValueError("Wildcard overlap URLs are not permitted")
    parsed = urlparse(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Overlap URL must be an exact HTTP(S) URL")
    return parsed._replace(
        scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower()
    ).geturl()


@dataclass(frozen=True)
class OverlapResolution:
    canonical_url: str
    contract_ids: tuple[str, ...]
    disposition: OverlapDisposition
    canonical_dataset_root_id: str
    evidence_reason: str
    evidence_basis: tuple[EvidenceBasis, ...]
    resolution_version: str
    reviewed_at: str

    def __post_init__(self) -> None:
        normalized_url = normalize_resolution_url(self.canonical_url)
        contracts = tuple(sorted(set(self.contract_ids)))
        if len(contracts) < 2:
            raise ValueError("Overlap resolution requires at least two contracts")
        if any(not item.strip() or "*" in item for item in contracts):
            raise ValueError("Wildcard or empty contract IDs are not permitted")
        if not self.canonical_dataset_root_id.strip():
            raise ValueError("Canonical dataset root is required")
        if not self.evidence_reason.strip():
            raise ValueError("Evidence reason is required")
        if not self.evidence_basis:
            raise ValueError("Evidence basis is required")
        if self.disposition is not OverlapDisposition.QUARANTINED_UNPROVEN:
            if not STRONG_IDENTITY_EVIDENCE.intersection(self.evidence_basis):
                raise ValueError(
                    "Non-quarantine dispositions require contract, parser, schema, "
                    "artifact, or source-document evidence"
                )
        if not self.resolution_version.strip():
            raise ValueError("Resolution version is required")
        date.fromisoformat(self.reviewed_at)
        object.__setattr__(self, "canonical_url", normalized_url)
        object.__setattr__(self, "contract_ids", contracts)

    @property
    def exact_key(self) -> tuple[str, tuple[str, ...]]:
        return self.canonical_url, self.contract_ids

    @property
    def state(self) -> OverlapResolutionState:
        return DISPOSITION_STATES[self.disposition]


def _resolution(
    url: str,
    contracts: tuple[str, ...],
    disposition: OverlapDisposition,
    root: str,
    reason: str,
    *basis: EvidenceBasis,
    resolution_version: str = "CROSS-001-v1",
    reviewed_at: str = "2026-07-23",
) -> OverlapResolution:
    return OverlapResolution(
        canonical_url=url,
        contract_ids=contracts,
        disposition=disposition,
        canonical_dataset_root_id=root,
        evidence_reason=reason,
        evidence_basis=tuple(basis),
        resolution_version=resolution_version,
        reviewed_at=reviewed_at,
    )


REVIEWED_OVERLAP_RESOLUTIONS: tuple[OverlapResolution, ...] = (
    _resolution(
        "https://archives.nseindia.com/content/nsccl/fao_participant_oi_10072026.csv",
        ("nse_fo_bhavcopy", "nse_participant_oi"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_fo_reports",
        "Per-segment workbook prefixes and the named row identify the FO-report parent and participant-OI child.",
        EvidenceBasis.WORKBOOK_LINEAGE,
        EvidenceBasis.CONTRACT_REVIEW,
    ),
    _resolution(
        "https://publicreporting.cftc.gov/resource/6dca-aqww.json?%24limit=500&%24order=report_date_as_yyyy_mm_dd+DESC",
        ("cftc_cot", "cftc_legacy_futures_only"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "cftc_cot",
        "The generic COT contract contains the report-specific legacy futures-only child.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://publicreporting.cftc.gov/resource/72hh-3qpy.json?%24limit=500&%24order=report_date_as_yyyy_mm_dd+DESC",
        ("cftc_cot", "cftc_disagg_futures_only"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "cftc_cot",
        "The generic COT contract contains the report-specific disaggregated futures-only child.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://publicreporting.cftc.gov/resource/gpe5-46if.json?%24limit=500&%24order=report_date_as_yyyy_mm_dd+DESC",
        ("cftc_cot", "cftc_tff_futures_only"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "cftc_cot",
        "The generic COT contract contains the report-specific TFF futures-only child.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://www.cdslindia.com/Publications/ForeignPortInvestor.html",
        ("cdsl_fpi_fortnightly", "source:85494bc82a037c42"),
        OverlapDisposition.SAME_DATASET_ALIAS,
        "cdsl_fpi_fortnightly",
        "The generated inventory identity and named contract point to the same CDSL report page and lineage rows.",
        EvidenceBasis.WORKBOOK_LINEAGE,
        EvidenceBasis.CONTRACT_REVIEW,
    ),
    _resolution(
        "https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm",
        ("cftc_release_schedule", "source:17f9c796f5851721"),
        OverlapDisposition.SAME_DATASET_ALIAS,
        "cftc_release_schedule",
        "The generated inventory identity duplicates the named CFTC release-schedule contract.",
        EvidenceBasis.WORKBOOK_LINEAGE,
        EvidenceBasis.SOURCE_DOCUMENTATION,
    ),
    _resolution(
        "https://www.eia.gov/petroleum/supply/weekly/schedule.php",
        ("eia_petroleum_schedule", "source:aaabb3face464c11"),
        OverlapDisposition.SAME_DATASET_ALIAS,
        "eia_petroleum_schedule",
        "The generated inventory identity duplicates the named EIA publication-schedule contract.",
        EvidenceBasis.WORKBOOK_LINEAGE,
        EvidenceBasis.SOURCE_DOCUMENTATION,
    ),
    _resolution(
        "https://www.fbil.org.in",
        ("fbil_usdinr_reference", "source:f2d924f77957dc38"),
        OverlapDisposition.SAME_DATASET_ALIAS,
        "fbil_usdinr_reference",
        "The generated identity and named FBIL reference contract share one reviewed discovery source.",
        EvidenceBasis.WORKBOOK_LINEAGE,
        EvidenceBasis.CONTRACT_REVIEW,
    ),
    _resolution(
        "https://www.fpi.nsdl.co.in/web/Reports/ReportDetail.aspx?RepID=94",
        ("nsdl_fpi_daily", "nsdl_fpi_daily_reportdetail"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nsdl_fpi_daily",
        "The report-detail contract is the concrete child of the generic NSDL daily-report contract.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows",
        ("wgc_gold_etf_flows", "wgc_gold_etf_holdings"),
        OverlapDisposition.DISTINCT_SHARED_ENDPOINT,
        "shared_endpoint:wgc_gold_etf_holdings_and_flows",
        "The landing page publishes separate holdings and flows datasets with distinct parser contracts.",
        EvidenceBasis.PARSER_CONTRACT,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://www.nseindia.com/all-reports-derivatives",
        ("nse_fo_bhavcopy", "nse_participant_oi"),
        OverlapDisposition.DISTINCT_SHARED_ENDPOINT,
        "shared_endpoint:nse_all_reports_derivatives",
        "One discovery page exposes distinct FO bhavcopy and participant-OI downloads.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SOURCE_DOCUMENTATION,
    ),
    _resolution(
        "https://www.nseindia.com/api/block-deal",
        ("nse_block_deal", "nse_block_deal_live"),
        OverlapDisposition.SAME_DATASET_ALIAS,
        "nse_block_deal_live",
        "Legacy and live names target the same block-deal payload and parser contract.",
        EvidenceBasis.PARSER_CONTRACT,
        EvidenceBasis.CONTRACT_REVIEW,
    ),
    _resolution(
        "https://www.nseindia.com/api/corporates-pit?from_date=%7Bfrom_date%7D&index=equities&symbol=%7Bsymbol%7D&to_date=%7Bto_date%7D",
        ("nse_pit_current", "nse_pit_symbol"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_pit_current",
        "The symbol-filtered PIT contract is a parameterized child of the current PIT feed.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.PARSER_CONTRACT,
    ),
    _resolution(
        "https://www.nseindia.com/api/live-analysis-variations?index=gainers",
        ("nse_market_variations", "nse_variations_gainers"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_market_variations",
        "The gainers view is a parameterized child of the market-variations source.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://www.nseindia.com/api/live-analysis-variations?index=loosers",
        ("nse_market_variations", "nse_variations_loosers"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_market_variations",
        "The NSE-spelled loosers view is a parameterized child of market variations.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://www.nseindia.com/api/liveEquity-derivatives?index=nifty_bank_fut",
        ("nse_live_equity_derivatives", "nse_live_equity_derivatives_banknifty_fut"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_live_equity_derivatives",
        "BANKNIFTY futures are a parameterized child of the live derivatives feed.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://www.nseindia.com/api/liveEquity-derivatives?index=nifty_bank_opt",
        ("nse_live_equity_derivatives", "nse_live_equity_derivatives_banknifty_opt"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_live_equity_derivatives",
        "BANKNIFTY options are a parameterized child of the live derivatives feed.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://www.nseindia.com/api/liveEquity-derivatives?index=nse50_fut",
        ("nse_live_equity_derivatives", "nse_live_equity_derivatives_index_fut"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_live_equity_derivatives",
        "NIFTY index futures are a parameterized child of the live derivatives feed.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://www.nseindia.com/api/liveEquity-derivatives?index=nse50_opt",
        ("nse_live_equity_derivatives", "nse_live_equity_derivatives_index_opt"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_live_equity_derivatives",
        "NIFTY index options are a parameterized child of the live derivatives feed.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://www.nseindia.com/api/liveEquity-derivatives?index=stock_fut",
        ("nse_live_equity_derivatives", "nse_live_equity_derivatives_stock_fut"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_live_equity_derivatives",
        "Stock futures are a parameterized child of the live derivatives feed.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://www.nseindia.com/api/liveEquity-derivatives?index=stock_opt",
        ("nse_live_equity_derivatives", "nse_live_equity_derivatives_stock_opt"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_live_equity_derivatives",
        "Stock options are a parameterized child of the live derivatives feed.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SCHEMA_REVIEW,
    ),
    _resolution(
        "https://www.nseindia.com/api/option-chain-equities?symbol=%7Bsymbol%7D",
        ("nse_option_chain", "nse_option_chain_equity"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_option_chain",
        "The symbol-templated equity chain is a child of the generic option-chain contract.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.PARSER_CONTRACT,
    ),
    _resolution(
        "https://www.nseindia.com/api/option-chain-equities?symbol=BANKNIFTY",
        ("nse_option_chain", "nse_option_chain_banknifty"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_option_chain",
        "The BANKNIFTY chain is a parameterized child of the generic option-chain contract.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.PARSER_CONTRACT,
    ),
    _resolution(
        "https://www.nseindia.com/api/option-chain-equities?symbol=NIFTY",
        ("nse_option_chain", "nse_option_chain_nifty"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_option_chain",
        "The NIFTY chain is a parameterized child of the generic option-chain contract.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.PARSER_CONTRACT,
    ),
    _resolution(
        "https://www.nseindia.com/companies-listing/corporate-filings-pit",
        ("nse_pit_current", "nse_pit_symbol"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_pit_current",
        "The PIT support page is shared by the current feed and symbol-filtered child.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SOURCE_DOCUMENTATION,
    ),
    _resolution(
        "https://www.nseindia.com/companies-listing/corporate-filings-regulation-31",
        ("nse_regulation_31", "source:026ebc80f680fa0f"),
        OverlapDisposition.SAME_DATASET_ALIAS,
        "nse_regulation_31",
        "The generated inventory identity duplicates the named Regulation 31 page contract.",
        EvidenceBasis.WORKBOOK_LINEAGE,
        EvidenceBasis.SOURCE_DOCUMENTATION,
    ),
    _resolution(
        "https://www.nseindia.com/market-data/most-active-equities",
        ("nse_market_activity", "nse_most_active_volume"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_market_activity",
        "Most-active-by-volume is a child screen within the market-activity source.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SOURCE_DOCUMENTATION,
    ),
    _resolution(
        "https://www.nseindia.com/market-data/volume-gainers-spurts",
        ("nse_market_activity", "nse_volume_gainers"),
        OverlapDisposition.PARENT_CHILD_CONTRACT,
        "nse_market_activity",
        "Volume gainers is a child screen within the market-activity source.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SOURCE_DOCUMENTATION,
    ),
    _resolution(
        "https://www.rbi.org.in/Scripts/BS_FiiUSer.aspx",
        ("rbi_fpi_caution", "rbi_fpi_monitoring"),
        OverlapDisposition.DISTINCT_SHARED_ENDPOINT,
        "shared_endpoint:rbi_fpi_monitoring",
        "Monitoring and caution-list semantics remain distinct contracts on one RBI publication page.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SOURCE_DOCUMENTATION,
    ),
    _resolution(
        "https://archives.nseindia.com/content/equities/bulk.csv",
        ("nse_bulk_deals_today_csv", "source:e8f2bc055c435b8d"),
        OverlapDisposition.SAME_DATASET_ALIAS,
        "nse_bulk_deals_today_csv",
        "The generated inventory identity and named daily bulk-CSV contract share one official NSE archives file and the same parse_nse_bulk_deals_csv schema.",
        EvidenceBasis.WORKBOOK_LINEAGE,
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.PARSER_CONTRACT,
        resolution_version="CROSS-001-v2",
        reviewed_at="2026-08-15",
    ),
    _resolution(
        "https://www.amfiindia.com/online-center/portfolio-disclosure",
        ("amfi_monthly_portfolio", "amfi_portfolio_disclosure"),
        OverlapDisposition.DISTINCT_SHARED_ENDPOINT,
        "shared_endpoint:amfi_portfolio_disclosure",
        "One AMFI landing page publishes the AMC disclosure directory and the delayed monthly holdings job as distinct parser contracts; directory rows are not holdings.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.PARSER_CONTRACT,
        EvidenceBasis.SOURCE_DOCUMENTATION,
        resolution_version="CROSS-001-v2",
        reviewed_at="2026-08-15",
    ),
    _resolution(
        "https://www.mcxindia.com/market-operations/clearing-settlement/delivery-reports",
        ("mcx_delivery_reports", "mcx_warehouse_stocks"),
        OverlapDisposition.DISTINCT_SHARED_ENDPOINT,
        "shared_endpoint:mcx_delivery_and_warehouse",
        "One MCX clearing page is a discovery landing for two jobs: expiry delivery/pay-in pressure and warehouse inventory. They keep separate contracts and cannot inherit each other's proof.",
        EvidenceBasis.CONTRACT_REVIEW,
        EvidenceBasis.SOURCE_DOCUMENTATION,
        resolution_version="CROSS-001-v2",
        reviewed_at="2026-08-15",
    ),
)
