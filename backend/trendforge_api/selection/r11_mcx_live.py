"""File A R11: MCX master + local-bar readiness, honest WAIT by default.

MCX cannot leave WAIT without an official LOCAL contract master AND current
local bars. FBIL USD/INR (delayed FX), CFTC and WGC are context only — none
of them can unlock MCX intraday or confirm anything. PRF-005/006/007 boards
stay EMPTY this ticket; R2-B's named activation is NSE-only, so
``canUnlockConfirmed=false`` for the whole MCX branch.

Missing lot/tick/expiry stays WAIT with a named why-code — numbers are never
invented. A tender-window hit vetoes READY (WAIT_TENDER). Swing RS/delivery
reuse S3/S5 evidence as GATES only (never a second score); delivery stays
EOD-only exactly as S5 enforces.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "trendforge.mcx-master.v1"
PROFILE_ID = "PRF-R11-MCX-WAIT"
PROFILE_VERSION = "1.0.0"
ACCEPTANCE_CEILING = "LIVE_MCX_WAIT_WITHOUT_NAMED_ACTIVATION"
COPY = "MCX contract safety - WAIT without master. Not COMEX. Not an order."
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

Readiness = Literal[
    "MASTER_AND_LOCAL_CONTEXT_READY",
    "WAIT_MCX_MASTER",
    "WAIT_MCX_LOCAL_BARS",
    "WAIT_MCX_STALE",
    "WAIT_MCX_CALENDAR",
]

MASTER_SOURCE_KEYS = ("mcx_contract_master", "mcx_market_watch")
LOCAL_BARS_KEY = "mcx_bhavcopy"


def _as_date(value: Any) -> date | None:
    from datetime import datetime as _dt

    if isinstance(value, _dt):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _fresh(source_key: str, data_date: str | None, now: date | None) -> bool:
    if now is None:
        return False
    from ..parsers.source_freshness import is_data_date_fresh

    return is_data_date_fresh(source_key, data_date, now=now)


def _latest_parse(source_key: str):
    from ..storage import get_latest_source_parse_result

    try:
        return get_latest_source_parse_result(source_key)
    except Exception:
        return None


class McxMasterRowV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    instrument_id: str | None = None
    lot_size: int | None = Field(default=None, alias="lotSize")
    tick_size: float | None = Field(default=None, alias="tickSize")
    expiry: str | None = None
    dte: int | None = None
    tender_window: str | None = None
    available_at: str | None = None
    source_hash: str | None = None
    readiness: Readiness
    why: tuple[str, ...] = ()
    can_support_confirmed: Literal[False] = False


class McxMasterBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    trading_date: str | None = None
    built_at: datetime
    ready_count: int = Field(default=0, ge=0)
    confirmed_count: int = 0
    executable: Literal[False] = False
    can_unlock_confirmed: Literal[False] = False
    readiness_counts: dict[str, int] = Field(default_factory=dict)
    tried_source_keys: tuple[str, ...] = ()
    rows: tuple[McxMasterRowV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def enforce_r11_law(self) -> "McxMasterBatchV1":
        if self.confirmed_count != 0:
            raise ValueError("R11 MCX confirmedCount is pinned to zero")
        if any(row.readiness == "MASTER_AND_LOCAL_CONTEXT_READY" for row in self.rows):
            if self.ready_count < 1:
                raise ValueError("readyCount must count READY rows")
        return self


def _master_rows(output: dict | None) -> list[dict[str, Any]]:
    if not output:
        return []
    rows = output.get("rows")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _row_readiness(
    *,
    has_master: bool,
    master_current: bool,
    bars_state: str | None,
    missing_fields: list[str],
    tender_hit: bool,
    calendar_ok: bool,
) -> Readiness:
    if not has_master or not master_current:
        return "WAIT_MCX_MASTER"
    if missing_fields:
        # Missing contract fields keep the row WAIT on the master dimension.
        return "WAIT_MCX_MASTER"
    if bars_state == "MISSING":
        return "WAIT_MCX_LOCAL_BARS"
    if bars_state == "STALE":
        return "WAIT_MCX_STALE"
    if not calendar_ok:
        return "WAIT_MCX_CALENDAR"
    if tender_hit:
        return "WAIT_MCX_CALENDAR"  # tender veto seats the row out of READY
    return "MASTER_AND_LOCAL_CONTEXT_READY"


def build_mcx_master(*, trading_date: str | None = None) -> McxMasterBatchV1:
    """Assemble the honest MCX readiness board from observed last-goods."""
    tried: list[str] = []

    master_parse = None
    master_key_used = None
    for key in MASTER_SOURCE_KEYS:
        tried.append(key)
        parsed = _latest_parse(key)
        if (
            parsed is not None
            and parsed.parser_state == "PARSED_STRUCTURED"
            and parsed.record_count > 0
        ):
            master_parse = parsed
            master_key_used = key
            break

    tried.append(LOCAL_BARS_KEY)
    bars_parse = _latest_parse(LOCAL_BARS_KEY)

    today: date | None = _as_date(trading_date) if trading_date else date.today()
    bars_state: str | None
    if bars_parse is None or bars_parse.parser_state != "PARSED_STRUCTURED":
        bars_state = "MISSING"
    elif not _fresh(LOCAL_BARS_KEY, bars_parse.data_date, today):
        bars_state = "STALE"
    else:
        bars_state = "CURRENT"

    calendar_ok = bool(
        bars_parse is not None
        and bars_parse.snapshot_id is not None
        and bars_parse.data_date
    )

    rows_out: list[McxMasterRowV1] = []
    counts: dict[str, int] = {}
    ready_count = 0

    if master_parse is None:
        warnings = [
            COPY,
            "No structured official MCX master last-good; every row seats WAIT.",
            "FBIL USD/INR is delayed FX context; CFTC/WGC are delayed globals - neither can unlock MCX.",
        ]
    else:
        warnings = [
            COPY,
            "FBIL USD/INR is delayed FX context; CFTC/WGC are delayed globals - neither can unlock MCX.",
        ]

    for raw in _master_rows(master_parse.output if master_parse else None):
        symbol = str(raw.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        why: list[str] = []
        lot = raw.get("lotSize", raw.get("lot_size"))
        tick = raw.get("tickSize", raw.get("tick_size"))
        expiry_raw = raw.get("expiry")
        lot_i: int | None
        try:
            lot_i = int(lot) if lot is not None else None
        except (TypeError, ValueError):
            lot_i = None
        tick_f: float | None
        try:
            tick_f = float(tick) if tick is not None else None
        except (TypeError, ValueError):
            tick_f = None
        expiry = str(expiry_raw)[:10] if expiry_raw else None

        if lot_i is None:
            why.append("WAIT_LOT")
        if tick_f is None:
            why.append("WAIT_TICK")
        if not expiry:
            why.append("WAIT_EXPIRY")

        tender_start = _as_date(raw.get("tenderStart"))
        tender_end = _as_date(raw.get("tenderEnd"))
        tender_hit = False
        tender_window = None
        if tender_start and tender_end:
            tender_window = f"{tender_start.isoformat()}..{tender_end.isoformat()}"
            if today and tender_start <= today <= tender_end:
                tender_hit = True
                why.append("WAIT_TENDER")

        dte = None
        if expiry and today:
            expiry_d = _as_date(expiry)
            if expiry_d:
                dte = (expiry_d - today).days

        missing = [c for c in ("WAIT_LOT", "WAIT_TICK", "WAIT_EXPIRY") if c in why]
        readiness = _row_readiness(
            has_master=master_parse is not None,
            master_current=True,
            bars_state=bars_state,
            missing_fields=missing,
            tender_hit=tender_hit,
            calendar_ok=calendar_ok,
        )
        if readiness == "MASTER_AND_LOCAL_CONTEXT_READY":
            ready_count += 1
        counts[readiness] = counts.get(readiness, 0) + 1

        rows_out.append(
            McxMasterRowV1(
                symbol=symbol,
                instrumentId=str(raw.get("instrumentId") or "") or None,
                lotSize=lot_i,
                tickSize=tick_f,
                expiry=expiry,
                dte=dte,
                tenderWindow=tender_window,
                availableAt=(master_parse.parsed_at if master_parse else None),
                sourceHash=(
                    master_key_used
                ),
                readiness=readiness,
                why=tuple(why),
            )
        )

    if not rows_out and master_parse is None:
        counts["WAIT_MCX_MASTER"] = counts.get("WAIT_MCX_MASTER", 0) + 1
        warnings.append("WAIT_MCX_MASTER")

    built = datetime.now(timezone.utc)
    return McxMasterBatchV1(
        tradingDate=trading_date or (today.isoformat() if today else None),
        builtAt=built,
        readyCount=ready_count,
        readinessCounts=dict(sorted(counts.items())),
        triedSourceKeys=tuple(dict.fromkeys(tried)),
        rows=tuple(rows_out),
        warnings=tuple(warnings),
    )


def mcx_profile_blocker(batch: "McxMasterBatchV1 | None") -> Literal["WAIT_MCX_MASTER"]:
    """PRF-005/006/007 stay EMPTY while the MCX master context is not READY.

    The blocker code is what those (future) boards would surface; this ticket
    never builds them.
    """
    if batch is None or batch.ready_count == 0:
        return "WAIT_MCX_MASTER"
    return "WAIT_MCX_MASTER"


def swing_delivery_gate(status: str | None) -> tuple[bool, str]:
    """Gate-only mapping over the existing S5 delivery statuses."""
    status = (status or "").strip()
    if status == "FORBIDDEN_ON_INTRADAY":
        return True, "FORBIDDEN_ON_INTRADAY"
    if status.startswith(("DELIVERY_Z", "CURRENT_PCT_Z_UNKNOWN")):
        return False, ""
    return True, "WAIT_DELIVERY"


def swing_rs_gate(rs_1d: float | None, rs_5d: float | None) -> bool:
    """True when at least one PIT RS companion value exists (gate, not score)."""
    return rs_1d is not None or rs_5d is not None


__all__ = [
    "ACCEPTANCE_CEILING",
    "McxMasterBatchV1",
    "McxMasterRowV1",
    "PROFILE_ID",
    "SCHEMA_VERSION",
    "build_mcx_master",
    "mcx_profile_blocker",
    "swing_delivery_gate",
    "swing_rs_gate",
]
