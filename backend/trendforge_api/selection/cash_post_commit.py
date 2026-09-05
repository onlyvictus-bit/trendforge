"""Idempotent post-commit bridge from market-data collection to A1-C1.

The collector remains authoritative for acquisition and last-good persistence.
This module only dispatches the already-built cash research stages after a
cash-relevant artifact is committed. Pipeline failure never rolls back source
collection and never changes activation or the WATCH/WAIT/REJECT ceiling.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from ..feature_registry import FEATURE_REGISTRY_VERSION
from ..market_data_service import NormalizedSourceResult
from ..market_data_store import ManifestStatus, MarketDataStore
from ..source_inventory_compiler import compile_default_inventory
from .cash_a1_staging import latest_cash_staging, persist_cash_staging, stage_cash_last_good
from .cash_a2_identity import (
    RestrictionAssessment,
    build_cash_identity_batch,
    latest_cash_identity,
    persist_cash_identity,
)
from .cash_a3_discovery import build_cash_discovery_batch, persist_cash_discovery
from .cash_a4_history import build_cash_history_batch, latest_cash_history, persist_cash_history
from .attention_order import build_attention_order, latest_attention_order, persist_attention_order
from .cash_c1_rank import build_cash_rank_batch, persist_cash_rank
from .fo_a6_enrichment import build_fo_enrichment_batch, persist_fo_enrichment
from .index_a5_context import build_cash_context_batch, latest_cash_context, persist_cash_context
from .inventory_source_bundle import (
    FRESHNESS_POLICY_VERSION,
    build_inventory_source_bundle,
    latest_inventory_source_bundle,
    persist_inventory_source_bundle,
)
from .r14_live import build_r14_ca_join, persist_r14_ca_join
from .r3_live import build_r3_resolution, persist_r3_resolution
from .r4_live import build_r4_identity_pin, persist_r4_identity_pin
from .r5_live import build_r5_structure_batch, persist_r5_structure_batch
from .r16_service import run_incremental as run_r16_incremental
from .r16_store import r16_schema_status
from .s8_service import build_and_persist_current_s8
from .mwpl_b import assess_mwpl, latest_mwpl, persist_mwpl
from .shadow_screener import run_shadow_screener
from .use_matrix_c0 import (
    build_source_use_matrix,
    latest_source_use_matrix,
    persist_source_use_matrix,
)


PIPELINE_CONTRACT = "trendforge.cashPostCommit.v1"
PIPELINE_VERSION = "a1-c1-r1-r2-r3-r4-r14-r5-s8-r16-orchestrator-9"
CASH_SOURCE = "nse_bhavcopy_eod"
BAN_SOURCE = "nse_fno_ban"
MWPL_SOURCE = "nse_mwpl_percentages"
INDEX_SOURCE = "nse_index_close_eod"
FO_SOURCE = "nse_fo_bhavcopy"
CA_SOURCE = "nse_corporate_filings_actions"
RELEVANT_SOURCE_KEYS = frozenset(
    {CASH_SOURCE, BAN_SOURCE, MWPL_SOURCE, INDEX_SOURCE, FO_SOURCE, CA_SOURCE}
)
SUCCESS_STATES = frozenset(
    {ManifestStatus.SUCCESS_NEW, ManifestStatus.SUCCESS_UNCHANGED}
)

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class CashPipelineStage(BaseModel):
    model_config = MODEL_CONFIG

    stage_id: str
    state: Literal["COMPLETED", "REUSED", "SKIPPED", "BLOCKED", "FAILED"]
    detail: str
    output_id: str | None = None


class CashPipelineExecution(BaseModel):
    model_config = MODEL_CONFIG

    stages: tuple[CashPipelineStage, ...]
    rank_batch_id: str | None = None
    r1_bundle_id: str | None = None
    r2_order_id: str | None = None
    r3_resolution_id: str | None = None
    r4_pin_id: str | None = None
    r14_join_id: str | None = None
    r5_structure_id: str | None = None
    s8_run_id: str | None = None
    r16_dataset_run_id: str | None = None
    permission_fingerprint: str | None = None


class CashPipelineRunContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    store: MarketDataStore
    collector_run_id: str
    trading_date: date
    results: dict[str, NormalizedSourceResult]
    trigger_source_keys: tuple[str, ...]
    fingerprint: str
    observed_at: datetime | None = None
    prior_permission_fingerprint: str | None = None
    ban_valid_empty: bool = False


class CashPipelineRun(BaseModel):
    model_config = MODEL_CONFIG

    run_id: str
    collector_run_id: str
    state: Literal["COMPLETED", "BLOCKED_INPUT", "FAILED_STAGE"]
    fingerprint: str
    trading_date: date
    trigger_source_keys: tuple[str, ...]
    started_at: datetime
    completed_at: datetime
    stages: tuple[CashPipelineStage, ...] = ()
    rank_batch_id: str | None = None
    r1_bundle_id: str | None = None
    r2_order_id: str | None = None
    r3_resolution_id: str | None = None
    r4_pin_id: str | None = None
    r14_join_id: str | None = None
    r5_structure_id: str | None = None
    s8_run_id: str | None = None
    r16_dataset_run_id: str | None = None
    permission_fingerprint: str | None = None
    error: str | None = None
    research_ceiling: str = "WATCH_WAIT_REJECT"
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    executable: bool = False


class CashPipelineDispatch(BaseModel):
    model_config = MODEL_CONFIG

    collector_run_id: str
    decision: Literal[
        "DISPATCHED", "SKIPPED_UNRELATED", "SKIPPED_DUPLICATE", "BLOCKED_INPUT"
    ]
    at: datetime
    trigger_source_keys: tuple[str, ...] = ()
    detail: str


class CashPipelineSnapshot(BaseModel):
    model_config = MODEL_CONFIG

    contract: str = PIPELINE_CONTRACT
    pipeline_version: str = PIPELINE_VERSION
    latest_dispatch: CashPipelineDispatch
    latest_run: CashPipelineRun | None = None
    updated_at: datetime


PipelineRunner = Callable[[CashPipelineRunContext], CashPipelineExecution]


def _aware_now() -> datetime:
    return datetime.now(UTC)


def _read_content(store: MarketDataStore, source_key: str, trading_date: date) -> bytes | None:
    latest = store.latest_for(source_key)
    if (
        latest is None
        or latest.status not in SUCCESS_STATES
        or not latest.content_hash
        or latest.data_date != trading_date
        or latest.normalized_row_count <= 0
    ):
        return None
    path = Path(latest.object_path) if latest.object_path else store.object_path_for_hash(
        latest.content_hash
    )
    if not path.is_file():
        return None
    return path.read_bytes()


def _permission_fingerprint() -> str:
    report = compile_default_inventory()
    directional_contracts = [
        {
            "sourceContractId": contract.source_contract_id,
            "datasetRootId": contract.dataset_root_id,
            "featureIds": list(contract.feature_ids),
            "independenceFamily": contract.independence_family,
            "authorityCap": contract.authority_cap,
            "allowedTimeframes": list(contract.allowed_timeframes),
            "allowedInstruments": list(contract.allowed_instruments),
            "directionalPermission": contract.directional_permission,
        }
        for contract in report.source_contracts
        if contract.feature_ids or contract.directional_permission
    ]
    payload = {
        "workbookSha256": report.workbook_sha256,
        "sourceMapReviewVersion": report.source_map_review_version,
        "livingSourceKeySha256": report.living_source_key_sha256,
        "normalizedSourceContractCount": report.normalized_source_contract_count,
        "gateAuthorizedSourceKeyCount": report.gate_authorized_source_key_count,
        "featureRegistryVersion": FEATURE_REGISTRY_VERSION,
        "directionalContracts": directional_contracts,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def run_existing_cash_pipeline(context: CashPipelineRunContext) -> CashPipelineExecution:
    """Run existing A1-C1 stages; this function does not implement another engine."""
    stages: list[CashPipelineStage] = []

    staging = persist_cash_staging(stage_cash_last_good(context.store))
    if not staging.source_result.ok or staging.row_count <= 0:
        raise ValueError("A1 did not produce structured non-empty cash facts")
    stages.append(
        CashPipelineStage(
            stage_id="A1",
            state="COMPLETED",
            detail=f"{staging.row_count} cash rows staged from saved last-good",
            output_id=staging.result_id,
        )
    )

    restriction = None
    if context.ban_valid_empty:
        result = context.results[BAN_SOURCE]
        restriction = RestrictionAssessment(
            source_id=BAN_SOURCE,
            proven=True,
            can_veto=True,
            state="READY",
            reason=(
                "Schema-valid current ban response is empty. No symbols are banned; "
                "this is eligibility only and not a supporting family."
            ),
            data_date=result.data_date.isoformat() if result.data_date else None,
            artifact_hash=result.normalized_content_hash,
            symbols=(),
        )
    identity = persist_cash_identity(
        build_cash_identity_batch(staging, store=context.store, restriction=restriction)
    )
    stages.append(
        CashPipelineStage(
            stage_id="A2",
            state="COMPLETED",
            detail=f"{identity.fact_count} identity facts; restriction={identity.restriction.state}",
            output_id=identity.batch_id,
        )
    )

    discovery = persist_cash_discovery(build_cash_discovery_batch(identity))
    stages.append(
        CashPipelineStage(
            stage_id="A3",
            state="COMPLETED",
            detail=f"{discovery.watch_count} WATCH rows from cash discovery",
            output_id=discovery.batch_id,
        )
    )

    history = persist_cash_history(build_cash_history_batch(identity))
    stages.append(
        CashPipelineStage(
            stage_id="A4",
            state="COMPLETED",
            detail=f"{history.raw_bar_count} immutable raw bars available",
            output_id=history.batch_id,
        )
    )

    index_content = _read_content(context.store, INDEX_SOURCE, context.trading_date)
    cash_context = persist_cash_context(
        build_cash_context_batch(
            index_content=index_content, discovery=discovery, history=history
        )
    )
    stages.append(
        CashPipelineStage(
            stage_id="A5",
            state="COMPLETED" if index_content else "SKIPPED",
            detail=(
                "Current index context applied; context cannot confirm a stock"
                if index_content
                else "Current index artifact unavailable; stock state unchanged"
            ),
            output_id=cash_context.batch_id,
        )
    )

    fo_content = _read_content(context.store, FO_SOURCE, context.trading_date)
    fo = persist_fo_enrichment(
        build_fo_enrichment_batch(fo_content=fo_content, discovery=discovery)
    )
    stages.append(
        CashPipelineStage(
            stage_id="A6",
            state="COMPLETED" if fo_content else "SKIPPED",
            detail=(
                "Current futures rows applied to WATCH shortlist only"
                if fo_content
                else "Current F&O artifact unavailable; cash names were not penalized"
            ),
            output_id=fo.batch_id,
        )
    )

    permission_fp = _permission_fingerprint()
    matrix = latest_source_use_matrix()
    if matrix is None or permission_fp != context.prior_permission_fingerprint:
        matrix = persist_source_use_matrix(build_source_use_matrix())
        c0_state = "COMPLETED"
        c0_detail = "Compiler/contracts changed or no matrix existed; permissions rebuilt"
    else:
        c0_state = "REUSED"
        c0_detail = "Existing compiler permission matrix reused"
    stages.append(
        CashPipelineStage(
            stage_id="C0",
            state=c0_state,
            detail=c0_detail,
            output_id=matrix.matrix_id,
        )
    )

    mwpl = latest_mwpl() or assess_mwpl(None)
    mwpl_result = context.results.get(MWPL_SOURCE)
    mwpl_content = (
        _read_content(context.store, MWPL_SOURCE, context.trading_date)
        if mwpl_result is not None and mwpl_result.status is ManifestStatus.SUCCESS_NEW
        else None
    )
    if mwpl_content:
        mwpl = persist_mwpl(assess_mwpl(mwpl_content))
        b_state = "COMPLETED"
        b_detail = f"New official MWPL artifact assessed: {mwpl.state}"
    else:
        b_state = "REUSED" if mwpl.persisted else "SKIPPED"
        b_detail = f"No newly proven MWPL artifact; retained {mwpl.state}"
    stages.append(CashPipelineStage(stage_id="B", state=b_state, detail=b_detail))

    rank = persist_cash_rank(build_cash_rank_batch(discovery=discovery, mwpl=mwpl))
    stages.append(
        CashPipelineStage(
            stage_id="C1",
            state="COMPLETED",
            detail=(
                f"{rank.row_count} research rows; ceiling={rank.acceptance_ceiling}; "
                f"can_rank={str(rank.can_rank_cash).lower()}"
            ),
            output_id=rank.batch_id,
        )
    )
    r1_bundle = persist_inventory_source_bundle(
        build_inventory_source_bundle(
            store=context.store,
            collector_run_id=context.collector_run_id,
            cash_pipeline_run_id=f"cash-{context.collector_run_id}",
            cash_pipeline_fingerprint=context.fingerprint,
            permission_fingerprint=permission_fp,
            snapshot_bundle_id=context.fingerprint,
            trading_date=context.trading_date,
            results=context.results,
            discovery=discovery,
            rank=rank,
            stage_states={stage.stage_id: stage.state for stage in stages},
            built_at=context.observed_at,
        )
    )
    stages.append(
        CashPipelineStage(
            stage_id="R1",
            state="COMPLETED",
            detail=(
                f"{r1_bundle.source_contract_count} source dispositions and "
                f"{r1_bundle.stock_record_count} stock evidence rows persisted"
            ),
            output_id=r1_bundle.bundle_id,
        )
    )
    shadow = run_shadow_screener(r1_bundle)
    r2_order = persist_attention_order(
        build_attention_order(
            r1_bundle,
            expected_permission_fingerprint=permission_fp,
            shadow_comparison=shadow.model_dump(mode="json", by_alias=True),
        )
    )
    stages.append(
        CashPipelineStage(
            stage_id="R2",
            state="COMPLETED",
            detail=(
                f"{r2_order.universe_count} deterministic research rows; "
                f"shadow={shadow.status}; ceiling={r2_order.acceptance_ceiling}"
            ),
            output_id=r2_order.run_id,
        )
    )
    r3_resolution_id = None
    try:
        compiler = compile_default_inventory()
        r3_resolution = persist_r3_resolution(
            build_r3_resolution(
                bundle=r1_bundle,
                attention=r2_order,
                source_result=staging.source_result,
                identity=identity,
                compiled_source_contracts=compiler.source_contracts,
                expected_permission_fingerprint=permission_fp,
            )
        )
        r3_resolution_id = r3_resolution.run_id
        stages.append(
            CashPipelineStage(
                stage_id="R3",
                state="COMPLETED",
                detail=(
                    f"{len(r3_resolution.rows)} fail-closed evidence resolutions; "
                    f"ceiling={r3_resolution.state_ceiling.value}"
                ),
                output_id=r3_resolution.run_id,
            )
        )
    except Exception as exc:
        stages.append(
            CashPipelineStage(
                stage_id="R3",
                state="FAILED",
                detail=f"{type(exc).__name__}: {exc}",
            )
        )

    r4_pin = None
    r4_pin_id = None
    try:
        r4_pin = build_r4_identity_pin(
            bundle=r1_bundle,
            attention=r2_order,
            identity=identity,
        )
        r4_pin_id = persist_r4_identity_pin(r4_pin).run_id
        stages.append(
            CashPipelineStage(
                stage_id="R4",
                state="COMPLETED",
                detail=(
                    f"{r4_pin.universe_count} ID pins; "
                    f"unknown={r4_pin.unknown_id_count}; "
                    f"pkVote=false; ceiling={r4_pin.acceptance_ceiling}"
                ),
                output_id=r4_pin.run_id,
            )
        )
    except Exception as exc:
        stages.append(
            CashPipelineStage(
                stage_id="R4",
                state="FAILED",
                detail=f"{type(exc).__name__}: {exc}",
            )
        )

    r14_join = None
    r14_join_id = None
    try:
        r14_join = persist_r14_ca_join(
            build_r14_ca_join(
                bundle=r1_bundle,
                attention=r2_order,
                identity=identity,
                pin=r4_pin,
            )
        )
        r14_join_id = r14_join.run_id
        stages.append(
            CashPipelineStage(
                stage_id="R14",
                state="COMPLETED",
                detail=(
                    f"{r14_join.joined_count} CA joins; "
                    f"waitCa={r14_join.wait_ca_count}; "
                    f"conflict={r14_join.conflict_count}; "
                    f"ceiling={r14_join.acceptance_ceiling}"
                ),
                output_id=r14_join.run_id,
            )
        )
    except Exception as exc:
        stages.append(
            CashPipelineStage(
                stage_id="R14",
                state="FAILED",
                detail=f"{type(exc).__name__}: {exc}",
            )
        )

    r5_structure = None
    r5_structure_id = None
    if r14_join is None:
        stages.append(
            CashPipelineStage(
                stage_id="R5",
                state="BLOCKED",
                detail=(
                    "WAIT_R14_JOIN_NOT_READY: R5 structure requires a completed "
                    "hash-matched R14 CA join; raw vintages are not CA authority"
                ),
            )
        )
    else:
        try:
            r5_structure = persist_r5_structure_batch(
                build_r5_structure_batch(
                    bundle=r1_bundle,
                    attention=r2_order,
                    identity=identity,
                    history=history,
                    staging=staging,
                    context=cash_context,
                    ca_join=r14_join,
                )
            )
            r5_structure_id = r5_structure.run_id
            stages.append(
                CashPipelineStage(
                    stage_id="R5",
                    state="COMPLETED",
                    detail=(
                        f"{r5_structure.universe_count} adjusted closed-bar rows; "
                        f"ceiling={r5_structure.acceptance_ceiling}"
                    ),
                    output_id=r5_structure.run_id,
                )
            )
        except Exception as exc:
            stages.append(
                CashPipelineStage(
                    stage_id="R5",
                    state="FAILED",
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )

    s8_run_id = None
    if r5_structure is None:
        stages.append(
            CashPipelineStage(
                stage_id="S8",
                state="BLOCKED",
                detail="WAIT_R5_NOT_READY: S8 requires completed current R5 structure",
            )
        )
    else:
        try:
            s8 = build_and_persist_current_s8(
                r5_batch=r5_structure,
                discovery=discovery,
                attention=r2_order,
                built_at=context.observed_at,
            )
            s8_run_id = s8.run_id
            stages.append(
                CashPipelineStage(
                    stage_id="S8",
                    state="COMPLETED",
                    detail=(
                        f"{len(s8.rows)} current research rows persisted; "
                        f"ceiling={s8.acceptance_ceiling}"
                    ),
                    output_id=s8.run_id,
                )
            )
        except Exception as exc:
            stages.append(
                CashPipelineStage(
                    stage_id="S8",
                    state="FAILED",
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
    r16_dataset_run_id = None
    if s8_run_id is None:
        stages.append(
            CashPipelineStage(
                stage_id="R16",
                state="BLOCKED",
                detail="WAIT_S8_NOT_READY: R16 requires a persisted current S8 run",
            )
        )
    elif not r16_schema_status()["applied"]:
        stages.append(
            CashPipelineStage(
                stage_id="R16",
                state="BLOCKED",
                detail="WAIT_R16_SCHEMA_NOT_APPLIED: explicit local migration approval is required",
            )
        )
    else:
        try:
            r16 = run_r16_incremental(mode="incremental")
            dataset = r16.get("dataset") or {}
            r16_dataset_run_id = dataset.get("runId")
            replay = r16.get("replay") or {}
            stages.append(
                CashPipelineStage(
                    stage_id="R16",
                    state="COMPLETED",
                    detail=(
                        f"{replay.get('hypothesisCount', 0)} frozen hypotheses; "
                        f"{replay.get('observationsAppended', 0)} labels appended; "
                        "trade authority remains false"
                    ),
                    output_id=r16_dataset_run_id,
                )
            )
        except Exception as exc:
            stages.append(
                CashPipelineStage(
                    stage_id="R16",
                    state="FAILED",
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )

    return CashPipelineExecution(
        stages=tuple(stages),
        rank_batch_id=rank.batch_id,
        r1_bundle_id=r1_bundle.bundle_id,
        r2_order_id=r2_order.run_id,
        r3_resolution_id=r3_resolution_id,
        r4_pin_id=r4_pin_id,
        r14_join_id=r14_join_id,
        r5_structure_id=r5_structure_id,
        s8_run_id=s8_run_id,
        r16_dataset_run_id=r16_dataset_run_id,
        permission_fingerprint=permission_fp,
    )


class CashPostCommitOrchestrator:
    def __init__(
        self,
        *,
        store: MarketDataStore,
        state_path: Path | None = None,
        runner: PipelineRunner = run_existing_cash_pipeline,
    ) -> None:
        self.store = store
        self.state_path = state_path or store.root / "operations" / "cash-pipeline.json"
        self.runner = runner

    def snapshot(self) -> CashPipelineSnapshot | None:
        if not self.state_path.is_file():
            return None
        try:
            return CashPipelineSnapshot.model_validate_json(
                self.state_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return None

    def _write(self, snapshot: CashPipelineSnapshot) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = snapshot.model_dump_json(by_alias=True, indent=2)
        temporary = self.state_path.with_name(f".{self.state_path.name}.tmp")
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, self.state_path)

    def _save_dispatch(
        self,
        *,
        collector_run_id: str,
        decision: str,
        triggers: tuple[str, ...],
        detail: str,
        latest_run: CashPipelineRun | None,
    ) -> CashPipelineSnapshot:
        now = _aware_now()
        snapshot = CashPipelineSnapshot(
            latest_dispatch=CashPipelineDispatch(
                collector_run_id=collector_run_id,
                decision=decision,
                at=now,
                trigger_source_keys=triggers,
                detail=detail,
            ),
            latest_run=latest_run,
            updated_at=now,
        )
        self._write(snapshot)
        return snapshot

    def _input_fingerprint(
        self,
        *,
        trading_date: date,
        results: Mapping[str, NormalizedSourceResult],
    ) -> str:
        latest = self.store.latest_all()
        sources: dict[str, Any] = {}
        for key in sorted(RELEVANT_SOURCE_KEYS):
            item = latest.get(key)
            current = results.get(key)
            sources[key] = {
                "contentHash": item.content_hash if item else None,
                "dataDate": item.data_date.isoformat() if item and item.data_date else None,
                "rowCount": item.normalized_row_count if item else 0,
                "observedStatus": current.status.value if current else None,
                "observedHash": current.normalized_content_hash if current else None,
            }
        payload = {
            "pipelineVersion": PIPELINE_VERSION,
            "freshnessPolicyVersion": FRESHNESS_POLICY_VERSION,
            "tradingDate": trading_date.isoformat(),
            "sources": sources,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def process(
        self,
        *,
        collector_run_id: str,
        trading_date: date,
        results: Mapping[str, NormalizedSourceResult],
    ) -> CashPipelineSnapshot:
        previous = self.snapshot()
        previous_run = previous.latest_run if previous else None
        triggers = tuple(
            sorted(
                key
                for key, result in results.items()
                if key in RELEVANT_SOURCE_KEYS
                and (
                    result.status in SUCCESS_STATES
                    or (key == BAN_SOURCE and result.status is ManifestStatus.VALID_EMPTY)
                )
            )
        )
        relevant_attempted = tuple(sorted(set(results).intersection(RELEVANT_SOURCE_KEYS)))
        if not relevant_attempted:
            return self._save_dispatch(
                collector_run_id=collector_run_id,
                decision="SKIPPED_UNRELATED",
                triggers=(),
                detail="No cash-relevant source was attempted; existing cash run was retained",
                latest_run=previous_run,
            )

        cash_attempt = results.get(CASH_SOURCE)
        latest_cash = self.store.latest_for(CASH_SOURCE)
        cash_current = (
            latest_cash is not None
            and latest_cash.status in SUCCESS_STATES
            and latest_cash.content_hash is not None
            and latest_cash.object_path is not None
            and latest_cash.data_date == trading_date
            and latest_cash.normalized_row_count > 0
        )
        cash_attempt_failed = cash_attempt is not None and cash_attempt.status not in SUCCESS_STATES
        if not triggers or not cash_current or cash_attempt_failed:
            now = _aware_now()
            fingerprint = self._input_fingerprint(
                trading_date=trading_date, results=results
            )
            run = CashPipelineRun(
                run_id=f"cash-{collector_run_id}",
                collector_run_id=collector_run_id,
                state="BLOCKED_INPUT",
                fingerprint=fingerprint,
                trading_date=trading_date,
                trigger_source_keys=triggers,
                started_at=now,
                completed_at=now,
                error=(
                    "No saved current cash last-good with structured non-empty rows; "
                    "HTTP status or an older object cannot start A1-C1."
                ),
            )
            return self._save_dispatch(
                collector_run_id=collector_run_id,
                decision="BLOCKED_INPUT",
                triggers=triggers,
                detail=run.error or "Required cash input blocked",
                latest_run=run,
            )

        fingerprint = self._input_fingerprint(trading_date=trading_date, results=results)
        previous_r1_r2_complete = (
            previous_run is not None
            and previous_run.state == "COMPLETED"
            and previous_run.r1_bundle_id is not None
            and previous_run.r2_order_id is not None
        )
        if (
            previous_run is not None
            and previous_run.fingerprint == fingerprint
            and previous_r1_r2_complete
            and previous_run.r3_resolution_id is None
        ):
            try:
                bundle = latest_inventory_source_bundle()
                attention = latest_attention_order()
                staging = latest_cash_staging()
                identity = latest_cash_identity()
                if (
                    bundle is None
                    or attention is None
                    or staging is None
                    or identity is None
                    or bundle.bundle_id != previous_run.r1_bundle_id
                    or attention.run_id != previous_run.r2_order_id
                    or attention.r1_bundle_id != bundle.bundle_id
                    or staging.result_id != identity.staging_result_id
                    or bundle.cash_pipeline_fingerprint != fingerprint
                ):
                    raise ValueError("Stored R1/R2/A1/A2 lineage is incomplete or mismatched")
                resolution = persist_r3_resolution(
                    build_r3_resolution(
                        bundle=bundle,
                        attention=attention,
                        source_result=staging.source_result,
                        identity=identity,
                        compiled_source_contracts=compile_default_inventory().source_contracts,
                        expected_permission_fingerprint=_permission_fingerprint(),
                    )
                )
                recovered_run = previous_run.model_copy(
                    update={
                        "completed_at": _aware_now(),
                        "stages": previous_run.stages
                        + (
                            CashPipelineStage(
                                stage_id="R3",
                                state="COMPLETED",
                                detail=(
                                    f"Recovered {len(resolution.rows)} R3 resolutions "
                                    "without rebuilding R1/R2"
                                ),
                                output_id=resolution.run_id,
                            ),
                        ),
                        "r3_resolution_id": resolution.run_id,
                    }
                )
                return self._save_dispatch(
                    collector_run_id=collector_run_id,
                    decision="DISPATCHED",
                    triggers=triggers,
                    detail="Recovered missing R3 from immutable stored R1/R2 outputs",
                    latest_run=recovered_run,
                )
            except Exception as exc:
                failed_run = previous_run.model_copy(
                    update={
                        "completed_at": _aware_now(),
                        "stages": previous_run.stages
                        + (
                            CashPipelineStage(
                                stage_id="R3",
                                state="FAILED",
                                detail=f"Recovery failed: {type(exc).__name__}: {exc}",
                            ),
                        ),
                    }
                )
                return self._save_dispatch(
                    collector_run_id=collector_run_id,
                    decision="DISPATCHED",
                    triggers=triggers,
                    detail="R3 recovery failed closed; immutable R1/R2 outputs were retained",
                    latest_run=failed_run,
                )

        previous_outputs_complete = (
            previous_r1_r2_complete
            and previous_run is not None
            and previous_run.r3_resolution_id is not None
            and previous_run.r4_pin_id is not None
            and previous_run.r14_join_id is not None
            and previous_run.r5_structure_id is not None
            and previous_run.s8_run_id is not None
            and (
                previous_run.r16_dataset_run_id is not None
                or any(
                    stage.stage_id == "R16" and stage.state == "BLOCKED"
                    for stage in previous_run.stages
                )
            )
        )
        if (
            previous_run is not None
            and previous_run.fingerprint == fingerprint
            and previous_outputs_complete
        ):
            return self._save_dispatch(
                collector_run_id=collector_run_id,
                decision="SKIPPED_DUPLICATE",
                triggers=triggers,
                detail=(
                    "Identical artifact fingerprint already has complete "
                    "R1/R2/R3/R4/R14/R5/S8/R16 outputs or an explicit R16 schema block"
                ),
                latest_run=previous_run,
            )

        started = _aware_now()
        try:
            execution = self.runner(
                CashPipelineRunContext(
                    store=self.store,
                    collector_run_id=collector_run_id,
                    trading_date=trading_date,
                    results=dict(results),
                    trigger_source_keys=triggers,
                    fingerprint=fingerprint,
                    prior_permission_fingerprint=(
                        previous_run.permission_fingerprint if previous_run else None
                    ),
                    ban_valid_empty=(
                        results.get(BAN_SOURCE) is not None
                        and results[BAN_SOURCE].status is ManifestStatus.VALID_EMPTY
                    ),
                )
            )
            run = CashPipelineRun(
                run_id=f"cash-{collector_run_id}",
                collector_run_id=collector_run_id,
                state="COMPLETED",
                fingerprint=fingerprint,
                trading_date=trading_date,
                trigger_source_keys=triggers,
                started_at=started,
                completed_at=_aware_now(),
                stages=execution.stages,
                rank_batch_id=execution.rank_batch_id,
                r1_bundle_id=execution.r1_bundle_id,
                r2_order_id=execution.r2_order_id,
                r3_resolution_id=execution.r3_resolution_id,
                r4_pin_id=execution.r4_pin_id,
                r14_join_id=execution.r14_join_id,
                r5_structure_id=execution.r5_structure_id,
                s8_run_id=execution.s8_run_id,
                r16_dataset_run_id=execution.r16_dataset_run_id,
                permission_fingerprint=execution.permission_fingerprint,
            )
        except Exception as exc:
            run = CashPipelineRun(
                run_id=f"cash-{collector_run_id}",
                collector_run_id=collector_run_id,
                state="FAILED_STAGE",
                fingerprint=fingerprint,
                trading_date=trading_date,
                trigger_source_keys=triggers,
                started_at=started,
                completed_at=_aware_now(),
                stages=(
                    CashPipelineStage(
                        stage_id="ORCHESTRATOR",
                        state="FAILED",
                        detail=f"{type(exc).__name__}: {exc}",
                    ),
                ),
                permission_fingerprint=(
                    previous_run.permission_fingerprint if previous_run else None
                ),
                error=f"{type(exc).__name__}: {exc}",
            )
        return self._save_dispatch(
            collector_run_id=collector_run_id,
            decision="DISPATCHED",
            triggers=triggers,
            detail=f"Cash pipeline finished with {run.state}; collector result was retained",
            latest_run=run,
        )
