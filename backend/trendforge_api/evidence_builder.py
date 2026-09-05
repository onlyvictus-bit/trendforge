from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import storage
from .causal_engine import CausalEvidenceInput


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return (
        parsed
        if parsed.utcoffset() is not None
        else parsed.replace(tzinfo=timezone.utc)
    )


def _source_date(value: str | None, observed_at: datetime) -> datetime:
    if not value:
        return observed_at
    try:
        return _datetime(str(value)[:10])
    except ValueError:
        return observed_at


def _claim(
    *,
    row: dict[str, Any],
    source_key: str,
    layer: str,
    signal_type: str,
    contribution: float,
    explanation: str,
    source_date_value: str | None,
    cause_type: str | None = None,
    sponsor_actor: str | None = None,
    stale_after_days: float | None = None,
) -> CausalEvidenceInput:
    observed_at = _datetime(row["parsed_at"])
    row_id = int(row["id"])
    payload: dict[str, Any] = {
        "evidenceId": f"{source_key}:{row_id}:{layer.lower()}:{signal_type.lower()}",
        "layer": layer,
        "signalType": signal_type,
        "contribution": contribution,
        "source": source_key,
        "sourceKey": source_key,
        "sourceRowId": row_id,
        "sourceDate": _source_date(source_date_value, observed_at),
        "observedAt": observed_at,
        "trustLevel": "OFFICIAL",
        "explanation": explanation,
        "rawInputKeys": [f"{source_key}:{row_id}"],
        "staleAfterDays": stale_after_days,
    }
    if cause_type:
        payload["causeType"] = cause_type
    if sponsor_actor:
        payload["sponsorActor"] = sponsor_actor
    return CausalEvidenceInput.model_validate(payload)


def _rows_for_symbol(symbol: str, as_of: datetime) -> dict[str, list[dict[str, Any]]]:
    storage.init_db()
    normalized = symbol.upper().strip()
    cutoff = as_of.isoformat()
    queries = {
        "nse_large_deals": "SELECT * FROM bulk_block_deals WHERE UPPER(symbol) = ? AND parsed_at <= ? ORDER BY data_date DESC, id DESC",
        "amfi_monthly_portfolio": "SELECT * FROM amfi_stock_deltas WHERE UPPER(stock) = ? AND parsed_at <= ? ORDER BY disclosure_month DESC, id DESC",
        "sebi_pit_sast": "SELECT * FROM sebi_disclosures WHERE UPPER(symbol) = ? AND parsed_at <= ? ORDER BY data_date DESC, id DESC",
        "corporate_events": "SELECT * FROM corporate_events WHERE UPPER(symbol) = ? AND parsed_at <= ? ORDER BY data_date DESC, id DESC",
    }
    output: dict[str, list[dict[str, Any]]] = {}
    conn = storage.connect()
    try:
        for source_key, query in queries.items():
            output[source_key] = [
                dict(row)
                for row in conn.execute(query, (normalized, cutoff)).fetchall()
            ]
        output["corporate_offer_events"] = [
            dict(row)
            for row in conn.execute(
                """
                WITH ranked_instruments AS (
                    SELECT isin, symbol, active,
                           ROW_NUMBER() OVER (
                               PARTITION BY isin
                               ORDER BY data_date DESC, id DESC
                           ) AS rank_for_isin
                    FROM nse_instruments
                    WHERE data_date <= ?
                ), resolved_offers AS (
                    SELECT event.*,
                           COALESCE(
                               NULLIF(TRIM(event.symbol), ''),
                               CASE WHEN instrument.active = 1
                                    THEN instrument.symbol END
                           ) AS resolved_symbol
                    FROM corporate_offer_events AS event
                    LEFT JOIN ranked_instruments AS instrument
                      ON instrument.isin = event.isin
                     AND instrument.rank_for_isin = 1
                    WHERE event.is_current = 1
                      AND event.parsed_at <= ?
                )
                SELECT * FROM resolved_offers
                WHERE UPPER(resolved_symbol) = ?
                ORDER BY data_date DESC, id DESC
                """,
                (as_of.date().isoformat(), cutoff, normalized),
            ).fetchall()
        ]
    finally:
        conn.close()
    return output


