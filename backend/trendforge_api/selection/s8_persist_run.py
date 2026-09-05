"""File A S8 (SEL-009): ONE reconstructable scan blob (S2-S7).

Assembles the hash-matched spine outputs into a single immutable payload:
- lineage ids for every stage (null + ``WAIT_STAGE_ABSENT`` when a stage has
  no run id - never invented),
- S2 weather snapshot with suspect flags (display-only),
- S3 completeness tuple (absent stage named honestly, not fake 1.0),
- per-symbol rows whose publicState is COPIED from S7 (never re-scored),
- what-changed kinds vs the prior comparable run,
- STO-008 state events written into the EXISTING selection_state_events
  table (prior_state uses WAIT as the named starting state when no prior run
  exists - mirroring the R1 persist pattern).

Ceiling LIVE_S8_RECONSTRUCTABLE_WAIT_ONLY. confirmedCount pinned 0. Geometry
keys are model-law null. No broker, no second database, no CONFIRMED.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .contracts import EvidenceDirection, SelectionState, stable_id
from .r5_live import R5StructureBatchV1, latest_r5_structure_batch
from .s4_structure_pack import S4StructurePackBatchV1, build_s4_structure_pack
from .s5_shortlist_enrichment import (
    S5EnrichmentBatchV1,
    build_s5_enrichment,
)
from .s6_family_resolution import S6ResolutionBatchV1, build_s6_resolution
from .s7_state_gates import S7StateBatchV1, build_s7_state
from .store import (
    get_selection_payload,
    list_latest_selection_payloads,
    persist_selection_payload,
)

SCHEMA_VERSION = "trendforge.s8-scan.v1"
PROFILE_ID = "PRF-S8-SCAN-RUN"
PROFILE_VERSION = "1.0.0"
ACCEPTANCE_CEILING = "LIVE_S8_RECONSTRUCTABLE_WAIT_ONLY"

# Named constant (documented in BUILD_STATUS) - matches the S3 projection
# threshold. Deliberately NOT a silent 1.0.
MIN_COMPLETENESS = 0.95

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

ROW_CHANGE_KINDS = {"STATE", "GATE", "FAMILY", "FEATURE", "NO_BASELINE"}
BLOB_CHANGE_KINDS = {"SOURCE", "FRESHNESS", "VERSION", "NO_BASELINE"}


class S8LineageV1(BaseModel):
    model_config = MODEL_CONFIG

    r1_run_hash: str | None = None
    r2_run_hash: str | None = None
    r14_run_hash: str | None = None
    r5_run_hash: str | None = None
    s2_run_id: str | None = None
    s3_run_id: str | None = None
    s4_pack_id: str | None = None
    s5_run_id: str | None = None
    s6_run_id: str | None = None
    s7_run_id: str | None = None
    tradability_run_hash: str | None = None
    native_guidance_run_hash: str | None = None
    missing_stages: tuple[str, ...] = ()


class S8WeatherBlockV1(BaseModel):
    model_config = MODEL_CONFIG

    regime_label: str | None = None
    suspect_flags: tuple[str, ...] = ()
    can_support_confirmed: bool = False


class S8CompletenessV1(BaseModel):
    model_config = MODEL_CONFIG

    eligible: int | None = None
    scanned: int | None = None
    excluded: int | None = None
    failed: int | None = None
    unattempted: int | None = None
    ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    threshold: float = MIN_COMPLETENESS


class S8RowV1(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str
    symbol: str
    public_state: SelectionState
    evidence_direction: EvidenceDirection
    evidence_strength: float = Field(ge=0, le=1, default=0.0)
    evidence_strength_label: str = "Evidence strength - not win probability"
    why: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    gate_codes: tuple[str, ...] = ()
    next_trigger: str | None = None
    invalidation_condition: str | None = None
    family_support: dict[str, float] = {}
    family_opposition: dict[str, float] = {}
    missing_families: tuple[str, ...] = ()
    fo_package_status: str | None = None
    options_package_status: str | None = None
    tradability_outcome: str = "WAIT"
    tradability_reason: str = "WAIT_TRADABILITY_NOT_EVALUATED"
    tradability_hash: str | None = None
    tradability_components: tuple[dict[str, Any], ...] = ()
    change_kinds: tuple[str, ...] = ()
    comparable_run_id: str | None = None
    claim_ids: tuple[str, ...] = ()
    native_guidance_ids: tuple[str, ...] = ()
    entry: None = None
    stop: None = None
    t1: None = None
    t2: None = None
    quantity: None = None

    @model_validator(mode="after")
    def enforce_s8_row_law(self) -> "S8RowV1":
        if self.public_state is SelectionState.CONFIRMED:
            raise ValueError("S8 blob cannot carry CONFIRMED")
        for kind in self.change_kinds:
            if kind not in ROW_CHANGE_KINDS:
                raise ValueError(f"unknown change kind: {kind}")
        return self


class S8ScanBlobV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = PROFILE_VERSION
    run_id: str
    as_of: datetime
    built_at: datetime
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    lineage: S8LineageV1
    weather: S8WeatherBlockV1 | None = None
    s3_completeness: S8CompletenessV1 | None = None
    completeness: S8CompletenessV1 | None = None
    hybrid_pin: dict[str, Any] | None = None
    lineage_change_kinds: tuple[str, ...] = ()
    source_activation_ready: bool = False
    can_unlock_confirmed: bool = False
    confirmed_count: int = 0
    validation_status: str = "RESEARCH_CEILING"
    trading_date: str | None = None
    rows: tuple[S8RowV1, ...]
    warnings: tuple[str, ...] = ()
    persisted: bool = False

    @model_validator(mode="after")
    def enforce_s8_law(self) -> "S8ScanBlobV1":
        if self.source_activation_ready or self.can_unlock_confirmed:
            raise ValueError("S8 cannot activate sources or unlock CONFIRMED")
        if self.confirmed_count != 0:
            raise ValueError("S8 confirmedCount is pinned to zero")
        for row in self.rows:
            if row.public_state is SelectionState.CONFIRMED:
                raise ValueError("S8 rows cannot be CONFIRMED")
        pin = self.hybrid_pin or {}
        if any(pin.get(k) for k in ("canVote", "can_vote", "isConfirmed")):
            raise ValueError("hybrid_pin is a non-voting overlay; canVote forbidden")
        for kind in self.lineage_change_kinds:
            if kind not in BLOB_CHANGE_KINDS:
                raise ValueError(f"unknown blob change kind: {kind}")
        return self


def _weather_block(weather: Any) -> tuple[S8WeatherBlockV1 | None, str | None]:
    """Return (block, s2_run_id). Content-derived id; wall-clock excluded."""
    if weather is None:
        return None, "S2"
    regime = getattr(weather, "regime_label", None)
    if regime is None:
        regime = getattr(weather, "regimeLabel", None)
    trading_date = getattr(weather, "trading_date", None)
    if trading_date is None:
        trading_date = getattr(weather, "tradingDate", None)
    why = tuple(str(w) for w in getattr(weather, "why", ()) or ())
    suspects = tuple(w for w in why if "SUSPECT" in w)
    block = S8WeatherBlockV1(
        regime_label=str(regime) if regime is not None else None,
        suspect_flags=suspects,
    )
    if trading_date is None:
        return block, None
    s2_run_id = stable_id("s2-context", str(trading_date), str(regime), ",".join(suspects))
    return block, s2_run_id


def _lineage_from_stages(
    *,
    s6: S6ResolutionBatchV1,
    s7: S7StateBatchV1,
    pack: S4StructurePackBatchV1,
    s5: S5EnrichmentBatchV1 | None,
    weather: Any,
    s3_batch: Any | None,
    r5_batch: Any | None = None,
) -> tuple[S8LineageV1, S8WeatherBlockV1 | None, S8CompletenessV1 | None]:
    missing: list[str] = []
    weather_block, s2_run_id = _weather_block(weather)
    if s2_run_id is None:
        missing.append("S2")

    s3_run_id = None
    completeness = None
    if s3_batch is not None:
        s3_run_id = getattr(s3_batch, "run_id", None)
        completeness = S8CompletenessV1(
            eligible=getattr(s3_batch, "eligible_count", None),
            scanned=getattr(s3_batch, "scanned_count", None),
            excluded=getattr(s3_batch, "excluded_count", None),
            failed=getattr(s3_batch, "failed_count", None),
            unattempted=getattr(s3_batch, "unattempted_count", None),
            ratio=getattr(s3_batch, "completeness", None),
            threshold=MIN_COMPLETENESS,
        )
    else:
        missing.append("S3")

    s5_run_id = getattr(s5, "run_id", None) if s5 is not None else None
    if s5_run_id is None:
        missing.append("S5")

    lineage = S8LineageV1(
        r1_run_hash=s6.r1_bundle_hash,
        r2_run_hash=s6.r2_run_hash,
        r14_run_hash=s6.r14_run_hash,
        r5_run_hash=(
            (getattr(r5_batch, "run_hash", None) if r5_batch is not None else None)
            or getattr(pack, "r5_run_hash", None)
            or s7.s6_run_hash
        ),
        s2_run_id=s2_run_id,
        s3_run_id=s3_run_id,
        s4_pack_id=pack.run_id,
        s5_run_id=s5_run_id,
        s6_run_id=s6.run_id,
        s7_run_id=s7.run_id,
        tradability_run_hash=getattr(s7, "tradability_run_hash", None),
        missing_stages=tuple(missing),
    )
    return lineage, weather_block, completeness


def build_s8_scan(
    *,
    s7: S7StateBatchV1,
    s6: S6ResolutionBatchV1,
    r5: Any | None = None,
    pack: Any | None = None,
    s5: Any | None = None,
    weather: Any = None,
    s3_batch: Any | None = None,
    native_core: Any | None = None,
    hybrid_pin: dict[str, Any] | None = None,
    prior_payload: dict[str, Any] | None = None,
    built_at: datetime | None = None,
) -> S8ScanBlobV1:
    """Assemble ONE reconstructable blob from same-request spine outputs."""
    now = built_at or getattr(s7, "built_at", None) or datetime.now(timezone.utc)
    weather_block, s2_run_id = _weather_block(weather)
    missing: list[str] = []
    weather_date = getattr(weather, "trading_date", None)
    if weather_date is None:
        weather_date = getattr(weather, "tradingDate", None)
    expected_weather_date = str(s7.trading_date or "")
    if s2_run_id is None:
        missing.append("S2")
    elif expected_weather_date and str(weather_date) != expected_weather_date:
        missing.append("S2_STALE")

    s3_run_id = None
    completeness = None
    if s3_batch is not None:
        s3_run_id = getattr(s3_batch, "run_id", None)
        completeness = S8CompletenessV1(
            eligible=getattr(s3_batch, "eligible_count", None),
            scanned=getattr(s3_batch, "scanned_count", None),
            excluded=getattr(s3_batch, "excluded_count", None),
            failed=getattr(s3_batch, "failed_count", None),
            unattempted=getattr(s3_batch, "unattempted_count", None),
            ratio=getattr(s3_batch, "completeness", None),
            threshold=MIN_COMPLETENESS,
        )
    else:
        missing.append("S3")

    s5_run_id = getattr(s5, "run_id", None) if s5 is not None else None
    if s5_run_id is None:
        missing.append("S5")

    r5_run_hash = (
        (getattr(r5, "run_hash", None) if r5 is not None else None)
        or getattr(pack, "r5_run_hash", None)
        or s7.s6_run_hash
    )
    native_guidance_run_hash = None
    native_guidance_by_symbol: dict[str, tuple[str, ...]] = {}
    if native_core is None:
        missing.append("R13_GUIDANCE")
    elif getattr(native_core, "r5_run_hash", None) != r5_run_hash:
        missing.append("R13_GUIDANCE_LINEAGE")
    else:
        native_guidance_run_hash = getattr(native_core, "run_hash", None)
        native_guidance_by_symbol = {
            str(item.symbol).upper(): tuple(item.representative_guidance_ids)
            for item in getattr(native_core, "rows", ())
        }

    lineage = S8LineageV1(
        r1_run_hash=s6.r1_bundle_hash,
        r2_run_hash=s6.r2_run_hash,
        r14_run_hash=s6.r14_run_hash,
        r5_run_hash=r5_run_hash,
        s2_run_id=s2_run_id,
        s3_run_id=s3_run_id,
        s4_pack_id=pack.run_id if pack is not None else None,
        s5_run_id=s5_run_id,
        s6_run_id=s6.run_id,
        s7_run_id=s7.run_id,
        tradability_run_hash=getattr(s7, "tradability_run_hash", None),
        native_guidance_run_hash=native_guidance_run_hash,
        missing_stages=tuple(
            missing
            + (["TRADABILITY"] if not getattr(s7, "tradability_run_hash", None) else [])
        ),
    )

    regime = getattr(weather, "regime_label", None) if weather is not None else None
    if regime is None and weather is not None:
        regime = getattr(weather, "regimeLabel", None)
    why_all = tuple(getattr(weather, "why", ()) or ()) if weather is not None else ()
    suspects = tuple(w for w in why_all if "SUSPECT" in w)
    weather_block = (
        S8WeatherBlockV1(
            regime_label=str(regime) if regime is not None else None,
            suspect_flags=suspects,
        )
        if weather is not None and (regime is not None or suspects)
        else None
    )

    partial = (
        completeness is not None
        and completeness.ratio is not None
        and completeness.ratio < MIN_COMPLETENESS
    )

    prior_rows: dict[str, dict[str, Any]] = {}
    prior_run_id = None
    if prior_payload:
        prior_run_id = prior_payload.get("runId") or prior_payload.get("run_id")
        for row in prior_payload.get("rows") or []:
            sym = row.get("symbol")
            if isinstance(sym, str):
                prior_rows[sym.upper()] = row

    rows_out: list[S8RowV1] = []
    for card in s7.rows:
        sym_key = card.symbol.upper()
        prow = prior_rows.get(sym_key)
        kinds: list[str] = []
        if prow is None:
            kinds.append("NO_BASELINE")
        else:
            if prow.get("publicState") != card.public_state.value:
                kinds.append("STATE")
            prior_gates = prow.get("gateCodes") or prow.get("gate_codes") or []
            if list(prior_gates) != list(card.why):
                kinds.append("GATE")
            prior_missing = (
                prow.get("missingFamilies") or prow.get("missing_families") or []
            )
            if list(prior_missing) != list(card.missing_families):
                kinds.append("FAMILY")
        why = tuple(card.why)
        if partial:
            why = why + ("WAIT_PARTIAL_SCAN",)
        fo_status = card.fo_package_status
        opt_status = card.options_package_status
        rows_out.append(
            S8RowV1(
                candidate_id=f"c-{card.symbol}",
                symbol=card.symbol,
                public_state=card.public_state,
                evidence_direction=card.evidence_direction,
                evidence_strength=card.evidence_strength,
                why=why,
                missing_evidence=tuple(card.missing_evidence),
                gate_codes=tuple(card.why),
                next_trigger=card.next_trigger,
                invalidation_condition=card.invalidation_condition,
                family_support=dict(card.family_support),
                family_opposition=dict(card.family_opposition),
                missing_families=tuple(card.missing_families),
                fo_package_status=str(fo_status) if fo_status else None,
                options_package_status=str(opt_status) if opt_status else None,
                tradability_outcome=str(card.tradability_outcome),
                tradability_reason=card.tradability_reason,
                tradability_hash=card.tradability_hash,
                tradability_components=tuple(
                    item.model_dump(mode="json", by_alias=True)
                    for item in (
                        card.tradability.components if card.tradability is not None else ()
                    )
                ),
                change_kinds=tuple(kinds),
                comparable_run_id=prior_run_id or ("NO_BASELINE" if prow is None else None),
                claim_ids=tuple(getattr(card, "claim_ids", ())),
                native_guidance_ids=native_guidance_by_symbol.get(sym_key, ()),
            )
        )

    lineage_values = sorted(
        v for v in lineage.model_dump().values() if isinstance(v, str)
    )
    rows_hash = hashlib.sha256(
        json.dumps([r.model_dump(mode="json") for r in rows_out], sort_keys=True).encode()
    ).hexdigest()
    run_id = stable_id(
        PROFILE_ID,
        str(as_of_date := (s7.trading_date or "")),
        lineage_values[0] if lineage_values else "",
        rows_hash,
    )

    warnings_list: list[str] = [
        "Reconstructable research run - not an order. Not a win rate.",
        "CONFIRMED unreachable while sourceActivationReady is false.",
    ]
    if lineage.missing_stages:
        warnings_list.append("WAIT_STAGE_ABSENT:" + ",".join(lineage.missing_stages))
    if partial:
        warnings_list.append("WAIT_PARTIAL_SCAN")

    blob_lineage_kinds: list[str] = []
    if prior_payload:
        pl = prior_payload.get("lineage") or {}
        pl_alias = lineage.model_dump(by_alias=True)
        for key, kind in (("r5RunHash", "SOURCE"), ("r14RunHash", "SOURCE"), ("r2RunHash", "SOURCE")):
            if pl.get(key) and pl[key] != pl_alias[key]:
                blob_lineage_kinds.append(kind)
                break
    else:
        blob_lineage_kinds.append("NO_BASELINE")

    return S8ScanBlobV1(
        run_id=run_id,
        as_of=now,
        built_at=now,
        trading_date=str(as_of_date) if as_of_date else None,
        lineage=lineage,
        weather=weather_block,
        s3_completeness=completeness,
        completeness=completeness,
        hybrid_pin=hybrid_pin,
        lineage_change_kinds=tuple(dict.fromkeys(blob_lineage_kinds)),
        rows=tuple(rows_out),
        warnings=tuple(warnings_list),
    )


def persist_s8_scan(blob: S8ScanBlobV1, prior_payload: dict[str, Any] | None = None) -> S8ScanBlobV1:
    stored = blob.model_copy(update={"persisted": True})
    candidates = tuple((row.candidate_id, row.symbol, row.public_state.value, row.model_dump(mode="json", by_alias=True)) for row in stored.rows)
    persist_selection_payload(run_id=stored.run_id, profile_id=PROFILE_ID, as_of=stored.as_of, payload=stored.model_dump(mode="json", by_alias=True), candidates=candidates)

    import trendforge_api.storage as storage

    prior_rows: dict[str, dict[str, Any]] = {}
    for row in (prior_payload or {}).get("rows") or []:
        sym = row.get("symbol")
        if isinstance(sym, str):
            prior_rows[sym.upper()] = row

    storage.init_db()
    conn = storage.connect()
    try:
        now = datetime.now(timezone.utc).isoformat()
        for row in stored.rows:
            prev = prior_rows.get(row.symbol.upper())
            prior_state = ((prev or {}).get("publicState") or (prev or {}).get("public_state") or SelectionState.WAIT.value)
            event_id = stable_id("s8-evt", stored.run_id, row.candidate_id)
            conn.execute(
                "INSERT OR IGNORE INTO selection_state_events (event_id, run_id, candidate_id, sequence, prior_state, resulting_state, accepted, reason_code, payload_json, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (event_id, stored.run_id, row.candidate_id, 1, prior_state, row.public_state.value, 0, (row.why[0] if row.why else "WAIT_SOURCE_ACTIVATION"), storage.encode_json({"changeKinds": list(row.change_kinds)}), now),
            )
        conn.commit()
    finally:
        conn.close()
    return stored


def latest_matching_s8(
    *,
    current_r5_run_hash: str | None,
    current_r2_run_hash: str | None,
    current_native_guidance_run_hash: str | None = None,
    current_tradability_run_hash: str | None = None,
) -> S8ScanBlobV1 | None:
    payloads = list_latest_selection_payloads(PROFILE_ID, limit=20)
    for payload in payloads:
        lineage = payload.get("lineage") or {}
        matches = (
            lineage.get("r5RunHash") == current_r5_run_hash
            and lineage.get("r2RunHash") == current_r2_run_hash
            and (
                current_native_guidance_run_hash is None
                or lineage.get("nativeGuidanceRunHash")
                == current_native_guidance_run_hash
            )
            and (
                current_tradability_run_hash is None
                or lineage.get("tradabilityRunHash")
                == current_tradability_run_hash
            )
        )
        if matches:
            return S8ScanBlobV1.model_validate(payload)
    if payloads:
        raise ValueError("WAIT_S8_LINEAGE")
    return None


__all__ = [
    "ACCEPTANCE_CEILING",
    "MIN_COMPLETENESS",
    "PROFILE_ID",
    "SCHEMA_VERSION",
    "S8LineageV1",
    "S8ScanBlobV1",
    "build_s8_scan",
    "latest_matching_s8",
    "persist_s8_scan",
]
