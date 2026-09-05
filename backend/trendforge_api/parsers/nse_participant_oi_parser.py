from __future__ import annotations

import json
from typing import Any

from .common import (
    decode_bytes,
    extract_data_date,
    find_value,
    parse_date_value,
    parse_float,
    rows_from_content,
    source_result,
)


PARTICIPANT_MAP = {
    "fii": "FII",
    "fiis": "FII",
    "fii/fpi": "FII",
    "fii_fpi": "FII",
    "fpi": "FII",
    "dii": "DII",
    "diis": "DII",
    "pro": "PRO",
    "proprietary": "PRO",
    "client": "CLIENT",
    "clients": "CLIENT",
    "client*": "CLIENT",
}


def _participant_name(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower().replace(" ", "")
    return PARTICIPANT_MAP.get(normalized, value.strip().upper())


def _sum_matching(
    row: dict[str, str], include: tuple[str, ...], exclude: tuple[str, ...] = ()
) -> float:
    total = 0.0
    for key, value in row.items():
        key_lower = key.lower()
        if all(item in key_lower for item in include) and not any(
            item in key_lower for item in exclude
        ):
            total += parse_float(value)
    return total


def parse_nse_participant_oi(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    rows, source_name = rows_from_content(content)
    parsed_rows: list[dict[str, Any]] = []

    for row in rows:
        participant = _participant_name(
            find_value(row, ("participant", "client_type", "type"))
        )
        if participant not in {"FII", "DII", "PRO", "CLIENT"}:
            continue
        fut_long = _sum_matching(row, ("fut", "long"))
        fut_short = _sum_matching(row, ("fut", "short"))
        opt_long = _sum_matching(row, ("opt", "long"))
        opt_short = _sum_matching(row, ("opt", "short"))
        if fut_long == fut_short == opt_long == opt_short == 0:
            long_total = _sum_matching(row, ("long",), ("change",))
            short_total = _sum_matching(row, ("short",), ("change",))
            fut_long = long_total
            fut_short = short_total
        parsed_rows.append(
            {
                "participant": participant,
                "futuresLongOi": fut_long,
                "futuresShortOi": fut_short,
                "futuresNetOi": fut_long - fut_short,
                "optionsLongOi": opt_long,
                "optionsShortOi": opt_short,
                "optionsNetOi": opt_long - opt_short,
                "totalNetOi": (fut_long - fut_short) + (opt_long - opt_short),
                "scope": "AGGREGATE_CONTEXT_ONLY",
            }
        )

    if not parsed_rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="No participant-wise OI rows found in latest raw snapshot.",
            output={
                "scope": "AGGREGATE_CONTEXT_ONLY",
                "dateSource": date_source,
                "rows": [],
                "records": [],
            },
        )

    by_participant = {row["participant"]: row for row in parsed_rows}
    fii = by_participant.get("FII", {}).get("futuresNetOi", 0)
    dii = by_participant.get("DII", {}).get("futuresNetOi", 0)
    if fii > 0 and dii > 0:
        regime = "BULLISH"
    elif fii < 0 and dii < 0:
        regime = "BEARISH"
    elif fii == 0 and dii == 0:
        regime = "NEUTRAL"
    else:
        regime = "MIXED"

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(parsed_rows),
        summary=f"NSE participant-wise OI parsed from {source_name}; aggregate regime only.",
        output={
            "scope": "AGGREGATE_CONTEXT_ONLY",
            "dateSource": date_source,
            "regime": regime,
            "regimeBasis": "FUTURES_ONLY_DIRECTIONAL_PROXY",
            "warning": "Participant OI is aggregate context only. Options long-minus-short is not treated as a directional regime signal.",
            "rows": parsed_rows,
            "records": parsed_rows,
        },
    )


def _bse_participant_label(raw: object) -> str | None:
    text = str(raw or "").strip()
    if not text or text.upper() in {"TOTAL", "ALL"}:
        return None
    cleaned = text.lower().replace(" ", "").replace("*", "")
    if cleaned in {"client", "clients"}:
        return "CLIENT"
    if cleaned in {"fii", "fiis", "fii/fpi", "fii_fpi", "fpi"}:
        return "FII"
    if cleaned in {"dii", "diis"}:
        return "DII"
    if cleaned in {"pro", "proprietary"}:
        return "PRO"
    return _participant_name(text)


