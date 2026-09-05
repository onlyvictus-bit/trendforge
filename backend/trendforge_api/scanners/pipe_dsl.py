"""File A R10 pipe DSL (PK5) — FUS-010 non-voting composition.

Named, versioned filter recipes over the R8 native-core match set:

    UNION / INTERSECTION  -> candidate membership from scanner match sets
    FILTER_STATE          -> keep survivors whose joined S7 state is listed
    ENRICH_S7             -> attach publicState + guidanceMatch; NEVER filters

FUS-010 law enforced here: a pipe contributes ZERO evidence claims — the
output carries symbols and counts only; component claims stay owned by
R5/R8/S6 and pass through FUS-009 untouched. An invalid stage fails the whole
run (PIPE_INVALID_STAGE). Stage in/out counts are deterministic; correlated
twins can never inflate counts because stages count symbols.

File A names `pk_pipe_dsl.py`; that name stays reserved for the PK shadow
harness. This LIVE module is `scanners/pipe_dsl.py` (D-055 mapping); PK may
import it later.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .native_core import NativeCoreRunV1, build_native_core_run
from .registry import SCANNER_ENGINE

SCHEMA_VERSION = "trendforge.pipe-run.v1"
PROFILE_ID = "PRF-R10-PIPES"
PROFILE_VERSION = "1.0.0"
ACCEPTANCE_CEILING = "LIVE_R10_ZERO_CLAIM_COMPOSITION"
GUIDANCE_COPY = "Pipes - guidance lens, zero claims."
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

StageOp = Literal["UNION", "INTERSECTION", "FILTER_STATE", "ENRICH_S7"]
StateName = Literal["WATCH", "WAIT", "REJECT"]
_REASON_CAP = 8


def _stages_json(stages: tuple[dict[str, Any], ...]) -> str:
    return json.dumps(list(stages), sort_keys=True, separators=(",", ":"))


def _parameter_hash(stages: tuple[dict[str, Any], ...]) -> str:
    return hashlib.sha256(_stages_json(stages).encode("utf-8")).hexdigest()


class PipeDefinitionV1(BaseModel):
    model_config = MODEL_CONFIG

    pipe_id: str = Field(min_length=1)
    version: Literal["v1"] = "v1"
    engine: str = SCANNER_ENGINE
    stages_json: str = Field(alias="stagesJson")
    parameter_hash: str = Field(alias="parameterHash")
    emits_claims: Literal[False] = False

    @model_validator(mode="after")
    def hash_matches_stages(self) -> "PipeDefinitionV1":
        digest = hashlib.sha256(self.stages_json.encode("utf-8")).hexdigest()
        if digest != self.parameter_hash:
            raise ValueError("parameterHash does not match stagesJson")
        return self


_SEED_STAGES: dict[str, tuple[dict[str, Any], ...]] = {
    "pipe.breakout_watch.v1": (
        {"op": "UNION", "scanners": ["native.breakout.v1"]},
        {"op": "FILTER_STATE", "states": ["WATCH"]},
        {"op": "ENRICH_S7"},
    ),
    "pipe.thrust_participation.v1": (
        {
            "op": "UNION",
            "scanners": ["native.rvol.v1", "native.volume_thrust.v1"],
        },
        {"op": "FILTER_STATE", "states": ["WATCH", "WAIT"]},
        {"op": "ENRICH_S7"},
    ),
}

PIPE_IDS: tuple[str, ...] = tuple(_SEED_STAGES)


def pipe_definition(pipe_id: str) -> PipeDefinitionV1:
    stages = _SEED_STAGES.get(pipe_id)
    if stages is None:
        raise ValueError("PIPE_UNKNOWN_ID")
    return PipeDefinitionV1(
        pipeId=pipe_id,
        stagesJson=_stages_json(stages),
        parameterHash=_parameter_hash(stages),
    )


PIPE_DEFINITIONS: tuple[PipeDefinitionV1, ...] = tuple(
    pipe_definition(pipe_id) for pipe_id in PIPE_IDS
)


class PipeStageResultV1(BaseModel):
    model_config = MODEL_CONFIG

    op: str
    in_count: int = Field(default=0, ge=0)
    out_count: int = Field(default=0, ge=0)
    reasons: tuple[str, ...] = ()
    survivors_unchanged: bool = False


class PipeSymbolResultV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    public_state: str | None = None
    guidance_match: bool | None = None


class PipeRunV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    engine: str = SCANNER_ENGINE
    pipe_id: str
    version: Literal["v1"] = "v1"
    parameter_hash: str
    run_id: str
    run_hash: str
    native_core_run_hash: str
    s7_run_hash: str | None = None
    trading_date: str
    built_at: datetime
    stages: tuple[PipeStageResultV1, ...]
    rows: tuple[PipeSymbolResultV1, ...]
    out_count: int = Field(default=0, ge=0)
    confirmed_count: int = 0
    executable: Literal[False] = False
    can_unlock_confirmed: Literal[False] = False
    emits_claims: Literal[False] = False
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def enforce_pipe_law(self) -> "PipeRunV1":
        if self.confirmed_count != 0:
            raise ValueError("R10 pipes confirmedCount is pinned to zero")
        if self.out_count != len(self.rows):
            raise ValueError("pipe outCount does not match rows")
        return self


def _validate_stage_shape(stage: dict[str, Any], *, first: bool) -> None:
    op = stage.get("op")
    scanners = stage.get("scanners") or ()
    states = stage.get("states") or ()
    if first and op not in ("UNION", "INTERSECTION"):
        raise ValueError("PIPE_INVALID_STAGE: first stage must be UNION or INTERSECTION")
    if op not in ("UNION", "INTERSECTION", "FILTER_STATE", "ENRICH_S7"):
        raise ValueError(f"PIPE_INVALID_STAGE: unknown op {op!r}")
    if op in ("UNION", "INTERSECTION"):
        from .registry import NATIVE_CORE_IDS

        known = set(NATIVE_CORE_IDS)
        if not scanners:
            raise ValueError("PIPE_INVALID_STAGE: scanner stage needs scanners[]")
        for scanner_id in scanners:
            if scanner_id not in known:
                raise ValueError(
                    f"PIPE_INVALID_STAGE: unknown scanner {scanner_id!r}"
                )
    elif op == "FILTER_STATE":
        allowed = {"WATCH", "WAIT", "REJECT"}
        if not states or any(state not in allowed for state in states):
            raise ValueError("PIPE_INVALID_STAGE: FILTER_STATE needs valid states[]")


def evaluate_stages(
    stages: tuple[dict[str, Any], ...],
    *,
    native_core: NativeCoreRunV1,
    s7_board: Any | None,
) -> tuple[tuple[PipeStageResultV1, ...], tuple[PipeSymbolResultV1, ...]]:
    """Deterministic FUS-010 evaluation. Invalid stage fails the whole run."""
    order = [row.symbol for row in native_core.rows]
    matched_by_symbol = {
        row.symbol: frozenset(row.matched_ids) for row in native_core.rows
    }
    guidance_by_symbol = {
        row.symbol: bool(row.guidance_match) for row in native_core.rows
    }
    state_by_symbol: dict[str, str] = {}
    enrich_allowed = True
    if s7_board is not None:
        state_by_symbol = {
            row.symbol: row.public_state.value for row in s7_board.rows
        }

    survivors: list[str] = list(order)
    results: list[PipeStageResultV1] = []

    for index, stage in enumerate(stages):
        _validate_stage_shape(stage, first=(index == 0))
        op = stage["op"]
        before = len(survivors)

        if op == "UNION":
            wanted = set(stage.get("scanners") or ())
            keep = [
                s for s in order
                if s in set(survivors) or (matched_by_symbol[s] & wanted)
            ]
            survivors = keep
            reasons = sorted(
                f"SCANNER_NOT_MATCHED:{sid}"
                for sid in sorted(wanted)
                if not any(sid in matched_by_symbol[s] for s in survivors)
            )
        elif op == "INTERSECTION":
            wanted = set(stage.get("scanners") or ())
            survivors = [
                s for s in survivors if wanted <= matched_by_symbol[s]
            ]
            reasons = sorted(
                f"SCANNER_NOT_MATCHED:{sid}" for sid in sorted(wanted)
                if not any(sid in matched_by_symbol[s] for s in survivors)
            )
        elif op == "FILTER_STATE":
            if s7_board is None:
                raise ValueError("WAIT_R10_S7_NOT_READY")
            allowed = set(stage.get("states") or ())
            survivors = [s for s in survivors if state_by_symbol.get(s) in allowed]
            reasons = ()
        else:  # ENRICH_S7
            # Enrichment attaches nothing when no board exists; never filters.
            reasons = ()

        stage_out = PipeStageResultV1(
            op=str(op),
            inCount=before,
            outCount=len(survivors),
            reasons=tuple(reasons[:_REASON_CAP]),
            survivorsUnchanged=len(survivors) == before,
        )
        results.append(stage_out)

    rows = tuple(
        PipeSymbolResultV1(
            symbol=symbol,
            publicState=(
                state_by_symbol.get(symbol)
                if s7_board is not None and enrich_allowed
                else None
            ),
            guidanceMatch=guidance_by_symbol.get(symbol),
        )
        for symbol in survivors
    )
    return tuple(results), rows


def build_pipe_run(
    pipe_id: str,
    *,
    native_core: NativeCoreRunV1 | None = None,
    s7_board: Any | None = None,
    stages_override: tuple[dict[str, Any], ...] | None = None,
) -> PipeRunV1:
    """Build one deterministic pipe run over the given lineage.

    ENRICH_S7 tolerates an absent S7 board (attaches nothing, never filters);
    FILTER_STATE without a board fails closed (WAIT_R10_S7_NOT_READY).
    """
    definition = pipe_definition(pipe_id)  # raises PIPE_UNKNOWN_ID
    nc = native_core if native_core is not None else build_native_core_run()
    stages = (
        stages_override
        if stages_override is not None
        else _SEED_STAGES.get(pipe_id, ())
    )

    stage_results, rows = evaluate_stages(
        tuple(stages), native_core=nc, s7_board=s7_board
    )

    identity_payload = {
        "pipeId": pipe_id,
        "parameterHash": definition.parameter_hash,
        "nativeCoreRunHash": nc.run_hash,
        "s7RunHash": getattr(s7_board, "run_hash", None),
        "stages": json.loads(definition.stages_json)
        if stages_override is None
        else list(stages),
    }
    run_hash = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    from ..selection.contracts import stable_id

    return PipeRunV1(
        pipeId=pipe_id,
        runId=stable_id("pipe-run", nc.run_id, run_hash),
        runHash=run_hash,
        parameterHash=definition.parameter_hash,
        nativeCoreRunHash=nc.run_hash,
        s7RunHash=getattr(s7_board, "run_hash", None),
        tradingDate=nc.trading_date,
        builtAt=nc.built_at,
        stages=stage_results,
        rows=rows,
        outCount=len(rows),
        warnings=(
            GUIDANCE_COPY,
            "Pipes emit zero evidence claims; component claims stay in R5/R8/S6.",
            "Invalid stage fails the whole pipe run.",
        ),
    )


__all__ = [
    "ACCEPTANCE_CEILING",
    "GUIDANCE_COPY",
    "PIPE_DEFINITIONS",
    "PIPE_IDS",
    "PipeDefinitionV1",
    "PipeRunV1",
    "PipeStageResultV1",
    "PipeSymbolResultV1",
    "build_pipe_run",
    "evaluate_stages",
    "pipe_definition",
]
