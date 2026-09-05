"""Pure compact normalizer for Dhan's public detailed instrument master."""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any

from .common import parse_date_value, source_result


def _text(value: Any) -> str:
    value = " ".join(str(value or "").split())
    return "" if value.upper() in {"NA", "N/A", "NULL"} else value


def _number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def parse_dhan_instrument_master(
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Dhan instrument master is not valid UTF-8 CSV.",
            output={"rows": [], "scope": "CATALOG_REFERENCE_ONLY"},
            error=str(exc),
        )
    reader = csv.DictReader(io.StringIO(text))
    required = {"EXCH_ID", "SEGMENT", "SECURITY_ID", "INSTRUMENT", "LOT_SIZE"}
    if not reader.fieldnames or not required <= set(reader.fieldnames):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Dhan instrument master is missing required CSV columns.",
            output={"rows": [], "scope": "CATALOG_REFERENCE_ONLY"},
            error="missing required columns",
        )
    source_rows = list(reader)
    if not source_rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="Dhan instrument master is empty; retain last-good.",
            output={"rows": [], "sourceRowCount": 0, "scope": "CATALOG_REFERENCE_ONLY"},
            error="empty CSV",
        )
    data_date = parse_date_value(last_modified)
    reference = date.fromisoformat(data_date) if data_date else None
    allowed_segments = {("NSE", "D"), ("NSE", "E"), ("NSE", "I"), ("BSE", "D"), ("BSE", "E"), ("BSE", "I")}
    groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    seen: set[tuple[str, str, str]] = set()
    invalid = duplicates = filtered_scope = filtered_expired = included = 0
    for position, raw in enumerate(source_rows, start=2):
        exchange = _text(raw.get("EXCH_ID")).upper()
        segment = _text(raw.get("SEGMENT")).upper()
        security_id = _text(raw.get("SECURITY_ID"))
        instrument = _text(raw.get("INSTRUMENT")).upper()
        lot_size = _number(raw.get("LOT_SIZE"))
        if not exchange or not segment or not security_id or not instrument or lot_size is None or lot_size <= 0:
            invalid += 1
            continue
        identity = (exchange, segment, security_id)
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        if exchange != "MCX" and (exchange, segment) not in allowed_segments:
            filtered_scope += 1
            continue
        expiry = parse_date_value(raw.get("SM_EXPIRY_DATE"))
        is_contract = instrument.startswith(("FUT", "OPT"))
        if is_contract and reference and expiry and date.fromisoformat(expiry) < reference:
            filtered_expired += 1
            continue
        reference_name = (
            _text(raw.get("UNDERLYING_SYMBOL"))
            or _text(raw.get("SYMBOL_NAME"))
            or _text(raw.get("DISPLAY_NAME"))
        )
        if not reference_name:
            invalid += 1
            continue
        included += 1
        instrument_type = _text(raw.get("INSTRUMENT_TYPE")).upper() or instrument
        key = (exchange, segment, instrument, reference_name)
        group = groups.setdefault(
            key,
            {
                "symbol": None,
                "mappingState": "BROKER_MASTER_IDENTITY_ONLY",
                "referenceName": reference_name,
                "exchange": exchange,
                "segment": segment,
                "instrument": instrument,
                "instrumentTypes": set(),
                "contractCount": 0,
                "lotSizes": set(),
                "expiries": set(),
                "optionTypes": set(),
                "tickSizes": set(),
                "freezeQuantities": set(),
                "asmGsmFlags": set(),
                "asmGsmCategories": set(),
                "sampleSecurityIds": [],
                "sampleIsins": [],
                "sampleDisplayNames": [],
                "strikeMin": None,
                "strikeMax": None,
                "mtfLeverageMin": None,
                "mtfLeverageMax": None,
                "firstSourceRow": position,
                "sourceUrl": url,
                "sourceTrust": "OPEN_SOURCE_UNOFFICIAL",
                "scope": "CATALOG_REFERENCE_ONLY",
                "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
            },
        )
        group["contractCount"] += 1
        group["instrumentTypes"].add(instrument_type)
        group["lotSizes"].add(lot_size)
        for field, target in (
            ("OPTION_TYPE", "optionTypes"),
            ("ASM_GSM_FLAG", "asmGsmFlags"),
            ("ASM_GSM_CATEGORY", "asmGsmCategories"),
        ):
            value = _text(raw.get(field))
            if value:
                group[target].add(value)
        if expiry:
            group["expiries"].add(expiry)
        for field, target in (("TICK_SIZE", "tickSizes"), ("SM_FREEZE_QTY", "freezeQuantities")):
            value = _number(raw.get(field))
            if value is not None:
                group[target].add(value)
        for value, target in (
            (security_id, "sampleSecurityIds"),
            (_text(raw.get("ISIN")), "sampleIsins"),
            (_text(raw.get("DISPLAY_NAME")), "sampleDisplayNames"),
        ):
            if value and value not in group[target] and len(group[target]) < 3:
                group[target].append(value)
        strike = _number(raw.get("STRIKE_PRICE"))
        if strike is not None and strike >= 0:
            group["strikeMin"] = strike if group["strikeMin"] is None else min(group["strikeMin"], strike)
            group["strikeMax"] = strike if group["strikeMax"] is None else max(group["strikeMax"], strike)
        leverage = _number(raw.get("MTF_LEVERAGE"))
        if leverage is not None:
            group["mtfLeverageMin"] = leverage if group["mtfLeverageMin"] is None else min(group["mtfLeverageMin"], leverage)
            group["mtfLeverageMax"] = leverage if group["mtfLeverageMax"] is None else max(group["mtfLeverageMax"], leverage)

    rows: list[dict[str, Any]] = []
    set_fields = (
        "instrumentTypes", "lotSizes", "expiries", "optionTypes", "tickSizes",
        "freezeQuantities", "asmGsmFlags", "asmGsmCategories",
    )
    for key in sorted(groups):
        group = groups[key]
        for field in set_fields:
            group[field] = sorted(group[field])
        rows.append(group)
    if not rows:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Dhan rows failed scope/identity/lot validation.",
            output={"rows": [], "sourceRowCount": len(source_rows), "invalidRowCount": invalid},
            error="no valid rows",
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(rows),
        summary=f"Parsed {len(rows)} compact Dhan instrument schedules.",
        output={
            "rows": rows,
            "sourceRowCount": len(source_rows),
            "includedSourceRowCount": included,
            "normalizedRowCount": len(rows),
            "invalidRowCount": invalid,
            "duplicateRowCount": duplicates,
            "filteredOutOfScopeCount": filtered_scope,
            "filteredExpiredContractCount": filtered_expired,
            "parserVersion": "1.0.0",
            "sourceTrust": "OPEN_SOURCE_UNOFFICIAL",
            "scope": "CATALOG_REFERENCE_ONLY",
            "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
            "symbolMappingPolicy": "BROKER_MASTER_IDENTITY_ONLY",
        },
    )
