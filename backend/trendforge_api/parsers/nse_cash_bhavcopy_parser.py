from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .common import (
    find_value,
    parse_date_value,
    parse_float,
    parse_int,
    rows_from_content,
    source_result,
)


def _advance_state(close: float, previous_close: float) -> str:
    if close > previous_close:
        return "ADVANCE"
    if close < previous_close:
        return "DECLINE"
    return "UNCHANGED"


CASH_BHAV_SCHEMA_ID = "nse_cash_eq_bhav_v1"


def parse_nse_cash_bhavcopy(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    rows, source_name = rows_from_content(content)
    fallback_date = parse_date_value(url) or parse_date_value(last_modified)
    pr_match = re.search(r"PR(\d{2})(\d{2})(\d{2})\.zip", url or "", re.I)
    if pr_match:
        try:
            fallback_date = datetime.strptime("".join(pr_match.groups()), "%d%m%y").date().isoformat()
        except ValueError:
            pass
    normalized: list[dict[str, Any]] = []
    dates: set[str] = set()
    for row in rows:
        trade_date = parse_date_value(
            find_value(row, ("trading_date", "trad_dt", "trade_date"))
        ) or fallback_date
        symbol = (
            (find_value(row, ("ticker_symbol", "tckr_symb", "symbol")) or "")
            .strip()
            .upper()
        )
        series = (
            (find_value(row, ("security_series", "scty_srs", "series")) or "")
            .strip()
            .upper()
        )
        isin = (find_value(row, ("isin",)) or "").strip().upper()
        close = parse_float(find_value(row, ("closing_price", "cls_pric", "close")))
        previous_close = parse_float(
            find_value(
                row,
                (
                    "previous_closing_price",
                    "prvs_clsg_pric",
                    "previous_close",
                    "prev_cl_pr",
                ),
            )
        )
        if (
            not trade_date
            or not symbol
            or series != "EQ"
            or close <= 0
            or previous_close <= 0
        ):
            continue
        dates.add(trade_date)
        normalized.append(
            {
                "tradeDate": trade_date,
                "symbol": symbol,
                "series": series,
                "isin": isin or None,
                "open": parse_float(
                    find_value(row, ("opening_price", "open_price", "opn_pric", "open"))
                ),
                "high": parse_float(
                    find_value(row, ("high_price", "hgh_pric", "high"))
                ),
                "low": parse_float(find_value(row, ("low_price", "lw_pric", "low"))),
                "close": close,
                "previousClose": previous_close,
                "volume": parse_int(
                    find_value(
                        row,
                        ("total_trading_volume", "ttl_tradg_vol", "net_trdqty", "volume"),
                    )
                ),
                "tradedValue": parse_float(
                    find_value(
                        row,
                        ("total_traded_value", "ttl_trf_val", "net_trdval", "turnover"),
                    )
                ),
                "tradeCount": parse_int(
                    find_value(
                        row,
                        (
                            "total_number_of_transactions_executed",
                            "ttl_nb_of_txs_exctd",
                            "number_of_trades",
                            "trades",
                        ),
                    )
                ),
                "advanceState": _advance_state(close, previous_close),
                "scope": "NSE_CASH_EOD_EQ",
            }
        )
    if not normalized or len(dates) != 1:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE"
            if not normalized
            else "WAIT_SCHEMA_MISMATCH",
            data_date=next(iter(dates), None),
            record_count=0,
            summary="NSE cash bhavcopy lacks one coherent dated set of schema-valid EQ rows.",
            output={"scope": "NSE_CASH_EOD_EQ", "sourceName": source_name},
        )
    data_date = next(iter(dates))
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(normalized),
        summary=f"Official NSE cash EQ bhavcopy parsed from {source_name}.",
        output={
            "scope": "NSE_CASH_EOD_EQ",
            "rows": normalized,
            "breadth": {
                "advances": sum(row["advanceState"] == "ADVANCE" for row in normalized),
                "declines": sum(row["advanceState"] == "DECLINE" for row in normalized),
                "unchanged": sum(
                    row["advanceState"] == "UNCHANGED" for row in normalized
                ),
            },
        },
    )