def _deal_claims(rows: list[dict[str, Any]]) -> list[CausalEvidenceInput]:
    claims: list[CausalEvidenceInput] = []
    for row in rows:
        buyer = str(row.get("buyer") or "").strip()
        seller = str(row.get("seller") or "").strip()
        premium = float(row.get("premium_pct") or 0)
        value = float(row.get("value") or 0)
        if buyer:
            sponsor_points = 3.0 if premium >= 0 and value >= 10_000_000 else 2.0
            claims.append(
                _claim(
                    row=row,
                    source_key="nse_large_deals",
                    layer="SPONSOR",
                    signal_type="BULK_DEAL",
                    contribution=sponsor_points,
                    explanation=f"Named buyer {buyer} acquired shares in a disclosed {row.get('deal_type') or 'large'} deal.",
                    source_date_value=row.get("data_date"),
                    sponsor_actor="NAMED_INVESTOR",
                    stale_after_days=30,
                )
            )
            claims.append(
                _claim(
                    row=row,
                    source_key="nse_large_deals",
                    layer="CAUSE",
                    signal_type="BULK_DEAL_INFORMATION",
                    contribution=2.0,
                    explanation="A named large transaction is an information-asymmetry candidate, subject to price acceptance.",
                    source_date_value=row.get("data_date"),
                    cause_type="INFORMATION_ASYMMETRY",
                    stale_after_days=30,
                )
            )
        elif seller:
            claims.append(
                _claim(
                    row=row,
                    source_key="nse_large_deals",
                    layer="SPONSOR",
                    signal_type="LARGE_SELLER",
                    contribution=-2.0,
                    explanation=f"Named seller {seller} creates potential supply overhang.",
                    source_date_value=row.get("data_date"),
                    stale_after_days=30,
                )
            )
    return claims


def _amfi_claims(rows: list[dict[str, Any]]) -> list[CausalEvidenceInput]:
    claims: list[CausalEvidenceInput] = []
    for row in rows:
        net_change = int(row.get("net_quantity_change") or 0)
        schemes_added = int(row.get("schemes_added") or 0)
        if net_change == 0 and schemes_added == 0:
            continue
        contribution = min(3.0, 1.0 + schemes_added * 0.5) if net_change > 0 else -2.0
        claims.append(
            _claim(
                row=row,
                source_key="amfi_monthly_portfolio",
                layer="SPONSOR",
                signal_type="MF_HOLDING",
                contribution=contribution,
                explanation=f"Monthly AMFI delta: {schemes_added} schemes added; net quantity change {net_change}.",
                source_date_value=row.get("disclosure_month"),
                sponsor_actor="DII" if contribution > 0 else None,
                stale_after_days=45,
            )
        )
    return claims


def _sebi_claims(rows: list[dict[str, Any]]) -> list[CausalEvidenceInput]:
    claims: list[CausalEvidenceInput] = []
    for row in rows:
        transaction = str(row.get("transaction_type") or "").upper()
        if any(
            token in transaction for token in ("ESOP", "ALLOT", "INTER-SE", "TRANSFER")
        ):
            continue
        is_buy = any(token in transaction for token in ("BUY", "ACQUIS", "PURCHASE"))
        is_sell = any(token in transaction for token in ("SELL", "DISPOS", "PLEDGE"))
        if not is_buy and not is_sell:
            continue
        relationship = str(row.get("relationship") or "").upper()
        actor = (
            "PROMOTER_INSIDER"
            if any(token in relationship for token in ("PROMOTER", "DIRECTOR", "KMP"))
            else "NAMED_INVESTOR"
        )
        if is_buy:
            claims.append(
                _claim(
                    row=row,
                    source_key="sebi_pit_sast",
                    layer="SPONSOR",
                    signal_type="PROMOTER_BUY",
                    contribution=3.0,
                    explanation=f"{row.get('entity')} disclosed a structured open-market acquisition.",
                    source_date_value=row.get("event_date") or row.get("data_date"),
                    sponsor_actor=actor,
                    stale_after_days=90,
                )
            )
            claims.append(
                _claim(
                    row=row,
                    source_key="sebi_pit_sast",
                    layer="CAUSE",
                    signal_type="INSIDER_INFORMATION_ASYMMETRY",
                    contribution=2.0,
                    explanation="A risk-capital insider acquisition can indicate information asymmetry.",
                    source_date_value=row.get("event_date") or row.get("data_date"),
                    cause_type="INFORMATION_ASYMMETRY",
                    stale_after_days=90,
                )
            )
        else:
            claims.append(
                _claim(
                    row=row,
                    source_key="sebi_pit_sast",
                    layer="SPONSOR",
                    signal_type="INSIDER_SELL_OR_PLEDGE",
                    contribution=-3.0,
                    explanation=f"{row.get('entity')} disclosed selling, disposal, or pledge activity.",
                    source_date_value=row.get("event_date") or row.get("data_date"),
                    stale_after_days=90,
                )
            )
    return claims


