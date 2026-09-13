from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from trendforge_api import storage
from trendforge_api.market_data_registry import load_market_data_registry
from trendforge_api.market_data_service import (
    MarketDataService,
    ParameterContext,
    ParsedSourcePayload,
    RawAcquisition,
)
from trendforge_api.market_data_store import ManifestStatus, MarketDataStore
from trendforge_api.nse_eod_ingestion import _persist_fetched_artifact
from trendforge_api.selection import r18_governance as governance
from trendforge_api.selection import r18_history_store as history_store
from trendforge_api.selection import r18_store
from trendforge_api.selection.r18_history_v2 import canonical_json
from trendforge_api.retention_coverage import audit_coverage
from trendforge_api.selection.cash_a1_staging import (
    persist_cash_staging,
    stage_cash_last_good,
)
from trendforge_api.selection.cash_a2_identity import (
    build_cash_identity_batch,
    latest_cash_identity,
    persist_cash_identity,
)
from trendforge_api.selection.cash_a4_history import (
    build_cash_history_batch,
    list_raw_bars,
    persist_cash_history,
)
from trendforge_api.selection.cash_post_commit import (
    CashPipelineRunContext,
    _r16_stage_state,
    run_existing_cash_pipeline,
)
from trendforge_api.selection.inventory_source_bundle import latest_inventory_source_bundle
from trendforge_api.selection.r14_live import latest_r14_ca_join
from trendforge_api.selection.r16_store import apply_r16_schema
from trendforge_api.selection.r5_live import (
    build_adjusted_closed_bars,
    latest_r5_structure_batch,
)

TRADE_DATE = date(2026, 8, 14)
SYMBOLS = ("RELIANCE", "TCS", "INFY", "HDFCBANK")
ISINS = {
    "RELIANCE": "INE002A01018",
    "TCS": "INE467B01029",
    "INFY": "INE009A01021",
    "HDFCBANK": "INE040A01034",
}


def _at_close(day: date) -> datetime:
    # 16:30 IST, safely after the NSE cash close.
    return datetime(day.year, day.month, day.day, 11, 0, tzinfo=UTC)


def _trading_days(through: date, count: int) -> tuple[date, ...]:
    days: list[date] = []
    cursor = through
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return tuple(reversed(days))


def _records(day: date) -> list[dict[str, Any]]:
    # Cross-sectional differences make RELIANCE a deterministic bullish WATCH
    # candidate while every session remains a valid immutable history input.
    specs = {
        "RELIANCE": (100.0, 112.0, 114.0, 99.0, 4_000_000.0),
        "TCS": (100.0, 102.0, 103.0, 99.0, 2_000_000.0),
        "INFY": (100.0, 100.0, 101.0, 99.0, 1_000_000.0),
        "HDFCBANK": (100.0, 98.0, 101.0, 97.0, 500_000.0),
    }
    rows: list[dict[str, Any]] = []
    for symbol in SYMBOLS:
        previous, close, high, low, volume = specs[symbol]
        rows.append(
            {
                "tradeDate": day.isoformat(),
                "symbol": symbol,
                "series": "EQ",
                "isin": ISINS[symbol],
                "open": previous,
                "high": high,
                "low": low,
                "close": close,
                "previousClose": previous,
                "volume": volume,
                "tradedValue": close * volume,
            }
        )
    return rows


