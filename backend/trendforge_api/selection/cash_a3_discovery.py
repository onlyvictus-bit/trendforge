"""A3 cash-EOD discovery (File A §25.25.4).

WATCH queue reasons only. No FTR-018, no EvidenceClaim, no can_rank, no CONFIRMED.
Previous close supplies return direction. PIT percentile supplies importance.
A profile match requires both.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .. import storage
from .cash_a2_identity import CashIdentityBatch, CashIdentityRow, latest_cash_identity
from .contracts import SelectionState

PROFILE_ID = "DISC_EOD_V1"
HIGH_PERCENTILE = 0.75
LOW_PERCENTILE = 0.25
PARTICIPATION_FLOOR = 0.25
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DiscoveryProfile(StrEnum):
    MOMENTUM = "DISC_EOD_MOMENTUM"
    RECOVERY = "DISC_EOD_RECOVERY"
    RANGE = "DISC_EOD_RANGE"
    LIQUIDITY = "DISC_EOD_LIQUIDITY"
    NARROW_SESSION = "DISC_EOD_NARROW_SESSION"


class SessionDirection(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"
    UNKNOWN = "UNKNOWN"


class CashDiscoveryMetrics(BaseModel):
    model_config = MODEL_CONFIG

    session_return: float | None = None
    range_pct: float | None = None
    close_location: float | None = None
    recovery_from_low: float | None = None
    session_direction: SessionDirection = SessionDirection.UNKNOWN
    return_percentile: float | None = None
    range_percentile: float | None = None
    close_location_percentile: float | None = None
    recovery_percentile: float | None = None
    volume_percentile: float | None = None
    turnover_percentile: float | None = None


class CashDiscoveryRow(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    instrument_id: str
    fact_id: str
    public_state: SelectionState
    discovery_profiles: tuple[DiscoveryProfile, ...] = ()
    discovery_reason: str
    metrics: CashDiscoveryMetrics
    eligible: bool
    banned: bool = False


class CashDiscoveryBatch(BaseModel):
    model_config = MODEL_CONFIG

    milestone: str = "A3"
    acceptance_ceiling: str = "WATCH_DISCOVERY_ONLY"
    profile_id: str = PROFILE_ID
    batch_id: str
    identity_batch_id: str | None
    can_rank: bool = False
    can_unlock_confirmed: bool = False
    eligible_count: int = Field(ge=0)
    watch_count: int = Field(ge=0)
    rows: tuple[CashDiscoveryRow, ...] = ()
    persisted: bool = False


def _f(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _percentile(values: list[float], value: float) -> float:
    if not values:
        return 0.0
    below = sum(1 for item in values if item < value)
    equal = sum(1 for item in values if item == value)
    return (below + 0.5 * equal) / len(values)


def _session_metrics(row: CashIdentityRow) -> CashDiscoveryMetrics | None:
    payload = row.fact.payload
    close = _f(payload.get("close"))
    previous = _f(payload.get("previousClose"))
    high = _f(payload.get("high"))
    low = _f(payload.get("low"))
    if close is None or previous is None or previous <= 0 or close <= 0:
        return None
    session_return = (close - previous) / previous
    if session_return > 0:
        direction = SessionDirection.UP
    elif session_return < 0:
        direction = SessionDirection.DOWN
    else:
        direction = SessionDirection.FLAT
    span = None
    close_location = None
    recovery = None
    if high is not None and low is not None and high > low:
        span = (high - low) / previous
        close_location = (close - low) / (high - low)
        recovery = close_location
    elif high is not None and low is not None:
        span = 0.0
        close_location = 0.5
        recovery = 0.5
    return CashDiscoveryMetrics(
        session_return=session_return,
        range_pct=span,
        close_location=close_location,
        recovery_from_low=recovery,
        session_direction=direction,
    )


def _eligible(row: CashIdentityRow) -> bool:
    if row.banned or row.public_state is SelectionState.REJECT:
        return False
    if row.fact.quality_state == "STALE":
        return False
    if any(gate.code == "S0_SOURCE_HEALTH" and gate.outcome.value == "WAIT" for gate in row.gates):
        return False
    return row.instrument.series == "EQ"


def _match_profiles(metrics: CashDiscoveryMetrics) -> tuple[DiscoveryProfile, ...]:
    hits: list[DiscoveryProfile] = []
    vol = metrics.volume_percentile
    turn = metrics.turnover_percentile
    participation = max(v for v in (vol, turn) if v is not None) if any(
        v is not None for v in (vol, turn)
    ) else None
    if (
        metrics.session_direction is SessionDirection.UP
        and metrics.close_location_percentile is not None
        and metrics.close_location_percentile >= HIGH_PERCENTILE
        and participation is not None
        and participation >= PARTICIPATION_FLOOR
    ):
        hits.append(DiscoveryProfile.MOMENTUM)
    if (
        metrics.session_direction in {SessionDirection.DOWN, SessionDirection.FLAT}
        and metrics.recovery_percentile is not None
        and metrics.recovery_percentile >= HIGH_PERCENTILE
        and (metrics.session_return or 0) <= 0
        and metrics.range_pct is not None
        and metrics.range_pct > 0
    ):
        hits.append(DiscoveryProfile.RECOVERY)
    if (
        metrics.range_percentile is not None
        and metrics.range_percentile >= HIGH_PERCENTILE
        and participation is not None
        and participation >= PARTICIPATION_FLOOR
    ):
        hits.append(DiscoveryProfile.RANGE)
    if turn is not None and turn >= HIGH_PERCENTILE:
        hits.append(DiscoveryProfile.LIQUIDITY)
    elif vol is not None and vol >= HIGH_PERCENTILE:
        hits.append(DiscoveryProfile.LIQUIDITY)
    if (
        metrics.range_percentile is not None
        and metrics.range_percentile <= LOW_PERCENTILE
        and participation is not None
        and participation >= PARTICIPATION_FLOOR
    ):
        hits.append(DiscoveryProfile.NARROW_SESSION)
    return tuple(hits)


def _reason(profiles: tuple[DiscoveryProfile, ...], metrics: CashDiscoveryMetrics) -> str:
    if not profiles:
        return (
            "No §25.25.4 cash-EOD profile matched. Stay WAIT. "
            "Not a trade decision."
        )
    names = ", ".join(item.value for item in profiles)
    return (
        f"{names} matched on {PROFILE_ID} "
        f"(session {metrics.session_direction.value}, "
        f"return_pct={metrics.return_percentile}, "
        f"range_pct={metrics.range_percentile}). "
        "WATCH queue reason only; not a trade."
    )


def build_cash_discovery_batch(
    identity: CashIdentityBatch | None = None,
) -> CashDiscoveryBatch:
    batch = identity if identity is not None else latest_cash_identity()
    if batch is None:
        return CashDiscoveryBatch(
            batch_id=str(uuid4()),
            identity_batch_id=None,
            eligible_count=0,
            watch_count=0,
            rows=(),
        )
    prepared: list[tuple[CashIdentityRow, CashDiscoveryMetrics | None, bool]] = []
    for row in batch.rows:
        eligible = _eligible(row)
        metrics = _session_metrics(row) if eligible else _session_metrics(row)
        prepared.append((row, metrics, eligible and metrics is not None))

    eligible_rows = [item for item in prepared if item[2] and item[1] is not None]
    returns = [item[1].session_return for item in eligible_rows if item[1].session_return is not None]
    ranges = [item[1].range_pct for item in eligible_rows if item[1].range_pct is not None]
    locations = [
        item[1].close_location for item in eligible_rows if item[1].close_location is not None
    ]
    recoveries = [
        item[1].recovery_from_low
        for item in eligible_rows
        if item[1].recovery_from_low is not None
    ]
    volumes = [
        float(item[0].fact.payload.get("volume") or 0)
        for item in eligible_rows
    ]
    turnovers = [
        float(item[0].fact.payload.get("tradedValue") or 0)
        for item in eligible_rows
    ]

    discovered: list[CashDiscoveryRow] = []
    for row, metrics, eligible in prepared:
        if metrics is None:
            discovered.append(
                CashDiscoveryRow(
                    symbol=row.instrument.symbol,
                    instrument_id=row.instrument.instrument_id,
                    fact_id=row.fact.fact_id,
                    public_state=row.public_state,
                    discovery_reason="Missing close/previousClose. Cannot discover.",
                    metrics=CashDiscoveryMetrics(),
                    eligible=False,
                    banned=row.banned,
                )
            )
            continue
        if eligible:
            metrics = metrics.model_copy(
                update={
                    "return_percentile": (
                        _percentile(returns, metrics.session_return)
                        if metrics.session_return is not None
                        else None
                    ),
                    "range_percentile": (
                        _percentile(ranges, metrics.range_pct)
                        if metrics.range_pct is not None
                        else None
                    ),
                    "close_location_percentile": (
                        _percentile(locations, metrics.close_location)
                        if metrics.close_location is not None
                        else None
                    ),
                    "recovery_percentile": (
                        _percentile(recoveries, metrics.recovery_from_low)
                        if metrics.recovery_from_low is not None
                        else None
                    ),
                    "volume_percentile": _percentile(
                        volumes, float(row.fact.payload.get("volume") or 0)
                    ),
                    "turnover_percentile": _percentile(
                        turnovers, float(row.fact.payload.get("tradedValue") or 0)
                    ),
                }
            )
            profiles = _match_profiles(metrics)
            state = (
                SelectionState.WATCH
                if profiles
                else SelectionState.WAIT
            )
        else:
            profiles = ()
            state = row.public_state
        discovered.append(
            CashDiscoveryRow(
                symbol=row.instrument.symbol,
                instrument_id=row.instrument.instrument_id,
                fact_id=row.fact.fact_id,
                public_state=state,
                discovery_profiles=profiles,
                discovery_reason=_reason(profiles, metrics),
                metrics=metrics,
                eligible=eligible,
                banned=row.banned,
            )
        )
    watch_count = sum(1 for item in discovered if item.public_state is SelectionState.WATCH)
    return CashDiscoveryBatch(
        batch_id=str(uuid4()),
        identity_batch_id=batch.batch_id,
        can_rank=False,
        can_unlock_confirmed=False,
        eligible_count=sum(1 for item in discovered if item.eligible),
        watch_count=watch_count,
        rows=tuple(discovered),
    )


def persist_cash_discovery(batch: CashDiscoveryBatch) -> CashDiscoveryBatch:
    if batch.can_rank or batch.can_unlock_confirmed:
        raise ValueError("A3 cannot set can_rank or can_unlock_confirmed")
    if any(row.public_state is SelectionState.CONFIRMED for row in batch.rows):
        raise ValueError("A3 cannot persist CONFIRMED")
    storage.init_db()
    conn = storage.connect()
    now = datetime.now(UTC).isoformat()
    try:
        conn.execute(
            """
            INSERT INTO cash_discovery_runs (
                batch_id, identity_batch_id, profile_id, eligible_count,
                watch_count, payload_json, persisted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch.batch_id,
                batch.identity_batch_id,
                batch.profile_id,
                batch.eligible_count,
                batch.watch_count,
                storage.encode_json(batch.model_dump(mode="json", by_alias=True)),
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return batch.model_copy(update={"persisted": True})


def latest_cash_discovery() -> CashDiscoveryBatch | None:
    storage.init_db()
    conn = storage.connect()
    try:
        head = conn.execute(
            """
            SELECT payload_json FROM cash_discovery_runs
            ORDER BY persisted_at DESC, batch_id DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()
    if head is None:
        return None
    payload = storage.decode_json(head["payload_json"])
    payload["persisted"] = True
    return CashDiscoveryBatch.model_validate(payload)
