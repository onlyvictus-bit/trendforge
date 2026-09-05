"""Live File A R14: official corporate-action / identity-continuity join.

This is NOT:
- A2 canonical identity (`cash_a2_identity.py` owns that)
- A4 vintage storage (`cash_a4_history.py` owns that; R14 joins stored rows)
- DAT-022 reconciliation itself (`corporate_actions.py` owns the formulas;
  R14 reuses `reconcile_corporate_actions` and never rewrites it)
- R6 sponsor votes, R2-B activation, live CONFIRMED, qty, broker, Kelly, S4/S5
- A 124th registry job (`nse_corporate_filings_actions` is already CA_SOURCE)

This IS:
- Bind each live R2 row through the R4 A2 instrument pin to official CA terms
- DAT-022 factor orientation (split/bonus/dividend/rights/merger) with
  timezone-aware clocks; future CA stays hidden from replay
- Identity continuity: successor/predecessor without same-instrument proof is
  IDENTITY_BREAK, never a silent ticker follow
- A versioned adjusted-series key via `series_layers.open_adjusted_series`;
  RAW bars are never mutated (STO-020)
- Hash-scoped persisted batch consumed by R5 as the only CA authority
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, time
from math import isfinite
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from .. import storage
from ..corporate_actions import (
    ReconciledCorporateAction,
    reconcile_corporate_actions,
)
from .attention_order import InventoryDiscoveryV1, latest_attention_order
from .cash_a2_identity import CashIdentityBatch, latest_cash_identity
from .cash_a4_history import CorporateActionVintage, list_ca_vintages, list_raw_bars
from .contracts import SelectionState, StateCeiling, stable_id
from .inventory_source_bundle import (
    InventorySourceBundleV1,
    latest_inventory_source_bundle,
)
from .r4_live import R4IdentityPinV1, latest_r4_identity_pin
from .series_layers import open_adjusted_series, raw_series
from .store import latest_selection_payload, persist_selection_payload

SCHEMA_VERSION = "trendforge.ca-join.v1"
PROFILE_ID = "PRF-R14-CA-JOIN"
PROFILE_VERSION = "1.0.0"
ACCEPTANCE_CEILING = "LIVE_CA_JOIN_WAIT_ONLY"
ALGORITHM_VERSION = "DAT-022-v1"  # pin; revisions must change this string
IST = ZoneInfo("Asia/Kolkata")
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)
VOLUME_ADJUSTING_CLASSES = frozenset({"SPLIT", "BONUS"})
PRICE_RECONSTRUCTING_CLASSES = frozenset(
    {"SPLIT", "BONUS", "DIVIDEND", "RIGHTS", "MERGER", "DEMERGER"}
)

JoinStatus = Literal[
    "NONE",
    "JOINED",
    "WAIT_DETAILS",
    "CONFLICT",
    "CANCELLED",
    "IDENTITY_BREAK",
    "UNKNOWN_ID",
    "COMPANION_REJECTED",
]
CaState = Literal["NONE", "ADJUSTED", "WAIT_CA"]
IdentityContinuity = Literal["SAME_INSTRUMENT", "UNPROVEN", "BREAK"]


class R14JoinedCaEventV1(BaseModel):
    """One DAT-022-resolved official action R5 may apply to pre-ex bars."""

    model_config = MODEL_CONFIG

    action_key: str
    action_class: str
    effective_date: date
    adjustment_factor: float = Field(gt=0)
    affects_volume: bool


class R14CaJoinRowV1(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str
    symbol: str
    display_order: int = Field(gt=0)
    instrument_id: str | None = None
    isin: str | None = None
    r2_public_state: SelectionState
    r14_state: SelectionState = SelectionState.WAIT
    join_status: JoinStatus
    ca_state: CaState
    visible_event_ids: tuple[str, ...] = ()
    hidden_future_event_count: int = Field(ge=0, default=0)
    factor_version: str | None = None
    adjusted_series_id: str | None = None
    raw_series_id: str
    identity_continuity: IdentityContinuity
    joined_events: tuple[R14JoinedCaEventV1, ...] = ()
    can_support_confirmed: bool = False
    can_affect_rank: bool = False
    why_wait: tuple[str, ...] = ()

    @model_validator(mode="after")
    def live_ceiling(self) -> "R14CaJoinRowV1":
        if self.r14_state is SelectionState.CONFIRMED:
            raise ValueError("live R14 cannot emit CONFIRMED")
        if self.r14_state is SelectionState.REJECT and (
            self.r2_public_state is not SelectionState.REJECT
        ):
            raise ValueError("R14 REJECT is only ever a copy of an R2 REJECT")
        if self.can_support_confirmed or self.can_affect_rank:
            raise ValueError("R14 CA join cannot vote, rank, or unlock CONFIRMED")
        if self.r14_state is SelectionState.WAIT and not self.why_wait:
            raise ValueError("R14 WAIT rows require explicit why_wait codes")
        if self.ca_state == "WAIT_CA" and self.factor_version is not None:
            raise ValueError("WAIT_CA cannot carry a factor version")
        if self.ca_state == "ADJUSTED" and (
            self.factor_version is None or self.adjusted_series_id is None
        ):
            raise ValueError("ADJUSTED rows require factor and adjusted series ids")
        if self.ca_state != "ADJUSTED" and self.joined_events:
            raise ValueError("joined events require the ADJUSTED CA state")
        return self


class R14CaJoinBatchV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    run_id: str
    run_hash: str
    r1_bundle_id: str
    r1_bundle_hash: str
    r2_run_id: str
    r2_run_hash: str
    r4_run_id: str
    r4_run_hash: str
    collector_run_id: str
    cash_pipeline_run_id: str
    permission_fingerprint: str
    trading_date: str
    decision_at: datetime
    state_ceiling: StateCeiling = StateCeiling.WAIT
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    algorithm_version: str = ALGORITHM_VERSION
    universe_count: int = Field(ge=0)
    joined_count: int = Field(ge=0, default=0)
    wait_ca_count: int = Field(ge=0, default=0)
    conflict_count: int = Field(ge=0, default=0)
    none_count: int = Field(ge=0, default=0)
    persisted: bool = False
    rows: tuple[R14CaJoinRowV1, ...]
    warnings: tuple[str, ...] = ()

    @field_validator("decision_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decision_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def live_ceiling(self) -> "R14CaJoinBatchV1":
        if self.universe_count != len(self.rows):
            raise ValueError("R14 universe count does not match rows")
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("R14 cannot activate sources or unlock CONFIRMED")
        if any(row.r14_state is SelectionState.CONFIRMED for row in self.rows):
            raise ValueError("R14 live rows cannot be CONFIRMED")
        if self.joined_count != sum(row.join_status == "JOINED" for row in self.rows):
            raise ValueError("R14 joined count does not match rows")
        if self.wait_ca_count != sum(row.ca_state == "WAIT_CA" for row in self.rows):
            raise ValueError("R14 WAIT_CA count does not match rows")
        if self.conflict_count != sum(row.join_status == "CONFLICT" for row in self.rows):
            raise ValueError("R14 conflict count does not match rows")
        if self.none_count != sum(row.join_status == "NONE" for row in self.rows):
            raise ValueError("R14 none count does not match rows")
        return self


def _aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _parse_datetime(value: Any) -> datetime | None:
    if value in {None, ""}:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


def _availability(row: dict[str, Any]) -> datetime | None:
    value = row.get("available_at") or row.get("availableAt")
    if value in {None, ""}:
        value = row.get("parsed_at") or row.get("parsedAt")
    return _parse_datetime(value)


def _symbol_observations(
    symbol: str, observations: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    if observations is not None:
        return [
            row
            for row in observations
            if str(row.get("symbol") or "").upper().strip() == symbol.upper()
        ]
    return storage.list_corporate_event_observations(symbol=symbol)


def _vintage_observation_rows(
    symbol: str, vintages: list[CorporateActionVintage] | None
) -> list[dict[str, Any]]:
    items = (
        list(vintages)
        if vintages is not None
        else [
            item
            for item in list_ca_vintages()
            if item.symbol.upper() == symbol.upper()
        ]
    )
    return [
        {
            "source_key": "a4_ca_vintage",
            "symbol": item.symbol.upper(),
            "action_type": item.action_class,
            "action_class": item.action_class,
            "ex_date": item.effective_date.isoformat(),
            "record_date": item.effective_date.isoformat(),
            "adjustment_factor": item.adjustment_factor,
            "revision_status": "ORIGINAL",
            "parsed_at": item.available_at.isoformat(),
        }
        for item in items
        if item.symbol.upper() == symbol.upper()
    ]


def _hidden_future_count(rows: list[dict[str, Any]], *, decision_at: datetime) -> int:
    hidden = 0
    for row in rows:
        available = _availability(row)
        if available is not None and available > decision_at:
            hidden += 1
    return hidden


def _pre_ex_close(
    *,
    symbol: str,
    effective_date: date,
    through: date,
    decision_at: datetime,
) -> float | None:
    """Last RAW close strictly before effective_date whose session closed."""
    references = [
        bar
        for bar in list_raw_bars(symbol, through=through)
        if bar.trade_date < effective_date
        and datetime.combine(bar.trade_date, time(15, 30), tzinfo=IST)
        <= decision_at.astimezone(IST)
        and bar.close is not None
        and float(bar.close) > 0
    ]
    if not references:
        return None
    return float(max(references, key=lambda bar: bar.trade_date).close)


def _resolve_dat022_factor(
    action: ReconciledCorporateAction,
    *,
    symbol: str,
    through: date,
    decision_at: datetime,
) -> tuple[float | None, str | None]:
    """DAT-022 factor for one reconciled action, or a WAIT code."""
    if action.adjustment_factor is not None:
        value = float(action.adjustment_factor)
        if isfinite(value) and value > 0:
            return value, None
        return None, "WAIT_CA_FACTOR_INVALID"
    if action.action_class in {"SPLIT", "BONUS"}:
        # Reconcile always sets the ratio factor for these; absence means
        # the official terms never carried a usable ratio.
        return None, "WAIT_CA_FACTOR_INVALID"
    reference = _pre_ex_close(
        symbol=symbol,
        effective_date=action.effective_date,
        through=through,
        decision_at=decision_at,
    )
    if reference is None:
        return None, "WAIT_CA_PRE_EX_CLOSE_MISSING"
    if action.action_class == "DIVIDEND" and action.cash_amount is not None:
        factor = (reference - float(action.cash_amount)) / reference
        if 0 < factor < 1:
            return round(factor, 10), None
        return None, "WAIT_CA_FACTOR_INVALID"
    if (
        action.action_class == "RIGHTS"
        and action.ratio_numerator is not None
        and action.ratio_denominator is not None
        and action.offer_price is not None
    ):
        theoretical = (
            reference * action.ratio_denominator
            + action.offer_price * action.ratio_numerator
        ) / (action.ratio_denominator + action.ratio_numerator)
        factor = theoretical / reference
        if factor > 0:
            return round(factor, 10), None
        return None, "WAIT_CA_FACTOR_INVALID"
    return None, "WAIT_CA_WAIT_DETAILS"


def _cross_symbol_terms(action: ReconciledCorporateAction) -> bool:
    symbol = action.symbol.upper()
    for term in (action.predecessor_symbol, action.successor_symbol):
        if term is not None and term.upper() != symbol:
            return True
    return False


def _raw_series_ref(symbol: str, artifact_hash: str):
    return raw_series(
        instrument_key=f"NSE:{symbol}:EQ", artifact_hash=artifact_hash
    )


def build_r14_ca_join(
    *,
    bundle: InventorySourceBundleV1 | None = None,
    attention: InventoryDiscoveryV1 | None = None,
    identity: CashIdentityBatch | None = None,
    pin: R4IdentityPinV1 | None = None,
    observations: list[dict[str, Any]] | None = None,
    vintages: list[CorporateActionVintage] | None = None,
    decision_at: datetime | None = None,
) -> R14CaJoinBatchV1:
    r1 = bundle or latest_inventory_source_bundle()
    r2 = attention or latest_attention_order()
    a2 = identity if identity is not None else latest_cash_identity()
    if r1 is None or r2 is None:
        raise ValueError("WAIT_R14_R1_R2_NOT_READY")
    if r2.r1_bundle_id != r1.bundle_id or r2.r1_bundle_hash != r1.bundle_hash:
        raise ValueError("WAIT_R14_LINEAGE_MISMATCH")
    r4 = pin if pin is not None else latest_r4_identity_pin()
    if (
        r4 is None
        or r4.r1_bundle_id != r1.bundle_id
        or r4.r1_bundle_hash != r1.bundle_hash
        or r4.r2_run_id != r2.run_id
        or r4.r2_run_hash != r2.run_hash
    ):
        raise ValueError("WAIT_R14_R4_NOT_READY")
    at = _aware(decision_at or r2.built_at, "decision_at")
    a2_symbols = (
        {row.instrument.symbol.upper() for row in a2.rows} if a2 is not None else set()
    )
    r4_by_candidate = {row.candidate_id: row for row in r4.rows}
    rows: list[R14CaJoinRowV1] = []
    for item in r2.rows:
        symbol = item.symbol.upper()
        r4_row = r4_by_candidate.get(item.candidate_id)
        if r4_row is None:
            r4_row = next((row for row in r4.rows if row.symbol == symbol), None)
        artifact = (
            item.lineage.get("artifactHash")
            if isinstance(item.lineage.get("artifactHash"), str)
            and item.lineage.get("artifactHash")
            else r1.bundle_hash
        )
        raw_ref = _raw_series_ref(symbol, artifact)
        reasons: list[str] = ["R14_LIVE_WAIT_CEILING"]
        state = SelectionState.WAIT
        if item.public_state is SelectionState.REJECT:
            state = SelectionState.REJECT
            reasons.append("R2_PUBLIC_REJECT")

        obs_rows = _symbol_observations(symbol, observations)
        obs_rows = obs_rows + _vintage_observation_rows(symbol, vintages)
        hidden = _hidden_future_count(obs_rows, decision_at=at)

        if r4_row is None or r4_row.identity_status == "UNKNOWN_ID":
            row = R14CaJoinRowV1(
                candidate_id=item.candidate_id,
                symbol=symbol,
                display_order=item.display_order,
                instrument_id=None,
                isin=None,
                r2_public_state=item.public_state,
                r14_state=state,
                join_status="UNKNOWN_ID",
                ca_state="WAIT_CA",
                visible_event_ids=(),
                hidden_future_event_count=hidden,
                raw_series_id=raw_ref.series_id,
                identity_continuity="UNPROVEN",
                why_wait=tuple(dict.fromkeys(reasons + ["UNKNOWN_ID"])),
            )
            rows.append(row)
            continue
        if r4_row.identity_status == "COMPANION_REJECTED":
            row = R14CaJoinRowV1(
                candidate_id=item.candidate_id,
                symbol=symbol,
                display_order=item.display_order,
                instrument_id=None,
                isin=None,
                r2_public_state=item.public_state,
                r14_state=state,
                join_status="COMPANION_REJECTED",
                ca_state="WAIT_CA",
                visible_event_ids=(),
                hidden_future_event_count=hidden,
                raw_series_id=raw_ref.series_id,
                identity_continuity="UNPROVEN",
                why_wait=tuple(
                    dict.fromkeys(reasons + ["COMPANION_SCRIP_CODE_NOT_IDENTITY"])
                ),
            )
            rows.append(row)
            continue

        reconciled = reconcile_corporate_actions(obs_rows, as_of=at)
        live_actions = [action for action in reconciled if action.state != "CANCELLED"]
        all_cancelled = bool(reconciled) and not live_actions
        joined_events: list[R14JoinedCaEventV1] = []
        identity_break = False
        conflict = False
        wait_details = False
        wait_code: str | None = None
        for action in live_actions:
            if action.state == "CONFLICT":
                conflict = True
                continue
            if _cross_symbol_terms(action):
                identity_break = True
                continue
            if action.action_class not in PRICE_RECONSTRUCTING_CLASSES:
                continue
            if action.state == "WAIT_DETAILS":
                wait_details = True
                if wait_code is None:
                    wait_code = "WAIT_CA_WAIT_DETAILS"
                continue
            factor, code = _resolve_dat022_factor(
                action, symbol=symbol, through=r1.trading_date, decision_at=at
            )
            if factor is None:
                wait_details = True
                if wait_code is None or (
                    code == "WAIT_CA_PRE_EX_CLOSE_MISSING"
                    and wait_code == "WAIT_CA_WAIT_DETAILS"
                ):
                    wait_code = code
                continue
            joined_events.append(
                R14JoinedCaEventV1(
                    action_key=action.action_key,
                    action_class=action.action_class,
                    effective_date=action.effective_date,
                    adjustment_factor=factor,
                    affects_volume=action.action_class in VOLUME_ADJUSTING_CLASSES,
                )
            )

        if conflict:
            join_status: JoinStatus = "CONFLICT"
            ca_state: CaState = "WAIT_CA"
            reasons.append("WAIT_CA_CONFLICT")
            continuity: IdentityContinuity = "SAME_INSTRUMENT"
        elif identity_break:
            join_status = "IDENTITY_BREAK"
            ca_state = "WAIT_CA"
            reasons.append("WAIT_CA_IDENTITY_BREAK")
            if any(
                term is not None
                for action in live_actions
                for term in (action.successor_symbol, action.predecessor_symbol)
                if term is not None and term.upper() not in a2_symbols
            ):
                reasons.append("SUCCESSOR_INSTRUMENT_NOT_IN_A2")
            continuity = "BREAK"
        elif wait_details:
            join_status = "WAIT_DETAILS"
            ca_state = "WAIT_CA"
            reasons.append(wait_code or "WAIT_CA_WAIT_DETAILS")
            continuity = "SAME_INSTRUMENT"
        elif joined_events:
            join_status = "JOINED"
            ca_state = "ADJUSTED"
            continuity = "SAME_INSTRUMENT"
        elif all_cancelled:
            join_status = "CANCELLED"
            ca_state = "NONE"
            continuity = "SAME_INSTRUMENT"
        else:
            join_status = "NONE"
            ca_state = "NONE"
            continuity = "SAME_INSTRUMENT"

        factor_version: str | None = None
        adjusted_series_id: str | None = None
        if ca_state != "WAIT_CA":
            ordered = sorted(
                joined_events, key=lambda event: (event.effective_date, event.action_key)
            )
            factor_version = stable_id(
                "r14-ca-factor",
                ALGORITHM_VERSION,
                tuple(
                    (
                        event.action_key,
                        event.action_class,
                        event.effective_date,
                        event.adjustment_factor,
                        event.affects_volume,
                    )
                    for event in ordered
                ),
            )
            if ca_state == "ADJUSTED":
                adjusted_series_id = open_adjusted_series(
                    raw_ref, adjustment_event_id=factor_version
                ).series_id

        rows.append(
            R14CaJoinRowV1(
                candidate_id=item.candidate_id,
                symbol=symbol,
                display_order=item.display_order,
                instrument_id=r4_row.instrument_id,
                isin=r4_row.isin,
                r2_public_state=item.public_state,
                r14_state=state,
                join_status=join_status,
                ca_state=ca_state,
                visible_event_ids=tuple(
                    action.action_key for action in live_actions
                ),
                hidden_future_event_count=hidden,
                factor_version=factor_version,
                adjusted_series_id=adjusted_series_id,
                raw_series_id=raw_ref.series_id,
                identity_continuity=continuity,
                joined_events=tuple(joined_events),
                why_wait=tuple(dict.fromkeys(reasons)),
            )
        )

    identity_payload = {
        "r1BundleHash": r1.bundle_hash,
        "r2RunHash": r2.run_hash,
        "r4RunHash": r4.run_hash,
        "algorithmVersion": ALGORITHM_VERSION,
        "decisionAt": at.isoformat(),
        "rows": [
            {
                "symbol": row.symbol,
                "joinStatus": row.join_status,
                "caState": row.ca_state,
                "factorVersion": row.factor_version,
                "visibleEventIds": list(row.visible_event_ids),
            }
            for row in rows
        ],
    }
    run_hash = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return R14CaJoinBatchV1(
        run_id=stable_id("r14-ca-join", r1.bundle_id, r2.run_id, r4.run_id, run_hash),
        run_hash=run_hash,
        r1_bundle_id=r1.bundle_id,
        r1_bundle_hash=r1.bundle_hash,
        r2_run_id=r2.run_id,
        r2_run_hash=r2.run_hash,
        r4_run_id=r4.run_id,
        r4_run_hash=r4.run_hash,
        collector_run_id=r1.collector_run_id,
        cash_pipeline_run_id=r1.cash_pipeline_run_id,
        permission_fingerprint=r1.permission_fingerprint,
        trading_date=r1.trading_date.isoformat(),
        decision_at=at,
        universe_count=len(rows),
        joined_count=sum(row.join_status == "JOINED" for row in rows),
        wait_ca_count=sum(row.ca_state == "WAIT_CA" for row in rows),
        conflict_count=sum(row.join_status == "CONFLICT" for row in rows),
        none_count=sum(row.join_status == "NONE" for row in rows),
        rows=tuple(rows),
        warnings=(
            "R14 joins official corporate actions for integrity only. A CA is "
            "never bullish evidence and can never unlock CONFIRMED.",
        ),
    )


def persist_r14_ca_join(value: R14CaJoinBatchV1) -> R14CaJoinBatchV1:
    stored = value.model_copy(update={"persisted": True})
    persist_selection_payload(
        run_id=stored.run_id,
        profile_id=PROFILE_ID,
        as_of=stored.decision_at,
        payload=stored.model_dump(mode="json", by_alias=True),
        candidates=tuple(
            (
                row.candidate_id,
                row.symbol,
                row.r14_state.value,
                row.model_dump(mode="json", by_alias=True),
            )
            for row in stored.rows
        ),
    )
    return stored


def latest_r14_ca_join() -> R14CaJoinBatchV1 | None:
    payload = latest_selection_payload(PROFILE_ID)
    return R14CaJoinBatchV1.model_validate(payload) if payload is not None else None
