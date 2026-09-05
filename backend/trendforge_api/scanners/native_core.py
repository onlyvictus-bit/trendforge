"""File A R8 native core scanner run (PK3).

Computes guidance-only match chips from the LAST hash-matched R5 batch:
- breakout / trend  -> FTR-006 claim, CG_PRICE_STRUCTURE
- NR compression    -> FTR-007 claim, CG_COMPRESSION
- RVOL / thrust     -> FTR-017 claim, CG_ACTIVITY_SESSION

No third engine: every matched scanner cites the R5-minted claim id. Twin
scanners on one claim are labelled correlated_possible and fold into ONE
representative per correlation group (FUS-009 first-wins in registry order).
Universe = full hash-matched R5 rows (one A4 set-query already performed by
R5; documented per prompt §1). confirmedCount pinned 0; executable false;
PK shadow stays isolated - its failure cannot change any row.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .registry import NATIVE_CORE_DEFINITIONS, SCANNER_ENGINE, scanner_definition
from ..selection.r5_live import R5StructureBatchV1, latest_r5_structure_batch

SCHEMA_VERSION = "trendforge.scanner-native-core.v1"
PROFILE_ID = "PRF-R8-NATIVE-CORE"
PROFILE_VERSION = "1.0.0"
ACCEPTANCE_CEILING = "LIVE_R8_GUIDANCE_CHIPS_ONLY"
GUIDANCE_COPY = "Native core - trade guidance, not an order."
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

# volume_thrust threshold = R5 min_rvol baseline x multiplier (same metric,
# stricter named threshold; never a second volume vote).
_THRUST_BASELINE_RVOL = 1.5
_THRUST_MULTIPLIER = 2.0


class NativeScannerMatchV1(BaseModel):
    model_config = MODEL_CONFIG

    scanner_id: str
    version: Literal["v1"] = "v1"
    matched: bool
    feature_id: str | None = None
    claim_id: str | None = None
    family: str
    group: str
    correlated_with: tuple[str, ...] = ()
    correlated_possible: bool = False
    guidance_label: str
    reason_code: str | None = None
    can_support_confirmed: Literal[False] = False
    scanner_state: str = "NO_MATCH"
    directional_context: Literal[
        "BULLISH", "BEARISH", "MIXED", "NEUTRAL", "UNKNOWN"
    ] = "UNKNOWN"
    candidate_relationship: Literal[
        "SUPPORTS", "CONFLICTS", "NEUTRAL", "UNKNOWN"
    ] = "UNKNOWN"
    metrics: dict[str, Any] = Field(default_factory=dict)
    trigger_level: float | None = None
    invalidation_level: float | None = None
    as_of: str | None = None
    bar_count: int = Field(default=0, ge=0)
    input_status: Literal["READY", "INPUT_INCOMPLETE", "INVALID"] = (
        "INPUT_INCOMPLETE"
    )
    formula_version: str | None = None
    parameter_hash: str | None = None
    lineage_hash: str | None = None
    adjustment_version: str | None = None
    input_completeness: float = Field(default=0.0, ge=0.0, le=1.0)
    is_representative: bool = False
    suppressed_by: str | None = None
    guidance_win_rate: None = None
    guidance_approved: Literal[False] = False
    guidance_confirmed: Literal[False] = False


class NativeCoreRowV1(BaseModel):
    model_config = MODEL_CONFIG

    symbol: str
    candidate_id: str
    lookback_bars: int = Field(default=0, ge=0)
    detected_setups: tuple[str, ...] = ()
    candidate_direction: Literal[
        "BULLISH", "BEARISH", "MIXED", "NEUTRAL", "UNKNOWN"
    ] = "UNKNOWN"
    matches: tuple[NativeScannerMatchV1, ...]
    representative_claim_ids: tuple[str, ...] = ()
    representative_guidance_ids: tuple[str, ...] = ()
    guidance_match: bool = False
    completeness: float = Field(default=0.0, ge=0.0, le=1.0)
    why: tuple[str, ...] = ()

    @property
    def matched_ids(self) -> tuple[str, ...]:
        return tuple(m.scanner_id for m in self.matches if m.matched)


class NativeCoreRunV1(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    profile_id: str = PROFILE_ID
    profile_version: str = "1.0.0"
    engine: str = SCANNER_ENGINE
    universe: Literal["FULL_HASH_MATCHED_R5"] = "FULL_HASH_MATCHED_R5"
    run_id: str
    run_hash: str
    r5_run_hash: str
    r14_run_hash: str | None = None
    trading_date: str
    built_at: datetime
    definitions: tuple = ()
    rows: tuple[NativeCoreRowV1, ...]
    matched_count: int = Field(default=0, ge=0)
    confirmed_count: int = 0
    executable: Literal[False] = False
    can_unlock_confirmed: Literal[False] = False
    source_activation_ready: Literal[False] = False
    acceptance_ceiling: str = ACCEPTANCE_CEILING
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def enforce_r8_law(self) -> "NativeCoreRunV1":
        if self.confirmed_count != 0:
            raise ValueError("R8 native core confirmedCount is pinned to zero")
        for row in self.rows:
            for match in row.matches:
                if match.can_support_confirmed:
                    raise ValueError("native matches can never support CONFIRMED")
                if match.correlated_possible and not match.matched:
                    raise ValueError(
                        "correlated_possible applies only to matched chips"
                    )
        return self


def representative_matches(
    matches: tuple[NativeScannerMatchV1, ...],
) -> tuple[NativeScannerMatchV1, ...]:
    """First-wins ONE representative per (family, group) among matched.

    Registry order breaks ties; later twins on the same claim are folded away
    so a correlated pair can never count as two independent confirms.
    """
    seen_groups: dict[tuple[str, str], NativeScannerMatchV1] = {}
    for match in matches:
        if not match.matched or match.claim_id is None:
            continue
        key = (match.family, match.group)
        if key not in seen_groups:
            seen_groups[key] = match
    return tuple(seen_groups.values())


def representative_guidance_chips(matches: tuple) -> tuple:
    """Select one display chip per family/group, including claimless R13 chips."""
    grouped: dict[tuple[str, str], list] = {}
    for match in matches:
        if not getattr(match, "matched", False):
            continue
        grouped.setdefault((match.family, match.group), []).append(match)
    representatives: list = []
    for candidates in grouped.values():
        representatives.append(
            min(
                candidates,
                key=lambda match: (
                    scanner_definition(match.scanner_id).display_priority,
                    -float(getattr(match, "input_completeness", 1.0)),
                    0 if getattr(match, "as_of", None) else 1,
                    match.scanner_id,
                ),
            )
        )
    return tuple(representatives)


def _claim_by_feature(row) -> dict[str, str]:
    claims: dict[str, str] = {}
    for claim in getattr(row, "claims", ()) or ():
        feature_id = getattr(claim, "feature_id", None)
        claim_id = getattr(claim, "claim_id", None)
        if feature_id and claim_id:
            claims.setdefault(feature_id, claim_id)
    return claims


_BASE_SCANNER_IDS = (
    "native.breakout.v1",
    "native.trend.v1",
    "native.nr_compression.v1",
    "native.rvol.v1",
    "native.volume_thrust.v1",
)


def _relationship(matched: bool, direction: str, candidate: str) -> str:
    if not matched or direction in {"NEUTRAL", "MIXED"}:
        return "NEUTRAL"
    if candidate == "UNKNOWN":
        return "UNKNOWN"
    if candidate in {"NEUTRAL", "MIXED"}:
        return "NEUTRAL"
    return "SUPPORTS" if direction == candidate else "CONFLICTS"


def _matches_for_row(row, bundle) -> tuple[NativeScannerMatchV1, ...]:
    by_feature = _claim_by_feature(row)
    metrics = getattr(row, "metrics", None)
    relative_volume = getattr(metrics, "relative_volume", None)
    reference_level = getattr(metrics, "reference_level", None)
    ftr006 = by_feature.get("FTR-006")
    ftr007 = by_feature.get("FTR-007")
    ftr017 = by_feature.get("FTR-017")
    thrust_hit = bool(
        ftr017
        and relative_volume is not None
        and float(relative_volume) >= _THRUST_BASELINE_RVOL * _THRUST_MULTIPLIER
    )
    specs = {
        "native.breakout.v1": (
            ftr006 is not None,
            "FTR-006",
            ftr006,
            (),
        ),
        "native.trend.v1": (
            ftr006 is not None,
            "FTR-006",
            ftr006,
            ("native.breakout.v1",),
        ),
        "native.nr_compression.v1": (ftr007 is not None, "FTR-007", ftr007, ()),
        "native.rvol.v1": (ftr017 is not None, "FTR-017", ftr017, ()),
        "native.volume_thrust.v1": (
            thrust_hit,
            "FTR-017",
            ftr017,
            ("native.rvol.v1",),
        ),
    }
    definition_by_id = {d.scanner_id: d for d in NATIVE_CORE_DEFINITIONS}
    candidate_direction = str(getattr(row, "evidence_direction", "UNKNOWN"))
    if "." in candidate_direction:
        candidate_direction = candidate_direction.rsplit(".", 1)[-1]
    candidate_direction = candidate_direction.upper()
    matches: list[NativeScannerMatchV1] = []
    for scanner_id in _BASE_SCANNER_IDS:
        matched, feature_id, claim_id, correlated = specs[scanner_id]
        definition = definition_by_id[scanner_id]
        direction = (
            "NEUTRAL"
            if scanner_id == "native.nr_compression.v1"
            else candidate_direction
        )
        matches.append(
            NativeScannerMatchV1(
                scannerId=scanner_id,
                matched=bool(matched),
                featureId=feature_id,
                claimId=claim_id,
                family=definition.family,
                group=definition.group,
                correlatedWith=tuple(correlated) if matched else (),
                correlatedPossible=False,
                guidanceLabel=definition.guidance_label,
                scannerState="MATCHED" if matched else "NO_MATCH",
                directionalContext=direction,
                candidateRelationship=_relationship(
                    bool(matched), direction, candidate_direction
                ),
                inputStatus="READY",
                formulaVersion="R8-R5-WRAPPER-1.0.0",
                parameterHash=definition.parameter_hash,
                inputCompleteness=1.0,
            )
        )

    from .native_extended import compute_extended_matches

    for chip in compute_extended_matches(
        bundle.bars,
        reference_level=reference_level,
        candidate_direction=candidate_direction,
        lineage_hash=bundle.lineage_hash,
        adjustment_version=bundle.adjustment_version,
        input_reason=bundle.reason,
    ):
        definition = definition_by_id[chip.scanner_id]
        matches.append(
            NativeScannerMatchV1(
                scannerId=chip.scanner_id,
                matched=chip.matched,
                featureId=chip.feature_id or None,
                family=definition.family,
                group=definition.group,
                correlatedWith=tuple(chip.correlated_with) if chip.matched else (),
                correlatedPossible=False,
                guidanceLabel=definition.guidance_label,
                reasonCode=chip.reason_code,
                scannerState=chip.scanner_state,
                directionalContext=chip.directional_context,
                candidateRelationship=chip.candidate_relationship,
                metrics=chip.metrics,
                triggerLevel=chip.trigger_level,
                invalidationLevel=chip.invalidation_level,
                asOf=chip.as_of,
                barCount=chip.bar_count,
                inputStatus=chip.input_status,
                formulaVersion=chip.formula_version,
                parameterHash=chip.parameter_hash,
                lineageHash=chip.lineage_hash,
                adjustmentVersion=chip.adjustment_version,
                inputCompleteness=chip.input_completeness,
                guidanceWinRate=None,
                guidanceApproved=False,
                guidanceConfirmed=False,
            )
        )

    # Twin marking: any group with >1 matched member is a correlated family
    # (claim-sharing twins AND chip-only siblings alike).
    from collections import Counter

    group_counts = Counter(m.group for m in matches if m.matched)
    marked: list[NativeScannerMatchV1] = []
    for match in matches:
        shared = bool(match.matched and group_counts.get(match.group, 0) > 1)
        marked.append(
            match.model_copy(update={"correlated_possible": shared})
        )
    representatives = representative_guidance_chips(tuple(marked))
    representative_by_group = {
        (match.family, match.group): match.scanner_id for match in representatives
    }
    output: list[NativeScannerMatchV1] = []
    for match in marked:
        representative_id = representative_by_group.get((match.family, match.group))
        output.append(
            match.model_copy(
                update={
                    "is_representative": bool(
                        match.matched and match.scanner_id == representative_id
                    ),
                    "suppressed_by": (
                        representative_id
                        if match.matched
                        and representative_id is not None
                        and match.scanner_id != representative_id
                        else None
                    ),
                }
            )
        )
    return tuple(output)


@dataclass(frozen=True)
class ScannerBarBundle:
    bars: tuple = ()
    input_status: str = "INPUT_INCOMPLETE"
    reason: str | None = "WAIT_R13_ADJUSTED_BARS"
    adjustment_version: str | None = None
    lineage_hash: str | None = None


def _pk_shadow_warning(pk_probe: Callable[[], Any] | None) -> str:
    try:
        if pk_probe is not None:
            pk_probe()
        else:
            from .pk_compatibility import build_pk_r4_inventory

            inventory = build_pk_r4_inventory()
            mapped = sum(
                1
                for entry in getattr(inventory, "entries", ())
                if getattr(entry, "disposition", None) is not None
                and "NATIVE" in str(getattr(entry, "disposition"))
            )
            return f"PK_SHADOW_PARITY_MAPPED={mapped}"
    except Exception:
        return "PK_SHADOW_UNAVAILABLE"


def _missing_bundles(symbols: list[str], reason: str) -> dict[str, ScannerBarBundle]:
    return {
        symbol: ScannerBarBundle(reason=reason)
        for symbol in symbols
    }


def _adjusted_bars_bulk(
    batch5: R5StructureBatchV1,
) -> dict[str, ScannerBarBundle]:
    """Load raw bars once, then apply the exact hash-matched R14 adjustment."""
    symbols = [row.symbol.upper() for row in batch5.rows]
    if not symbols:
        return {}
    try:
        from datetime import date as _date

        from ..selection.cash_a2_identity import latest_cash_identity
        from ..selection.cash_a4_history import list_raw_bars_by_symbol
        from ..selection.r14_live import latest_r14_ca_join
        from ..selection.r5_live import build_adjusted_closed_bars

        day = _date.fromisoformat(str(batch5.trading_date)[:10])
        identity = latest_cash_identity()
        ca_join = latest_r14_ca_join()
        if (
            identity is None
            or ca_join is None
            or not batch5.r14_run_hash
            or ca_join.run_hash != batch5.r14_run_hash
        ):
            return _missing_bundles(symbols, "WAIT_R13_R14_LINEAGE")
        identity_by_symbol = {
            row.instrument.symbol.upper(): row.instrument for row in identity.rows
        }
        ca_by_symbol = {row.symbol.upper(): row for row in ca_join.rows}
        raw_by_symbol = list_raw_bars_by_symbol(set(symbols), through=day)
        output: dict[str, ScannerBarBundle] = {}
        for symbol in symbols:
            instrument = identity_by_symbol.get(symbol)
            ca_row = ca_by_symbol.get(symbol)
            if instrument is None:
                output[symbol] = ScannerBarBundle(reason="WAIT_R13_A2_IDENTITY")
                continue
            if ca_row is None:
                output[symbol] = ScannerBarBundle(reason="WAIT_R13_R14_ROW")
                continue
            bars, reasons = build_adjusted_closed_bars(
                instrument=instrument,
                raw_bars=raw_by_symbol.get(symbol, []),
                decision_at=batch5.decision_at,
                ca_row=ca_row,
            )
            closed = tuple(
                bar
                for bar in bars
                if bar.identity.is_closed
                and bar.identity.close_time <= batch5.decision_at
            )
            if reasons:
                output[symbol] = ScannerBarBundle(reason=str(reasons[0]))
                continue
            if not closed:
                output[symbol] = ScannerBarBundle(
                    reason="WAIT_R13_CLOSED_HISTORY"
                )
                continue
            versions = {bar.identity.adjustment_version for bar in closed}
            if len(versions) != 1:
                output[symbol] = ScannerBarBundle(
                    reason="WAIT_R13_ADJUSTMENT_MIXED"
                )
                continue
            lineage_payload = {
                "r5RunHash": batch5.run_hash,
                "r14RunHash": batch5.r14_run_hash,
                "barIds": [bar.identity.bar_id for bar in closed],
                "rawHashes": [bar.identity.raw_hash for bar in closed],
                "adjustmentVersion": next(iter(versions)),
            }
            lineage_hash = hashlib.sha256(
                json.dumps(
                    lineage_payload, sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest()
            output[symbol] = ScannerBarBundle(
                bars=closed,
                input_status="READY",
                reason=None,
                adjustment_version=next(iter(versions)),
                lineage_hash=lineage_hash,
            )
        return output
    except Exception:
        return _missing_bundles(symbols, "WAIT_R13_ADJUSTED_BAR_LOAD")


def build_native_core_run(
    *,
    r5: R5StructureBatchV1 | None = None,
    pk_probe: Callable[[], Any] | None = None,
) -> NativeCoreRunV1:
    """Build the native-core run from the last hash-matched R5 batch."""
    batch5 = r5 if r5 is not None else latest_r5_structure_batch()
    if batch5 is None:
        raise ValueError("WAIT_R8_R5_NOT_READY")

    rows: list[NativeCoreRowV1] = []
    matched_count = 0
    bars_map = _adjusted_bars_bulk(batch5)
    warmup_tally: Counter[str] = Counter()
    for row in batch5.rows:
        bundle = bars_map.get(
            row.symbol.upper(),
            ScannerBarBundle(reason="WAIT_R13_ADJUSTED_BARS"),
        )
        matches = _matches_for_row(row, bundle)
        reps = representative_matches(matches)
        guidance_reps = representative_guidance_chips(matches)
        row_matched = tuple(m.scanner_id for m in matches if m.matched)
        guidance_match = any(
            m.matched and m.family == "STRUCTURE" for m in matches
        )
        if row_matched:
            matched_count += 1
        completeness = (
            1.0
            if getattr(row, "metrics", None) is not None
            and bundle.input_status == "READY"
            else 0.5
            if getattr(row, "metrics", None) is not None
            else 0.0
        )
        why: list[str] = []
        if not row_matched:
            why.append("NO_NATIVE_CORE_MATCH")
        if bundle.reason:
            why.append(bundle.reason)
        warm_kept = 0
        for m in matches:
            if not m.matched and m.reason_code:
                code = str(m.reason_code)
                if code.startswith("INPUT_INCOMPLETE_WARMUP"):
                    warmup_tally[code] += 1
                    if warm_kept >= 6:
                        continue  # per-row noise cap; tally keeps the full count
                    warm_kept += 1
                why.append(code)
        if any(m.matched and m.correlated_possible for m in matches):
            why.append("CORRELATED_POSSIBLE_NOT_INDEPENDENT")
        rows.append(
            NativeCoreRowV1(
                symbol=row.symbol,
                candidateId=row.candidate_id,
                lookbackBars=len(bundle.bars),
                detectedSetups=row.detected_setups,
                candidateDirection=str(row.evidence_direction),
                matches=matches,
                representativeClaimIds=tuple(
                    m.claim_id for m in reps if m.claim_id is not None
                ),
                representativeGuidanceIds=tuple(
                    match.scanner_id for match in guidance_reps
                ),
                guidanceMatch=guidance_match,
                completeness=completeness,
                why=tuple(why),
            )
        )

    identity_payload = {
        "definitionHashes": {
            d.scanner_id: d.parameter_hash for d in NATIVE_CORE_DEFINITIONS
        },
        "r5RunHash": batch5.run_hash,
        "r14RunHash": batch5.r14_run_hash,
        "profileVersion": PROFILE_VERSION,
        "rows": [row.model_dump(mode="json", by_alias=True) for row in rows],
    }
    run_hash = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    from ..selection.contracts import stable_id

    return NativeCoreRunV1(
        runId=stable_id("native-core", batch5.run_id, run_hash),
        runHash=run_hash,
        r5RunHash=batch5.run_hash,
        r14RunHash=batch5.r14_run_hash,
        tradingDate=batch5.trading_date,
        builtAt=batch5.decision_at,
        definitions=NATIVE_CORE_DEFINITIONS,
        rows=tuple(rows),
        matchedCount=matched_count,
        warnings=(
            GUIDANCE_COPY,
            "Scanners wrap R5 closed-bar claims; they never confirm or rank.",
            "R13 guidance uses hash-matched R5/R14 adjusted closed EOD bars.",
            _pk_shadow_warning(pk_probe),
        )
        + (
            (
                "WARMUP_TALLY "
                + ", ".join(
                    f"{code}={count}"
                    for code, count in sorted(warmup_tally.items())
                ),
            )
            if warmup_tally
            else ()
        ),
    )


def attach_native_matches_to_s3(batch, run: NativeCoreRunV1):
    """Return the S3 batch with nativeCoreMatches attached; rank untouched.

    Only the batch-level map gains entries; rows are byte-identical, so the
    R2/S3 attention order cannot change.
    """
    matches: dict[str, tuple[str, ...]] = {}
    for row in run.rows:
        ids = row.matched_ids
        if ids:
            matches[row.symbol] = ids
    return batch.model_copy(update={"native_core_matches": matches})


__all__ = [
    "ACCEPTANCE_CEILING",
    "GUIDANCE_COPY",
    "NativeCoreRowV1",
    "NativeCoreRunV1",
    "NativeScannerMatchV1",
    "PROFILE_ID",
    "SCHEMA_VERSION",
    "attach_native_matches_to_s3",
    "build_native_core_run",
    "representative_guidance_chips",
    "representative_matches",
]
