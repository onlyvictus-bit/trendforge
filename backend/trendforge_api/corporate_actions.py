from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .models import OHLCVCandle


ActionClass = Literal[
    "SPLIT", "BONUS", "DIVIDEND", "RIGHTS", "MERGER", "DEMERGER", "OTHER"
]
ReconciliationState = Literal["RECONCILED", "CONFLICT", "CANCELLED", "WAIT_DETAILS"]


class ReconciledCorporateAction(BaseModel):
    action_key: str = Field(alias="actionKey")
    symbol: str
    action_class: ActionClass = Field(alias="actionClass")
    effective_date: date = Field(alias="effectiveDate")
    state: ReconciliationState
    adjustment_factor: float | None = Field(default=None, alias="adjustmentFactor")
    ratio_numerator: float | None = Field(default=None, alias="ratioNumerator")
    ratio_denominator: float | None = Field(default=None, alias="ratioDenominator")
    cash_amount: float | None = Field(default=None, alias="cashAmount")
    offer_price: float | None = Field(default=None, alias="offerPrice")
    predecessor_symbol: str | None = Field(default=None, alias="predecessorSymbol")
    successor_symbol: str | None = Field(default=None, alias="successorSymbol")
    continuity_confirmed: bool = Field(default=False, alias="continuityConfirmed")
    source_event_ids: list[int] = Field(alias="sourceEventIds")
    source_count: int = Field(alias="sourceCount", ge=1)
    reason: str

    model_config = {"populate_by_name": True}


class AdjustmentIntegrityAssessment(BaseModel):
    symbol: str
    timeframe: str
    source: str
    state: Literal["PASS", "REJECT_DATA_INTEGRITY", "WAIT_DATA_WEAK"]
    required_action_count: int = Field(alias="requiredActionCount", ge=0)
    event_ids: list[int] = Field(alias="eventIds")
    reason: str
    executable: Literal[False] = False

    model_config = {"populate_by_name": True}


class CandleAdjustmentReconcileRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: str = Field(min_length=1, max_length=20)
    source: str = Field(min_length=1, max_length=120)

    model_config = {"extra": "forbid"}


def classify_action(value: str) -> ActionClass:
    normalized = value.upper()
    if "SPLIT" in normalized or "SUB-DIV" in normalized:
        return "SPLIT"
    if "BONUS" in normalized:
        return "BONUS"
    if "DIVIDEND" in normalized:
        return "DIVIDEND"
    if "RIGHT" in normalized:
        return "RIGHTS"
    if "DEMERGER" in normalized or "DE-MERGER" in normalized:
        return "DEMERGER"
    if "MERGER" in normalized or "AMALGAM" in normalized:
        return "MERGER"
    return "OTHER"


def _parse_date(value: Any) -> date | None:
    if value in {None, ""}:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if value in {None, ""}:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


def _factor(
    action_class: ActionClass, numerator: Any, denominator: Any
) -> float | None:
    try:
        top = float(numerator)
        bottom = float(denominator)
    except (TypeError, ValueError):
        return None
    if top <= 0 or bottom <= 0:
        return None
    if action_class == "SPLIT":
        return round(bottom / top, 10)
    if action_class == "BONUS":
        return round(bottom / (top + bottom), 10)
    return None


def _row_value(row: dict[str, Any], snake: str, camel: str) -> Any:
    return row.get(snake, row.get(camel))


def _positive_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    normalized = str(value or "").strip().upper()
    if normalized in {"TRUE", "YES", "Y", "1"}:
        return True
    if normalized in {"FALSE", "NO", "N", "0"}:
        return False
    return None


def _normalized_symbol(value: Any) -> str | None:
    normalized = str(value or "").strip().upper()
    return normalized or None


