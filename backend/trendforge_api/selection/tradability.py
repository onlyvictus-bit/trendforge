"""CROSS-015 / FTR-035 unified, fail-closed tradability restriction gate.

The gate consolidates exchange restrictions before S7 assigns a public state.
It is a veto/readiness contract only: PASS is never evidence and never unlocks
CONFIRMED by itself.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any, Iterable, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .contracts import stable_id


SCHEMA_VERSION = "trendforge.tradability.v1"
PROFILE_ID = "FTR-035-TRADABILITY"
POLICY_VERSION = "1.0.0"
MODEL_CONFIG = ConfigDict(
    alias_generator=to_camel, populate_by_name=True, frozen=True
)


class TradabilityOutcome(StrEnum):
    PASS = "PASS"
    WAIT = "WAIT"
    REJECT = "REJECT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SourceEvidenceState(StrEnum):
    POPULATED = "POPULATED"
    VALID_EMPTY = "VALID_EMPTY"
    MISSING = "MISSING"
    STALE = "STALE"
    MALFORMED = "MALFORMED"
    CONFLICTING = "CONFLICTING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RestrictionSourceV1(BaseModel):
    model_config = MODEL_CONFIG

    source_key: str
    evidence_state: SourceEvidenceState
    data_date: str | None = None
    parser_version: str | None = None
    content_hash: str | None = None
    rows: tuple[dict[str, Any], ...] = ()
    detail: str | None = None


class TradabilityComponentV1(BaseModel):
    model_config = MODEL_CONFIG

    component: str
    market: str
    outcome: TradabilityOutcome
    reason_code: str
    source_key: str | None = None
    source_state: SourceEvidenceState = SourceEvidenceState.NOT_APPLICABLE
    data_date: str | None = None
    parser_version: str | None = None
    content_hash: str | None = None
    matched: bool = False
    detail: str


class TradabilityResultV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    profile_id: str
    market: str
    horizon: str
    evaluated_at: datetime
    outcome: TradabilityOutcome
    primary_reason: str
    reason_codes: tuple[str, ...]
    components: tuple[TradabilityComponentV1, ...]
    tradability_hash: str
    can_confirm: bool = False
    vote_eligible: bool = False
    applies_to_underlying: bool = True

    @model_validator(mode="after")
    def enforce_non_voting_law(self) -> "TradabilityResultV1":
        if self.can_confirm or self.vote_eligible:
            raise ValueError("tradability may veto or wait; it can never vote/confirm")
        return self

    def component(self, name: str) -> TradabilityComponentV1:
        target = name.strip().upper()
        for item in self.components:
            if item.component == target:
                return item
        raise KeyError(target)


class TradabilityBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    policy_profile_id: str
    policy_version: str = POLICY_VERSION
    run_id: str
    run_hash: str
    evaluated_at: datetime
    rows: tuple[TradabilityResultV1, ...]
    pass_count: int = Field(ge=0)
    wait_count: int = Field(ge=0)
    reject_count: int = Field(ge=0)
    can_unlock_confirmed: bool = False
    warnings: tuple[str, ...] = (
        "Tradability PASS is not evidence and cannot unlock CONFIRMED.",
    )

    @model_validator(mode="after")
    def enforce_batch_law(self) -> "TradabilityBatchV1":
        if self.can_unlock_confirmed:
            raise ValueError("tradability batch cannot unlock CONFIRMED")
        counts = {
            TradabilityOutcome.PASS: self.pass_count,
            TradabilityOutcome.WAIT: self.wait_count,
            TradabilityOutcome.REJECT: self.reject_count,
        }
        for outcome, expected in counts.items():
            if sum(row.outcome is outcome for row in self.rows) != expected:
                raise ValueError(f"invalid {outcome.value} count")
        return self


_POLICIES = {
    "PRF-001": ("NSE", "INTRADAY"),
    "PRF-002": ("NSE", "INTRADAY"),
    "PRF-003": ("NSE", "SWING_EOD"),
    "PRF-004": ("NSE", "SWING_EVENT"),
    "PRF-005": ("MCX", "INTRADAY_AND_SWING"),
    "PRF-006": ("MCX", "INTRADAY_AND_SWING"),
    "PRF-007": ("MCX", "INTRADAY_AND_SWING"),
    "PRF-003-SWING-EOD": ("NSE", "SWING_EOD"),
}

_SOURCE_BY_COMPONENT = {
    "T2T": "nse_trade_to_trade",
    "ASM": "nse_asm",
    "GSM": "nse_gsm",
    "ESM": "nse_esm",
    "PRICE_BAND": "nse_price_bands",
    "HALT": "nse_market_status",
    "SECURITY_STATUS": "nse_equity_universe",
    "AUCTION": "nse_auction_securities",
    "FNO_BAN": "nse_fno_ban",
    "MWPL": "nse_mwpl_percentages",
}

_SOURCE_FAILURE_REASON = {
    SourceEvidenceState.MISSING: "SOURCE_MISSING",
    SourceEvidenceState.STALE: "SOURCE_STALE",
    SourceEvidenceState.MALFORMED: "SOURCE_MALFORMED",
    SourceEvidenceState.CONFLICTING: "SOURCE_CONFLICTING",
}


def _normalized_symbol(row: Mapping[str, Any]) -> str:
    return str(
        row.get("symbol")
        or row.get("SYMBOL")
        or row.get("nse_symbol")
        or row.get("underlying")
        or ""
    ).strip().upper()


def _stage_number(row: Mapping[str, Any]) -> int:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("stage", "measure", "code", "description")
    ).upper()
    roman = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}
    match = re.search(r"(?:STAGE\s*)?(VI|IV|V|III|II|I|[1-9])\b", text)
    if not match:
        return 0
    token = match.group(1)
    return roman.get(token, int(token) if token.isdigit() else 0)


def _component(
    name: str,
    market: str,
    outcome: TradabilityOutcome,
    reason: str,
    detail: str,
    source: RestrictionSourceV1 | None = None,
    *,
    matched: bool = False,
) -> TradabilityComponentV1:
    return TradabilityComponentV1(
        component=name,
        market=market,
        outcome=outcome,
        reasonCode=reason,
        sourceKey=source.source_key if source else None,
        sourceState=(
            source.evidence_state if source else SourceEvidenceState.NOT_APPLICABLE
        ),
        dataDate=source.data_date if source else None,
        parserVersion=source.parser_version if source else None,
        contentHash=source.content_hash if source else None,
        matched=matched,
        detail=detail,
    )


def _source_ready_component(
    name: str,
    market: str,
    source: RestrictionSourceV1 | None,
) -> TradabilityComponentV1 | None:
    if source is None:
        source = RestrictionSourceV1(
            sourceKey=_SOURCE_BY_COMPONENT[name],
            evidenceState=SourceEvidenceState.MISSING,
        )
    suffix = _SOURCE_FAILURE_REASON.get(source.evidence_state)
    if suffix:
        return _component(
            name,
            market,
            TradabilityOutcome.WAIT,
            f"WAIT_{name}_{suffix}",
            f"{name} cannot be cleared because {source.evidence_state.value.lower()} evidence is not usable.",
            source,
        )
    return None


def _rows_for(source: RestrictionSourceV1, symbol: str) -> tuple[dict[str, Any], ...]:
    return tuple(row for row in source.rows if _normalized_symbol(row) == symbol)


def _list_component(
    name: str,
    symbol: str,
    market: str,
    source: RestrictionSourceV1 | None,
    *,
    matched_outcome: TradabilityOutcome,
    matched_reason: str,
) -> TradabilityComponentV1:
    unavailable = _source_ready_component(name, market, source)
    if unavailable:
        return unavailable
    assert source is not None
    matches = _rows_for(source, symbol)
    if not matches:
        return _component(
            name, market, TradabilityOutcome.PASS, f"PASS_{name}_CLEAR",
            f"{symbol} is absent from the current schema-valid {name} restriction set.",
            source,
        )
    return _component(
        name, market, matched_outcome, matched_reason,
        f"{symbol} is present in the current {name} restriction set.",
        source, matched=True,
    )


def _price_band_component(
    symbol: str,
    market: str,
    source: RestrictionSourceV1 | None,
    current_price: float | None,
) -> TradabilityComponentV1:
    unavailable = _source_ready_component("PRICE_BAND", market, source)
    if unavailable:
        return unavailable
    assert source is not None
    matches = _rows_for(source, symbol)
    if not matches:
        return _component(
            "PRICE_BAND", market, TradabilityOutcome.WAIT,
            "WAIT_PRICE_BAND_SYMBOL_MISSING",
            "The complete price-band file does not contain this symbol.", source,
        )
    row = matches[0]
    if row.get("hasPriceBand") is False:
        return _component(
            "PRICE_BAND",
            market,
            TradabilityOutcome.PASS,
            "PASS_PRICE_BAND_NOT_APPLICABLE",
            "The official complete list classifies this symbol as No Band.",
            source,
        )
    lower = row.get("lowerBand") or row.get("lower_band") or row.get("lowerPriceBand")
    upper = row.get("upperBand") or row.get("upper_band") or row.get("upperPriceBand")
    try:
        low, high = float(lower), float(upper)
    except (TypeError, ValueError):
        return _component(
            "PRICE_BAND", market, TradabilityOutcome.WAIT,
            "WAIT_PRICE_BAND_VALUES_MISSING",
            "The symbol row lacks valid lower and upper price-band values.", source,
        )
    if low <= 0 or high <= low:
        return _component(
            "PRICE_BAND", market, TradabilityOutcome.WAIT,
            "WAIT_PRICE_BAND_VALUES_INVALID", "Price-band geometry is invalid.", source,
        )
    if current_price is None:
        return _component(
            "PRICE_BAND", market, TradabilityOutcome.WAIT,
            "WAIT_PRICE_FOR_BAND_CHECK", "A current aligned price is required for the band check.", source,
        )
    epsilon = max(0.01, current_price * 0.0001)
    if current_price <= low + epsilon or current_price >= high - epsilon:
        return _component(
            "PRICE_BAND", market, TradabilityOutcome.REJECT,
            "REJECT_PRICE_BAND_LOCKED", "Price is at or beyond an exchange band boundary.",
            source, matched=True,
        )
    distance = min((current_price - low) / current_price, (high - current_price) / current_price)
    if distance <= 0.01:
        return _component(
            "PRICE_BAND", market, TradabilityOutcome.WAIT,
            "WAIT_PRICE_BAND_PROXIMITY", "Price is within one percent of an exchange band.",
            source, matched=True,
        )
    return _component(
        "PRICE_BAND", market, TradabilityOutcome.PASS, "PASS_PRICE_BAND_CLEAR",
        "Price is inside the current exchange band with more than one percent room.", source,
    )


def _market_status_component(
    market: str,
    horizon: str,
    source: RestrictionSourceV1 | None,
) -> TradabilityComponentV1:
    unavailable = _source_ready_component("HALT", market, source)
    if unavailable:
        return unavailable
    assert source is not None
    statuses = " ".join(
        str(row.get("status") or row.get("marketStatus") or row.get("market_status") or "")
        for row in source.rows
        if "CAPITAL" in str(row.get("market") or row.get("marketType") or "CAPITAL").upper()
    ).upper()
    if not statuses:
        return _component(
            "HALT", market, TradabilityOutcome.WAIT, "WAIT_HALT_STATUS_UNKNOWN",
            "The market-status artifact has no recognized capital-market state.", source,
        )
    if any(token in statuses for token in ("HALT", "SUSPEND")):
        return _component(
            "HALT", market, TradabilityOutcome.REJECT, "REJECT_MARKET_HALTED",
            "The official market-status artifact reports a halt or suspension.", source,
            matched=True,
        )
    if "INTRADAY" in horizon and "OPEN" not in statuses:
        return _component(
            "HALT", market, TradabilityOutcome.REJECT, "REJECT_MARKET_NOT_OPEN",
            "The capital market is not open for this intraday evaluation.", source,
            matched=True,
        )
    return _component(
        "HALT", market, TradabilityOutcome.PASS, "PASS_MARKET_STATUS_CLEAR",
        "The official market state is compatible with this horizon.", source,
    )


def _security_status_component(
    symbol: str,
    market: str,
    source: RestrictionSourceV1 | None,
) -> TradabilityComponentV1:
    unavailable = _source_ready_component("SECURITY_STATUS", market, source)
    if unavailable:
        return unavailable
    assert source is not None
    matches = _rows_for(source, symbol)
    if not matches:
        return _component(
            "SECURITY_STATUS", market, TradabilityOutcome.WAIT,
            "WAIT_SECURITY_STATUS_SYMBOL_MISSING",
            "The current official security master does not contain this symbol.", source,
        )
    row = matches[0]
    active = row.get("active")
    status = str(row.get("status") or row.get("tradingStatus") or "").upper()
    if active in {False, 0, "0"} or any(token in status for token in ("SUSPEND", "HALT", "INACTIVE")):
        return _component(
            "SECURITY_STATUS", market, TradabilityOutcome.REJECT,
            "REJECT_SECURITY_SUSPENDED",
            "The official security master marks the symbol inactive or suspended.",
            source, matched=True,
        )
    return _component(
        "SECURITY_STATUS", market, TradabilityOutcome.PASS,
        "PASS_SECURITY_STATUS_ACTIVE",
        "The current official security master contains an active symbol.", source,
    )


def _mwpl_component(
    symbol: str,
    market: str,
    source: RestrictionSourceV1 | None,
) -> TradabilityComponentV1:
    unavailable = _source_ready_component("MWPL", market, source)
    if unavailable:
        return unavailable
    assert source is not None
    matches = _rows_for(source, symbol)
    if not matches:
        return _component(
            "MWPL", market, TradabilityOutcome.WAIT, "WAIT_MWPL_SYMBOL_MISSING",
            "No current symbol-level MWPL percentage is available.", source,
        )
    try:
        value = float(matches[0].get("mwplPercent") or matches[0].get("mwpl_percent"))
    except (TypeError, ValueError):
        return _component(
            "MWPL", market, TradabilityOutcome.WAIT, "WAIT_MWPL_VALUE_MISSING",
            "The MWPL row lacks a valid utilization percentage.", source,
        )
    if value >= 95:
        return _component(
            "MWPL", market, TradabilityOutcome.REJECT, "REJECT_MWPL_BANNED",
            "MWPL utilization is at or above the ban threshold.", source, matched=True,
        )
    if value >= 80:
        return _component(
            "MWPL", market, TradabilityOutcome.WAIT, "WAIT_MWPL_ELEVATED",
            "MWPL utilization is elevated and blocks OI-dependent approval.", source,
            matched=True,
        )
    return _component(
        "MWPL", market, TradabilityOutcome.PASS, "PASS_MWPL_CLEAR",
        "MWPL utilization is below the caution threshold.", source,
    )


def _mcx_result(
    *, symbol: str, profile_id: str, horizon: str, decision_at: datetime,
    mcx_assessment: Any | None,
) -> TradabilityResultV1:
    if mcx_assessment is None:
        components = (
            _component(
                "MCX_CONTRACT", "MCX", TradabilityOutcome.WAIT,
                "WAIT_MCX_CONTRACT_ASSESSMENT",
                "A typed local MCX master, price/OI and calendar assessment is required.",
            ),
        )
    else:
        raw_state = str(getattr(mcx_assessment, "state", "WAIT"))
        outcome = (
            TradabilityOutcome.REJECT if "REJECT" in raw_state
            else TradabilityOutcome.PASS if "WATCH" in raw_state or "PASS" in raw_state
            else TradabilityOutcome.WAIT
        )
        codes = tuple(
            str(getattr(gate, "gate_id", None) or getattr(gate, "gateId", None) or "WAIT_MCX_GATE")
            for gate in getattr(mcx_assessment, "gate_results", ())
        )
        components = (
            _component(
                "MCX_CONTRACT", "MCX", outcome,
                codes[0] if codes else f"{outcome.value}_MCX_CONTRACT",
                "Existing typed MCX master/local/calendar assessment was adapted.",
            ),
        )
    return _finalize_result(
        symbol=symbol, profile_id=profile_id, market="MCX", horizon=horizon,
        decision_at=decision_at, components=components,
    )


def _finalize_result(
    *, symbol: str, profile_id: str, market: str, horizon: str,
    decision_at: datetime, components: Iterable[TradabilityComponentV1],
) -> TradabilityResultV1:
    ordered = tuple(components)
    rejects = [item for item in ordered if item.outcome is TradabilityOutcome.REJECT]
    waits = [item for item in ordered if item.outcome is TradabilityOutcome.WAIT]
    if rejects:
        outcome, primary = TradabilityOutcome.REJECT, rejects[0].reason_code
    elif waits:
        outcome, primary = TradabilityOutcome.WAIT, waits[0].reason_code
    else:
        outcome, primary = TradabilityOutcome.PASS, "PASS_TRADABILITY_CLEAR"
    reasons = tuple(item.reason_code for item in ordered if item.outcome is not TradabilityOutcome.NOT_APPLICABLE)
    identity = {
        "symbol": symbol,
        "profileId": profile_id,
        "market": market,
        "horizon": horizon,
        "evaluatedAt": decision_at.isoformat(),
        "outcome": outcome.value,
        "components": [item.model_dump(mode="json", by_alias=True) for item in ordered],
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return TradabilityResultV1(
        symbol=symbol, profileId=profile_id, market=market, horizon=horizon,
        evaluatedAt=decision_at, outcome=outcome, primaryReason=primary,
        reasonCodes=reasons, components=ordered, tradabilityHash=digest,
    )


def evaluate_tradability(
    *,
    symbol: str,
    profile_id: str,
    decision_at: datetime,
    sources: Mapping[str, RestrictionSourceV1],
    current_price: float | None = None,
    derivatives_used: bool = False,
    mcx_assessment: Any | None = None,
) -> TradabilityResultV1:
    """Evaluate one symbol using only schema-valid point-in-time source facts."""

    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise ValueError("decision_at must be timezone-aware")
    if profile_id not in _POLICIES:
        raise ValueError(f"UNKNOWN_TRADABILITY_PROFILE:{profile_id}")
    normalized = symbol.strip().upper()
    market, horizon = _POLICIES[profile_id]
    if market == "MCX":
        return _mcx_result(
            symbol=normalized, profile_id=profile_id, horizon=horizon,
            decision_at=decision_at, mcx_assessment=mcx_assessment,
        )

    intraday = "INTRADAY" in horizon
    components: list[TradabilityComponentV1] = []
    components.append(
        _list_component(
            "T2T", normalized, market, sources.get("nse_trade_to_trade"),
            matched_outcome=(TradabilityOutcome.REJECT if intraday else TradabilityOutcome.WAIT),
            matched_reason=("REJECT_T2T_INTRADAY" if intraday else "WAIT_T2T_DELIVERY_ONLY"),
        )
    )
    components.append(
        _list_component(
            "ASM", normalized, market, sources.get("nse_asm"),
            matched_outcome=TradabilityOutcome.WAIT, matched_reason="WAIT_ASM_ACTIVE",
        )
    )

    for name in ("GSM", "ESM"):
        source = sources.get(_SOURCE_BY_COMPONENT[name])
        unavailable = _source_ready_component(name, market, source)
        if unavailable:
            components.append(unavailable)
            continue
        assert source is not None
        matches = _rows_for(source, normalized)
        if not matches:
            components.append(
                _component(
                    name, market, TradabilityOutcome.PASS, f"PASS_{name}_CLEAR",
                    f"{normalized} is absent from the current {name} restriction set.", source,
                )
            )
            continue
        stage = max(_stage_number(row) for row in matches)
        reject = (name == "GSM" and stage >= 3) or (name == "ESM" and intraday and stage >= 2)
        components.append(
            _component(
                name, market,
                TradabilityOutcome.REJECT if reject else TradabilityOutcome.WAIT,
                f"{'REJECT' if reject else 'WAIT'}_{name}_STAGE",
                f"{normalized} has active {name} stage {stage or 'UNKNOWN'}.",
                source, matched=True,
            )
        )

    components.append(
        _price_band_component(normalized, market, sources.get("nse_price_bands"), current_price)
    )
    components.append(
        _market_status_component(market, horizon, sources.get("nse_market_status"))
    )
    components.append(
        _security_status_component(normalized, market, sources.get("nse_equity_universe"))
    )

    if intraday:
        components.append(
            _list_component(
                "AUCTION", normalized, market, sources.get("nse_auction_securities"),
                matched_outcome=TradabilityOutcome.WAIT,
                matched_reason="WAIT_AUCTION_SECURITY_ACTIVE",
            )
        )
    else:
        components.append(
            _component(
                "AUCTION", market, TradabilityOutcome.NOT_APPLICABLE,
                "NOT_APPLICABLE_AUCTION_SWING", "Auction state is not a swing-EOD gate.",
            )
        )

    if derivatives_used:
        components.append(
            _list_component(
                "FNO_BAN", normalized, market, sources.get("nse_fno_ban"),
                matched_outcome=TradabilityOutcome.REJECT,
                matched_reason="REJECT_FNO_BAN_ACTIVE",
            )
        )
        components.append(
            _mwpl_component(normalized, market, sources.get("nse_mwpl_percentages"))
        )
    else:
        for name in ("FNO_BAN", "MWPL"):
            components.append(
                _component(
                    name, market, TradabilityOutcome.NOT_APPLICABLE,
                    f"NOT_APPLICABLE_{name}_CASH",
                    f"{name} applies only when derivatives are used.",
                )
            )

    return _finalize_result(
        symbol=normalized, profile_id=profile_id, market=market, horizon=horizon,
        decision_at=decision_at, components=components,
    )


def load_restriction_sources(
    source_keys: Iterable[str], *, as_of: date | None = None
) -> dict[str, RestrictionSourceV1]:
    """Read and re-parse current archived source artifacts without fetching/writing."""

    from .. import storage
    from ..parsers.source_freshness import is_data_date_fresh
    from ..source_parser import parse_source
    from .cash_a1_staging import default_market_data_store

    current = as_of or date.today()
    loaded: dict[str, RestrictionSourceV1] = {}
    market_store = default_market_data_store()
    for key in sorted(set(source_keys)):
        try:
            latest = market_store.latest_for(key)
            if latest is not None:
                artifact = market_store.object_path_for_hash(latest.content_hash)
                normalized = json.loads(artifact.read_bytes())
                if (
                    not isinstance(normalized, dict)
                    or normalized.get("sourceKey") != key
                    or normalized.get("normalizedSourceKey") != key
                ):
                    raise ValueError("canonical normalized artifact identity mismatch")
                parser_state = str(normalized.get("parserState") or "")
                data_date = normalized.get("dataDate")
                outputs = (normalized.get("payload") or {}).get("outputs") or ()
                rows = tuple(
                    row
                    for output in outputs
                    if isinstance(output, dict)
                    for row in output.get("rows", ())
                    if isinstance(row, dict)
                )
                valid_empty = bool(
                    any(
                        isinstance(output, dict)
                        and (
                            output.get("validEmpty") is True
                            or output.get("noDataNow") is True
                        )
                        for output in outputs
                    )
                )
                if not rows and not valid_empty:
                    rows = tuple(
                        row
                        for row in normalized.get("records", ())
                        if isinstance(row, dict)
                    )
                if parser_state != "PARSED_STRUCTURED":
                    state = SourceEvidenceState.MALFORMED
                elif not is_data_date_fresh(key, data_date, now=current):
                    state = SourceEvidenceState.STALE
                elif rows:
                    state = SourceEvidenceState.POPULATED
                elif valid_empty:
                    state = SourceEvidenceState.VALID_EMPTY
                else:
                    state = SourceEvidenceState.MALFORMED
                loaded[key] = RestrictionSourceV1(
                    sourceKey=key,
                    evidenceState=state,
                    dataDate=data_date,
                    parserVersion="market-data-normalized-v1",
                    contentHash=latest.content_hash,
                    rows=rows,
                    detail=(
                        f"Loaded canonical normalized last-good: {len(rows)} row(s)."
                        if rows
                        else "Loaded canonical normalized schema-valid empty last-good."
                    ),
                )
                continue
        except (OSError, ValueError, KeyError):
            # A corrupt canonical object is malformed evidence, not permission
            # to silently substitute an older legacy-monitor artifact.
            loaded[key] = RestrictionSourceV1(
                sourceKey=key,
                evidenceState=SourceEvidenceState.MALFORMED,
                detail="Canonical market-data last-good could not be read or parsed.",
            )
            continue
        metadata = storage.list_source_parser_outputs(key, limit=1)
        if not metadata:
            loaded[key] = RestrictionSourceV1(
                sourceKey=key, evidenceState=SourceEvidenceState.MISSING,
                detail="No archived parser output exists.",
            )
            continue
        meta = metadata[0]
        try:
            parsed = parse_source(key, save=False)
        except Exception as exc:
            loaded[key] = RestrictionSourceV1(
                sourceKey=key, evidenceState=SourceEvidenceState.MALFORMED,
                dataDate=meta.get("data_date"), parserVersion=meta.get("parser_version"),
                contentHash=meta.get("content_hash"), detail=f"Reparse failed: {type(exc).__name__}",
            )
            continue
        rows = tuple(row for row in parsed.output.get("rows", ()) if isinstance(row, dict))
        valid_empty = bool(
            parsed.output.get("validEmpty")
            or parsed.output.get("noDataNow") is True
        )
        if parsed.parser_state != "PARSED_STRUCTURED":
            state = SourceEvidenceState.MALFORMED
        elif not is_data_date_fresh(key, parsed.data_date, now=current):
            state = SourceEvidenceState.STALE
        elif parsed.record_count > 0 and rows:
            state = SourceEvidenceState.POPULATED
        elif parsed.record_count == 0 and valid_empty:
            state = SourceEvidenceState.VALID_EMPTY
        else:
            state = SourceEvidenceState.MALFORMED
        loaded[key] = RestrictionSourceV1(
            sourceKey=key, evidenceState=state, dataDate=parsed.data_date,
            parserVersion=meta.get("parser_version"), contentHash=meta.get("content_hash"),
            rows=rows, detail=parsed.summary,
        )
    return loaded


def build_tradability_batch(
    *,
    symbols: Iterable[str],
    profile_id: str,
    decision_at: datetime | None = None,
    sources: Mapping[str, RestrictionSourceV1] | None = None,
    prices_by_symbol: Mapping[str, float] | None = None,
    derivatives_used: bool = False,
    mcx_assessments: Mapping[str, Any] | None = None,
) -> TradabilityBatchV1:
    evaluated = decision_at or datetime.now(timezone.utc)
    if profile_id not in _POLICIES:
        raise ValueError(f"UNKNOWN_TRADABILITY_PROFILE:{profile_id}")
    market, _horizon = _POLICIES[profile_id]
    required = (
        ()
        if market == "MCX"
        else (
            "nse_trade_to_trade", "nse_asm", "nse_gsm", "nse_esm",
            "nse_price_bands", "nse_market_status",
            "nse_equity_universe",
            *(('nse_auction_securities',) if "INTRADAY" in _horizon else ()),
            *(('nse_fno_ban', 'nse_mwpl_percentages') if derivatives_used else ()),
        )
    )
    source_map = dict(sources) if sources is not None else load_restriction_sources(required, as_of=evaluated.date())
    prices = {str(k).upper(): v for k, v in (prices_by_symbol or {}).items()}
    mcx_map = {str(k).upper(): v for k, v in (mcx_assessments or {}).items()}
    rows = tuple(
        evaluate_tradability(
            symbol=symbol, profile_id=profile_id, decision_at=evaluated,
            sources=source_map, current_price=prices.get(symbol.strip().upper()),
            derivatives_used=derivatives_used,
            mcx_assessment=mcx_map.get(symbol.strip().upper()),
        )
        for symbol in sorted({item.strip().upper() for item in symbols if item.strip()})
    )
    identity = {
        "schemaVersion": SCHEMA_VERSION,
        "policyProfileId": profile_id,
        "policyVersion": POLICY_VERSION,
        "evaluatedAt": evaluated.isoformat(),
        "rows": [row.model_dump(mode="json", by_alias=True) for row in rows],
    }
    run_hash = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return TradabilityBatchV1(
        policyProfileId=profile_id,
        runId=stable_id("tradability", profile_id, evaluated.isoformat(), run_hash),
        runHash=run_hash,
        evaluatedAt=evaluated,
        rows=rows,
        passCount=sum(row.outcome is TradabilityOutcome.PASS for row in rows),
        waitCount=sum(row.outcome is TradabilityOutcome.WAIT for row in rows),
        rejectCount=sum(row.outcome is TradabilityOutcome.REJECT for row in rows),
    )


def pass_fixture_batch(
    symbols: Iterable[str], *, profile_id: str = "PRF-003",
    decision_at: datetime | None = None,
) -> TradabilityBatchV1:
    """Explicit test helper; runtime code never calls this function."""

    evaluated = decision_at or datetime.now(timezone.utc)
    sources = {
        "nse_trade_to_trade": RestrictionSourceV1(sourceKey="nse_trade_to_trade", evidenceState="VALID_EMPTY", dataDate=evaluated.date().isoformat()),
        "nse_asm": RestrictionSourceV1(sourceKey="nse_asm", evidenceState="VALID_EMPTY", dataDate=evaluated.date().isoformat()),
        "nse_gsm": RestrictionSourceV1(sourceKey="nse_gsm", evidenceState="VALID_EMPTY", dataDate=evaluated.date().isoformat()),
        "nse_esm": RestrictionSourceV1(sourceKey="nse_esm", evidenceState="VALID_EMPTY", dataDate=evaluated.date().isoformat()),
        "nse_price_bands": RestrictionSourceV1(
            sourceKey="nse_price_bands", evidenceState="POPULATED", dataDate=evaluated.date().isoformat(),
            rows=tuple({"symbol": s.strip().upper(), "lowerBand": 1, "upperBand": 1_000_000} for s in symbols),
        ),
        "nse_market_status": RestrictionSourceV1(
            sourceKey="nse_market_status", evidenceState="POPULATED", dataDate=evaluated.date().isoformat(),
            rows=({"market": "Capital Market", "status": "Open"},),
        ),
        "nse_equity_universe": RestrictionSourceV1(
            sourceKey="nse_equity_universe", evidenceState="POPULATED", dataDate=evaluated.date().isoformat(),
            rows=tuple({"symbol": s.strip().upper(), "series": "EQ", "active": 1} for s in symbols),
        ),
    }
    prices = {s.strip().upper(): 100.0 for s in symbols}
    return build_tradability_batch(
        symbols=symbols, profile_id=profile_id, decision_at=evaluated,
        sources=sources, prices_by_symbol=prices,
    )


__all__ = [
    "POLICY_VERSION", "PROFILE_ID", "SCHEMA_VERSION", "RestrictionSourceV1",
    "SourceEvidenceState", "TradabilityBatchV1", "TradabilityComponentV1",
    "TradabilityOutcome", "TradabilityResultV1", "build_tradability_batch",
    "evaluate_tradability", "load_restriction_sources", "pass_fixture_batch",
]
