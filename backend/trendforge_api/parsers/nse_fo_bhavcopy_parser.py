from __future__ import annotations

from typing import Any

from .common import (
    compact_key,
    decode_bytes,
    extract_data_date,
    find_value,
    parse_date_value,
    parse_float,
    parse_int,
    rows_from_content,
    source_result,
)


REQUIRED_COLUMN_GROUPS: dict[str, tuple[str, ...]] = {
    "symbol": ("ticker_symbol", "tckr_symb", "symbol", "underlying"),
    "close": ("closing_price", "cls_pric", "close_price", "close"),
    "previous_close": (
        "previous_closing_price",
        "prvs_clsg_pric",
        "previous_close",
        "prev_close",
    ),
    "open_interest": ("open_interest", "opn_intrst", "oi"),
    "oi_change": (
        "change_in_open_interest",
        "chng_in_opn_intrst",
        "change_in_oi",
        "oi_change",
    ),
}


def _missing_required_columns(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return list(REQUIRED_COLUMN_GROUPS)
    available = {compact_key(key) for key in rows[0]}
    return [
        name
        for name, aliases in REQUIRED_COLUMN_GROUPS.items()
        if not any(compact_key(alias) in available for alias in aliases)
    ]


def _oi_quadrant(price_change: float, oi_change: int) -> str:
    if price_change > 0 and oi_change > 0:
        return "LONG_BUILD_UP"
    if price_change > 0 and oi_change < 0:
        return "SHORT_COVERING"
    if price_change < 0 and oi_change > 0:
        return "SHORT_BUILD_UP"
    if price_change < 0 and oi_change < 0:
        return "LONG_UNWINDING"
    return "NEUTRAL_OR_UNKNOWN"


FO_BHAV_SCHEMA_ID = "nse_fo_udiff_bhav_v1"


def parse_nse_fo_bhavcopy(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    data_date, date_source = extract_data_date(text, url, last_modified)
    rows, source_name = rows_from_content(content)
    missing_columns = _missing_required_columns(rows)
    if missing_columns:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=data_date,
            record_count=0,
            summary="NSE F&O bhavcopy is missing required derivative fields: "
            + ", ".join(missing_columns),
            output={
                "scope": "STOCK_DERIVATIVES_EOD",
                "dateSource": date_source,
                "sourceLayout": source_name,
                "missingRequiredColumns": missing_columns,
            },
        )
    if data_date is None:
        return source_result(
            parser_state="WAIT_SOURCE_DATE",
            data_date=None,
            record_count=0,
            summary="NSE F&O bhavcopy has no verifiable trade date.",
            output={
                "scope": "STOCK_DERIVATIVES_EOD",
                "dateSource": date_source,
                "sourceLayout": source_name,
            },
        )
    contracts: list[dict[str, Any]] = []
    for row in rows:
        symbol = find_value(row, ("ticker_symbol", "tckr_symb", "symbol", "underlying"))
        instrument = (
            find_value(
                row,
                (
                    "financial_instrument_type",
                    "fin_instrm_tp",
                    "instrument",
                    "instrument_type",
                ),
            )
            or ""
        )
        expiry_raw = find_value(row, ("expiry_date", "xpry_dt", "expiry")) or ""
        close_price = parse_float(
            find_value(row, ("closing_price", "cls_pric", "close_price", "close"))
        )
        previous_close = parse_float(
            find_value(
                row,
                (
                    "previous_closing_price",
                    "prvs_clsg_pric",
                    "previous_close",
                    "prev_close",
                ),
            )
        )
        settle_price = parse_float(
            find_value(row, ("settlement_price", "sttlm_pric", "settle"))
        )
        underlying_price = parse_float(
            find_value(row, ("underlying_price", "undrlyg_pric", "spot_price", "spot"))
        )
        open_interest = parse_int(
            find_value(row, ("open_interest", "opn_intrst", "oi"))
        )
        oi_change = parse_int(
            find_value(
                row,
                (
                    "change_in_open_interest",
                    "chng_in_opn_intrst",
                    "change_in_oi",
                    "oi_change",
                ),
            )
        )
        volume = parse_int(
            find_value(
                row, ("total_trading_volume", "ttl_tradg_vol", "contracts", "volume")
            )
        )
        strike = parse_float(find_value(row, ("strike_price", "strk_pric", "strike")))
        option_type = (
            (find_value(row, ("option_type", "optn_tp")) or "").strip().upper()
        )
        if not symbol or close_price <= 0 or open_interest < 0:
            continue
        price_change = close_price - previous_close if previous_close > 0 else 0.0
        is_future = "FUT" in instrument.upper() or (strike <= 0 and not option_type)
        basis = (
            close_price - underlying_price
            if is_future and underlying_price > 0
            else None
        )
        contracts.append(
            {
                "symbol": symbol.strip().upper(),
                "instrument": instrument.strip().upper(),
                "expiry": parse_date_value(expiry_raw) or expiry_raw.strip(),
                "strike": strike,
                "optionType": option_type,
                "close": close_price,
                "previousClose": previous_close,
                "settlementPrice": settle_price,
                "underlyingPrice": underlying_price,
                "basis": round(basis, 6) if basis is not None else None,
                "basisPercent": round((basis / underlying_price) * 100, 6)
                if basis is not None
                else None,
                "openInterest": open_interest,
                "oiChange": oi_change,
                "volume": volume,
                "priceChange": round(price_change, 6),
                "oiQuadrant": _oi_quadrant(price_change, oi_change),
                "scope": "STOCK_DERIVATIVES_EOD",
            }
        )
    if not contracts:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="No usable NSE F&O bhavcopy rows found.",
            output={"scope": "STOCK_DERIVATIVES_EOD", "dateSource": date_source},
        )
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(contracts),
        summary=f"NSE F&O contracts parsed from {source_name}; EOD OI/basis context available.",
        output={
            "scope": "STOCK_DERIVATIVES_EOD",
            "dateSource": date_source,
            "rows": contracts,
            "warning": "EOD bhavcopy cannot prove live OI or provide synchronized live option Greeks.",
        },
    )
