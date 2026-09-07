"""One read-only research bundle; never call the legacy build-on-GET routes."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .. import storage
from ..fii_stock_signals import CanonicalLatestResultLoader
from ..hybrid_v2.pipeline import build_hybrid_v2_overlay
from ..macro_event_context import latest_macro_event_context_snapshot
from ..openalgo_shadow import disabled_shadow_batch
from ..read_snapshot import SnapshotExpired, read_snapshot
from ..scanners.pipe_dsl import PIPE_DEFINITIONS, build_pipe_run
from ..scanners.registry import NATIVE_CORE_DEFINITIONS
from .attention_order import latest_attention_order
from .cash_a1_staging import default_market_data_store
from .cash_a3_discovery import latest_cash_discovery
from .inventory_source_bundle import latest_inventory_source_bundle
from .evidence_radar import build_evidence_radar
from .r2b_live import build_r2b_named_activation, latest_r2b_named_activation
from .r4_live import latest_r4_identity_pin
from .r5_live import latest_r5_structure_batch
from .r6_live import build_r6_enrichment
from .r11_mcx_live import build_mcx_master
from .r14_live import latest_r14_ca_join
from .r16_service import metrics_payload, status_payload
from .research_quantity import ResearchQtyBatchV1, ResearchQtyRowV1, compute_research_quantity
from .s3_cheap_discovery import build_s3_cheap_discovery, build_s3_watch_queue
from .s7_state_gates import S7StateBatchV1
from .s8_service import assemble_current_scan
from .s4s5_compare import build_s4s5_compare
from .top10_research import build_top10_research

SCHEMA_VERSION = "trendforge.research-snapshot.v1"
PANEL_KEYS = (
    "attention", "evidence", "structure", "identityPin", "caJoin", "overlay",
    "namedActivation", "s3Watch", "s4Pack", "s5Enrich", "s6Resolve", "s7State",
    "s8Latest", "dataLane", "researchQty", "r16Status", "r16Metrics",
    "nativeCore", "pipeDefs", "mcxMaster", "labBundle", "openalgoShadow",
    "marketWeather", "top10Research", "evidenceRadar", "s4s5Compare",
)
_LOG = logging.getLogger(__name__)
_MODEL = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True, extra="forbid")
PanelScope = Literal["RESEARCH", "CONTEXT", "CONTROL_OBSERVATION", "VALIDATION"]


class PanelStatusV1(BaseModel):
    model_config = _MODEL
    state: Literal["READY", "UNAVAILABLE"]
    code: str | None = None
    scope: PanelScope = "RESEARCH"


class ResearchSnapshotV1(BaseModel):
    model_config = _MODEL
    schema_version: Literal["trendforge.research-snapshot.v1"] = "trendforge.research-snapshot.v1"
    snapshot_id: str
    snapshot_hash: str
    captured_at: datetime
    decision_at: datetime
    evaluated_at: datetime
    coherence: Literal["SQLITE_READ_TRANSACTION"] = "SQLITE_READ_TRANSACTION"
    lineage: dict[str, str | None]
    panels: dict[str, dict[str, Any] | None]
    panel_status: dict[str, PanelStatusV1]
    assembly_count: int = Field(ge=0, le=1)
    executable: Literal[False] = False
    warnings: tuple[str, ...] = (
        "Atomic database view is not proof of live data, freshness or trade authorization.",
        "Control observations are separate from the research decision cutoff.",
        "S8 in this response is an unpersisted projection; saved history is unchanged.",
    )

    @model_validator(mode="after")
    def validate_envelope(self) -> ResearchSnapshotV1:
        if set(self.panels) != set(PANEL_KEYS) or set(self.panel_status) != set(PANEL_KEYS):
            raise ValueError("SNAPSHOT_PANEL_SET_INVALID")
        for key in PANEL_KEYS:
            status = self.panel_status[key]
            if (self.panels[key] is not None) != (status.state == "READY"):
                raise ValueError("SNAPSHOT_PANEL_STATUS_INVALID")
            if status.state == "UNAVAILABLE" and not status.code:
                raise ValueError("SNAPSHOT_MISSING_REASON")
        if not self.panels["attention"] or not self.panels["evidence"]:
            raise ValueError("SNAPSHOT_CORE_MISSING")
        if any(value.utcoffset() is None for value in (self.captured_at, self.decision_at, self.evaluated_at)):
            raise ValueError("SNAPSHOT_TIMESTAMP_NOT_AWARE")
        if self.evaluated_at != self.captured_at:
            raise ValueError("SNAPSHOT_EVALUATION_TIME_MISMATCH")
        _validate_panel_lineage(self.panels, self.lineage)
        digest = _digest(self.model_dump(mode="json", by_alias=True, exclude={"snapshot_id", "snapshot_hash"}))
        if self.snapshot_hash != digest or self.snapshot_id != "rs-" + digest:
            raise ValueError("SNAPSHOT_HASH_MISMATCH")
        return self


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _payload(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return value
    raise ValueError("SNAPSHOT_PANEL_INVALID")


def _match(value: Any, expected: dict[str, Any], code: str) -> Any:
    if value is None or any(getattr(value, k, None) != v for k, v in expected.items()):
        raise ValueError(code)
    return value


def _validate_panel_lineage(panels: dict[str, Any], lineage: dict[str, Any]) -> None:
    """Reject a self-consistent checksum over semantically mixed generations."""
    def check(value: dict[str, Any] | None, expected: dict[str, Any]) -> None:
        if value is None or any(expected_value is None or value.get(key) != expected_value
                                for key, expected_value in expected.items()):
            raise ValueError("SNAPSHOT_PANEL_LINEAGE_MISMATCH")

    check(panels["evidence"], {"bundleId": lineage.get("r1BundleId"), "bundleHash": lineage.get("r1BundleHash")})
    check(panels["attention"], {"runId": lineage.get("r2RunId"), "runHash": lineage.get("r2RunHash"),
                               "r1BundleHash": lineage.get("r1BundleHash"), "r1BundleId": lineage.get("r1BundleId")})
    parents = {"r1BundleHash": lineage.get("r1BundleHash"), "r2RunHash": lineage.get("r2RunHash")}
    for key, own in (("identityPin", "r4RunHash"), ("caJoin", "r14RunHash"), ("structure", "r5RunHash")):
        if panels[key] is not None:
            check(panels[key], {**parents, "runHash": lineage.get(own)})
    if panels["caJoin"] is not None:
        check(panels["caJoin"], {"r4RunHash": lineage.get("r4RunHash")})
    for key in ("structure", "s4Pack", "s5Enrich", "s6Resolve"):
        if panels[key] is not None:
            check(panels[key], {**parents, "r14RunHash": lineage.get("r14RunHash")})
    s7 = panels["s7State"]
    native = panels["nativeCore"]
    if s7 is not None:
        check(s7, {"r2RunHash": lineage.get("r2RunHash"), "r14RunHash": lineage.get("r14RunHash"),
                   "s6RunHash": (panels["s6Resolve"] or {}).get("runHash")})
    if native is not None:
        check(native, {"r5RunHash": lineage.get("r5RunHash"), "r14RunHash": lineage.get("r14RunHash")})
    s8 = panels["s8Latest"]
    if s8 is not None:
        check(s8.get("lineage"), {
            "r1RunHash": lineage.get("r1BundleHash"), "r2RunHash": lineage.get("r2RunHash"),
            "r14RunHash": lineage.get("r14RunHash"), "r5RunHash": lineage.get("r5RunHash"),
            "s3RunId": (panels["s3Watch"] or {}).get("sourceRunId"),
            "s4PackId": (panels["s4Pack"] or {}).get("runId"),
            "s6RunId": (panels["s6Resolve"] or {}).get("runId"),
            "s7RunId": (s7 or {}).get("runId"),
            "nativeGuidanceRunHash": (native or {}).get("runHash"),
            "tradabilityRunHash": (s7 or {}).get("tradabilityRunHash"),
        })
        if s8.get("persisted") is not False:
            raise ValueError("SNAPSHOT_MUST_NOT_CLAIM_S8_PERSISTED")
        if s8["lineage"].get("s5RunId") != (panels["s5Enrich"] or {}).get("runId"):
            raise ValueError("SNAPSHOT_PANEL_LINEAGE_MISMATCH")
    if panels["namedActivation"] is not None:
        check(panels["namedActivation"], parents)
    lab = panels["labBundle"]
    if lab is not None and lab.get("nativeCore") is not None:
        check(lab["nativeCore"], {"runHash": (native or {}).get("runHash")})
        for entry in lab.get("pipeRuns", []):
            if entry.get("run") is not None:
                check(entry["run"], {"nativeCoreRunHash": (native or {}).get("runHash"),
                                      "s7RunHash": (s7 or {}).get("runHash")})


def research_quantity_from_board(board: S7StateBatchV1, weather: Any) -> ResearchQtyBatchV1:
    """Same conservative quantity projection, without rebuilding another S7."""
    rows = []
    for card in board.rows:
        result = compute_research_quantity(
            public_state=card.public_state.value, evidence_direction=card.evidence_direction.value,
            draft_confirmed_eligible=card.draft_confirmed_eligible,
            is_reject_or_ban=card.public_state.value == "REJECT", official_close=None,
            invalidation_condition=card.invalidation_condition, atr=None, lot_size=None,
            s8_completeness_ratio=None, regime_label=getattr(weather, "regime_label", None),
            index_suspect=False,
        )
        rows.append(ResearchQtyRowV1(
            symbol=card.symbol, public_state=card.public_state.value,
            evidence_direction=card.evidence_direction.value,
            draft_confirmed_eligible=card.draft_confirmed_eligible,
            side=result.get("side") or result.get("_side", "FLAT"),
            research_quantity=int(result.get("researchQuantity") or 0),
            qty_unit=str(result.get("qtyUnit") or "shares"),
            research_entry=result.get("researchEntry"), research_stop=result.get("researchStop"),
            research_t1=result.get("researchT1"), reason=result.get("reason", ""),
            data_quality_cap=float(result.get("dataQualityCap", 1)),
            regime_cap=float(result.get("regimeCap", 1)),
            liquidity_cap=float(result.get("liquidityCap", 1)),
        ))
    return ResearchQtyBatchV1(rows=tuple(rows), executable=False)


def build_research_snapshot(*, lane_factory: Callable[[], Any],
                            captured_at: datetime | None = None) -> ResearchSnapshotV1:
    """Capture one immutable input view, assemble once, serialize before release."""
    with read_snapshot(storage.DB_PATH):
        return _build_snapshot(lane_factory, captured_at or datetime.now(UTC))


def _build_snapshot(lane_factory: Callable[[], Any], captured_at: datetime) -> ResearchSnapshotV1:
    panels: dict[str, dict[str, Any] | None] = dict.fromkeys(PANEL_KEYS)
    statuses = {key: PanelStatusV1(state="UNAVAILABLE", code="WAIT_SNAPSHOT_DEPENDENCY") for key in PANEL_KEYS}

    def put(key: str, value: Any, scope: PanelScope = "RESEARCH") -> Any:
        if value is None:
            raise ValueError("WAIT_SNAPSHOT_DATA_MISSING")
        panels[key] = _payload(value)
        statuses[key] = PanelStatusV1(state="READY", scope=scope)
        return value

    def optional(key: str, builder: Callable[[], Any], scope: PanelScope = "RESEARCH") -> Any:
        try:
            return put(key, builder(), scope)
        except SnapshotExpired:
            raise
        except Exception as exc:
            text = str(exc)
            code = text if re.fullmatch(r"[A-Z][A-Z0-9_]{2,100}", text) else "WAIT_SNAPSHOT_PANEL_ERROR"
            statuses[key] = PanelStatusV1(state="UNAVAILABLE", code=code, scope=scope)
            _LOG.warning("snapshot_panel_unavailable panel=%s error_type=%s", key, type(exc).__name__)
            return None

    bundle = latest_inventory_source_bundle()
    attention = latest_attention_order()
    if bundle is None or attention is None:
        raise ValueError("WAIT_RESEARCH_SNAPSHOT_CORE")
    _match(attention, {
        "r1_bundle_id": bundle.bundle_id, "r1_bundle_hash": bundle.bundle_hash,
        "collector_run_id": bundle.collector_run_id,
        "cash_pipeline_fingerprint": bundle.cash_pipeline_fingerprint,
        "permission_fingerprint": bundle.permission_fingerprint,
    }, "WAIT_RESEARCH_SNAPSHOT_LINEAGE")
    put("attention", attention)
    put("evidence", bundle)
    parents = {"r1_bundle_id": bundle.bundle_id, "r1_bundle_hash": bundle.bundle_hash,
               "r2_run_id": attention.run_id, "r2_run_hash": attention.run_hash}
    pin = optional("identityPin", lambda: _match(latest_r4_identity_pin(), parents, "WAIT_SNAPSHOT_R4_LINEAGE"))
    ca = optional("caJoin", lambda: _match(latest_r14_ca_join(), {
        **parents, "permission_fingerprint": bundle.permission_fingerprint,
        "r4_run_hash": pin.run_hash if pin else None,
    }, "WAIT_SNAPSHOT_R14_LINEAGE")) if pin else None
    r5 = optional("structure", lambda: _match(latest_r5_structure_batch(), {
        **parents, "r14_run_id": ca.run_id, "r14_run_hash": ca.run_hash,
        "collector_run_id": bundle.collector_run_id,
        "cash_pipeline_fingerprint": bundle.cash_pipeline_fingerprint,
        "permission_fingerprint": bundle.permission_fingerprint,
    }, "WAIT_SNAPSHOT_R5_LINEAGE")) if ca else None
    lane = optional("dataLane", lane_factory, "CONTROL_OBSERVATION")

    def observed_activation():
        stored = _match(latest_r2b_named_activation(), parents, "WAIT_SNAPSHOT_ACTIVATION_LEDGER")
        current = build_r2b_named_activation()  # Pure assessment, NEVER persists.
        return _match(stored, {"run_hash": current.run_hash}, "WAIT_SNAPSHOT_ACTIVATION_RECHECK")

    activation = optional("namedActivation", observed_activation, "CONTROL_OBSERVATION")
    decision_at = r5.decision_at if r5 is not None else attention.built_at
    assembly = None
    loader = CanonicalLatestResultLoader(default_market_data_store())
    assembly_count = 0
    if r5 is not None:
        assembly_count = 1
        try:
            assembly = assemble_current_scan(
                r5_batch=r5, attention=attention, bundle=bundle, ca_join=ca,
                built_at=captured_at, loader=loader, lane=lane,
                event_snapshot=latest_macro_event_context_snapshot(db_path=storage.DB_PATH),
                activation_ready=bool(activation is not None and activation.source_activation_ready),
            )
            for key, value in {
                "s3Watch": build_s3_watch_queue(assembly.s3, limit=50),
                "s4Pack": assembly.pack, "s5Enrich": assembly.s5,
                "s6Resolve": assembly.s6, "s7State": assembly.s7,
                "s8Latest": assembly.blob, "nativeCore": assembly.native,
                "marketWeather": assembly.weather,
            }.items():
                if value is not None:
                    put(key, value)
        except SnapshotExpired:
            raise
        except Exception as exc:
            _LOG.warning("snapshot_assembly_unavailable error_type=%s", type(exc).__name__)
            code = str(exc) if re.fullmatch(r"[A-Z][A-Z0-9_]{2,100}", str(exc)) else "WAIT_SNAPSHOT_ASSEMBLY"
            for key in ("s3Watch", "s4Pack", "s5Enrich", "s6Resolve", "s7State", "s8Latest", "nativeCore", "marketWeather"):
                panels[key] = None
                statuses[key] = PanelStatusV1(state="UNAVAILABLE", code=code)
            assembly = None
    else:
        optional("s3Watch", lambda: build_s3_watch_queue(build_s3_cheap_discovery(
            discovery=latest_cash_discovery(), attention=attention, built_at=captured_at
        ), limit=50))

    put("pipeDefs", {"schemaVersion": "trendforge.pipe-registry.v1", "definitions": [_payload(d) for d in PIPE_DEFINITIONS]})
    if assembly is not None:
        optional("researchQty", lambda: research_quantity_from_board(assembly.s7, assembly.weather))
        entries = []
        for definition in PIPE_DEFINITIONS:
            try:
                run = build_pipe_run(definition.pipe_id, native_core=assembly.native, s7_board=assembly.s7)
                entries.append({"pipeId": definition.pipe_id, "run": _payload(run), "code": None})
            except ValueError:
                entries.append({"pipeId": definition.pipe_id, "run": None, "code": "WAIT_SNAPSHOT_PIPE"})
        put("labBundle", {
            "schemaVersion": "trendforge.scanner-lab.v1", "profileId": "PRF-R15-LAB",
            "acceptanceCeiling": "LIVE_R15_LAB_GUIDANCE_ONLY", "confirmedCount": 0,
            "executable": False, "emitsClaims": False,
            "nativeDefinitions": [_payload(d) for d in NATIVE_CORE_DEFINITIONS],
            "nativeCore": _payload(assembly.native), "nativeCoreCode": None,
            "pipeDefinitions": [_payload(d) for d in PIPE_DEFINITIONS], "pipeRuns": entries,
            "pkShadow": {"state": "PK_SHADOW", "parity": "PARITY_UNKNOWN"},
            "warnings": ["Shared snapshot guidance; zero new claims."],
        })
    else:
        code = statuses["nativeCore"].code or "WAIT_SNAPSHOT_DEPENDENCY"
        put("labBundle", {
            "schemaVersion": "trendforge.scanner-lab.v1", "profileId": "PRF-R15-LAB",
            "acceptanceCeiling": "LIVE_R15_LAB_GUIDANCE_ONLY", "confirmedCount": 0,
            "executable": False, "emitsClaims": False,
            "nativeDefinitions": [_payload(d) for d in NATIVE_CORE_DEFINITIONS],
            "nativeCore": None, "nativeCoreCode": code,
            "pipeDefinitions": [_payload(d) for d in PIPE_DEFINITIONS],
            "pipeRuns": [{"pipeId": d.pipe_id, "run": None, "code": code} for d in PIPE_DEFINITIONS],
            "pkShadow": {"state": "PK_SHADOW", "parity": "PARITY_UNKNOWN"},
            "warnings": ["Definitions only; research inputs unavailable."],
        })
    optional("overlay", lambda: build_hybrid_v2_overlay(limit=40), "CONTEXT")
    optional("s4s5Compare", lambda: build_s4s5_compare(limit=40), "CONTEXT")
    if ca is not None:
        optional("top10Research", lambda: build_top10_research(
            enrichment=build_r6_enrichment(bundle=bundle, attention=attention, r14=ca, r5=r5,
                                           loader=loader, built_at=captured_at),
            built_at=captured_at,
        ), "CONTEXT")
        optional("evidenceRadar", lambda: build_evidence_radar(
            bundle=bundle, attention=attention, r14=ca, loader=loader, built_at=captured_at,
        ), "CONTEXT")
    optional("mcxMaster", lambda: build_mcx_master(trading_date=attention.trading_date), "CONTEXT")
    pit = optional("r16Status", status_payload, "VALIDATION")
    if pit is not None and pit.get("latestDatasetRunId"):
        optional("r16Metrics", lambda: metrics_payload(dataset_run_id=pit["latestDatasetRunId"]), "VALIDATION")
    else:
        statuses["r16Metrics"] = PanelStatusV1(state="UNAVAILABLE", code="WAIT_SNAPSHOT_PIT_DATASET", scope="VALIDATION")
    optional("openalgoShadow", disabled_shadow_batch, "CONTROL_OBSERVATION")

    lineage = {
        "r1BundleId": bundle.bundle_id, "r1BundleHash": bundle.bundle_hash,
        "r2RunId": attention.run_id, "r2RunHash": attention.run_hash,
        "r4RunHash": pin.run_hash if pin else None,
        "r14RunHash": ca.run_hash if ca else None,
        "r5RunHash": r5.run_hash if r5 else None,
        "permissionFingerprint": bundle.permission_fingerprint,
    }
    # model_construct is used only to canonicalize defaults; model_validate below
    # performs all validation including the content hash and panel invariants.
    draft = ResearchSnapshotV1.model_construct(
        captured_at=captured_at, decision_at=decision_at, evaluated_at=captured_at,
        lineage=lineage, panels=panels, panel_status=statuses,
        assembly_count=assembly_count,
    )
    normalized = draft.model_dump(mode="json", by_alias=True, exclude={"snapshot_id", "snapshot_hash"})
    digest = _digest(normalized)
    return ResearchSnapshotV1.model_validate({**normalized, "snapshotId": "rs-" + digest, "snapshotHash": digest})
