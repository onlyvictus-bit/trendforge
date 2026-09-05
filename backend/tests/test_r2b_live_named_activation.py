from __future__ import annotations

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.hybrid_v2.tests_support.fixtures import persist_overlay_lineage
from trendforge_api.main import app
from trendforge_api.models import SourceParseResult, SourceSnapshotRecord
from trendforge_api.selection.r2b_live import (
    ACCEPTANCE_CEILING,
    CONFIRM_PATH_SOURCE_KEYS,
    SCHEMA_VERSION,
    R2BNamedActivationV1,
    R2BNamedSourceV1,
    build_r2b_named_activation,
    persist_r2b_named_activation,
)
from trendforge_api.source_cohort_r0b import R0B_COHORT


def test_constants_pin_amended_ceiling() -> None:
    assert SCHEMA_VERSION == "trendforge.named-activation.v1"
    assert ACCEPTANCE_CEILING == "LIVE_NAMED_ACTIVATION_AMENDED_EOD"
    assert CONFIRM_PATH_SOURCE_KEYS == frozenset(
        {
            "nse_bhavcopy_eod",
            "nse_fno_ban",
            "nse_fo_bhavcopy",
            "nse_index_close_eod",
            "nse_corporate_filings_actions",
        }
    )


def test_named_sources_are_r0b_cohort_and_cannot_confirm(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch, with_structure=False)
    batch = build_r2b_named_activation()
    assert batch.source_activation_ready is False
    assert batch.can_unlock_confirmed is False
    assert batch.executable is False
    assert batch.authorized_count == 0
    assert batch.may_confirm_count == 0
    assert batch.compiler_gate_authorized_count == 0
    keys = {row.source_key for row in batch.rows}
    assert keys == {item.source_key for item in R0B_COHORT}
    assert all(row.may_support_confirmed is False for row in batch.rows)
    assert all(row.r0b_can_vote is False for row in batch.rows)
    mwpl = next(row for row in batch.rows if row.source_key == "nse_mwpl_percentages")
    assert mwpl.confirm_eligible is False
    assert mwpl.activation_status == "NOT_AUTHORIZED"
    cash = next(row for row in batch.rows if row.source_key == "nse_bhavcopy_eod")
    assert cash.confirm_eligible is True
    assert cash.r0b_proven is True
    assert cash.activation_status == "WAIT_PROOF"
    assert "SOURCE_ACTIVATION_READY_FALSE" in batch.rows[0].why_wait
    assert "NO_FILE_A_ACTIVATION_AMENDMENT" in batch.rows[0].why_wait


def test_validator_rejects_activation_ready() -> None:
    row = R2BNamedSourceV1(
        source_key="nse_bhavcopy_eod",
        class_name="CASH_EOD",
        role="price_volume",
        why_wait=("R2B_NAMED_ACTIVATION_CLOSED",),
    )
    try:
        R2BNamedActivationV1(
            run_id="x",
            run_hash="y",
            r1_bundle_id="a",
            r1_bundle_hash="b",
            r2_run_id="c",
            r2_run_hash="d",
            collector_run_id="e",
            permission_fingerprint="f",
            trading_date="2026-08-14",
            decision_at=__import__("datetime").datetime(
                2026, 8, 14, 17, 0, tzinfo=__import__("datetime").UTC
            ),
            compiler_gate_authorized_count=0,
            r0b_proven_count=0,
            r0b_reviewed_count=0,
            named_source_count=1,
            source_activation_ready=True,
            rows=(row,),
        )
    except ValueError as exc:
        assert "cannot activate" in str(exc).lower() or "CONFIRMED" in str(exc)
    else:
        raise AssertionError("sourceActivationReady=true was accepted")


def test_missing_r1_r2_fails_closed(tmp_path, monkeypatch) -> None:
    from trendforge_api import storage

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r2b-empty.db")
    storage._INITIALIZED_DB_PATHS.clear()
    try:
        build_r2b_named_activation()
    except ValueError as exc:
        assert "WAIT_R2B_R1_R2_NOT_READY" in str(exc)
    else:
        raise AssertionError("empty spine was accepted")


def test_api_is_hash_scoped_and_post_405(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch, with_structure=False)
    stored = persist_r2b_named_activation(build_r2b_named_activation())
    client = TestClient(app)
    response = client.get("/api/v1/selection/named-activation")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schemaVersion"] == SCHEMA_VERSION
    assert payload["sourceActivationReady"] is False
    assert payload["canUnlockConfirmed"] is False
    assert payload["authorizedCount"] == 0
    assert payload["runId"] == stored.run_id
    one = client.get("/api/v1/selection/named-activation/nse_bhavcopy_eod")
    assert one.status_code == 200
    assert one.json()["maySupportConfirmed"] is False
    missing = client.get("/api/v1/selection/named-activation/not-a-source")
    assert missing.status_code == 404
    assert client.post("/api/v1/selection/named-activation").status_code == 405


# ---------------------------------------------------------------------------
# R2-B activation amendment (2026-08-25): observed last-good may authorize the
# five named confirm-path sources. Everything else stays fail-closed.
# ---------------------------------------------------------------------------

_FIVE = tuple(sorted(CONFIRM_PATH_SOURCE_KEYS))


