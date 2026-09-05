"""File A S9 (SEL-010): offline PIT homework on free NSE EOD.

Attaches STO-017 path observations to a persisted S8 run using LATER official
adjusted bars. ``validationStatus`` is always ``PIT_NOT_APPROVED`` until R16/R18
gates pass. This is homework, not a scoreboard: no win-rate UI, no performance
chart, no auto-trade.

Ceiling LIVE_S9_PIT_NOT_APPROVED. confirmedCount pinned 0.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .contracts import SelectionState, stable_id
from .r5_live import latest_r5_structure_batch
from .cash_a4_history import list_raw_bars_by_symbol
from .store import (
    get_selection_payload,
    list_latest_selection_payloads,
    persist_selection_payload,
)

SCHEMA_VERSION = "trendforge.s9-pit.v1"
PROFILE_ID = "PRF-S9-PIT-HOMEWORK"
PROFILE_VERSION = "1.0.0"
ACCEPTANCE_CEILING = "LIVE_S9_PIT_NOT_APPROVED"
VALIDATION_STATUS = "PIT_NOT_APPROVED"
HORIZON_SESSIONS = 5
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

STO017Status = Literal[
    "WIN", "LOSS", "CENSORED", "INVALIDATED_BEFORE_ENTRY",
    "NO_ENTRY", "DELISTED", "NO_FORWARD_SESSION", "ATR_MISSING",
]


class S9ObservationRowV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    s8_public_state: str = "WAIT"
    status: str = "CENSORED"
    mfe_percent: float | None = None
    mae_percent: float | None = None
    bars_to_outcome: int | None = None
    horizon_sessions: int = HORIZON_SESSIONS
    fill_policy: str = "NEXT_SESSION_OPEN_AFTER_AVAILABLE_AT"
    costs_declared: bool = False
    censor_reason: str | None = None
    research_entry: float | None = None
    research_stop: float | None = None


class S9PitHomeworkBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    run_id: str
    source_s8_run_id: str
    as_of: datetime
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    validation_status: str = VALIDATION_STATUS
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    confirmed_count: int = 0
    rows: tuple[S9ObservationRowV1, ...]
    warnings: tuple[str, ...] = ()
    persisted: bool = False

    @model_validator(mode="after")
    def enforce_s9_law(self) -> "S9PitHomeworkBatchV1":
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("S9 cannot activate sources or unlock CONFIRMED")
        if self.confirmed_count != 0:
            raise ValueError("S9 confirmedCount is pinned to zero")
        if self.validation_status != VALIDATION_STATUS:
            raise ValueError(f"validationStatus must be {VALIDATION_STATUS}")
        for row in self.rows:
            if row.status in ("WIN",) and row.mfe_percent is None:
                raise ValueError("WIN rows must carry MFE")
        return self


def build_s9_pit_homework(
    *,
    s8_payload: dict[str, Any] | None = None,
    future_bars_by_symbol: dict[str, list[dict[str, Any]]] | None = None,
    built_at: datetime | None = None,
) -> S9PitHomeworkBatchV1:
    """Attach STO-017 path observations to the latest S8 run.

    ``future_bars_by_symbol`` maps symbol → list of bar dicts with keys:
    open, high, low, close, available_at (ISO string). Bars with
    available_at <= S8 asOf are excluded (PIT discipline).
    """
    now = built_at or datetime.now(timezone.utc)
    prior = s8_payload or {}
    lineage = prior.get("lineage") or {}
    s8_run_id = prior.get("runId") or prior.get("run_id") or "UNKNOWN"

    s8_rows = prior.get("rows") or []
    future_bars = future_bars_by_symbol or {}

    obs_rows: list[S9ObservationRowV1] = []
    for s8_row in s8_rows:
        sym = s8_row.get("symbol", "")
        state = s8_row.get("publicState", "WAIT")
        direction_raw = s8_row.get("evidenceDirection", "")
        entry = s8_row.get("researchEntry") or s8_row.get("nextTrigger")

        if state == "REJECT":
            obs_rows.append(S9ObservationRowV1(
                symbol=sym, s8_public_state=state,
                status="NO_ENTRY", censor_reason="S8_REJECT",
            ))
            continue
        if state not in ("WAIT", "WATCH"):
            obs_rows.append(S9ObservationRowV1(
                symbol=sym, s8_public_state=state,
                status="NO_ENTRY", censor_reason=f"UNEXPECTED_STATE_{state}",
            ))
            continue

        bars = future_bars.get(sym.upper(), [])
        if not bars:
            obs_rows.append(S9ObservationRowV1(
                symbol=sym, s8_public_state=state,
                status="NO_FORWARD_SESSION",
                censor_reason="NO_LATER_BARS_ON_DISK",
            ))
            continue

        # Use label_price_path with ATR-proxy barriers
        direction = "bullish" if "BULL" in str(direction_raw).upper() else "bearish"
        close = _first_close(bars)
        atr_proxy = _atr_proxy(bars)
        if close is None or atr_proxy is None or atr_proxy <= 0:
            obs_rows.append(S9ObservationRowV1(
                symbol=sym, s8_public_state=state,
                status="ATR_MISSING", censor_reason="NO_VALID_BARS",
            ))
            continue

        target = close + 2 * atr_proxy if direction == "bullish" else close - 2 * atr_proxy
        stop = close - atr_proxy if direction == "bullish" else close + atr_proxy

        from trendforge_api.validation_engine import label_price_path

        candles = [
            type("Bar", (), {"open": b["open"], "high": b["high"], "low": b["low"], "close": b["close"]})()
            for b in bars
        ]

        outcome = label_price_path(
            candles, entry=close, stop=stop, target=target, direction=direction
        )
        obs = outcome.label if hasattr(outcome, 'label') else getattr(outcome, 'label', 'CENSORED')
        if isinstance(outcome, dict):
            obs = outcome.get('label', 'CENSORED')

        status = obs if obs in ("WIN", "LOSS") else "CENSORED"
        obs_rows.append(S9ObservationRowV1(
            symbol=sym, s8_public_state=state, status=status,
            mfe_percent=getattr(outcome, "mfe_percent", None),
            mae_percent=getattr(outcome, "mae_percent", None),
            bars_to_outcome=getattr(outcome, "bars", None),
            censor_reason=None if status in ("WIN", "LOSS") else "INCOMPLETE_HORIZON",
        ))

    lineage_hashes = sorted(v for v in lineage.values() if isinstance(v, str))
    run_hash_source = json.dumps({
        "s8RunId": s8_run_id,
        "lineage": lineage_hashes,
        "rows": [r.model_dump(mode="json") for r in obs_rows],
    }, sort_keys=True)
    run_hash = __import__("hashlib").sha256(run_hash_source.encode()).hexdigest()
    run_id = stable_id(PROFILE_ID, s8_run_id, run_hash)

    return S9PitHomeworkBatchV1(
        run_id=run_id,
        source_s8_run_id=s8_run_id,
        as_of=now,
        rows=tuple(obs_rows),
        warnings=(
            "Offline PIT homework on free NSE EOD. Not approved. Not an order.",
        ),
    )


def _first_close(bars: list[dict]) -> float | None:
    return bars[0].get("close") if bars else None


def _atr_proxy(bars: list[dict], period: int = 14) -> float | None:
    if len(bars) < 2:
        return None
    effective = min(period, max(len(bars) - 1, 2))
    trs = []
    for i in range(1, min(len(bars), effective + 1)):
        b = bars[i]
        prev_close = bars[i - 1].get("close", b["close"])
        tr = max(
            b["high"] - b["low"],
            abs(b["high"] - prev_close),
            abs(b["low"] - prev_close),
        )
        trs.append(tr)
    return sum(trs) / len(trs) if trs else None


def persist_s9_homework(batch: S9PitHomeworkBatchV1) -> S9PitHomeworkBatchV1:
    stored = batch.model_copy(update={"persisted": True})
    candidates = tuple(
        (row.symbol, row.symbol, row.s8_public_state, row.model_dump(mode="json", by_alias=True))
        for row in stored.rows
    )
    persist_selection_payload(
        run_id=stored.run_id,
        profile_id=PROFILE_ID,
        as_of=stored.as_of,
        payload=stored.model_dump(mode="json", by_alias=True),
        candidates=candidates,
    )
    return stored


__all__ = [
    "ACCEPTANCE_CEILING",
    "MIN_COMPLETENESS",
    "PROFILE_ID",
    "SCHEMA_VERSION",
    "VALIDATION_STATUS",
    "S9ObservationRowV1",
    "S9PitHomeworkBatchV1",
    "build_s9_pit_homework",
    "persist_s9_homework",
]

# Re-export MIN_COMPLETENESS from s8 if needed
try:
    from .s8_persist_run import MIN_COMPLETENESS  # noqa: F401
except ImportError:
    MIN_COMPLETENESS = 0.95

def load_future_bars_from_a4(
    s8_as_of: str,
    symbols: set[str],
    horizon: int = HORIZON_SESSIONS,
) -> dict[str, list[dict[str, Any]]]:
    """Load official adjusted EOD bars strictly AFTER s8_as_of per symbol.

    Returns dict[symbol, list[bar_dict]] with at most `horizon` completed
    sessions per symbol. Bars are from cash_a4_history (official authority).
    """
    from datetime import date as date_type
    import datetime as dt_module

    if isinstance(s8_as_of, str):
        as_of = date_type.fromisoformat(s8_as_of[:10])
    else:
        as_of = s8_as_of

    through = date_type.max  # all bars on disk
    all_bars = list_raw_bars_by_symbol(symbols, through=through)

    result: dict[str, list[dict[str, Any]]] = {}
    for sym, bar_list in all_bars.items():
        future = [
            {
                "open": b.open,
                "high": b.high or b.close,
                "low": b.low or b.close,
                "close": b.close,
                "volume": b.volume,
                "trade_date": b.trade_date.isoformat(),
            }
            for b in bar_list
            if b.trade_date > as_of and b.close is not None and b.close > 0
        ]
        future.sort(key=lambda b: b["trade_date"])
        result[sym.upper()] = future[:horizon]
    return result