def reconcile_corporate_actions(
    rows: list[dict[str, Any]], *, as_of: datetime
) -> list[ReconciledCorporateAction]:
    if as_of.utcoffset() is None:
        raise ValueError(
            "corporate-action reconciliation cutoff must be timezone-aware"
        )
    grouped: dict[tuple[str, ActionClass, date], list[dict[str, Any]]] = defaultdict(
        list
    )
    for row in rows:
        parsed_at = _parse_datetime(_row_value(row, "parsed_at", "parsedAt"))
        if parsed_at is None or parsed_at > as_of:
            continue
        symbol = str(row.get("symbol") or "").upper().strip()
        action_class = classify_action(
            str(
                _row_value(row, "action_class", "actionClass")
                or row.get("action_type")
                or row.get("actionType")
                or ""
            )
        )
        effective = _parse_date(
            _row_value(row, "ex_date", "exDate")
            or _row_value(row, "record_date", "recordDate")
        )
        if not symbol or effective is None:
            continue
        grouped[(symbol, action_class, effective)].append(row)

    output: list[ReconciledCorporateAction] = []
    for (symbol, action_class, effective), observations in sorted(grouped.items()):
        latest_by_source: dict[str, dict[str, Any]] = {}
        for row in observations:
            source = str(row.get("source_key") or row.get("sourceKey") or "UNKNOWN")
            previous = latest_by_source.get(source)
            row_time = _parse_datetime(_row_value(row, "parsed_at", "parsedAt"))
            previous_time = (
                _parse_datetime(_row_value(previous, "parsed_at", "parsedAt"))
                if previous
                else None
            )
            if previous is None or (
                row_time and previous_time and row_time >= previous_time
            ):
                latest_by_source[source] = row
        selected = list(latest_by_source.values())
        revisions = {
            str(
                _row_value(row, "revision_status", "revisionStatus") or "UNKNOWN"
            ).upper()
            for row in selected
        }
        ids = [int(row.get("id") or 0) for row in selected]
        key = f"{symbol}:{action_class}:{effective.isoformat()}"
        if revisions == {"CANCELLED"}:
            output.append(
                ReconciledCorporateAction(
                    actionKey=key,
                    symbol=symbol,
                    actionClass=action_class,
                    effectiveDate=effective,
                    state="CANCELLED",
                    sourceEventIds=ids,
                    sourceCount=len(selected),
                    reason="Latest official observations agree that the action was cancelled.",
                )
            )
            continue
        if "CANCELLED" in revisions:
            output.append(
                ReconciledCorporateAction(
                    actionKey=key,
                    symbol=symbol,
                    actionClass=action_class,
                    effectiveDate=effective,
                    state="CONFLICT",
                    sourceEventIds=ids,
                    sourceCount=len(selected),
                    reason="Official sources disagree on whether the action was cancelled.",
                )
            )
            continue
        terms = {
            (
                _positive_float(_row_value(row, "ratio_numerator", "ratioNumerator")),
                _positive_float(
                    _row_value(row, "ratio_denominator", "ratioDenominator")
                ),
                _positive_float(_row_value(row, "cash_amount", "cashAmount")),
                _positive_float(_row_value(row, "offer_price", "offerPrice")),
            )
            for row in selected
        }
        factors = {
            factor
            for top_value, bottom_value, _, _ in terms
            if (factor := _factor(action_class, top_value, bottom_value)) is not None
        }
        ratio_terms = {
            (top_value, bottom_value)
            for top_value, bottom_value, _, _ in terms
            if top_value is not None and bottom_value is not None
        }
        cash_values = {
            cash_value for _, _, cash_value, _ in terms if cash_value is not None
        }
        offer_values = {
            offer_value for _, _, _, offer_value in terms if offer_value is not None
        }
        explicit_factors = {
            explicit_value
            for row in selected
            if (
                explicit_value := _positive_float(
                    _row_value(row, "adjustment_factor", "priceAdjustmentFactor")
                )
            )
            is not None
        }
        predecessor_symbols = {
            predecessor_value
            for row in selected
            if (
                predecessor_value := _normalized_symbol(
                    _row_value(row, "predecessor_symbol", "predecessorSymbol")
                )
            )
            is not None
        }
        successor_symbols = {
            successor_value
            for row in selected
            if (
                successor_value := _normalized_symbol(
                    _row_value(row, "successor_symbol", "successorSymbol")
                )
            )
            is not None
        }
        continuity_values = {
            continuity_value
            for row in selected
            if (
                continuity_value := _optional_bool(
                    _row_value(row, "continuity_confirmed", "continuityConfirmed")
                )
            )
            is not None
        }
        top_value, bottom_value = (
            next(iter(ratio_terms)) if len(ratio_terms) == 1 else (None, None)
        )
        cash_value = next(iter(cash_values)) if len(cash_values) == 1 else None
        offer_value = next(iter(offer_values)) if len(offer_values) == 1 else None
        explicit_factor = (
            next(iter(explicit_factors)) if len(explicit_factors) == 1 else None
        )
        predecessor_symbol = (
            next(iter(predecessor_symbols)) if len(predecessor_symbols) == 1 else None
        )
        successor_symbol = (
            next(iter(successor_symbols)) if len(successor_symbols) == 1 else None
        )
        continuity_confirmed = continuity_values == {True}
        details_conflict = (
            len(factors) > 1
            or len(ratio_terms) > 1
            or len(cash_values) > 1
            or len(offer_values) > 1
            or len(explicit_factors) > 1
            or len(predecessor_symbols) > 1
            or len(successor_symbols) > 1
            or len(continuity_values) > 1
        )
        if details_conflict:
            state: ReconciliationState = "CONFLICT"
            factor_value = None
            reason = "Official observations disagree on the adjustment terms."
        elif action_class in {"SPLIT", "BONUS"} and factors:
            state = "RECONCILED"
            factor_value = next(iter(factors))
            reason = f"{len(selected)} official source observation(s) reconcile to factor {factor_value:.8f}."
        elif action_class == "DIVIDEND" and cash_value is not None:
            state = "RECONCILED"
            factor_value = None
            reason = f"Cash dividend {cash_value:.4f} will use the last pre-ex reference close."
        elif (
            action_class == "RIGHTS"
            and top_value is not None
            and bottom_value is not None
            and offer_value is not None
        ):
            state = "RECONCILED"
            factor_value = None
            reason = (
                "Rights terms will use a theoretical ex-rights reference-price model."
            )
        elif action_class in {"MERGER", "DEMERGER"}:
            same_symbol_continuity = (
                continuity_confirmed
                and predecessor_symbol == symbol
                and successor_symbol == symbol
            )
            if explicit_factor is None:
                state = "WAIT_DETAILS"
                factor_value = None
                reason = (
                    "Merger/demerger reconstruction requires an explicit official "
                    "price-adjustment factor; a share-exchange ratio alone is insufficient."
                )
            elif not same_symbol_continuity:
                state = "WAIT_DETAILS"
                factor_value = None
                reason = (
                    "Cross-symbol merger/demerger reconstruction requires a separate "
                    "instrument-lineage series and cannot adjust one symbol in place."
                )
            else:
                state = "RECONCILED"
                factor_value = explicit_factor
                reason = (
                    "Official explicit reconstruction factor is authorized for confirmed "
                    "same-symbol continuity."
                )
        elif action_class == "OTHER":
            state = "RECONCILED"
            factor_value = None
            reason = "Event is contextual and does not reconstruct historical OHLCV."
        else:
            state = "WAIT_DETAILS"
            factor_value = None
            reason = (
                "The action lacks a deterministic adjustment ratio or supported model."
            )
        output.append(
            ReconciledCorporateAction(
                actionKey=key,
                symbol=symbol,
                actionClass=action_class,
                effectiveDate=effective,
                state=state,
                adjustmentFactor=factor_value,
                ratioNumerator=top_value,
                ratioDenominator=bottom_value,
                cashAmount=cash_value,
                offerPrice=offer_value,
                predecessorSymbol=predecessor_symbol,
                successorSymbol=successor_symbol,
                continuityConfirmed=continuity_confirmed,
                sourceEventIds=ids,
                sourceCount=len(selected),
                reason=reason,
            )
        )
    return output


