"""Pure compact normalizer for Angel One's public instrument master."""

from __future__ import annotations

import json
from typing import Any

from .common import parse_date_value, source_result


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def parse_angelone_instrument_master(
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Angel One instrument master is not valid JSON.",
            output={"rows": [], "scope": "CATALOG_REFERENCE_ONLY"},
            error=str(exc),
        )
    if not isinstance(payload, list):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Angel One instrument master must be a JSON list.",
            output={"rows": [], "scope": "CATALOG_REFERENCE_ONLY"},
            error="top-level value is not a list",
        )
    if not payload:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="Angel One instrument master is empty; retain last-good.",
            output={"rows": [], "sourceRowCount": 0, "scope": "CATALOG_REFERENCE_ONLY"},
            error="empty list",
        )

    target_exchanges = {"NSE", "BSE", "NFO", "BFO", "MCX"}
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    seen: set[tuple[str, str]] = set()
    invalid = duplicates = filtered = included = 0
    exchange_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for position, raw in enumerate(payload, start=1):
        if not isinstance(raw, dict):
            invalid += 1
            continue
        token = _text(raw.get("token"))
        instrument_symbol = _text(raw.get("symbol"))
        exchange = _text(raw.get("exch_seg")).upper()
        if not token or not instrument_symbol or not exchange:
            invalid += 1
            continue
        identity = (exchange, token)
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        if exchange not in target_exchanges:
            filtered += 1
            continue
        instrument_type = _text(raw.get("instrumenttype")).upper()
        lot_size = _number(raw.get("lotsize"))
        if lot_size is None or lot_size <= 0:
            invalid += 1
            continue
        exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
        type_key = instrument_type or "UNSPECIFIED"
        type_counts[type_key] = type_counts.get(type_key, 0) + 1
        included += 1
        reference_name = _text(raw.get("name")) or instrument_symbol
        group_key = (exchange, type_key, reference_name)
        group = groups.setdefault(
            group_key,
            {
                "symbol": None,
                "mappingState": "BROKER_MASTER_IDENTITY_ONLY",
                "referenceName": reference_name,
                "exchange": exchange,
                "instrumentType": instrument_type or None,
                "contractCount": 0,
                "lotSizes": set(),
                "tickSizesRaw": set(),
                "freezeQuantities": set(),
                "expiriesRaw": set(),
                "sampleInstrumentSymbols": [],
                "sampleBrokerTokens": [],
                "strikeMinRaw": None,
                "strikeMaxRaw": None,
                "casEnabledCount": 0,
                "firstSourceRow": position,
                "sourceUrl": url,
                "sourceTrust": "OPEN_SOURCE_UNOFFICIAL",
                "scope": "CATALOG_REFERENCE_ONLY",
                "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
            },
        )
        group["contractCount"] += 1
        group["lotSizes"].add(lot_size)
        tick_size = _number(raw.get("tick_size"))
        if tick_size is not None:
            group["tickSizesRaw"].add(tick_size)
        freeze = _number(raw.get("freeze_qty"))
        if freeze is not None:
            group["freezeQuantities"].add(freeze)
        expiry = _text(raw.get("expiry"))
        if expiry:
            group["expiriesRaw"].add(expiry)
        if instrument_symbol not in group["sampleInstrumentSymbols"] and len(group["sampleInstrumentSymbols"]) < 3:
            group["sampleInstrumentSymbols"].append(instrument_symbol)
        if token not in group["sampleBrokerTokens"] and len(group["sampleBrokerTokens"]) < 3:
            group["sampleBrokerTokens"].append(token)
        strike = _number(raw.get("strike"))
        if strike is not None and strike > 0:
            current_min = group["strikeMinRaw"]
            current_max = group["strikeMaxRaw"]
            group["strikeMinRaw"] = strike if current_min is None else min(current_min, strike)
            group["strikeMaxRaw"] = strike if current_max is None else max(current_max, strike)
        if bool(raw.get("is_cas_enabled")):
            group["casEnabledCount"] += 1

    rows: list[dict[str, Any]] = []
    for group_key in sorted(groups):
        group = groups[group_key]
        group["lotSizes"] = sorted(group["lotSizes"])
        group["tickSizesRaw"] = sorted(group["tickSizesRaw"])
        group["freezeQuantities"] = sorted(group["freezeQuantities"])
        group["expiriesRaw"] = sorted(group["expiriesRaw"])
        rows.append(group)
    if not rows:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Angel One rows failed required identity/lot validation.",
            output={"rows": [], "sourceRowCount": len(payload), "invalidRowCount": invalid},
            error="no valid rows",
        )
    data_date = parse_date_value(last_modified)
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} compact Angel One instrument schedules.",
        output={
            "rows": rows,
            "sourceRowCount": len(payload),
            "includedSourceRowCount": included,
            "normalizedRowCount": len(rows),
            "invalidRowCount": invalid,
            "duplicateRowCount": duplicates,
            "filteredUnsupportedExchangeCount": filtered,
            "targetExchanges": sorted(target_exchanges),
            "exchangeCounts": exchange_counts,
            "instrumentTypeCounts": type_counts,
            "parserVersion": "1.0.0",
            "sourceTrust": "OPEN_SOURCE_UNOFFICIAL",
            "scope": "CATALOG_REFERENCE_ONLY",
            "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
            "symbolMappingPolicy": "BROKER_MASTER_IDENTITY_ONLY",
        },
    )