def _hash(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode()).hexdigest()


def _store_current_last_good(
    monkeypatch,
    source_key: str,
    *,
    data_date: str = "2026-08-14",
    parser_state: str = "PARSED_STRUCTURED",
) -> None:
    # The amendment ledger only reads snapshot+parse evidence; the structured
    # row tables are irrelevant here, so isolate tests from their schemas.
    monkeypatch.setattr(
        storage, "save_structured_source_rows", lambda result: None
    )
    snapshot = storage.save_source_snapshot(
        SourceSnapshotRecord(
            sourceKey=source_key,
            name=source_key,
            url=f"https://www.nseindia.com/fixtures/{source_key}.csv",
            checkState="UNCHANGED",
            statusCode=200,
            contentHash=_hash(f"{source_key}-last-good"),
            contentLength=256,
            checkedAt="2026-08-14T17:00:00+00:00",
            changed=False,
        )
    )
    storage.save_source_parse_result(
        SourceParseResult(
            source_key=source_key,
            snapshot_id=snapshot.id,
            parser_state=parser_state,
            data_date=data_date,
            record_count=1 if parser_state == "PARSED_STRUCTURED" else 0,
            summary="amendment fixture structured rows",
            output={"rows": [{"symbol": "HVBTEST"}], "validEmpty": False},
            error=None,
            parsed_at="2026-08-14T17:00:00+00:00",
        )
    )


def test_amendment_authorized_when_five_last_goods_current(
    tmp_path, monkeypatch
) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch, with_structure=False)
    for key in _FIVE:
        _store_current_last_good(monkeypatch, key)
    batch = build_r2b_named_activation()
    assert batch.source_activation_ready is True
    assert batch.authorized_count == 5
    assert batch.may_confirm_count == 5
    # The amendment unlocks public research CONFIRMED only; never execution.
    assert batch.executable is False
    assert batch.can_unlock_confirmed is False
    by_key = {row.source_key: row for row in batch.rows}
    for key in _FIVE:
        row = by_key[key]
        assert row.activation_status == "AUTHORIZED"
        assert row.may_support_confirmed is True
        assert row.r0b_can_vote is False
    mwpl = by_key["nse_mwpl_percentages"]
    assert mwpl.activation_status == "NOT_AUTHORIZED"
    assert mwpl.may_support_confirmed is False


def test_missing_one_last_good_keeps_global_lock(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch, with_structure=False)
    for key in _FIVE[:-1]:  # four of five; corporate filings stays missing
        _store_current_last_good(monkeypatch, key)
    batch = build_r2b_named_activation()
    assert batch.source_activation_ready is False
    assert batch.authorized_count == 0
    assert batch.may_confirm_count == 0
    assert all(row.activation_status != "AUTHORIZED" for row in batch.rows)
    warnings_text = " ".join(batch.warnings)
    assert "R2B_LAST_GOOD_MISSING" in warnings_text


def test_stale_last_good_blocks_activation(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch, with_structure=False)
    for key in _FIVE:
        _store_current_last_good(monkeypatch, key, data_date="2026-08-01")
    batch = build_r2b_named_activation()
    assert batch.source_activation_ready is False
    assert batch.authorized_count == 0
    warnings_text = " ".join(batch.warnings)
    assert "R2B_STALE_DATA" in warnings_text or "R2B_LAST_GOOD_STALE" in warnings_text


def test_authorized_row_without_global_flip_is_rejected() -> None:
    row = R2BNamedSourceV1(
        source_key="nse_bhavcopy_eod",
        class_name="CASH_EOD",
        role="price_volume",
        r0b_proven=True,
        confirm_eligible=True,
        activation_status="AUTHORIZED",
        may_support_confirmed=True,
        why_wait=(),
    )
    try:
        R2BNamedActivationV1(
            run_id="x",
            run_hash="y",
            r1_bundle_id="a",
            r1_bundle_hash="b",
            r2_run_id="c",
            r2_run_hash="d",
            collector_run_id="e",
            permission_fingerprint="f",
            trading_date="2026-08-14",
            decision_at=__import__("datetime").datetime(
                2026, 8, 14, 17, 0, tzinfo=__import__("datetime").UTC
            ),
            compiler_gate_authorized_count=0,
            r0b_proven_count=5,
            r0b_reviewed_count=5,
            named_source_count=1,
            authorized_count=1,
            may_confirm_count=1,
            rows=(row,),
        )
    except ValueError as exc:
        assert "CONFIRMED" in str(exc) or "activate" in str(exc).lower()
    else:
        raise AssertionError("authorized row without global flip was accepted")


def test_mwpl_row_can_never_be_authorized(tmp_path, monkeypatch) -> None:
    persist_overlay_lineage(tmp_path, monkeypatch, with_structure=False)
    for key in _FIVE:
        _store_current_last_good(monkeypatch, key)
    _store_current_last_good(monkeypatch, "nse_mwpl_percentages")
    batch = build_r2b_named_activation()
    by_key = {row.source_key: row for row in batch.rows}
    assert by_key["nse_mwpl_percentages"].may_support_confirmed is False
    assert by_key["nse_mwpl_percentages"].activation_status == "NOT_AUTHORIZED"