def parse_bse_participant_oi(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    """Parse BSE DeriMarketDisclosureData_ng participant OI JSON.

    Live contract (verified 2026-08-10):
      GET .../DeriMarketDisclosureData_ng/w
      -> Table rows with CLIENT_TYPE (CLIENT*/FII/DII/Proprietary/Total),
         IND/STK futures long/short and option contract counts, RD_DATE.
    Aggregate context only — not stock-level FII positioning.
    """
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary=f"BSE participant OI schema validation failed: invalid JSON: {exc}.",
            output={"qualityIssues": [f"invalid JSON: {exc}"]},
            error=f"invalid JSON: {exc}",
        )

    table: list | None = None
    if isinstance(payload, dict):
        inner = payload.get("Table") or payload.get("table") or payload.get("data")
        if isinstance(inner, list):
            table = inner
    elif isinstance(payload, list):
        table = payload

    if not table:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="BSE DeriMarketDisclosure response contained no participant OI rows.",
        )

    parsed_rows: list[dict[str, Any]] = []
    data_date: str | None = None
    for index, item in enumerate(table):
        if not isinstance(item, dict):
            continue
        participant = _bse_participant_label(
            item.get("CLIENT_TYPE") or item.get("WEBSITE_CATEGORY") or item.get("client_type")
        )
        if participant not in {"FII", "DII", "PRO", "CLIENT"}:
            continue
        row_date = parse_date_value(
            item.get("RD_DATE") or item.get("TRADEDATE") or item.get("date")
        )
        if row_date and (data_date is None or row_date > data_date):
            data_date = row_date

        fut_long = parse_float(item.get("IND_FUT_LONG"), default=0) + parse_float(
            item.get("STK_FUT_LONG"), default=0
        ) + parse_float(item.get("FUT_LONG"), default=0)
        fut_short = parse_float(item.get("IND_FUT_SHORT"), default=0) + parse_float(
            item.get("STK_FUT_SHORT"), default=0
        ) + parse_float(item.get("FUT_SHORT"), default=0)
        opt_long = (
            parse_float(item.get("IND_CL_LNG_CNTRCTS"), default=0)
            + parse_float(item.get("IND_PT_LNG_CNTRCTS"), default=0)
            + parse_float(item.get("STK_CL_LNG_CNTRCTS"), default=0)
            + parse_float(item.get("STK_PT_LNG_CNTRCTS"), default=0)
            + parse_float(item.get("OPT_CALL_LONG"), default=0)
            + parse_float(item.get("OPT_PUT_LONG"), default=0)
        )
        opt_short = (
            parse_float(item.get("IND_CL_SHRT_CNTRCTS"), default=0)
            + parse_float(item.get("IND_PT_SHRT_CNTRCTS"), default=0)
            + parse_float(item.get("STK_CL_SHRT_CNTRCTS"), default=0)
            + parse_float(item.get("STK_PT_SHRT_CNTRCTS"), default=0)
            + parse_float(item.get("OPT_CALL_SHORT"), default=0)
            + parse_float(item.get("OPT_PUT_SHORT"), default=0)
        )
        # If only total contract fields present, keep futures zeros and put totals on options side.
        if fut_long == fut_short == opt_long == opt_short == 0:
            opt_long = parse_float(item.get("TOT_LNG_CNTRCTS") or item.get("TOTAL_LONG"), default=0)
            opt_short = parse_float(
                item.get("TOT_SHRT_CNTRCTS") or item.get("TOTAL_SHORT"), default=0
            )

        parsed_rows.append(
            {
                "participant": participant,
                "futuresLongOi": fut_long,
                "futuresShortOi": fut_short,
                "futuresNetOi": fut_long - fut_short,
                "optionsLongOi": opt_long,
                "optionsShortOi": opt_short,
                "optionsNetOi": opt_long - opt_short,
                "totalNetOi": (fut_long - fut_short) + (opt_long - opt_short),
                "scope": "AGGREGATE_CONTEXT_ONLY",
                "exchange": "BSE",
                "rawClientType": str(
                    item.get("CLIENT_TYPE") or item.get("WEBSITE_CATEGORY") or ""
                ),
            }
        )

    if not parsed_rows:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="BSE participant OI Table had no FII/DII/PRO/CLIENT rows.",
        )

    by_participant = {row["participant"]: row for row in parsed_rows}
    fii = by_participant.get("FII", {}).get("futuresNetOi", 0)
    dii = by_participant.get("DII", {}).get("futuresNetOi", 0)
    if fii > 0 and dii > 0:
        regime = "BULLISH"
    elif fii < 0 and dii < 0:
        regime = "BEARISH"
    elif fii == 0 and dii == 0:
        regime = "NEUTRAL"
    else:
        regime = "MIXED"

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(parsed_rows),
        summary="BSE participant-wise OI parsed from DeriMarketDisclosure; aggregate regime only.",
        output={
            "scope": "AGGREGATE_CONTEXT_ONLY",
            "exchange": "BSE",
            "dateSource": "RD_DATE" if data_date else (last_modified or url or "unknown"),
            "regime": regime,
            "regimeBasis": "FUTURES_ONLY_DIRECTIONAL_PROXY",
            "warning": (
                "BSE participant OI is aggregate context only. "
                "Not stock-level FII buying. Options long-minus-short is not a directional regime signal."
            ),
            "rows": parsed_rows,
            "records": parsed_rows,
        },
    )
