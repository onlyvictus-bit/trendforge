"""Live File A R2-B: named source activation ledger.

AMENDMENT 2026-08-25 (ticket 4 of 4): the ledger may now AUTHORIZE exactly
the five named confirm-path sources when each has a current official
last-good (observed from storage, never a constant). That single global flip
is what lets S7 seat PRF-003 EOD public CONFIRMED. It still:

- Never sets executable, qty, broker access, or can_unlock_confirmed
- Never authorizes nse_mwpl_percentages or any non-named source
- Fails closed: one missing/stale/broken last-good keeps everything locked

File A §9.6.1, §25.20.1 and locked plan R2-B as amended by
docs/fable/remaining_build/FILE_A_R2B_ACTIVATION_AMENDMENT_DRAFT.md.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ..source_cohort_r0b import evaluate_r0b_cohort
from ..source_inventory_compiler import compile_default_inventory
from .attention_order import latest_attention_order
from .contracts import SelectionState, StateCeiling, stable_id
from .inventory_source_bundle import latest_inventory_source_bundle
from .store import latest_selection_payload, persist_selection_payload

SCHEMA_VERSION = "trendforge.named-activation.v1"
PROFILE_ID = "PRF-R2B-NAMED-ACTIVATION"
PROFILE_VERSION = "2.0.0"
ACCEPTANCE_CEILING = "LIVE_NAMED_ACTIVATION_AMENDED_EOD"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

ActivationStatus = Literal["NOT_AUTHORIZED", "WAIT_PROOF", "AUTHORIZED"]

# Draft §A named confirm path — ONLY these five may ever be authorized.
CONFIRM_PATH_SOURCE_KEYS = frozenset(
    {
        "nse_bhavcopy_eod",
        "nse_fno_ban",
        "nse_fo_bhavcopy",
        "nse_index_close_eod",
        "nse_corporate_filings_actions",
    }
)


class R2BNamedSourceV1(BaseModel):
    model_config = MODEL_CONFIG

    source_key: str
    class_name: str
    role: str
    gate_permission: bool = False
    directional_permission: bool = False
    r0b_reviewed: bool = False
    r0b_proven: bool = False
    r0b_can_vote: bool = False
    confirm_eligible: bool = False
    activation_status: ActivationStatus = "NOT_AUTHORIZED"
    may_support_confirmed: bool = False
    why_wait: tuple[str, ...] = ()

    @model_validator(mode="after")
    def live_ceiling(self) -> "R2BNamedSourceV1":
        if self.r0b_can_vote:
            raise ValueError("R0-B members cannot vote in this milestone")
        authorized = self.activation_status == "AUTHORIZED"
        if self.may_support_confirmed != authorized:
            raise ValueError(
                "maySupportConfirmed requires AUTHORIZED status on this ledger"
            )
        if authorized and not (self.confirm_eligible and self.r0b_proven):
            raise ValueError("AUTHORIZED rows must be proven confirm-eligible")
        if self.source_key not in CONFIRM_PATH_SOURCE_KEYS and (
            authorized or self.may_support_confirmed
        ):
            raise ValueError("only named confirm-path sources may be authorized")
        if not self.why_wait and not authorized:
            raise ValueError("R2-B WAIT rows require explicit why_wait codes")
        return self


class R2BNamedActivationV1(BaseModel):
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
    collector_run_id: str
    permission_fingerprint: str
    trading_date: str
    decision_at: datetime
    workbook_sha256: str | None = None
    state_ceiling: StateCeiling = StateCeiling.WAIT
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    executable: bool = False
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    compiler_gate_authorized_count: int = Field(ge=0)
    r0b_proven_count: int = Field(ge=0)
    r0b_reviewed_count: int = Field(ge=0)
    authorized_count: int = 0
    may_confirm_count: int = 0
    named_source_count: int = Field(ge=0)
    persisted: bool = False
    rows: tuple[R2BNamedSourceV1, ...]
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def live_ceiling(self) -> "R2BNamedActivationV1":
        authorized_rows = {
            row.source_key for row in self.rows if row.activation_status == "AUTHORIZED"
        }
        confirm_rows = {row.source_key for row in self.rows if row.may_support_confirmed}
        if len(authorized_rows) != self.authorized_count:
            raise ValueError("authorizedCount does not match AUTHORIZED rows")
        if len(confirm_rows) != self.may_confirm_count:
            raise ValueError("mayConfirmCount does not match confirming rows")
        if self.can_unlock_confirmed or self.executable:
            raise ValueError("R2-B never unlocks execution or canUnlockConfirmed")
        if self.source_activation_ready:
            if authorized_rows != CONFIRM_PATH_SOURCE_KEYS:
                raise ValueError(
                    "sourceActivationReady requires ALL five named confirm-path "
                    "sources authorized (observed last-good); R2-B cannot activate "
                    "anything else"
                )
            if confirm_rows != CONFIRM_PATH_SOURCE_KEYS:
                raise ValueError("ready ledger must confirm exactly the named five")
        elif authorized_rows:
            raise ValueError(
                "authorization requires the global amendment flip; "
                "R2-B cannot activate partially"
            )
        if self.named_source_count != len(self.rows):
            raise ValueError("R2-B named source count does not match rows")
        return self


def _why(member) -> tuple[str, ...]:
    reasons = [
        "R2B_NAMED_ACTIVATION_CLOSED",
        "SOURCE_ACTIVATION_READY_FALSE",
        "NO_FILE_A_ACTIVATION_AMENDMENT",
        "R5_CONFIRMED_STILL_LOCKED",
    ]
    if not member.proven:
        reasons.append("R0B_NOT_PROVEN")
    if not member.confirm_eligible:
        reasons.append("NOT_CONFIRM_ELIGIBLE")
    if not member.can_vote:
        reasons.append("R0B_CAN_VOTE_FALSE")
    reasons.append("GATE_PERMISSION_FALSE")
    return tuple(dict.fromkeys(reasons))


def _observed_last_good(
    source_key: str, trading_date
) -> tuple[bool, str]:
    """Observe whether this source's stored last-good is structured and fresh.

    Mirrors gate_readiness.dependency_state evidence rules (snapshot present,
    latest snapshot parsed, PARSED_STRUCTURED, non-empty or valid-empty,
    data_date inside the registry freshness window). No compiler ceiling is
    consulted here: the named-activation ledger IS the activation authority.
    """
    from ..parsers.source_freshness import is_data_date_fresh
    from ..source_contracts import VALID_EMPTY_SOURCES
    from ..storage import (
        get_latest_source_parse_result,
        get_latest_source_snapshot,
    )

    snapshot = get_latest_source_snapshot(source_key)
    if snapshot is None:
        return False, "R2B_LAST_GOOD_MISSING"
    if snapshot.check_state == "BROKEN":
        return False, "R2B_SOURCE_BROKEN"
    parsed = get_latest_source_parse_result(source_key)
    if parsed is None:
        return False, "R2B_PARSE_NOT_LATEST"
    if parsed.snapshot_id != snapshot.id:
        return False, "R2B_PARSE_NOT_LATEST"
    if parsed.parser_state != "PARSED_STRUCTURED":
        return False, "R2B_NOT_STRUCTURED"
    valid_empty = (
        source_key in VALID_EMPTY_SOURCES
        and parsed.output.get("validEmpty") is True
    )
    if parsed.record_count <= 0 and not valid_empty:
        return False, "R2B_EMPTY_PARSE"
    now = _as_date(trading_date)
    if not is_data_date_fresh(source_key, parsed.data_date, now=now):
        return False, "R2B_STALE_DATA"
    return True, "R2B_LAST_GOOD_CURRENT"


def _as_date(value) -> date | None:
    from datetime import datetime as _datetime

    if isinstance(value, _datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def build_r2b_named_activation() -> R2BNamedActivationV1:
    r1 = latest_inventory_source_bundle()
    r2 = latest_attention_order()
    if r1 is None or r2 is None:
        raise ValueError("WAIT_R2B_R1_R2_NOT_READY")
    if (
        r2.r1_bundle_id != r1.bundle_id
        or r2.r1_bundle_hash != r1.bundle_hash
        or r2.collector_run_id != r1.collector_run_id
        or r2.permission_fingerprint != r1.permission_fingerprint
    ):
        raise ValueError("WAIT_R2B_LINEAGE_MISMATCH")

    compiler = compile_default_inventory()
    compiled = {item.source_contract_id: item for item in compiler.source_contracts}
    cohort = evaluate_r0b_cohort()

    observed: dict[str, tuple[bool, str]] = {
        member.source_key: _observed_last_good(member.source_key, r1.trading_date)
        for member in cohort.members
        if member.source_key in CONFIRM_PATH_SOURCE_KEYS
    }
    amendment_flip = all(
        ok for ok, _ in observed.values()
    ) and set(observed) == CONFIRM_PATH_SOURCE_KEYS

    rows: list[R2BNamedSourceV1] = []
    authorized_count = 0
    may_confirm_count = 0
    for member in cohort.members:
        contract = compiled.get(member.source_key)
        named_current = observed.get(member.source_key, (False, ""))[0]
        authorize = (
            amendment_flip
            and named_current
            and member.source_key in CONFIRM_PATH_SOURCE_KEYS
            and member.confirm_eligible
            and member.proven
        )
        if authorize:
            authorized_count += 1
            may_confirm_count += 1
        rows.append(
            R2BNamedSourceV1(
                source_key=member.source_key,
                class_name=member.class_name,
                role=member.role,
                gate_permission=bool(contract.gate_permission) if contract else False,
                directional_permission=(
                    bool(contract.directional_permission) if contract else False
                ),
                r0b_reviewed=member.reviewed,
                r0b_proven=member.proven,
                r0b_can_vote=False,
                confirm_eligible=member.confirm_eligible,
                activation_status=(
                    "AUTHORIZED"
                    if authorize
                    else (
                        "WAIT_PROOF"
                        if member.confirm_eligible and member.proven
                        else "NOT_AUTHORIZED"
                    )
                ),
                may_support_confirmed=authorize,
                why_wait=() if authorize else _why(member),
            )
        )

    warnings = [
        "R2-B is the named activation ledger. It never turns on execution, quantity or broker access.",
    ]
    if amendment_flip:
        warnings.append(
            "Amendment 2026-08-25: all five named confirm-path sources have current official last-goods; S7 may seat PRF-003 EOD public CONFIRMED."
        )
    else:
        blockers = sorted(
            f"{key}:{code}" for key, (ok, code) in observed.items() if not ok
        )
        warnings.append(
            "sourceActivationReady stays false; missing current last-good for: "
            + (", ".join(blockers) if blockers else "none evaluated")
        )

    payload = {
        "r1BundleHash": r1.bundle_hash,
        "r2RunHash": r2.run_hash,
        "workbookSha256": compiler.workbook_sha256,
        "sourceActivationReady": amendment_flip,
        "warnings": tuple(warnings),
        "rows": [row.model_dump(mode="json", by_alias=True) for row in rows],
    }
    run_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    at = r2.built_at
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("decision_at must be timezone-aware")
    return R2BNamedActivationV1(
        run_id=stable_id("r2b-named-activation", r1.bundle_id, r2.run_id, run_hash),
        run_hash=run_hash,
        r1_bundle_id=r1.bundle_id,
        r1_bundle_hash=r1.bundle_hash,
        r2_run_id=r2.run_id,
        r2_run_hash=r2.run_hash,
        collector_run_id=r1.collector_run_id,
        permission_fingerprint=r1.permission_fingerprint,
        trading_date=r1.trading_date.isoformat()
        if hasattr(r1.trading_date, "isoformat")
        else str(r1.trading_date),
        decision_at=at,
        workbook_sha256=compiler.workbook_sha256,
        source_activation_ready=amendment_flip,
        compiler_gate_authorized_count=compiler.gate_authorized_source_key_count,
        r0b_proven_count=cohort.proven_count,
        r0b_reviewed_count=cohort.reviewed_count,
        authorized_count=authorized_count,
        may_confirm_count=may_confirm_count,
        named_source_count=len(rows),
        rows=tuple(rows),
        warnings=tuple(warnings),
    )


def persist_r2b_named_activation(value: R2BNamedActivationV1) -> R2BNamedActivationV1:
    stored = value.model_copy(update={"persisted": True})
    persist_selection_payload(
        run_id=stored.run_id,
        profile_id=PROFILE_ID,
        as_of=stored.decision_at,
        payload=stored.model_dump(mode="json", by_alias=True),
        candidates=tuple(
            (
                row.source_key,
                row.source_key,
                SelectionState.WAIT.value,
                row.model_dump(mode="json", by_alias=True),
            )
            for row in stored.rows
        ),
    )
    return stored


def latest_r2b_named_activation() -> R2BNamedActivationV1 | None:
    payload = latest_selection_payload(PROFILE_ID)
    return R2BNamedActivationV1.model_validate(payload) if payload is not None else None
