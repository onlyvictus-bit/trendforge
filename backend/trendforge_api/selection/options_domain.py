from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from math import isfinite
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from ..source_contracts import SourceResult, SourceResultState
from .contracts import (
    GateOutcome,
    InstrumentIdentity,
    MODEL_CONFIG,
    SelectionGateResult,
    SelectionState,
)


class OptionType(StrEnum):
    CE = "CE"
    PE = "PE"


class OptionQuote(BaseModel):
    model_config = MODEL_CONFIG

    expiry: date
    strike: float = Field(gt=0)
    option_type: OptionType
    bid: float | None = Field(default=None, ge=0)
    ask: float | None = Field(default=None, ge=0)
    ltp: float | None = Field(default=None, ge=0)
    open_interest: float = Field(ge=0)
    volume: float = Field(ge=0)
    implied_volatility: float | None = Field(default=None, gt=0)

    @field_validator(
        "strike",
        "bid",
        "ask",
        "ltp",
        "open_interest",
        "volume",
        "implied_volatility",
    )
    @classmethod
    def require_finite(cls, value: float | None) -> float | None:
        if value is not None and not isfinite(value):
            raise ValueError("option quote values must be finite")
        return value

    @model_validator(mode="after")
    def validate_market(self) -> "OptionQuote":
        if self.bid is not None and self.ask is not None and self.ask < self.bid:
            raise ValueError("option ask cannot be below bid")
        if self.ltp is None and self.bid is None and self.ask is None:
            raise ValueError("option row needs LTP or a bid/ask quote")
        return self


class OptionDomainMetrics(BaseModel):
    model_config = MODEL_CONFIG

    expiry: date
    strike_count: int = Field(ge=0)
    completeness: float = Field(ge=0, le=1)
    pcr_oi: float | None = None
    call_wall: float | None = None
    put_wall: float | None = None
    max_pain: float | None = None
    iv_status: str
    greeks_status: str
    gex_proxy_status: Literal["POSTPONED_GEX_PROXY"] = "POSTPONED_GEX_PROXY"