def _corporate_event_claims(rows: list[dict[str, Any]]) -> list[CausalEvidenceInput]:
    claims: list[CausalEvidenceInput] = []
    for row in rows:
        action = str(row.get("action_type") or "").upper()
        if not any(token in action for token in ("BUYBACK", "OPEN OFFER", "TAKEOVER")):
            continue
        source_key = str(row.get("source_key") or "corporate_events")
        claims.append(
            _claim(
                row=row,
                source_key=source_key,
                layer="CAUSE",
                signal_type="FORCED_CORPORATE_FLOW",
                contribution=2.0,
                explanation=f"{action} can create mandatory corporate demand or an event-price anchor.",
                source_date_value=row.get("announcement_date") or row.get("data_date"),
                cause_type="FORCED_MANDATORY_FLOW",
                stale_after_days=14,
            )
        )
    return claims


def _corporate_offer_claims(
    rows: list[dict[str, Any]],
) -> list[CausalEvidenceInput]:
    latest_by_offer: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        if float(row.get("offer_price") or 0) <= 0 or int(
            row.get("quantity") or 0
        ) <= 0:
            continue
        key = (
            str(row.get("parent_source_key") or ""),
            str(row.get("company_id") or row.get("isin") or ""),
            str(row.get("offer_type") or ""),
        )
        current = latest_by_offer.get(key)
        if current is None:
            latest_by_offer[key] = row
            continue
        current_is_complete_pre = (
            current.get("phase") == "PRE"
            and current.get("start_date")
            and current.get("end_date")
            and int(current.get("quantity") or 0) > 0
        )
        row_is_complete_pre = (
            row.get("phase") == "PRE"
            and row.get("start_date")
            and row.get("end_date")
            and int(row.get("quantity") or 0) > 0
        )
        if row_is_complete_pre and not current_is_complete_pre:
            latest_by_offer[key] = row
        elif row_is_complete_pre == current_is_complete_pre and str(
            row.get("data_date") or ""
        ) > str(current.get("data_date") or ""):
            latest_by_offer[key] = row

    claims: list[CausalEvidenceInput] = []
    for row in latest_by_offer.values():
        offer_type = str(row.get("offer_type") or "CORPORATE_OFFER")
        price = float(row.get("offer_price") or 0)
        quantity = int(row.get("quantity") or 0)
        claims.append(
            _claim(
                row=row,
                source_key=str(row.get("parent_source_key") or "bse_offer_xbrl"),
                layer="CAUSE",
                signal_type="FORCED_CORPORATE_FLOW",
                contribution=2.0,
                explanation=(
                    f"Official {offer_type} terms set an event anchor at INR {price:g} "
                    f"for {quantity:,} shares; structure and price acceptance remain mandatory."
                ),
                source_date_value=row.get("announcement_date") or row.get("data_date"),
                cause_type="FORCED_MANDATORY_FLOW",
                stale_after_days=14,
            )
        )
    return claims


def build_symbol_evidence(symbol: str, *, as_of: datetime) -> list[CausalEvidenceInput]:
    if as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    rows = _rows_for_symbol(symbol, as_of)
    claims = (
        _deal_claims(rows["nse_large_deals"])
        + _amfi_claims(rows["amfi_monthly_portfolio"])
        + _sebi_claims(rows["sebi_pit_sast"])
        + _corporate_event_claims(rows["corporate_events"])
        + _corporate_offer_claims(rows["corporate_offer_events"])
    )
    return [
        claim
        for claim in claims
        if claim.source_date <= as_of and claim.observed_at <= as_of
    ]


def persist_symbol_evidence(symbol: str, *, as_of: datetime) -> int:
    claims = build_symbol_evidence(symbol, as_of=as_of)
    return storage.save_evidence_claims(
        symbol,
        [claim.model_dump(mode="json", by_alias=True) for claim in claims],
    )
