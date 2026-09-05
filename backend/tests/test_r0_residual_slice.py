from __future__ import annotations

import pytest
from pydantic import ValidationError

from trendforge_api.selection.contracts import (
    DataMode,
    EvidenceDirection,
    EvidenceFamily,
    GateOutcome,
    InstrumentIdentity,
    SelectionCandidate,
    SelectionGateResult,
    SelectionScanRun,
    SelectionState,
    StateCeiling,
    stable_id,
)
from trendforge_api.source_extended_field_proofs import (
    ALLOWED_EXTENDED_FIELDS,
    proof_for_source,
)
from trendforge_api.source_inventory_compiler import (
    DEFAULT_WORKBOOK,
    EXTENDED_SOURCE_CONTRACT_FIELDS,
    compile_default_inventory,
    compile_inventory,
    file_sha256,
    load_master_inventory_rows,
)
from trendforge_api.source_overlap_resolutions import (
    OverlapDisposition,
    OverlapResolution,
    OverlapResolutionState,
    EvidenceBasis,
    REVIEWED_OVERLAP_RESOLUTIONS,
    REVIEWED_WORKBOOK_SHA256,
    resolve_dataset_root_identity,
)
from trendforge_api.intraday_stock_details import (
    IntradayStockDetailCandidate,
    legacy_discovery_state,
)
from trendforge_api.market_activity import legacy_activity_state
from datetime import datetime, timezone


UTC = timezone.utc
AS_OF = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
HASH = "a" * 64


def _candidate_kwargs(**overrides):
    instrument = InstrumentIdentity.create(
        exchange="NSE",
        segment="EQ",
        symbol="TEST",
        isin="INE000A01010",
        series="EQ",
    )
    run = SelectionScanRun.create(
        profile_id="PRF-TEST",
        profile_version="1",
        as_of=AS_OF,
        universe_version="u1",
        data_mode=DataMode.EOD_RESEARCH,
        eligible_count=1,
        scanned_count=1,
    )
    payload = {
        "candidateId": stable_id("cand", run.run_id, instrument.instrument_id),
        "runId": run.run_id,
        "instrument": instrument,
        "market": "NSE",
        "profileId": run.profile_id,
        "profileVersion": run.profile_version,
        "timeframe": "1d",
        "state": SelectionState.WAIT,
        "stateCeiling": StateCeiling.WAIT,
        "evidenceDirection": EvidenceDirection.BULLISH,
        "discoveryReason": "Research wait.",
        "familySupports": (EvidenceFamily.STRUCTURE,),
        "topReason": "Research wait.",
        "nextConfirmation": "Need official proof.",
        "invalidationCondition": "Missing proof.",
        "context": "CROSS-014 quarantine fixture.",
        "freshness": "UNKNOWN",
        "completeness": 0.1,
        "whatChanged": "None.",
        "evidenceStrength": 0.1,
        "gateResults": (
            SelectionGateResult(
                code="WAIT_SOURCE_CONTRACT",
                outcome=GateOutcome.WAIT,
                blocksConfirmed=True,
                reason="CROSS-014 fixture remains blocked until official proof exists.",
            ),
        ),
        "sourceAgesSeconds": {},
        "dataMode": DataMode.EOD_RESEARCH,
        "demoOnly": True,
        "executable": False,
    }
    payload.update(overrides)
    return payload


def test_cross014_detail_score_cannot_enter_selection_candidate() -> None:
    with pytest.raises(ValidationError, match="FUS-008"):
        SelectionCandidate(**_candidate_kwargs(detailScore=82.5))


def test_cross014_combined_score_cannot_enter_selection_candidate() -> None:
    with pytest.raises(ValidationError, match="FUS-008"):
        SelectionCandidate(**_candidate_kwargs(combined_score=0.9))


def test_cross014_legacy_state_ignores_score_and_direction() -> None:
    for score in (0.0, 54.9, 55.0, 82.5, 99.0, 100.0):
        assert legacy_discovery_state(0.49, detail_score=score) == "WAIT_SOURCE"
        assert legacy_discovery_state(0.5, detail_score=score) == "WAIT_CONFIRMATION"
        assert legacy_discovery_state(1.0, detail_score=score) == "WAIT_CONFIRMATION"
    assert legacy_discovery_state(0.99, detail_score=100.0) != "WATCH_LONG"
    assert legacy_discovery_state(0.99, detail_score=100.0) != "WATCH_SHORT"
    assert legacy_activity_state(1.0, stale=False) == "WAIT_CONFIRMATION"
    assert legacy_activity_state(0.74, stale=False) == "WAIT_PARTIAL_SOURCE"
    assert legacy_activity_state(1.0, stale=True) == "WAIT_STALE"


def test_cross014_discovery_score_does_not_set_state_or_strength() -> None:
    candidate = IntradayStockDetailCandidate(
        symbol="TEST",
        state="WATCH_LONG",
        direction_hint="BULLISH_EVIDENCE",
        detail_score=99.0,
    )
    decision = SelectionCandidate(**_candidate_kwargs())
    assert decision.state is SelectionState.WAIT
    assert decision.evidence_strength == 0.1
    assert decision.evidence_strength != candidate.detail_score / 100
    assert "detail_score" not in decision.model_dump()
    assert decision.executable is False