def _candle_date(candle: OHLCVCandle) -> date:
    parsed = _parse_datetime(candle.timestamp)
    if parsed is None:
        raise ValueError(f"candle timestamp lacks timezone: {candle.timestamp}")
    return parsed.date()


PRICE_ADJUSTING_CLASSES = {
    "SPLIT",
    "BONUS",
    "DIVIDEND",
    "RIGHTS",
    "MERGER",
    "DEMERGER",
}


def _action_price_factor(
    action: ReconciledCorporateAction, candles: list[OHLCVCandle]
) -> float | None:
    if action.adjustment_factor is not None:
        return action.adjustment_factor
    references = [
        candle for candle in candles if _candle_date(candle) < action.effective_date
    ]
    if not references:
        return None
    reference = max(references, key=_candle_date)
    reference_close = reference.close
    if reference.adjustment_status == "ADJUSTED":
        reference_close /= reference.adjustment_factor
    if action.action_class == "DIVIDEND" and action.cash_amount is not None:
        factor = (reference_close - action.cash_amount) / reference_close
        return round(factor, 10) if 0 < factor < 1 else None
    if (
        action.action_class == "RIGHTS"
        and action.ratio_numerator is not None
        and action.ratio_denominator is not None
        and action.offer_price is not None
    ):
        theoretical = (
            reference_close * action.ratio_denominator
            + action.offer_price * action.ratio_numerator
        ) / (action.ratio_denominator + action.ratio_numerator)
        factor = theoretical / reference_close
        return round(factor, 10) if factor > 0 else None
    return None


