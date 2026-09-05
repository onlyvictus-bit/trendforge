"""Immutable NSE cash-EOD R16 hypotheses and conservative path labels."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, time
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .contracts import stable_id

SCHEMA_VERSION = "trendforge.r16-pit.v1"
PROFILE_ID = "PRF-R16-NSE-CASH-EOD-SWING"
PROFILE_VERSION = "1.0.0"
INSTRUMENT_CLASS = "EQUITY"
TIMEFRAME = "EOD"
SETUP_POLICY_ID = "SWING_BREAKOUT_BREAKDOWN_V1"
GEOMETRY_POLICY_VERSION = "R16_GEOMETRY_V1"
TARGET_POLICY_VERSION = "R16_1R_2R_V1"
AVAILABILITY_POLICY_VERSION = "NSE_EOD_DERIVED_1800_IST_V1"
LABEL_POLICY_VERSION = "R16_NEXT_SESSION_TRIGGER_FILL_V1"
GAP_POLICY_VERSION = "R16_NO_CHASE_GAP_V1"
COLLISION_POLICY = "STOP_FIRST_CONSERVATIVE"
COST_POLICY_VERSION = "R16_NSE_CASH_COST_V1"
HORIZONS = (5, 10, 20)
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

Direction = Literal["BULLISH", "BEARISH", "NEUTRAL"]
GeometryStatus = Literal["READY", "NO_GEOMETRY"]
ObservationStatus = Literal[
    "TARGET", "STOP", "NO_HIT", "NO_ENTRY", "NO_GEOMETRY", "CENSORED",
    "NO_FORWARD_SESSION", "DATA_GAP", "DELISTED",
    "CORPORATE_ACTION_UNRESOLVED", "INVALIDATED_BEFORE_ENTRY",
]


class R16CostPolicyV1(BaseModel):
    model_config = MODEL_CONFIG

    policy_version: str = COST_POLICY_VERSION
    entry_cost_bps: float = Field(default=10.0, ge=0)
    exit_cost_bps: float = Field(default=10.0, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)
    stressed_round_trip_bps: float = Field(default=60.0, ge=0)
    research_assumption_only: bool = True

    @property
    def round_trip_bps(self) -> float:
        return self.entry_cost_bps + self.exit_cost_bps + 2 * self.slippage_bps


DEFAULT_COST_POLICY = R16CostPolicyV1()


class R16FrozenHypothesisV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    hypothesis_id: str
    dataset_revision_hash: str
    source_s8_run_id: str
    source_s8_hash: str
    source_s8_lineage_hash: str
    candidate_id: str
    symbol: str
    instrument_class: str = INSTRUMENT_CLASS
    market: str = "NSE_CASH"
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    timeframe: str = TIMEFRAME
    trading_date: str
    decision_cutoff_at: datetime
    max_input_available_at: datetime | None = None
    direction: Direction
    horizon_sessions: int = Field(gt=0)
    public_state: Literal["WATCH", "WAIT", "REJECT"]
    geometry_status: GeometryStatus
    setup_policy_id: str = SETUP_POLICY_ID
    geometry_policy_version: str = GEOMETRY_POLICY_VERSION
    target_policy_version: str = TARGET_POLICY_VERSION
    availability_policy_version: str = AVAILABILITY_POLICY_VERSION
    label_policy_version: str = LABEL_POLICY_VERSION
    gap_policy_version: str = GAP_POLICY_VERSION
    cost_model_version: str | None = None
    costs_declared: bool = False
    entry_cost_bps: float | None = None
    exit_cost_bps: float | None = None
    slippage_bps: float | None = None
    stressed_round_trip_bps: float | None = None
    trigger_price: float | None = None
    entry_low: float | None = None
    entry_high: float | None = None
    invalidation: float | None = None
    target_1: float | None = None
    target_2: float | None = None
    atr14: float | None = None
    structural_risk: float | None = None
    source_bar_hashes: tuple[str, ...] = ()
    source_feature_hashes: dict[str, str] = {}
    exclusion_reason: str | None = None
    confirmation_authorized: bool = False
    execution_authorized: bool = False

    @model_validator(mode="after")
    def validate_law(self) -> "R16FrozenHypothesisV1":
        if self.confirmation_authorized or self.execution_authorized:
            raise ValueError("R16 hypotheses cannot authorize confirmation or execution")
        if self.market != "NSE_CASH" or self.instrument_class != INSTRUMENT_CLASS:
            raise ValueError("R16 v1 supports NSE cash equity only")
        if self.timeframe != TIMEFRAME or self.horizon_sessions not in HORIZONS:
            raise ValueError("R16 v1 supports EOD 5/10/20-session cells only")
        levels = (
            self.trigger_price, self.entry_low, self.entry_high,
            self.invalidation, self.target_1, self.target_2,
        )
        if self.geometry_status == "READY" and any(value is None for value in levels):
            raise ValueError("READY geometry requires trigger, entry, invalidation and targets")
        if self.geometry_status == "NO_GEOMETRY" and any(value is not None for value in levels):
            raise ValueError("NO_GEOMETRY cannot zero-fill or retain levels")
        if self.geometry_status == "READY" and not self.source_bar_hashes:
            raise ValueError("READY geometry requires immutable source-bar hashes")
        if self.decision_cutoff_at.tzinfo is None:
            raise ValueError("decision_cutoff_at must be timezone-aware")
        if self.max_input_available_at and self.max_input_available_at > self.decision_cutoff_at:
            raise ValueError("decision input availability exceeds cutoff")
        if self.costs_declared and not self.cost_model_version:
            raise ValueError("declared costs require a version")
        return self


class R16ObservationV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    observation_id: str
    hypothesis_id: str
    dataset_revision_hash: str
    source_s8_run_id: str
    symbol: str
    direction: Direction
    horizon_sessions: int = Field(gt=0)
    status: ObservationStatus
    label_computed_at: datetime
    path_hash: str
    entry_price: float | None = None
    entry_at: datetime | None = None
    exit_price: float | None = None
    outcome_at: datetime | None = None
    fill_assumption: str | None = None
    exit_assumption: str | None = None
    mfe_percent: float | None = None
    mae_percent: float | None = None
    mfe_r: float | None = None
    mae_r: float | None = None
    gross_r: float | None = None
    net_r: float | None = None
    stressed_net_r: float | None = None
    bars_to_entry: int | None = None
    bars_to_event: int | None = None
    bars_observed: int = Field(ge=0, default=0)
    intrabar_ambiguous: bool = False
    collision_policy: str = COLLISION_POLICY
    gap_policy_version: str = GAP_POLICY_VERSION
    target_2_hit: bool = False
    outcome_bar_hashes: tuple[str, ...] = ()
    censor_reason: str | None = None
    costs_declared: bool = False
    cost_model_version: str | None = None
    confirmation_authorized: bool = False
    execution_authorized: bool = False

    @model_validator(mode="after")
    def validate_law(self) -> "R16ObservationV1":
        if self.confirmation_authorized or self.execution_authorized:
            raise ValueError("R16 observations cannot authorize confirmation or execution")
        if self.status in {"TARGET", "STOP", "NO_HIT"} and self.entry_price is None:
            raise ValueError("entered observations require an entry")
        if self.label_computed_at.tzinfo is None:
            raise ValueError("label_computed_at must be timezone-aware")
        return self


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else None
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def _number(row: dict[str, Any], key: str) -> float | None:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError):
        return None
    return value if value == value else None


def _payload_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _bar_available_at(row: dict[str, Any]) -> datetime | None:
    direct = _parse_datetime(row.get("available_at") or row.get("availableAt"))
    if direct is not None:
        return direct.astimezone(UTC)
    day = _parse_date(row.get("trade_date") or row.get("tradeDate"))
    if day is None:
        return None
    return datetime.combine(day, time(18, 0), ZoneInfo("Asia/Kolkata")).astimezone(UTC)


def _bar_hash(row: dict[str, Any]) -> str | None:
    direct = row.get("artifact_hash") or row.get("artifactHash")
    return str(direct) if direct else None


def _visible_bars(
    bars: list[dict[str, Any]], *, trading_date: date, cutoff_at: datetime
) -> list[dict[str, Any]]:
    visible: list[dict[str, Any]] = []
    for raw in bars:
        day = _parse_date(raw.get("trade_date") or raw.get("tradeDate"))
        available = _bar_available_at(raw)
        if day is None or day >= trading_date or available is None:
            continue
        if available > cutoff_at.astimezone(UTC):
            continue
        if all(_number(raw, key) is not None for key in ("open", "high", "low", "close")):
            visible.append(raw)
    return sorted(
        visible,
        key=lambda row: str(row.get("trade_date") or row.get("tradeDate")),
    )


def _atr14(bars: list[dict[str, Any]]) -> float | None:
    if len(bars) < 15:
        return None
    values: list[float] = []
    for prior, current in zip(bars[-15:-1], bars[-14:]):
        high = _number(current, "high")
        low = _number(current, "low")
        previous_close = _number(prior, "close")
        if high is None or low is None or previous_close is None:
            return None
        values.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    return sum(values) / len(values) if values else None


def _latest_pivot(bars: list[dict[str, Any]], *, direction: Direction) -> float | None:
    if len(bars) < 3 or direction == "NEUTRAL":
        return None
    key = "low" if direction == "BULLISH" else "high"
    for index in range(len(bars) - 2, 0, -1):
        previous = _number(bars[index - 1], key)
        current = _number(bars[index], key)
        following = _number(bars[index + 1], key)
        if previous is None or current is None or following is None:
            continue
        if direction == "BULLISH" and current < previous and current <= following:
            return current
        if direction == "BEARISH" and current > previous and current >= following:
            return current
    return None


def _s8_contract(s8_payload: dict[str, Any]) -> tuple[str, date, datetime, str, str]:
    run_id = str(s8_payload.get("runId") or s8_payload.get("run_id") or "")
    trading_day = _parse_date(
        s8_payload.get("tradingDate") or s8_payload.get("trading_date")
    )
    cutoff = _parse_datetime(s8_payload.get("asOf") or s8_payload.get("as_of"))
    if not run_id or trading_day is None or cutoff is None:
        raise ValueError("WAIT_R16_S8_IDENTITY_INCOMPLETE")
    lineage = s8_payload.get("lineage") or {}
    missing = set(lineage.get("missingStages") or lineage.get("missing_stages") or ())
    required = {
        "r1RunHash", "r2RunHash", "r14RunHash", "r5RunHash", "s2RunId",
        "s3RunId", "s4PackId", "s5RunId", "s6RunId", "s7RunId",
        "nativeGuidanceRunHash",
    }
    absent = {key for key in required if not lineage.get(key)}
    if missing or absent:
        raise ValueError(
            "WAIT_R16_S8_LINEAGE_INCOMPLETE:" + ",".join(sorted(missing | absent))
        )
    completeness = s8_payload.get("s3Completeness") or s8_payload.get("completeness") or {}
    ratio = completeness.get("ratio")
    threshold = completeness.get("threshold", 0.95)
    if ratio is None or float(ratio) < float(threshold):
        raise ValueError("WAIT_R16_S3_COMPLETENESS")
    return run_id, trading_day, cutoff, _payload_hash(s8_payload), _payload_hash(lineage)


def validate_s8_contract(s8_payload: dict[str, Any]) -> None:
    """Validate identity, lineage and completeness before date conflict checks."""

    _s8_contract(s8_payload)

def build_frozen_hypotheses(
    *,
    s8_payload: dict[str, Any],
    bars_by_symbol: dict[str, list[dict[str, Any]]],
    dataset_revision_hash: str | None = None,
    cost_policy: R16CostPolicyV1 | None = DEFAULT_COST_POLICY,
) -> tuple[R16FrozenHypothesisV1, ...]:
    """Freeze exact-cell hypotheses from cutoff-visible facts only."""

    run_id, trading_day, cutoff, s8_hash, lineage_hash = _s8_contract(s8_payload)
    revision_hash = dataset_revision_hash or _payload_hash(
        {
            "s8": s8_hash,
            "profile": PROFILE_VERSION,
            "geometry": GEOMETRY_POLICY_VERSION,
            "label": LABEL_POLICY_VERSION,
            "cost": cost_policy.policy_version if cost_policy else None,
        }
    )
    lineage = s8_payload.get("lineage") or {}
    feature_hashes = {
        str(key): str(value)
        for key, value in lineage.items()
        if isinstance(value, str) and value
    }

    output: list[R16FrozenHypothesisV1] = []
    for row in s8_payload.get("rows") or []:
        symbol = str(row.get("symbol") or "").upper()
        if not symbol:
            continue
        state = str(row.get("publicState") or row.get("public_state") or "WAIT").upper()
        direction_text = str(
            row.get("evidenceDirection") or row.get("evidence_direction") or "NEUTRAL"
        ).upper()
        if "BEAR" in direction_text:
            direction: Direction = "BEARISH"
        elif "BULL" in direction_text:
            direction = "BULLISH"
        else:
            direction = "NEUTRAL"
        bars = _visible_bars(
            bars_by_symbol.get(symbol, []),
            trading_date=trading_day,
            cutoff_at=cutoff,
        )
        levels: dict[str, Any] = {
            "geometry_status": "NO_GEOMETRY",
            "exclusion_reason": "WAIT_INSUFFICIENT_VISIBLE_BARS",
        }
        if state == "REJECT":
            levels["exclusion_reason"] = "S8_REJECT"
        elif direction == "NEUTRAL":
            levels["exclusion_reason"] = "WAIT_DIRECTION_UNKNOWN"
        elif len(bars) >= 20:
            window = bars[-20:]
            hashes = [_bar_hash(item) for item in window]
            atr = _atr14(bars)
            pivot = _latest_pivot(window, direction=direction)
            highs = [_number(item, "high") for item in window]
            lows = [_number(item, "low") for item in window]
            if any(value is None for value in hashes):
                levels["exclusion_reason"] = "WAIT_RAW_LINEAGE_MISSING"
            elif atr is None or atr <= 0:
                levels["exclusion_reason"] = "WAIT_ATR14_UNAVAILABLE"
            elif pivot is None:
                levels["exclusion_reason"] = "WAIT_STRUCTURAL_PIVOT_UNAVAILABLE"
            elif any(value is None for value in (*highs, *lows)):
                levels["exclusion_reason"] = "WAIT_INVALID_VISIBLE_BAR"
            else:
                trigger = max(highs) if direction == "BULLISH" else min(lows)
                risk = trigger - pivot if direction == "BULLISH" else pivot - trigger
                if risk <= 0 or risk > atr:
                    levels["exclusion_reason"] = "WAIT_STRUCTURE_EXCEEDS_ATR_RISK_CEILING"
                else:
                    levels = {
                        "geometry_status": "READY",
                        "trigger_price": trigger,
                        "entry_low": (
                            trigger if direction == "BULLISH" else trigger - 0.15 * atr
                        ),
                        "entry_high": (
                            trigger + 0.15 * atr if direction == "BULLISH" else trigger
                        ),
                        "invalidation": pivot,
                        "target_1": (
                            trigger + risk if direction == "BULLISH" else trigger - risk
                        ),
                        "target_2": (
                            trigger + 2 * risk if direction == "BULLISH" else trigger - 2 * risk
                        ),
                        "atr14": atr,
                        "structural_risk": risk,
                        "exclusion_reason": None,
                    }
        selected = bars[-20:]
        source_hashes = tuple(filter(None, (_bar_hash(item) for item in selected)))
        max_available = max(
            (_bar_available_at(item) for item in selected), default=None
        )
        candidate_id = str(row.get("candidateId") or row.get("candidate_id") or symbol)
        for horizon in HORIZONS:
            identity = stable_id(
                "r16hyp", revision_hash, run_id, candidate_id, symbol, direction,
                str(horizon), SETUP_POLICY_ID, LABEL_POLICY_VERSION,
                cost_policy.policy_version if cost_policy else "NO_COST_POLICY",
                lineage_hash,
            )
            cost_fields: dict[str, Any] = {}
            if cost_policy is not None:
                cost_fields = {
                    "costs_declared": True,
                    "cost_model_version": cost_policy.policy_version,
                    "entry_cost_bps": cost_policy.entry_cost_bps,
                    "exit_cost_bps": cost_policy.exit_cost_bps,
                    "slippage_bps": cost_policy.slippage_bps,
                    "stressed_round_trip_bps": cost_policy.stressed_round_trip_bps,
                }
            output.append(
                R16FrozenHypothesisV1(
                    hypothesis_id=identity,
                    dataset_revision_hash=revision_hash,
                    source_s8_run_id=run_id,
                    source_s8_hash=s8_hash,
                    source_s8_lineage_hash=lineage_hash,
                    candidate_id=candidate_id,
                    symbol=symbol,
                    trading_date=trading_day.isoformat(),
                    decision_cutoff_at=cutoff,
                    max_input_available_at=max_available,
                    direction=direction,
                    horizon_sessions=horizon,
                    public_state=(
                        state if state in {"WATCH", "WAIT", "REJECT"} else "WAIT"
                    ),
                    source_bar_hashes=source_hashes,
                    source_feature_hashes=feature_hashes,
                    **cost_fields,
                    **levels,
                )
            )
    return tuple(output)


def _observation(
    hypothesis: R16FrozenHypothesisV1,
    *,
    status: ObservationStatus,
    label_computed_at: datetime,
    path_hash: str,
    outcome_hashes: tuple[str, ...],
    **fields: Any,
) -> R16ObservationV1:
    observation_id = stable_id(
        "r16obs", hypothesis.hypothesis_id, path_hash, status,
        label_computed_at.isoformat(),
    )
    return R16ObservationV1(
        observation_id=observation_id,
        hypothesis_id=hypothesis.hypothesis_id,
        dataset_revision_hash=hypothesis.dataset_revision_hash,
        source_s8_run_id=hypothesis.source_s8_run_id,
        symbol=hypothesis.symbol,
        direction=hypothesis.direction,
        horizon_sessions=hypothesis.horizon_sessions,
        status=status,
        label_computed_at=label_computed_at,
        path_hash=path_hash,
        outcome_bar_hashes=outcome_hashes,
        costs_declared=hypothesis.costs_declared,
        cost_model_version=hypothesis.cost_model_version,
        **fields,
    )


def _risk_metrics(
    hypothesis: R16FrozenHypothesisV1,
    *,
    entry: float,
    exit_price: float,
    best: float,
    worst: float,
) -> dict[str, float | None]:
    risk = abs(entry - float(hypothesis.invalidation))
    if risk <= 0:
        return {
            "mfe_percent": None, "mae_percent": None, "mfe_r": None,
            "mae_r": None, "gross_r": None, "net_r": None,
            "stressed_net_r": None,
        }
    signed_pnl = (
        exit_price - entry if hypothesis.direction == "BULLISH" else entry - exit_price
    )
    gross_r = signed_pnl / risk
    normal_bps = None
    if hypothesis.costs_declared:
        normal_bps = (
            float(hypothesis.entry_cost_bps or 0)
            + float(hypothesis.exit_cost_bps or 0)
            + 2 * float(hypothesis.slippage_bps or 0)
        )
    normal_cost_r = entry * normal_bps / 10000 / risk if normal_bps is not None else None
    stressed_cost_r = (
        entry * float(hypothesis.stressed_round_trip_bps) / 10000 / risk
        if hypothesis.stressed_round_trip_bps is not None else None
    )
    return {
        "mfe_percent": round(best / entry * 100, 6),
        "mae_percent": round(worst / entry * 100, 6),
        "mfe_r": round(best / risk, 6),
        "mae_r": round(worst / risk, 6),
        "gross_r": round(gross_r, 6),
        "net_r": round(gross_r - normal_cost_r, 6) if normal_cost_r is not None else None,
        "stressed_net_r": (
            round(gross_r - stressed_cost_r, 6)
            if stressed_cost_r is not None else None
        ),
    }
def label_hypothesis(
    hypothesis: R16FrozenHypothesisV1,
    *,
    bars: list[dict[str, Any]],
    label_computed_at: datetime | None = None,
) -> R16ObservationV1:
    """Append-only label snapshot using later, available, closed EOD sessions."""

    candidates: list[tuple[dict[str, Any], date, datetime]] = []
    malformed_after_cutoff = False
    hypothesis_day = date.fromisoformat(hypothesis.trading_date)
    for row in bars:
        day = _parse_date(row.get("trade_date") or row.get("tradeDate"))
        available = _bar_available_at(row)
        if day is None or day <= hypothesis_day or available is None:
            continue
        if any(_number(row, key) is None for key in ("open", "high", "low", "close")):
            malformed_after_cutoff = True
            continue
        candidates.append((row, day, available))
    candidates.sort(key=lambda item: (item[1], item[2]))
    computed_at = label_computed_at
    if computed_at is None:
        computed_at = max(
            (available for _, _, available in candidates),
            default=hypothesis.decision_cutoff_at,
        )
    if computed_at.tzinfo is None:
        raise ValueError("label_computed_at must be timezone-aware")
    later = [item for item in candidates if item[2] <= computed_at.astimezone(UTC)]
    later = later[: hypothesis.horizon_sessions]
    hashes = tuple(filter(None, (_bar_hash(row) for row, _, _ in later)))
    path_hash = _payload_hash(
        {
            "hypothesis": hypothesis.hypothesis_id,
            "bars": [
                {
                    "date": day.isoformat(),
                    "availableAt": available.isoformat(),
                    "hash": _bar_hash(row),
                    "ohlc": [
                        _number(row, key) for key in ("open", "high", "low", "close")
                    ],
                }
                for row, day, available in later
            ],
            "labelPolicy": hypothesis.label_policy_version,
            "gapPolicy": hypothesis.gap_policy_version,
        }
    )
    if hypothesis.geometry_status != "READY":
        return _observation(
            hypothesis,
            status="NO_GEOMETRY",
            label_computed_at=computed_at,
            path_hash=path_hash,
            outcome_hashes=hashes,
            censor_reason=hypothesis.exclusion_reason,
        )
    if not later:
        status: ObservationStatus = (
            "DATA_GAP" if malformed_after_cutoff else "NO_FORWARD_SESSION"
        )
        return _observation(
            hypothesis,
            status=status,
            label_computed_at=computed_at,
            path_hash=path_hash,
            outcome_hashes=hashes,
            censor_reason=(
                "MALFORMED_LATER_BAR" if malformed_after_cutoff
                else "NO_LATER_AVAILABLE_BAR"
            ),
        )

    bullish = hypothesis.direction == "BULLISH"
    entry_price: float | None = None
    entry_at: datetime | None = None
    bars_to_entry: int | None = None
    best = 0.0
    worst = 0.0
    target_2_hit = False
    last_close: float | None = None
    for index, (row, _, available) in enumerate(later, start=1):
        high_value = _number(row, "high")
        low_value = _number(row, "low")
        open_value = _number(row, "open")
        close_value = _number(row, "close")
        if None in (high_value, low_value, open_value, close_value):
            return _observation(
                hypothesis,
                status="DATA_GAP",
                label_computed_at=computed_at,
                path_hash=path_hash,
                outcome_hashes=hashes,
                outcome_at=available,
                bars_observed=index,
                censor_reason="MALFORMED_LATER_BAR",
            )
        high = float(high_value)
        low = float(low_value)
        open_ = float(open_value)
        close = float(close_value)
        last_close = close
        if bool(
            row.get("corporate_action_unresolved")
            or row.get("corporateActionUnresolved")
        ):
            return _observation(
                hypothesis,
                status="CORPORATE_ACTION_UNRESOLVED",
                label_computed_at=computed_at,
                path_hash=path_hash,
                outcome_hashes=hashes,
                outcome_at=available,
                bars_observed=index,
                censor_reason="UNRESOLVED_CORPORATE_ACTION",
            )
        if bool(row.get("delisted")):
            return _observation(
                hypothesis,
                status="DELISTED",
                label_computed_at=computed_at,
                path_hash=path_hash,
                outcome_hashes=hashes,
                outcome_at=available,
                bars_observed=index,
                censor_reason="SECURITY_DELISTED",
            )
        if entry_price is None:
            open_invalid = (
                open_ <= float(hypothesis.invalidation)
                if bullish else open_ >= float(hypothesis.invalidation)
            )
            bar_invalid = (
                low <= float(hypothesis.invalidation)
                if bullish else high >= float(hypothesis.invalidation)
            )
            touches_entry = (
                high >= float(hypothesis.entry_low)
                and low <= float(hypothesis.entry_high)
            )
            if open_invalid or (bar_invalid and not touches_entry):
                return _observation(
                    hypothesis,
                    status="INVALIDATED_BEFORE_ENTRY",
                    label_computed_at=computed_at,
                    path_hash=path_hash,
                    outcome_hashes=hashes,
                    outcome_at=available,
                    bars_observed=index,
                    censor_reason="INVALIDATION_BEFORE_ENTRY",
                )
            gap_beyond = (
                open_ > float(hypothesis.entry_high)
                if bullish else open_ < float(hypothesis.entry_low)
            )
            if gap_beyond:
                return _observation(
                    hypothesis,
                    status="NO_ENTRY",
                    label_computed_at=computed_at,
                    path_hash=path_hash,
                    outcome_hashes=hashes,
                    outcome_at=available,
                    bars_observed=index,
                    censor_reason="GAP_BEYOND_ENTRY_ZONE_NO_CHASE",
                )
            if float(hypothesis.entry_low) <= open_ <= float(hypothesis.entry_high):
                entry_price = open_
                fill_assumption = "NEXT_SESSION_OPEN_INSIDE_ENTRY_ZONE"
            elif touches_entry:
                entry_price = (
                    float(hypothesis.entry_low)
                    if bullish else float(hypothesis.entry_high)
                )
                fill_assumption = "INTRABAR_TRIGGER_FILL"
            else:
                continue
            entry_at = available
            bars_to_entry = index
        else:
            fill_assumption = "PRIOR_SESSION_ENTRY"

        favorable = high - entry_price if bullish else entry_price - low
        adverse = entry_price - low if bullish else high - entry_price
        best = max(best, favorable)
        worst = max(worst, adverse)
        stop_hit = (
            low <= float(hypothesis.invalidation)
            if bullish else high >= float(hypothesis.invalidation)
        )
        target_hit = (
            high >= float(hypothesis.target_1)
            if bullish else low <= float(hypothesis.target_1)
        )
        target_2_hit = target_2_hit or (
            high >= float(hypothesis.target_2)
            if bullish else low <= float(hypothesis.target_2)
        )
        if stop_hit or target_hit:
            ambiguous = stop_hit and target_hit
            status: ObservationStatus = "STOP" if stop_hit else "TARGET"
            if stop_hit:
                gap_stop = (
                    open_ < float(hypothesis.invalidation)
                    if bullish else open_ > float(hypothesis.invalidation)
                )
                exit_price = open_ if gap_stop else float(hypothesis.invalidation)
                exit_assumption = (
                    "GAP_STOP_AT_OPEN" if gap_stop else "STOP_LEVEL_FILL"
                )
            else:
                exit_price = float(hypothesis.target_1)
                exit_assumption = "TARGET_LEVEL_FILL"
            return _observation(
                hypothesis,
                status=status,
                label_computed_at=computed_at,
                path_hash=path_hash,
                outcome_hashes=hashes,
                entry_price=entry_price,
                entry_at=entry_at,
                exit_price=exit_price,
                outcome_at=available,
                fill_assumption=fill_assumption,
                exit_assumption=exit_assumption,
                bars_to_entry=bars_to_entry,
                bars_to_event=index,
                bars_observed=index,
                intrabar_ambiguous=ambiguous,
                target_2_hit=target_2_hit,
                **_risk_metrics(
                    hypothesis,
                    entry=entry_price,
                    exit_price=exit_price,
                    best=best,
                    worst=worst,
                ),
            )

    if entry_price is None:
        status = (
            "NO_ENTRY" if len(later) >= hypothesis.horizon_sessions else "CENSORED"
        )
        return _observation(
            hypothesis,
            status=status,
            label_computed_at=computed_at,
            path_hash=path_hash,
            outcome_hashes=hashes,
            bars_observed=len(later),
            censor_reason=(
                "ENTRY_ZONE_NOT_TOUCHED"
                if status == "NO_ENTRY" else "HORIZON_NOT_COMPLETE"
            ),
        )
    if len(later) < hypothesis.horizon_sessions:
        return _observation(
            hypothesis,
            status="CENSORED",
            label_computed_at=computed_at,
            path_hash=path_hash,
            outcome_hashes=hashes,
            entry_price=entry_price,
            entry_at=entry_at,
            bars_to_entry=bars_to_entry,
            bars_observed=len(later),
            target_2_hit=target_2_hit,
            censor_reason="HORIZON_NOT_COMPLETE",
        )
    return _observation(
        hypothesis,
        status="NO_HIT",
        label_computed_at=computed_at,
        path_hash=path_hash,
        outcome_hashes=hashes,
        entry_price=entry_price,
        entry_at=entry_at,
        exit_price=last_close,
        outcome_at=later[-1][2],
        fill_assumption="TRIGGER_FILL",
        exit_assumption="HORIZON_CLOSE_MARK",
        bars_to_entry=bars_to_entry,
        bars_to_event=len(later),
        bars_observed=len(later),
        target_2_hit=target_2_hit,
        **_risk_metrics(
            hypothesis,
            entry=entry_price,
            exit_price=float(last_close),
            best=best,
            worst=worst,
        ),
    )


__all__ = [
    "COST_POLICY_VERSION",
    "DEFAULT_COST_POLICY",
    "HORIZONS",
    "LABEL_POLICY_VERSION",
    "PROFILE_ID",
    "PROFILE_VERSION",
    "R16CostPolicyV1",
    "R16FrozenHypothesisV1",
    "R16ObservationV1",
    "build_frozen_hypotheses",
    "label_hypothesis",
    "validate_s8_contract",
]
