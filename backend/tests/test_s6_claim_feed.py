"""S6 claim-feed widening: R5-published claims reach the FUS-009 feed."""

from __future__ import annotations

from types import SimpleNamespace

from trendforge_api.selection.contracts import EvidenceDirection
from trendforge_api.selection.r3_claim_adapter import ClaimAdapterResult
from trendforge_api.selection.s6_claim_feed import (
    attach_market_context,
    merged_feed,
    structure_claims_from_r5,
)
from tests.test_m_factor_claims import _raw_bars, _rebuild, _r5_row_from_analysis


def _fake_r5_batch_with_claims(symbol: str = "TEST"):
    row, _ = _r5_row_from_analysis(EvidenceDirection.BULLISH, _raw_bars("bull"))
    structure = _rebuild(row, _raw_bars("bull"))
    batch = SimpleNamespace(
        rows=[
            SimpleNamespace(symbol=symbol, claims=tuple(structure.claims), facts=tuple(getattr(structure, "facts", ()))),
            SimpleNamespace(symbol="EMPTY", claims=(), facts=()),
        ]
    )
    return batch, structure


def _empty_cash() -> ClaimAdapterResult:
    return ClaimAdapterResult(
        claims_by_symbol={},
        facts_by_symbol={},
        source_results=(),
        suppressions_by_symbol={},
    )


def test_structure_claims_collected_per_symbol() -> None:
    batch, structure = _fake_r5_batch_with_claims("TEST")
    collected = structure_claims_from_r5(batch)
    assert set(collected) == {"TEST"}
    assert {c.feature_id for c in collected["TEST"]} == {
        c.feature_id for c in structure.claims
    }


def test_merged_feed_unions_cash_and_structure_without_loss() -> None:
    from trendforge_api.selection.contracts import (
        EvidenceClaim,
        EvidenceFamily,
        StateCeiling,
    )

    batch, structure = _fake_r5_batch_with_claims("TEST")
    first = structure.claims[0]
    cash_claim = EvidenceClaim.create(
        feature_id="FTR-040",
        feature_version="1.0.0",
        family=EvidenceFamily.PARTICIPATION,
        correlation_group="CG_ACTIVITY_SESSION",
        direction=first.direction,
        strength_before_caps=0.5,
        source_fact_ids=first.source_fact_ids,
        authority=first.authority,
        available_at=first.available_at,
        state_ceiling=StateCeiling.WATCH,
        can_support_confirmed=False,
        explanation="cash session participation fixture",
    )
    cash = ClaimAdapterResult(
        claims_by_symbol={"TEST": (cash_claim,)},
        facts_by_symbol={"TEST": ()},
        source_results=(),
        suppressions_by_symbol={"TEST": ()},
    )
    claims, facts = merged_feed(cash, batch)

    ids = [c.feature_id for c in claims["TEST"]]
    assert ids.count("FTR-040") == 1
    assert "FTR-006" in ids or "FTR-005" in ids or "FTR-007" in ids
    assert len(facts["TEST"]) >= 1

    # Dedupe proof: the exact same claim arriving twice survives once.
    dup_cash = ClaimAdapterResult(
        claims_by_symbol={"TEST": (structure.claims[0],)},
        facts_by_symbol={"TEST": ()},
        source_results=(),
        suppressions_by_symbol={"TEST": ()},
    )
    deduped, _ = merged_feed(dup_cash, batch)
    all_ids = [c.claim_id for c in deduped["TEST"]]
    assert len(all_ids) == len(set(all_ids))


def test_merged_feed_without_r5_is_cash_only() -> None:
    batch, _ = _fake_r5_batch_with_claims()
    claims, _ = merged_feed(_empty_cash(), None)
    assert claims == {}
    claims2, _ = merged_feed(_empty_cash(), batch)
    assert set(claims2) == {"TEST"}  # structure-only rows still feed


def test_market_context_attach_is_display_only() -> None:
    resolution = SimpleNamespace(model_copy=lambda **kw: ("copied", kw))
    weather = SimpleNamespace(
        regime_label="RISK_ON", trading_date="2026-08-24", why=("why1",)
    )
    out = attach_market_context(resolution, weather)
    copied, kwargs = out
    assert kwargs == {
        "update": {
            "market_context": {
                "regimeLabel": "RISK_ON",
                "tradingDate": "2026-08-24",
                "why": ("why1",),
                "canSupportConfirmed": False,
            }
        }
    }
    assert attach_market_context(None, weather) is None
    assert attach_market_context(resolution, None) is resolution


def test_r5_row_rejects_confirming_claims_at_boundary() -> None:
    import pytest

    from trendforge_api.selection.r5_live import R5StructureRowV1

    row, _ = _r5_row_from_analysis(EvidenceDirection.BULLISH, _raw_bars("bull"))
    structure = _rebuild(row, _raw_bars("bull"))
    payload = row.model_dump()
    payload["claims"] = [c.model_dump() for c in structure.claims]
    payload["facts"] = [f.model_dump() for f in (structure.facts or ())]
    ok = R5StructureRowV1.model_validate(payload)
    assert ok.claims and all(not c.can_support_confirmed for c in ok.claims)

    bad_claim = structure.claims[0].model_copy(
        update={"can_support_confirmed": True}
    )
    payload["claims"] = [bad_claim.model_dump()]
    with pytest.raises(ValueError):
        R5StructureRowV1.model_validate(payload)


def test_r5_row_tolerates_old_payloads_without_new_fields() -> None:
    from trendforge_api.selection.r5_live import R5StructureRowV1

    row, _ = _r5_row_from_analysis(EvidenceDirection.BULLISH, _raw_bars("bull"))
    old = row.model_dump(exclude={"claims", "facts"})
    reloaded = R5StructureRowV1.model_validate(old)
    assert reloaded.claims == () and reloaded.facts == ()