def apply_reconciled_actions_at_ingestion(
    candles: list[OHLCVCandle], actions: list[ReconciledCorporateAction]
) -> list[OHLCVCandle]:
    if not candles:
        return []
    last_date = max(_candle_date(candle) for candle in candles)
    relevant = [
        action
        for action in actions
        if action.effective_date <= last_date
        and action.state != "CANCELLED"
        and action.action_class in PRICE_ADJUSTING_CLASSES
    ]
    if not relevant:
        return list(candles)
    factors = {
        action.action_key: _action_price_factor(action, candles) for action in relevant
    }
    output: list[OHLCVCandle] = []
    for candle in candles:
        candle_date = _candle_date(candle)
        prior_actions = [
            action for action in relevant if candle_date < action.effective_date
        ]
        unresolved = any(
            action.state != "RECONCILED" or factors[action.action_key] is None
            for action in prior_actions
        )
        if unresolved:
            output.append(
                candle.model_copy(
                    update={"adjustment_status": "UNADJUSTED", "adjustment_factor": 1.0}
                )
            )
            continue
        factor = 1.0
        volume_factor = 1.0
        for action in prior_actions:
            action_factor = factors[action.action_key] or 1.0
            factor *= action_factor
            if action.action_class in {"SPLIT", "BONUS"}:
                volume_factor *= action_factor
        if prior_actions and candle.adjustment_status != "ADJUSTED":
            output.append(
                candle.model_copy(
                    update={
                        "open": round(candle.open * factor, 8),
                        "high": round(candle.high * factor, 8),
                        "low": round(candle.low * factor, 8),
                        "close": round(candle.close * factor, 8),
                        "volume": round(candle.volume / volume_factor, 8),
                        "adjustment_status": "ADJUSTED",
                        "adjustment_factor": round(factor, 10),
                    }
                )
            )
        elif prior_actions:
            output.append(candle)
        else:
            status = (
                candle.adjustment_status
                if candle.adjustment_status == "ADJUSTED"
                else "NOT_REQUIRED"
            )
            output.append(candle.model_copy(update={"adjustment_status": status}))
    return output


def assess_adjustment_integrity(
    candles: list[OHLCVCandle], actions: list[ReconciledCorporateAction]
) -> AdjustmentIntegrityAssessment:
    if not candles:
        return AdjustmentIntegrityAssessment(
            symbol="UNKNOWN",
            timeframe="UNKNOWN",
            source="UNKNOWN",
            state="WAIT_DATA_WEAK",
            requiredActionCount=0,
            eventIds=[],
            reason="No candles are available for adjustment assessment.",
        )
    first_date = min(_candle_date(candle) for candle in candles)
    last_date = max(_candle_date(candle) for candle in candles)
    relevant = [
        action
        for action in actions
        if first_date < action.effective_date <= last_date
        and action.state != "CANCELLED"
        and action.action_class in PRICE_ADJUSTING_CLASSES
    ]
    event_ids = [
        event_id for action in relevant for event_id in action.source_event_ids
    ]

    def result(
        state: Literal["PASS", "REJECT_DATA_INTEGRITY", "WAIT_DATA_WEAK"],
        reason: str,
    ) -> AdjustmentIntegrityAssessment:
        return AdjustmentIntegrityAssessment(
            symbol=candles[0].symbol,
            timeframe=candles[0].timeframe,
            source=candles[0].source,
            state=state,
            requiredActionCount=len(relevant),
            eventIds=event_ids,
            reason=reason,
        )

    factors = {
        action.action_key: _action_price_factor(action, candles) for action in relevant
    }
    unresolved = [
        action
        for action in relevant
        if action.state != "RECONCILED" or factors[action.action_key] is None
    ]
    if unresolved:
        return result(
            "REJECT_DATA_INTEGRITY",
            "Corporate-action observations conflict or lack adjustment details.",
        )
    for candle in candles:
        candle_date = _candle_date(candle)
        prior = [action for action in relevant if candle_date < action.effective_date]
        expected = 1.0
        for action in prior:
            expected *= factors[action.action_key] or 1.0
        if prior and (
            candle.adjustment_status != "ADJUSTED"
            or abs(candle.adjustment_factor - expected) > 0.000001
        ):
            return result(
                "REJECT_DATA_INTEGRITY",
                (
                    f"Candle {candle.timestamp} is not adjusted by the expected factor "
                    f"{expected:.8f}."
                ),
            )
    return result(
        "PASS",
        (
            "All known corporate actions are reconciled and applied during ingestion."
            if relevant
            else "No known effective corporate action intersects this candle range."
        ),
    )