class OptionDomainAssessment(BaseModel):
    model_config = MODEL_CONFIG

    underlying: InstrumentIdentity
    state: SelectionState
    source_id: str
    snapshot_at: datetime
    expiry: date
    metrics: OptionDomainMetrics | None = None
    gate_results: tuple[SelectionGateResult, ...]
    null_reasons: tuple[str, ...]
    can_support_confirmed: bool = False
    evidence_role: str = "OPTIONS_CONTEXT_ONLY"

    @field_validator("snapshot_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("snapshot_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def enforce_static_context_boundary(self) -> "OptionDomainAssessment":
        if self.can_support_confirmed:
            raise ValueError("static option snapshot cannot confirm direction")
        if self.state is SelectionState.WATCH and self.metrics is None:
            raise ValueError("valid option context needs metrics")
        if self.state is SelectionState.WAIT and not self.gate_results:
            raise ValueError("option WAIT needs a named domain gate")
        return self


def _gate(code: str, reason: str, *, required: bool) -> SelectionGateResult:
    outcome = GateOutcome.WAIT if required else GateOutcome.UNKNOWN
    return SelectionGateResult(
        code=code,
        outcome=outcome,
        blocks_confirmed=required,
        reason=reason,
        required=required,
    )


def _unknown(
    *,
    underlying: InstrumentIdentity,
    source_result: SourceResult,
    snapshot_at: datetime,
    expiry: date,
    gates: list[SelectionGateResult],
    reasons: list[str],
    required: bool,
) -> OptionDomainAssessment:
    if not gates:
        gates.append(
            _gate(
                "WAIT_OPTION_CHAIN_UNKNOWN",
                "Option-chain domain could not be established.",
                required=required,
            )
        )
    return OptionDomainAssessment(
        underlying=underlying,
        state=SelectionState.WAIT,
        source_id=source_result.source_id,
        snapshot_at=snapshot_at,
        expiry=expiry,
        gate_results=tuple(gates),
        null_reasons=tuple(reasons),
    )


def evaluate_option_chain(
    *,
    underlying: InstrumentIdentity,
    source_result: SourceResult,
    snapshot_at: datetime,
    decision_at: datetime,
    expiry: date,
    spot: float,
    multiplier: float,
    expected_strike_count: int,
    raw_rows: tuple[dict[str, Any], ...],
    required: bool = True,
    expected_source_id: str = "SRC-NSE-OPTIONS",
) -> OptionDomainAssessment:
    """Validate one same-expiry snapshot before deriving context metrics."""

    if snapshot_at.tzinfo is None or snapshot_at.utcoffset() is None:
        raise ValueError("snapshot_at must be timezone-aware")
    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise ValueError("decision_at must be timezone-aware")

    gates: list[SelectionGateResult] = []
    reasons: list[str] = []
    if source_result.source_id != expected_source_id:
        reasons.append("OPTION_SOURCE_ID_MISMATCH")
        gates.append(
            _gate(
                "WAIT_OPTION_SOURCE_IDENTITY",
                "Option payload came from a different source contract.",
                required=required,
            )
        )
    if (
        source_result.state is not SourceResultState.STRUCTURED_OK
        or source_result.freshness != "FRESH"
    ):
        reasons.append("SOURCE_NOT_STRUCTURED_FRESH")
        gates.append(
            _gate(
                "WAIT_OPTION_SOURCE_STATE",
                "Option source is missing, failed, stale or not structured.",
                required=required,
            )
        )
    if not source_result.is_available_at(decision_at) or snapshot_at > decision_at:
        reasons.append("SNAPSHOT_NOT_AVAILABLE_AT_DECISION")
        gates.append(
            _gate(
                "WAIT_OPTION_PIT",
                "Option snapshot was not available at the decision time.",
                required=required,
            )
        )
    if expiry <= decision_at.date():
        reasons.append("EXPIRY_NOT_POSITIVE")
        gates.append(
            _gate(
                "WAIT_OPTION_EXPIRED",
                "Option time-to-expiry is zero or negative.",
                required=required,
            )
        )
    if not isfinite(spot) or spot <= 0 or not isfinite(multiplier) or multiplier <= 0:
        reasons.append("INVALID_SPOT_OR_MULTIPLIER")
        gates.append(
            _gate(
                "WAIT_OPTION_MODEL_DOMAIN",
                "Spot and multiplier must be finite and positive.",
                required=required,
            )
        )
    if expected_strike_count <= 0:
        reasons.append("EXPECTED_STRIKE_COUNT_UNKNOWN")
        gates.append(
            _gate(
                "WAIT_OPTION_COMPLETENESS_CONTRACT",
                "Expected strike count must be declared.",
                required=required,
            )
        )

    rows: list[OptionQuote] = []
    quote_keys: set[tuple[date, float, OptionType]] = set()
    for index, raw in enumerate(raw_rows):
        try:
            row = OptionQuote.model_validate(raw)
        except ValidationError as exc:
            reasons.append(f"INVALID_ROW_{index}:{exc.errors()[0]['type']}")
            gates.append(
                _gate(
                    "WAIT_OPTION_QUOTE_DOMAIN",
                    "An option quote is negative, non-finite, crossed or malformed.",
                    required=required,
                )
            )
            continue
        if row.expiry != expiry:
            reasons.append(f"MIXED_EXPIRY_ROW_{index}")
            gates.append(
                _gate(
                    "WAIT_OPTION_MIXED_EXPIRY",
                    "All option rows must belong to the selected expiry.",
                    required=required,
                )
            )
        quote_key = (row.expiry, row.strike, row.option_type)
        if quote_key in quote_keys:
            reasons.append(f"DUPLICATE_OPTION_ROW_{index}")
            gates.append(
                _gate(
                    "WAIT_OPTION_DUPLICATE_CONTRACT",
                    "The option snapshot contains a duplicate expiry/strike/side row.",
                    required=required,
                )
            )
        quote_keys.add(quote_key)
        rows.append(row)

    strikes = {row.strike for row in rows}
    strike_sides = {
        strike: {row.option_type for row in rows if row.strike == strike}
        for strike in strikes
    }
    complete_strikes = {
        strike
        for strike, sides in strike_sides.items()
        if sides == {OptionType.CE, OptionType.PE}
    }
    completeness = (
        min(len(complete_strikes) / expected_strike_count, 1.0)
        if expected_strike_count > 0
        else 0.0
    )
    if len(complete_strikes) != expected_strike_count:
        reasons.append("INCOMPLETE_STRIKE_SET")
        gates.append(
            _gate(
                "WAIT_OPTION_CHAIN_INCOMPLETE",
                "Option strike set is incomplete for the selected expiry.",
                required=required,
            )
        )

    ce_oi = sum(row.open_interest for row in rows if row.option_type is OptionType.CE)
    pe_oi = sum(row.open_interest for row in rows if row.option_type is OptionType.PE)
    if ce_oi <= 0:
        reasons.append("CE_OI_DENOMINATOR_ZERO")
        gates.append(
            _gate(
                "WAIT_OPTION_CE_OI_ZERO",
                "PCR denominator is zero; PCR remains unknown.",
                required=required,
            )
        )

    if gates:
        return _unknown(
            underlying=underlying,
            source_result=source_result,
            snapshot_at=snapshot_at,
            expiry=expiry,
            gates=gates,
            reasons=reasons,
            required=required,
        )

    call_wall = max(
        (row for row in rows if row.option_type is OptionType.CE),
        key=lambda row: (row.open_interest, -row.strike),
    ).strike
    put_wall = max(
        (row for row in rows if row.option_type is OptionType.PE),
        key=lambda row: (row.open_interest, row.strike),
    ).strike

    def pain(settlement: float) -> float:
        return multiplier * sum(
            (
                max(settlement - row.strike, 0)
                if row.option_type is OptionType.CE
                else max(row.strike - settlement, 0)
            )
            * row.open_interest
            for row in rows
        )

    max_pain = min(sorted(strikes), key=lambda strike: (pain(strike), strike))
    metrics = OptionDomainMetrics(
        expiry=expiry,
        strike_count=len(complete_strikes),
        completeness=completeness,
        pcr_oi=pe_oi / ce_oi,
        call_wall=call_wall,
        put_wall=put_wall,
        max_pain=max_pain,
        iv_status=(
            "SOURCE_IV_PRESENT"
            if all(row.implied_volatility is not None for row in rows)
            else "UNKNOWN_MISSING_IV"
        ),
        greeks_status="UNKNOWN_MODEL_INPUTS_NOT_SUPPLIED",
    )
    return OptionDomainAssessment(
        underlying=underlying,
        state=SelectionState.WATCH,
        source_id=source_result.source_id,
        snapshot_at=snapshot_at,
        expiry=expiry,
        metrics=metrics,
        gate_results=(),
        null_reasons=(),
    )