class _CashSourceTransport:
    def __init__(self) -> None:
        self.raw_by_date: dict[date, bytes] = {}

    async def fetch_resolver(
        self, source_key: str, catalog_url: str, trading_date: date | None = None
    ) -> RawAcquisition:
        assert source_key == "nse_bhavcopy_eod"
        assert trading_date is not None
        body = json.dumps(
            {"records": _records(trading_date)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        self.raw_by_date[trading_date] = body
        return RawAcquisition.success(
            source_url=catalog_url,
            status_code=200,
            media_type="application/json",
            content=body,
            payload=json.loads(body),
            fetched_at=_at_close(trading_date),
        )

    async def fetch_endpoint(
        self, endpoint_key: str, parameters: dict[str, str]
    ) -> RawAcquisition:
        raise AssertionError(
            f"cash fixture must use the resolver path, got {endpoint_key} {parameters}"
        )


def _cash_normalizer(
    _contract, acquisitions: tuple[RawAcquisition, ...], context: ParameterContext
) -> ParsedSourcePayload:
    assert len(acquisitions) == 1
    payload = json.loads(acquisitions[0].content)
    records = tuple(payload["records"])
    return ParsedSourcePayload(
        parser_state="PARSED_STRUCTURED",
        records=records,
        data_date=context.trading_date,
        payload={"fixture": "03E_SOURCE_TO_END"},
        source_row_count=len(records),
    )


def _context(day: date) -> ParameterContext:
    return ParameterContext(
        trading_date=day,
        market_session="CLOSED",
        symbols=SYMBOLS,
        now=_at_close(day),
    )


def _index_csv(day: date, seq: int) -> bytes:
    """Synthetic NSE index-close bytes (TEST DATA ONLY).

    Ingested through the canonical ``_persist_fetched_artifact`` writer so the
    real index parser, snapshot archive and parse-result store back S2's
    ``nse_index_close_eod`` last-good rows. No direct SQL, no network.
    """
    stamp = day.strftime("%d-%m-%Y")
    nifty_close = 25_000.0 + seq * 5.0
    nifty_prev = 25_000.0 + (seq - 1) * 5.0 if seq else 24_995.0
    nifty_pts = round(nifty_close - nifty_prev, 1)
    nifty_pct = round(nifty_pts / nifty_prev * 100.0, 2)
    vix_close = round(13.0 + (seq % 5) * 0.1, 1)
    vix_pct = round(0.1 / (vix_close - 0.1) * 100.0, 2)
    return (
        "Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,"
        "Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.)\n"
        f"Nifty 50,{stamp},{nifty_prev},{nifty_close + 20},{nifty_prev - 20},"
        f"{nifty_close},{nifty_pts},{nifty_pct},300000000,25000\n"
        f"Nifty Bank,{stamp},51000,51500,50900,51400.5,150.5,0.29,100000000,15000\n"
        f"India VIX,{stamp},13.2,13.6,12.9,{vix_close},0.1,{vix_pct},0,0\n"
    ).encode()


def test_r16_stage_state_wait_is_blocked_with_reason() -> None:
    state, output_id, detail = _r16_stage_state(        {
            "replay": {
                "state": "WAIT",
                "datasetRunCount": 0,
                "rejectedS8": [{"runId": "s8-fixture", "reason": "WAIT_FIXTURE"}],
            }
        }
    )
    assert state == "BLOCKED"
    assert output_id is None
    assert "WAIT_FIXTURE" in detail
    assert "hypotheses=0" in detail


def test_r16_stage_state_complete_requires_dataset_run_id() -> None:
    state, output_id, detail = _r16_stage_state(
        {
            "dataset": {"runId": "dataset-fixture"},
            "replay": {
                "state": "COMPLETE",
                "datasetRunCount": 1,
                "hypothesisCount": 3,
                "observationsAppended": 0,
            },
        }
    )
    assert state == "COMPLETED"
    assert output_id == "dataset-fixture"
    assert "3 frozen hypotheses" in detail


def test_source_to_s8_retains_exact_r5_history_before_r16(tmp_path: Path, monkeypatch) -> None:
    """Prove exact source -> R5 -> S8 retention and truthful R16 boundary state."""

    store = MarketDataStore(
        root=tmp_path / "market-data",
        db_path=tmp_path / "trendforge.db",
    )
    monkeypatch.setattr(storage, "DB_PATH", store.db_path)
    storage._INITIALIZED_DB_PATHS.clear()

    transport = _CashSourceTransport()
    service = MarketDataService(
        transport=transport,
        normalizer=_cash_normalizer,
        store=store,
    )
    contract = load_market_data_registry().by_key["nse_bhavcopy_eod"]

    final_result = None
    for seq, day in enumerate(_trading_days(TRADE_DATE, 22)):
        result = asyncio.run(
            service.run_source(
                contract,
                context=_context(day),
                run_id=f"source-{day.isoformat()}",
                slot="eod",
            )
        )
        assert result.status is ManifestStatus.SUCCESS_NEW
        assert result.raw_content_hashes == (
            hashlib.sha256(transport.raw_by_date[day]).hexdigest(),
        )

        # Index close companions through the canonical ingestion writer so S2
        # weather (and therefore the S8 lineage R16 requires) is date-bound.
        index_saved = _persist_fetched_artifact(
            {
                "state": "FETCHED",
                "sourceKey": "nse_index_close_eod",
                "date": day,
                "url": (
                    "https://nsearchives.nseindia.com/content/indices/"
                    f"ind_close_all_{day.strftime('%d%m%Y')}.csv"
                ),
                "status": 200,
                "headers": {"content-type": "text/csv"},
                "content": _index_csv(day, seq),
            }
        )
        assert index_saved["parserState"] == "PARSED_STRUCTURED"

        # Use the same canonical A1 -> A2 -> A4 owners as the production pipeline
        # to accumulate immutable history; no direct SQL fixture inserts.
        staging = persist_cash_staging(stage_cash_last_good(store))
        identity = persist_cash_identity(build_cash_identity_batch(staging, store=store))
        history = persist_cash_history(
            build_cash_history_batch(identity, decision_at=_at_close(day))
        )
        assert history.raw_bar_count == len(SYMBOLS)
        final_result = result

    assert final_result is not None
    status = apply_r16_schema()
    assert status["applied"] is True
    assert status["retentionReady"] is True

    execution = run_existing_cash_pipeline(
        CashPipelineRunContext(
            store=store,
            collector_run_id="source-to-end-final",
            trading_date=TRADE_DATE,
            results={"nse_bhavcopy_eod": final_result},
            trigger_source_keys=("nse_bhavcopy_eod",),
            fingerprint="e" * 64,
            observed_at=_at_close(TRADE_DATE),
        )
    )
    states = {stage.stage_id: stage for stage in execution.stages}
    assert states["R5"].state == "COMPLETED"
    assert states["S8"].state == "COMPLETED"
    assert execution.s8_run_id is not None

    r1 = latest_inventory_source_bundle()
    assert r1 is not None
    cash_source = next(
        row for row in r1.source_records if row.source_key == "nse_bhavcopy_eod"
    )
    assert cash_source.raw_content_hash == hashlib.sha256(
        transport.raw_by_date[TRADE_DATE]
    ).hexdigest()

    r5 = latest_r5_structure_batch()
    assert r5 is not None
    reliance = next(row for row in r5.rows if row.symbol == "RELIANCE")
    assert reliance.history_count >= 21
    assert reliance.facts, "fixture must exercise real R5 closed-bar analysis"
    used_bar_ids = {
        str(bar_id)
        for fact in reliance.facts
        for bar_id in fact.payload.get("bar_ids", ())
    }
    assert len(used_bar_ids) >= 21

    # R5 facts name adjusted ClosedBar IDs, while cash_raw_session_bars stores
    # canonical raw-bar IDs. Rebuild with the same accepted R5 helper so this
    # probe compares exact identities instead of guessing an ID translation.
    identity = latest_cash_identity()
    ca_join = latest_r14_ca_join()
    assert identity is not None
    assert ca_join is not None
    instrument = next(
        row.instrument for row in identity.rows if row.instrument.symbol == "RELIANCE"
    )
    ca_row = next(row for row in ca_join.rows if row.symbol == "RELIANCE")
    raw_bars = list_raw_bars("RELIANCE", through=TRADE_DATE)
    closed_bars, waits = build_adjusted_closed_bars(
        instrument=instrument,
        raw_bars=raw_bars,
        decision_at=r5.decision_at,
        ca_row=ca_row,
    )
    assert waits == ()
    closed_by_id = {bar.identity.bar_id: bar for bar in closed_bars}
    assert used_bar_ids <= set(closed_by_id)
    used_hashes = {closed_by_id[bar_id].identity.raw_hash for bar_id in used_bar_ids}
    assert len(used_hashes) >= 21
    assert set(reliance.source_artifact_hashes) == used_hashes

    # Read the immutable S8 publication itself. 03E must not accept an S8/R16
    # chain whose R5 historical inputs were never protected by that S8 decision.
    conn = storage.connect()
    try:
        publication = conn.execute(
            "SELECT lineage_json, status FROM historical_retention_publications "
            "WHERE artifact_type='S8_DECISION_VERSION' AND artifact_id=?",
            (execution.s8_run_id,),
        ).fetchone()
        hypothesis_rows = conn.execute(
            "SELECT payload_json FROM pit_hypotheses "
            "WHERE source_s8_run_id=? AND symbol='RELIANCE' "
            "ORDER BY horizon_sessions",
            (execution.s8_run_id,),
        ).fetchall()
    finally:
        conn.close()
    assert publication is not None
    assert publication["status"] == "PUBLISHED"
    lineage = json.loads(publication["lineage_json"])
    retained_hashes = {
        str(root["contentHash"])
        for root in lineage["evidenceRoots"]
        if root.get("contentHash")
    }
    assert used_hashes <= retained_hashes, (
        "S8 retention omitted immutable A4/R5 bar artifacts used by the decision; "
        f"missing={sorted(used_hashes - retained_hashes)}"
    )

    # The fixture now carries index-close companions, so S2 is date-bound and the
    # S8 lineage is R16-eligible. R16 must therefore complete with hypotheses
    # whose count exactly matches the stored rows — never COMPLETED with zero.
    assert states["R16"].state == "COMPLETED"
    assert states["R16"].output_id is not None
    assert len(hypothesis_rows) >= 1

    # --- M2: R18 chain from the real R16 records (TEST DATA ONLY) ---
    # Members mirror canonical pit_hypotheses/pit_observations rows exactly;
    # only research-configuration labels (strategy family, formula set, model
    # artifact bytes) are declared fixture constants, documented as such.
    # No direct SQL writes anywhere in this test.
    from trendforge_api.r16_retention import verified_record
    from trendforge_api.selection.r16_pit import _payload_hash as _r16_hash

    r18_schema = r18_store.apply_rhist03d_schema()
    assert r18_schema["applied"] is True

    direction_of = {"BULLISH": "LONG", "BEARISH": "SHORT"}
    members: list[dict[str, Any]] = []
    conn = storage.connect()
    try:
        instrument_by_symbol = {
            str(row.instrument.symbol): str(row.instrument.instrument_id)
            for row in identity.rows
        }
        pairs = [
            str(json.loads(row["payload_json"])["hypothesisId"])
            for row in conn.execute(
                "SELECT payload_json FROM pit_hypotheses ORDER BY hypothesis_id"
            ).fetchall()
        ]
        verified: list[tuple[dict[str, Any], Any, dict[str, Any], Any]] = []
        for hypothesis_id in pairs:
            _, decision, decision_pub = verified_record(
                conn, "DECISION_VERSION", hypothesis_id
            )
            obs_row = conn.execute(
                "SELECT payload_json FROM pit_observations WHERE hypothesis_id=?",
                (hypothesis_id,),
            ).fetchone()
            assert obs_row is not None, f"R16 hypothesis without outcome: {hypothesis_id}"
            _, outcome, outcome_pub = verified_record(
                conn,
                "OUTCOME",
                str(json.loads(obs_row["payload_json"])["observationId"]),
            )
            verified.append((decision, decision_pub, outcome, outcome_pub))
    finally:
        conn.close()

    feature_manifest_id = "r16-source-features"
    formula_set_version = "fixture-formula-v1"
    formula_set_hash = hashlib.sha256(b"03e-source-to-end-formula-v1").hexdigest()
    for decision, decision_pub, outcome, outcome_pub in verified:
        symbol = str(decision["symbol"])
        hz = int(decision["horizonSessions"])
        roots: dict[tuple[str, str], dict[str, str]] = {}
        for pub in (decision_pub, outcome_pub):
            for root in pub.evidence_roots:
                if root.content_hash is not None:
                    roots[(root.role, str(root.content_hash).lower())] = {
                        "role": root.role,
                        "contentHash": str(root.content_hash).lower(),
                    }
        feature_hash = hashlib.sha256(
            canonical_json(decision.get("sourceFeatureHashes") or {}).encode()
        ).hexdigest()
        members.append(
            {
                "instrument_id": instrument_by_symbol[symbol],
                "opportunity_id": (
                    f"{symbol}:{decision.get('timeframe')}:continuation:"
                    f"{decision.get('direction')}:{hz}"
                ),
                "profile_id": str(decision["profileId"]),
                "profile_version": str(decision["profileVersion"]),
                "strategy_id": "CONTINUATION",
                "strategy_version": "1.0.0",
                "setup_id": str(decision["setupPolicyId"]),
                "setup_episode_id": str(decision["hypothesisId"]),
                "timeframe": str(decision["timeframe"]),
                "horizon": str(hz),
                "direction": direction_of[str(decision["direction"])],
                "decision_version_id": str(decision["hypothesisId"]),
                "decision_version_hash": _r16_hash(decision),
                "decision_at": str(decision["decisionCutoffAt"]),
                "decision_data_cutoff": str(decision["decisionCutoffAt"]),
                "max_feature_available_at": str(decision["maxInputAvailableAt"]),
                "public_state": str(decision["publicState"]),
                "outcome_id": str(outcome["observationId"]),
                "outcome_hash": _r16_hash(outcome),
                "outcome_state": str(outcome["status"]),
                "outcome_available_at": str(outcome["labelComputedAt"]),
                "label_available_at": str(outcome["labelComputedAt"]),
                "feature_manifest_id": feature_manifest_id,
                "feature_manifest_hash": feature_hash,
                "formula_set_version": formula_set_version,
                "formula_set_hash": formula_set_hash,
                "input_hashes": [str(h) for h in decision.get("sourceBarHashes", ())],
                "evidence_roots": sorted(roots.values(), key=lambda r: r["role"]),
                "split": "TRAIN",
                "fold": "F1",
                "inclusion_reason": "BASE_POPULATION",
            }
        )

    decision_cutoff = datetime(2026, 8, 14, 11, 0, tzinfo=UTC)
    label_cutoff = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    build_cutoff = datetime(2026, 8, 14, 13, 0, tzinfo=UTC)
    label_policy = str(verified[0][0]["labelPolicyVersion"])
    cost_model = str(verified[0][0]["costModelVersion"])

    def _manifest_feature_hash(rows: list[Any]) -> str:
        assert rows, "dataset needs members"
        first = rows[0]["feature_manifest_hash"]
        assert all(row["feature_manifest_hash"] == first for row in rows)
        return str(first)

    def _manifest(dataset_id: str, purpose: str, rows: list[dict[str, Any]]) -> Any:
        return governance.build_frozen_dataset_manifest(
            dataset_id=dataset_id,
            dataset_version="1.0.0",
            purpose=purpose,
            created_at=build_cutoff,
            decision_cutoff=decision_cutoff,
            label_cutoff=label_cutoff,
            build_cutoff=build_cutoff,
            population_policy_id="R16_COMPLETE_BASE_POPULATION",
            population_policy_version="1.0.0",
            label_policy_id="R16_LABEL_POLICY",
            label_policy_version=label_policy,
            feature_manifest_id=feature_manifest_id,
            feature_manifest_hash=_manifest_feature_hash(rows),
            formula_set_version=formula_set_version,
            formula_set_hash=formula_set_hash,
            cost_model_version=cost_model,
            members=tuple(rows),
            base_population=True,
            source_population_count=len(rows),
            code_digest=None,
        )

    built_members = [
        governance.build_frozen_dataset_member(**values) for values in members
    ]
    train_rows = [
        row.model_dump(mode="python", by_alias=False) for row in built_members[:6]
    ]
    eval_rows = [
        row.model_dump(mode="python", by_alias=False) for row in built_members[6:]
    ]
    train_manifest = _manifest("DS-03E-TRAIN", "TRAIN", train_rows)
    eval_manifest = _manifest("DS-03E-EVAL", "EVALUATION", eval_rows)
    assert history_store.persist_frozen_dataset(train_manifest)["stored"] is True
    assert history_store.persist_frozen_dataset(eval_manifest)["stored"] is True
    r18_store.finalize_rhist03d_artifact(
        "ML_DATASET", "DS-03E-TRAIN", "1.0.0", verify_parents=True
    )
    r18_store.finalize_rhist03d_artifact(
        "ML_DATASET", "DS-03E-EVAL", "1.0.0", verify_parents=True
    )

    model_created = datetime(2026, 8, 14, 13, 30, tzinfo=UTC)
    model = governance.build_governed_model_version(
        model_id="MDL-03E-SOURCE-TO-END",
        model_version="1.0.0",
        purpose="RESEARCH_EVALUATION",
        market="NSE",
        horizon="SWING",
        training_dataset=train_manifest.model_dump(mode="python", by_alias=False),
        evaluation_dataset=eval_manifest.model_dump(mode="python", by_alias=False),
        feature_set_hash=train_manifest.feature_manifest_hash,
        formula_set_hash=formula_set_hash,
        model_artifact_hash=hashlib.sha256(b"03e-fixture-model-artifact").hexdigest(),
        code_build_hash=hashlib.sha256(b"03e-fixture-code").hexdigest(),
        config_hash=hashlib.sha256(b"03e-fixture-config").hexdigest(),
        hyperparameters={"fixture": "03e-source-to-end-no-training"},
        random_seeds=(7,),
        cost_model_version=cost_model,
        evaluation_id="EVAL-03E-SOURCE-TO-END-1",
        evaluation_hash=eval_manifest.dataset_hash,
        created_at=model_created,
    )
    assert history_store.persist_governed_model(model) is True
    r18_store.finalize_rhist03d_artifact(
        "MODEL_VERSION", "MDL-03E-SOURCE-TO-END", "1.0.0", verify_parents=True
    )

    profile_created = datetime(2026, 8, 14, 14, 0, tzinfo=UTC)
    profile = governance.build_strategy_profile_version(
        profile_id="PRF-03E-SOURCE-TO-END",
        profile_version="1.0.0",
        strategy_id="CONTINUATION",
        strategy_version="1.0.0",
        market="NSE",
        instrument_class="EQUITY",
        horizon="SWING",
        timeframes=("EOD",),
        setups=("SWING_BREAKOUT_BREAKDOWN_V1",),
        directions=("LONG", "SHORT"),
        required_to_calculate=("closed_bars",),
        required_to_qualify=("liquidity",),
        optional_context=(),
        prohibited_for_condition=("future_data",),
        relative_strength_contract="same-time-sector-v1",
        gate_policy="tradability-v1",
        ranking_group="swing-continuation",
        risk_cost_assumptions=("cost-v1",),
        model_id="MDL-03E-SOURCE-TO-END",
        model_version="1.0.0",
        model_hash=model.model_hash,
        research_ceiling="WAIT",
        activation_allowed=False,
        created_at=profile_created,
        valid_from=profile_created,
    )
    assert history_store.persist_strategy_profile(profile) is True
    r18_store.finalize_rhist03d_artifact(
        "STRATEGY_PROFILE", "PRF-03E-SOURCE-TO-END", "1.0.0", verify_parents=True
    )

    audit = governance.build_governance_audit_record(
        audit_id="AUD-03E-SOURCE-TO-END-1",
        reviewed_artifact_type="MODEL_VERSION",
        artifact_id="MDL-03E-SOURCE-TO-END",
        artifact_version="1.0.0",
        artifact_hash=model.model_hash,
        dataset_id="DS-03E-TRAIN",
        dataset_hash=train_manifest.dataset_hash,
        model_id="MDL-03E-SOURCE-TO-END",
        model_hash=model.model_hash,
        profile_id="PRF-03E-SOURCE-TO-END",
        profile_hash=profile.content_hash,
        evaluation_id="EVAL-03E-SOURCE-TO-END-1",
        evaluation_hash=eval_manifest.dataset_hash,
        predecessor_audit_hash=None,
        decision="REVIEW",
        reviewer="03e-source-to-end-fixture",
        reason="controlled test-data review of the source-to-end chain",
        reviewed_at=datetime(2026, 8, 14, 15, 0, tzinfo=UTC),
        evidence_hash=train_manifest.evidence_root_digest,
        governance_policy_version="fixture-v1",
        pit_prerequisite_proven=True,
        resulting_state="REVIEWED",
    )
    assert history_store.persist_audit_record(audit) is True
    r18_store.finalize_rhist03d_artifact(
        "AUDIT", "AUD-03E-SOURCE-TO-END-1", "1", verify_parents=True
    )

    report = audit_coverage()
    assert report["verdict"] == "PASS"
    assert report["expectedCount"] > 0
    assert report["coveredCount"] == report["expectedCount"]
    assert report["orphanCount"] == 0
    assert report["blockingCount"] == 0
    assert report["perProducer"]["S8_DECISION_VERSION"]["expected"] == 1
    conn = storage.connect()
    try:
        all_hypotheses = conn.execute("SELECT COUNT(*) FROM pit_hypotheses").fetchone()[0]
        all_observations = conn.execute(
            "SELECT COUNT(*) FROM pit_observations"
        ).fetchone()[0]
    finally:
        conn.close()
    assert report["perProducer"]["R16_DECISION_VERSION"]["expected"] == int(
        all_hypotheses
    )
    assert report["perProducer"]["R16_OUTCOME"]["expected"] == int(all_observations)
    assert report["perProducer"]["R18_ML_DATASET"]["expected"] == 2
    again = audit_coverage()
    assert again["reportHash"] == report["reportHash"]
    assert again["verdict"] == "PASS"


def _run_eligible_pipeline(tmp_path: Path, monkeypatch: Any, tag: str) -> str:
    """Shared controlled pipeline (TEST DATA ONLY); returns the S8 run id."""
    store = MarketDataStore(
        root=tmp_path / "market-data",
        db_path=tmp_path / "trendforge.db",
    )
    monkeypatch.setattr(storage, "DB_PATH", store.db_path)
    storage._INITIALIZED_DB_PATHS.clear()

    transport = _CashSourceTransport()
    service = MarketDataService(
        transport=transport,
        normalizer=_cash_normalizer,
        store=store,
    )
    contract = load_market_data_registry().by_key["nse_bhavcopy_eod"]
    final_result = None
    for seq, day in enumerate(_trading_days(TRADE_DATE, 22)):
        result = asyncio.run(
            service.run_source(
                contract,
                context=_context(day),
                run_id=f"source-{tag}-{day.isoformat()}",
                slot="eod",
            )
        )
        staging = persist_cash_staging(stage_cash_last_good(store))
        identity = persist_cash_identity(build_cash_identity_batch(staging, store=store))
        persist_cash_history(
            build_cash_history_batch(identity, decision_at=_at_close(day))
        )
        saved = _persist_fetched_artifact(
            {
                "state": "FETCHED",
                "sourceKey": "nse_index_close_eod",
                "date": day,
                "url": (
                    "https://nsearchives.nseindia.com/content/indices/"
                    f"ind_close_all_{day.strftime('%d%m%Y')}.csv"
                ),
                "status": 200,
                "headers": {"content-type": "text/csv"},
                "content": _index_csv(day, seq),
            }
        )
        assert saved["parserState"] == "PARSED_STRUCTURED"
        final_result = result
    apply_r16_schema()
    execution = run_existing_cash_pipeline(
        CashPipelineRunContext(
            store=store,
            collector_run_id=f"source-to-end-{tag}",
            trading_date=TRADE_DATE,
            results={"nse_bhavcopy_eod": final_result},
            trigger_source_keys=("nse_bhavcopy_eod",),
            fingerprint="e" * 64,
            observed_at=_at_close(TRADE_DATE),
        )
    )
    assert execution.s8_run_id is not None
    return str(execution.s8_run_id)


def test_corrupt_s8_parent_breaks_coverage_fail_closed(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """Fault injection (TEST DATA ONLY): tampering the S8 parent payload must
    fail coverage closed, never silently stay PASS."""
    s8_run_id = _run_eligible_pipeline(tmp_path, monkeypatch, "corrupt")
    before = audit_coverage()
    assert before["verdict"] in ("PASS", "FAIL")
    conn = storage.connect()
    try:
        row = conn.execute(
            "SELECT payload_json FROM selection_scan_runs WHERE run_id=?",
            (s8_run_id,),
        ).fetchone()
        assert row is not None
        payload = json.loads(row["payload_json"])
        payload["rows"][0]["candidateId"] = "tampered-candidate"
        conn.execute(
            "UPDATE selection_scan_runs SET payload_json=? WHERE run_id=?",
            (json.dumps(payload, sort_keys=True), s8_run_id),
        )
        conn.commit()
    finally:
        conn.close()
    report = audit_coverage()
    assert report["verdict"] == "FAIL"
    statuses = {str(finding["status"]) for finding in report["findings"]}
    assert statuses & {
        "LINEAGE_BROKEN",
        "LINEAGE_MISSING",
        "INCONSISTENT_IDENTITY",
        "MISSING_RETENTION",
    }


def test_deleted_s8_artifact_leaves_retention_orphan(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """Fault injection (TEST DATA ONLY): deleting a governed artifact while its
    retention proof survives must surface orphans, never PASS."""
    s8_run_id = _run_eligible_pipeline(tmp_path, monkeypatch, "orphan")
    conn = storage.connect()
    try:
        # Fault injection only: remove the governed row plus its dependent
        # projection rows so the retention proof is left without an artifact.
        conn.execute(
            "DELETE FROM selection_state_events WHERE run_id=?", (s8_run_id,)
        )
        conn.execute(
            "DELETE FROM selection_candidates WHERE run_id=?", (s8_run_id,)
        )
        conn.execute(
            "DELETE FROM selection_scan_runs WHERE run_id=?", (s8_run_id,)
        )
        conn.commit()
    finally:
        conn.close()
    report = audit_coverage()
    assert report["verdict"] == "FAIL"
    assert report["orphanCount"] >= 1
    assert "RETENTION_ORPHAN" in {
        str(finding["status"]) for finding in report["findings"]
    }