from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from .models import DataTrust
from .source_inventory_compiler import compile_default_inventory
from .source_monitor import SOURCE_CATALOG


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_REGISTRY_PATH = PROJECT_ROOT / "TREND_FORGE_SOURCE_REGISTRY.md"
INVENTORY_START = "<!-- COMPLETE_LINK_INVENTORY_START -->"
INVENTORY_END = "<!-- COMPLETE_LINK_INVENTORY_END -->"
URL_PATTERN = re.compile(r"<(https?://[^>]+)>")


class RegistryUrlContract(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    url: str
    hostname: str
    source_role: str = Field(alias="sourceRole")
    allowed_jobs: list[str] = Field(alias="allowedJobs")
    can_unlock_ready: bool = Field(alias="canUnlockReady")
    authority_reason: str = Field(alias="authorityReason")


class ActiveSourceContract(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_key: str = Field(alias="sourceKey")
    artifact_family: str = Field(alias="artifactFamily")
    source_role: str = Field(alias="sourceRole")
    allowed_jobs: list[str] = Field(alias="allowedJobs")
    expected_frequency: str = Field(alias="expectedFrequency")
    stale_after_hours: int | None = Field(alias="staleAfterHours")
    parser_status: str = Field(alias="parserStatus")
    can_unlock_gate: bool = Field(alias="canUnlockGate")
    standalone_ready_authority: bool = Field(alias="standaloneReadyAuthority")
    live_verification_required: bool = Field(alias="liveVerificationRequired")
    dataset_root_id: str = Field(alias="datasetRootId")
    endpoint_ids: list[str] = Field(alias="endpointIds")
    maturity_state: str = Field(alias="maturityState")
    missing_contract_fields: list[str] = Field(alias="missingContractFields")
    safe_use: str = Field(alias="safeUse")
    blocked_use: str = Field(alias="blockedUse")
    next_action: str = Field(alias="nextAction")


class RegistryCoverage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    inventory_url_count: int = Field(alias="inventoryUrlCount")
    classified_url_count: int = Field(alias="classifiedUrlCount")
    unclassified_url_count: int = Field(alias="unclassifiedUrlCount")
    active_source_count: int = Field(alias="activeSourceCount")
    contracted_source_count: int = Field(alias="contractedSourceCount")
    gate_source_count: int = Field(alias="gateSourceCount")
    pending_live_verification_count: int = Field(alias="pendingLiveVerificationCount")
    role_counts: dict[str, int] = Field(alias="roleCounts")
    active_sources: list[ActiveSourceContract] = Field(alias="activeSources")
    unclassified_urls: list[str] = Field(alias="unclassifiedUrls")
    compiler_state: str = Field(alias="compilerState")
    source_activation_ready: bool = Field(alias="sourceActivationReady")
    rule: str


OFFICIAL_OR_PRIMARY_SUFFIXES = (
    "amfiindia.com",
    "bakerhughesrigcount.gcs-web.com",
    "bseindia.com",
    "cdslindia.com",
    "cftc.gov",
    "cmegroup.com",
    "desagri.gov.in",
    "commerce.gov.in",
    "data.gov.in",
    "dgciskol.gov.in",
    "eia.gov",
    "fbil.org.in",
    "fred.stlouisfed.org",
    "gold.org",
    "hydro.imd.gov.in",
    "imd.gov.in",
    "lbma.org.uk",
    "lme.com",
    "mca.gov.in",
    "mcxindia.com",
    "msei.in",
    "nseindia.com",
    "nsdl.co.in",
    "opec.org",
    "rbi.org.in",
    "sebi.gov.in",
    "sge.com.cn",
    "shfe.com.cn",
    "stats.gov.cn",
    "usda.gov",
)

SECONDARY_DISCOVERY_SUFFIXES = (
    "barchart.com",
    "cotpricecharts.com",
    "insiderscreener.com",
    "equitymaster.com",
    "mfapi.in",
    "moneycontrol.com",
    "myneta.info",
    "niftytrader.in",
    "quandl.com",
    "tickertape.in",
    "screener.in",
    "dhan.co",
    "trendlyne.com",
)

# Historical inventory links from this host remain visible, but no stable
# public data API was verified. They are audit hints, never data acquisition.
NOT_IN_USE_SUFFIXES = ("stockedge.com",)

REFERENCE_ONLY_SUFFIXES = (
    "chartalert.in",
    "chartink.com",
    "clickalgo.com",
    "gocharting.com",
    "harmonicpattern.com",
    "harmonictrader.com",
    "investarindia.com",
    "justticks.in",
    "marketinout.com",
    "motivewave.com",
    "patternshunters.com",
    "tradingview.com",
    "trendoscope.com",
    "trendspider.com",
    "trntrading.ai",
)

OPEN_SOURCE_REFERENCE_SUFFIXES = ("github.com", "readthedocs.io")
LICENSED_CANDIDATE_SUFFIXES = ("globaldatafeeds.in",)


CATEGORY_JOBS: dict[str, tuple[str, ...]] = {
    "universe_identity": ("ELIGIBILITY_VETO", "RESEARCH_CONTEXT"),
    "sector_membership": ("ELIGIBILITY_VETO", "RESEARCH_CONTEXT"),
    "stock_eod": ("ELIGIBILITY_VETO", "FLOW_CONFIRMATION", "EXECUTION_RISK"),
    "institutional_flow": ("SPONSOR_PROOF",),
    "stock_safety": ("ELIGIBILITY_VETO",),
    "promoter_risk": ("ELIGIBILITY_VETO", "SPONSOR_PROOF"),
    "derivatives_regime": ("ELIGIBILITY_VETO", "FLOW_CONFIRMATION"),
    "derivatives_intraday_context": ("FLOW_CONFIRMATION", "EXECUTION_RISK"),
    "derivatives_safety": ("ELIGIBILITY_VETO",),
    "borrow_pressure": ("FLOW_CONFIRMATION", "EXECUTION_RISK"),
    "stock_derivatives_eod": ("FLOW_CONFIRMATION", "EXECUTION_RISK"),
    "smart_money_events": ("CAUSAL_TRIGGER", "SPONSOR_PROOF", "EXECUTION_RISK"),
    "corporate_actions": ("ELIGIBILITY_VETO", "CAUSAL_TRIGGER"),
    "buyback": ("CAUSAL_TRIGGER", "SPONSOR_PROOF"),
    "control_change": ("CAUSAL_TRIGGER", "SPONSOR_PROOF", "EXECUTION_RISK"),
    "dii_stock_level": ("SPONSOR_PROOF",),
    "regulatory_filings": ("ELIGIBILITY_VETO", "CAUSAL_TRIGGER", "SPONSOR_PROOF"),
    "ownership_limits": ("ELIGIBILITY_VETO",),
    "company_registry": ("ELIGIBILITY_VETO", "SPONSOR_PROOF"),
    "mcx_eod": ("ELIGIBILITY_VETO", "FLOW_CONFIRMATION", "EXECUTION_RISK"),
    "mcx_currency_leg": ("ELIGIBILITY_VETO", "FLOW_CONFIRMATION", "EXECUTION_RISK"),
    "mcx_global_gold": ("CAUSAL_TRIGGER", "FLOW_CONFIRMATION"),
    "mcx_global_positioning": ("FLOW_CONFIRMATION",),
    "temporary_ohlcv": ("RESEARCH_ONLY",),
    "unofficial_wrapper": ("RESEARCH_ONLY",),
    "unofficial_intraday": ("RESEARCH_ONLY",),
}


GATE_ELIGIBLE_CATEGORIES = {
    "universe_identity",
    "sector_membership",
    "borrow_pressure",
    "corporate_actions",
    "derivatives_safety",
    "mcx_eod",
    "regulatory_filings",
    "smart_money_events",
    "stock_derivatives_eod",
    "stock_eod",
    "stock_safety",
}

DELAYED_CONTEXT_CATEGORIES = {
    "dii_stock_level",
    "derivatives_regime",
    "institutional_flow",
    "promoter_risk",
    "derivatives_intraday_context",
    "mcx_global_gold",
    "mcx_global_positioning",
}


def load_saved_link_inventory(path: Path | None = None) -> list[str]:
    registry_path = path or SOURCE_REGISTRY_PATH
    text = registry_path.read_text(encoding="utf-8")
    start = text.find(INVENTORY_START)
    end = text.find(INVENTORY_END)
    if start < 0 or end < 0 or end <= start:
        raise ValueError(
            "Canonical saved-link inventory markers are missing or out of order."
        )
    urls = URL_PATTERN.findall(text[start:end])
    return list(dict.fromkeys(urls))


def _host_matches(hostname: str, suffixes: tuple[str, ...]) -> bool:
    return any(
        hostname == suffix or hostname.endswith(f".{suffix}") for suffix in suffixes
    )


def _official_jobs(url: str) -> list[str]:
    lowered = url.lower()
    if any(
        token in lowered
        for token in ("asm", "gsm", "surveillance", "mwpl", "ban", "holiday")
    ):
        return ["ELIGIBILITY_VETO"]
    if any(
        token in lowered
        for token in ("option-chain", "derivative", "open-interest", "slb")
    ):
        return ["ELIGIBILITY_VETO", "FLOW_CONFIRMATION", "EXECUTION_RISK"]
    if any(
        token in lowered
        for token in ("insider", "sast", "sharehold", "pledge", "portfolio", "fii-dii")
    ):
        return ["SPONSOR_PROOF"]
    if any(
        token in lowered
        for token in ("deal", "buyback", "takeover", "corporate", "filing", "action")
    ):
        return ["CAUSAL_TRIGGER", "SPONSOR_PROOF"]
    if any(
        token in lowered
        for token in ("bhav", "price", "market-data", "all-reports", "future-prices")
    ):
        return ["ELIGIBILITY_VETO", "FLOW_CONFIRMATION", "EXECUTION_RISK"]
    if any(
        token in lowered
        for token in (
            "cftc",
            "gold",
            "petroleum",
            "naturalgas",
            "opec",
            "rig",
            "warehouse",
            "wasde",
            "rain",
        )
    ):
        return ["CAUSAL_TRIGGER", "FLOW_CONFIRMATION"]
    return ["RESEARCH_CONTEXT"]


def classify_registry_url(url: str) -> RegistryUrlContract:
    hostname = (urlparse(url).hostname or "").lower()
    if hostname in {"127.0.0.1", "localhost"}:
        return RegistryUrlContract(
            url=url,
            hostname=hostname,
            sourceRole="LOCAL_APPLICATION",
            allowedJobs=["OPERATIONS"],
            canUnlockReady=False,
            authorityReason="Local route for application operation and verification, not market evidence.",
        )
    if _host_matches(hostname, OFFICIAL_OR_PRIMARY_SUFFIXES):
        return RegistryUrlContract(
            url=url,
            hostname=hostname,
            sourceRole="OFFICIAL_OR_PRIMARY",
            allowedJobs=_official_jobs(url),
            canUnlockReady=False,
            authorityReason="Official or primary landing/data source; URL presence alone cannot unlock READY.",
        )
    if _host_matches(hostname, LICENSED_CANDIDATE_SUFFIXES):
        return RegistryUrlContract(
            url=url,
            hostname=hostname,
            sourceRole="LICENSED_CANDIDATE",
            allowedJobs=["FLOW_CONFIRMATION", "EXECUTION_RISK"],
            canUnlockReady=False,
            authorityReason="Requires a contracted feed, entitlement and verified adapter before gate use.",
        )
    if _host_matches(hostname, NOT_IN_USE_SUFFIXES):
        return RegistryUrlContract(
            url=url,
            hostname=hostname,
            sourceRole="NOT_IN_USE",
            allowedJobs=["NOT_IN_USE"],
            canUnlockReady=False,
            authorityReason="No stable public market-data API was verified; retained as an audit hint only.",
        )
    if _host_matches(hostname, SECONDARY_DISCOVERY_SUFFIXES):
        return RegistryUrlContract(
            url=url,
            hostname=hostname,
            sourceRole="SECONDARY_DISCOVERY",
            allowedJobs=["DISCOVERY"],
            canUnlockReady=False,
            authorityReason="May create a lead only; the claim must be reconciled to official evidence.",
        )
    if _host_matches(hostname, REFERENCE_ONLY_SUFFIXES):
        return RegistryUrlContract(
            url=url,
            hostname=hostname,
            sourceRole="REFERENCE_ONLY",
            allowedJobs=["DESIGN_REFERENCE"],
            canUnlockReady=False,
            authorityReason="Workflow, UX or comparison reference; not a TrendForge data authority.",
        )
    if _host_matches(hostname, OPEN_SOURCE_REFERENCE_SUFFIXES):
        return RegistryUrlContract(
            url=url,
            hostname=hostname,
            sourceRole="OPEN_SOURCE_REFERENCE",
            allowedJobs=["IMPLEMENTATION_REFERENCE"],
            canUnlockReady=False,
            authorityReason="Library or implementation reference subject to license and deterministic validation.",
        )
    return RegistryUrlContract(
        url=url,
        hostname=hostname,
        sourceRole="UNCLASSIFIED",
        allowedJobs=["QUARANTINE"],
        canUnlockReady=False,
        authorityReason="No reviewed domain policy exists; source is quarantined.",
    )


def classify_registry_urls(urls: list[str]) -> list[RegistryUrlContract]:
    return [classify_registry_url(url) for url in urls]


def _active_source_role(authority: DataTrust, category: str) -> str:
    if authority in {
        DataTrust.UNOFFICIAL_TEMP,
        DataTrust.UNOFFICIAL_WRAPPER,
        DataTrust.OPEN_SOURCE_UNOFFICIAL,
    }:
        return "UNOFFICIAL_RESEARCH"
    if authority == DataTrust.OFFICIAL_OR_LICENSED:
        return "OFFICIAL_OR_LICENSED_PENDING"
    if category in DELAYED_CONTEXT_CATEGORIES:
        return "OFFICIAL_DELAYED_CONTEXT"
    return "OFFICIAL_OR_PRIMARY"


def _requires_live_verification(parser_status: str) -> bool:
    return any(
        marker in parser_status
        for marker in (
            "PLANNED",
            "PENDING",
            "PARTIAL",
            "UNVERIFIED",
            "REFERENCE_ONLY",
            "FAIL_CLOSED",
        )
    )


def active_source_contracts() -> list[ActiveSourceContract]:
    report = compile_default_inventory()
    descriptors = {descriptor.key: descriptor for descriptor in SOURCE_CATALOG}
    contracts: list[ActiveSourceContract] = []
    for compiled in report.source_contracts:
        descriptor = descriptors.get(compiled.source_contract_id)
        required = {
            "endpoint_ids": bool(compiled.endpoint_ids),
            "artifact_kind": compiled.artifact_kind != "UNSPECIFIED",
            "parser_id": bool(compiled.parser_id),
            "parser_version": bool(compiled.parser_version),
            "dataset_id": bool(compiled.dataset_id),
            "decision_jobs": bool(compiled.decision_jobs),
            "feature_ids": bool(compiled.feature_ids),
            "strategy_profiles": bool(compiled.strategy_profiles),
            "authority_cap": compiled.authority_cap != "UNSPECIFIED_NO_VOTE",
            "allowed_timeframes": bool(compiled.allowed_timeframes),
            "allowed_instruments": bool(compiled.allowed_instruments),
            "tests": bool(compiled.tests),
        }
        missing = sorted(
            set(compiled.missing_extended_fields)
            | {name for name, present in required.items() if not present}
        )
        endpoint_url = next(
            (
                endpoint.canonical_url
                for endpoint in report.normalized_endpoints
                if endpoint.endpoint_id in compiled.endpoint_ids
            ),
            "",
        )
        role = (
            classify_registry_url(endpoint_url).source_role
            if endpoint_url
            else "QUARANTINED"
        )
        live_verification_required = bool(
            missing or compiled.contract_status != "COMPLETE"
        )
        contracts.append(
            ActiveSourceContract(
                sourceKey=compiled.source_contract_id,
                artifactFamily=(
                    descriptor.category if descriptor else compiled.artifact_kind
                ),
                sourceRole=role,
                allowedJobs=compiled.decision_jobs,
                expectedFrequency=(
                    descriptor.expected_frequency if descriptor else "UNSPECIFIED"
                ),
                staleAfterHours=(descriptor.stale_after_hours if descriptor else None),
                parserStatus=compiled.contract_status,
                canUnlockGate=bool(
                    report.source_activation_ready and compiled.gate_permission
                ),
                standaloneReadyAuthority=False,
                liveVerificationRequired=live_verification_required,
                datasetRootId=compiled.dataset_root_id,
                endpointIds=compiled.endpoint_ids,
                maturityState=compiled.maturity_state.value,
                missingContractFields=missing,
                safeUse=compiled.safe_use,
                blockedUse=compiled.blocked_use,
                nextAction=compiled.next_action,
            )
        )
    return contracts


def build_registry_coverage() -> RegistryCoverage:
    report = compile_default_inventory()
    inventory = [row.canonical_url for row in report.normalized_endpoints]
    classified = classify_registry_urls(inventory)
    active = active_source_contracts()
    unclassified = [
        record.url for record in classified if record.source_role == "UNCLASSIFIED"
    ]
    role_counts: dict[str, int] = {}
    for record in classified:
        role_counts[record.source_role] = role_counts.get(record.source_role, 0) + 1
    return RegistryCoverage(
        inventoryUrlCount=len(inventory),
        classifiedUrlCount=len(classified) - len(unclassified),
        unclassifiedUrlCount=len(unclassified),
        activeSourceCount=len(active),
        contractedSourceCount=len(active),
        gateSourceCount=sum(1 for contract in active if contract.can_unlock_gate),
        pendingLiveVerificationCount=sum(
            1 for contract in active if contract.live_verification_required
        ),
        roleCounts=role_counts,
        activeSources=active,
        unclassifiedUrls=unclassified,
        compilerState=report.compiler_state.value,
        sourceActivationReady=report.source_activation_ready,
        rule=(
            "Compiler and URL classification are inventory governance only. "
            "No source may unlock CONFIRMED until its explicit contract, current "
            "artifact, parser, normalization, freshness, evidence-family and gate "
            "requirements are all proven."
        ),
    )