def test_tdg_gap_001_does_not_infer_catalog_fields() -> None:
    assert set(EXTENDED_SOURCE_CONTRACT_FIELDS) == ALLOWED_EXTENDED_FIELDS
    assert proof_for_source("nse_equity_universe") is None
    ban = proof_for_source("nse_fno_ban")
    assert ban is not None
    assert ban.fields["timezone"] == "Asia/Kolkata"
    assert ban.fields["publication_calendar"] == "NSE_FO_TRADING_DAYS"
    assert ban.fields["rate_budget"].startswith("SHARED_NSE_DOMAIN_CAP")
    assert ban.fields["circuit_breaker_policy"].startswith("SHARED_NSE_DOMAIN_BREAKER")
    assert "rate_budget" not in ban.waivers
    report = compile_default_inventory()
    assert report.source_activation_ready is False
    assert report.gate_authorized_source_key_count == 0
    for contract in report.source_contracts:
        schema = contract.extended_fields.get("schema_version", "")
        assert not schema.startswith("STRUCTURED_PARSER")
        assert contract.extended_fields.get("publication_calendar") != "daily"
        assert contract.gate_permission is False
    ban_contracts = [
        item
        for item in report.source_contracts
        if item.source_contract_id == "nse_fno_ban"
    ]
    if ban_contracts:
        assert ban_contracts[0].extended_fields["schema_version"] == "nse_fo_secban_csv_v1"
        assert ban_contracts[0].extended_fields["rate_budget"].startswith("SHARED_NSE_DOMAIN_CAP")
        assert "rate_budget" not in ban_contracts[0].missing_extended_fields


def test_cross007_unreviewed_roots_stay_unspecified() -> None:
    group, resolver, cap = resolve_dataset_root_identity(
        urls=["https://example.com/unknown.csv"],
        source_keys=["unknown_source"],
        overlap_resolutions=(),
    )
    assert group == "UNSPECIFIED"
    assert resolver == "UNSPECIFIED"
    assert cap == "UNSPECIFIED_NO_VOTE"


def test_cross007_reviewed_overlap_sets_mirror_without_gate() -> None:
    resolution = OverlapResolution(
        canonical_url="https://archives.nseindia.com/content/nsccl/fao_participant_oi_10072026.csv",
        contract_ids=("nse_fo_bhavcopy", "nse_participant_oi"),
        disposition=OverlapDisposition.PARENT_CHILD_CONTRACT,
        canonical_dataset_root_id="nse_fo_reports",
        evidence_reason="Reviewed parent/child FO reports.",
        evidence_basis=(EvidenceBasis.CONTRACT_REVIEW, EvidenceBasis.WORKBOOK_LINEAGE),
        resolution_version="test",
        reviewed_at="2026-07-23",
    )
    group, resolver, cap = resolve_dataset_root_identity(
        urls=[resolution.canonical_url],
        source_keys=["nse_participant_oi"],
        overlap_resolutions=(resolution,),
    )
    assert group == "nse_fo_reports"
    assert resolver == OverlapDisposition.PARENT_CHILD_CONTRACT.value
    assert cap == "REVIEWED_NO_GATE"


def test_cross007_compiler_roots_do_not_unlock_execution() -> None:
    report = compile_default_inventory()
    assert report.execution_authorized_count == 0
    reviewed = [
        root
        for root in report.dataset_roots
        if root.mirror_group_id != "UNSPECIFIED"
    ]
    for root in reviewed:
        assert root.can_unlock_execution is False
        assert root.fallback_authority_cap in {
            "REVIEWED_NO_GATE",
            "UNOFFICIAL_CANNOT_INHERIT_OFFICIAL",
        }


def test_h1a0_regression_does_not_authorize() -> None:
    report = compile_default_inventory()
    assert report.h1a0_acceptance_total == 6
    assert report.invalid_overlap_resolution_count == 0
    assert report.source_activation_ready is False
    assert report.gate_authorized_source_key_count == 0
    failed = [item for item in report.acceptance if not item.passed]
    assert all(item.id == "H1A0-04" for item in failed)
    assert report.h1a0_acceptance_passed == 6
    assert report.stale_overlap_resolution_count == 0


def test_workbook_pin_covers_reviewed_identities() -> None:
    if not DEFAULT_WORKBOOK.exists():
        pytest.skip("master inventory workbook not present")
    current = file_sha256(DEFAULT_WORKBOOK)
    assert current == REVIEWED_WORKBOOK_SHA256
    assert len(REVIEWED_OVERLAP_RESOLUTIONS) == 32
    rows, path, digest = load_master_inventory_rows(DEFAULT_WORKBOOK)
    identity = compile_inventory(
        rows,
        workbook_path=path,
        workbook_sha256=digest,
        overlap_resolutions=REVIEWED_OVERLAP_RESOLUTIONS,
        expected_resolution_workbook_sha256=digest,
    )
    assert identity.stale_overlap_resolution_count == 0
    assert identity.invalid_overlap_resolution_count == 0
    unexplained = {
        rec.canonical_url
        for rec in identity.overlap_resolution_records
        if rec.state is OverlapResolutionState.UNEXPLAINED_OVERLAP
    }
    assert unexplained == set()
    assert identity.h1a0_acceptance_passed == 6
    urls = {item.canonical_url for item in REVIEWED_OVERLAP_RESOLUTIONS}
    assert "https://archives.nseindia.com/content/equities/bulk.csv" in urls
    assert "https://www.amfiindia.com/online-center/portfolio-disclosure" in urls
    assert (
        "https://www.mcxindia.com/market-operations/clearing-settlement/delivery-reports"
        in urls
    )
