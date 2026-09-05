from __future__ import annotations

import csv
import io
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from .common import (
    decode_bytes,
    extract_data_date,
    find_value,
    parse_float,
    rows_from_content,
    source_result,
)


RELEVANT_MARKET_TOKENS = ("GOLD", "SILVER", "CRUDE", "COPPER", "NATURAL GAS")
TFF_RELEVANT_MARKET_TOKENS = (
    "U.S. DOLLAR INDEX",
    "10-YEAR U.S. TREASURY",
    "5-YEAR U.S. TREASURY",
    "2-YEAR U.S. TREASURY",
    "S&P 500",
    "NASDAQ-100",
    "VIX",
)


class _LinkExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attr_map = {key.lower(): value for key, value in attrs if value}
        href = attr_map.get("href")
        if href:
            self._href = urljoin(self.base_url, href)
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append(
                {
                    "text": " ".join(part for part in self._text if part),
                    "url": self._href,
                }
            )
            self._href = None
            self._text = []


def _is_relevant_market(market: str) -> bool:
    upper = market.upper()
    return any(token in upper for token in RELEVANT_MARKET_TOKENS)


def _is_relevant_tff_market(market: str) -> bool:
    upper = market.upper()
    return any(token in upper for token in TFF_RELEVANT_MARKET_TOKENS)


def _net(long_value: float, short_value: float) -> float:
    return long_value - short_value


def _row_layout(row: dict[str, str]) -> str | None:
    if find_value(row, ("lev_money_positions_long", "dealer_positions_long_all")) is not None:
        return "CFTC_TFF"
    if find_value(row, ("noncomm_positions_long_all",)) is not None:
        return "CFTC_LEGACY"
    if find_value(row, ("m_money_positions_long_all", "prod_merc_positions_long")) is not None:
        return "CFTC_DISAGGREGATED"
    return None


def _structured_position(row: dict[str, str], fallback_date: str | None) -> dict[str, Any] | None:
    layout = _row_layout(row)
    if layout is None:
        return None
    market = (
        find_value(
            row, ("market_and_exchange_names", "market", "market_and_exchange_name")
        )
        or ""
    ).strip()
    if layout == "CFTC_TFF":
        if not _is_relevant_tff_market(market):
            return None
    elif not _is_relevant_market(market):
        return None
    report_date = (
        find_value(
            row,
            (
                "report_date_as_yyyy_mm_dd",
                "report_date_as_yyyy-mm-dd",
                "report_date",
            ),
        )
        or fallback_date
    )
    base = {
        "market": market,
        "contractMarketCode": find_value(
            row,
            ("cftc_contract_market_code", "contract_market_code", "cftc_market_code"),
        ),
        "reportDate": report_date,
        "openInterest": parse_float(
            find_value(row, ("open_interest_all", "open_interest"))
        ),
        "sourceLayout": layout,
    }

    if layout == "CFTC_LEGACY":
        noncommercial_long = parse_float(
            find_value(row, ("noncomm_positions_long_all",))
        )
        noncommercial_short = parse_float(
            find_value(row, ("noncomm_positions_short_all",))
        )
        commercial_long = parse_float(
            find_value(row, ("comm_positions_long_all",))
        )
        commercial_short = parse_float(
            find_value(row, ("comm_positions_short_all",))
        )
        nonreportable_long = parse_float(
            find_value(row, ("nonrept_positions_long_all", "nonreportable_long"))
        )
        nonreportable_short = parse_float(
            find_value(row, ("nonrept_positions_short_all", "nonreportable_short"))
        )
        if noncommercial_long == noncommercial_short == commercial_long == commercial_short == 0:
            return None
        return {
            **base,
            "nonCommercialLong": noncommercial_long,
            "nonCommercialShort": noncommercial_short,
            "nonCommercialNet": _net(noncommercial_long, noncommercial_short),
            "commercialLong": commercial_long,
            "commercialShort": commercial_short,
            "commercialNet": _net(commercial_long, commercial_short),
            "nonReportableLong": nonreportable_long,
            "nonReportableShort": nonreportable_short,
            "nonReportableNet": _net(nonreportable_long, nonreportable_short),
            "scope": "COMMODITY_REGIME_ONLY",
        }

    if layout == "CFTC_TFF":
        dealer_long = parse_float(
            find_value(row, ("dealer_positions_long_all", "dealer_positions_long"))
        )
        dealer_short = parse_float(
            find_value(row, ("dealer_positions_short_all", "dealer_positions_short"))
        )
        asset_long = parse_float(
            find_value(row, ("asset_mgr_positions_long_all", "asset_mgr_positions_long"))
        )
        asset_short = parse_float(
            find_value(row, ("asset_mgr_positions_short_all", "asset_mgr_positions_short"))
        )
        leveraged_long = parse_float(
            find_value(row, ("lev_money_positions_long_all", "lev_money_positions_long"))
        )
        leveraged_short = parse_float(
            find_value(row, ("lev_money_positions_short_all", "lev_money_positions_short"))
        )
        other_long = parse_float(
            find_value(row, ("other_rept_positions_long_all", "other_rept_positions_long"))
        )
        other_short = parse_float(
            find_value(row, ("other_rept_positions_short_all", "other_rept_positions_short"))
        )
        if dealer_long == dealer_short == asset_long == asset_short == leveraged_long == leveraged_short == 0:
            return None
        return {
            **base,
            "dealerLong": dealer_long,
            "dealerShort": dealer_short,
            "dealerNet": _net(dealer_long, dealer_short),
            "assetManagerLong": asset_long,
            "assetManagerShort": asset_short,
            "assetManagerNet": _net(asset_long, asset_short),
            "leveragedMoneyLong": leveraged_long,
            "leveragedMoneyShort": leveraged_short,
            "leveragedMoneyNet": _net(leveraged_long, leveraged_short),
            "otherReportableLong": other_long,
            "otherReportableShort": other_short,
            "otherReportableNet": _net(other_long, other_short),
            "scope": "FINANCIAL_REGIME_ONLY",
        }

    managed_long = parse_float(
        find_value(row, ("m_money_positions_long_all", "managed_money_long"))
    )
    managed_short = parse_float(
        find_value(row, ("m_money_positions_short_all", "managed_money_short"))
    )
    commercial_long = parse_float(
        find_value(
            row,
            (
                "prod_merc_positions_long_all",
                "prod_merc_positions_long",
                "producer_merchant_long",
            ),
        )
    )
    commercial_short = parse_float(
        find_value(
            row,
            (
                "prod_merc_positions_short_all",
                "prod_merc_positions_short",
                "producer_merchant_short",
            ),
        )
    )
    swap_long = parse_float(
        find_value(row, ("swap_positions_long_all", "swap_long_all", "swap_dealer_long"))
    )
    swap_short = parse_float(
        find_value(row, ("swap_positions_short_all", "swap_short_all", "swap_dealer_short"))
    )
    other_long = parse_float(
        find_value(row, ("other_rept_positions_long_all", "other_rept_positions_long", "other_reportable_long"))
    )
    other_short = parse_float(
        find_value(row, ("other_rept_positions_short_all", "other_rept_positions_short", "other_reportable_short"))
    )
    nonreportable_long = parse_float(
        find_value(row, ("nonrept_positions_long_all", "nonreportable_long", "nonrept_long_all"))
    )
    nonreportable_short = parse_float(
        find_value(row, ("nonrept_positions_short_all", "nonreportable_short", "nonrept_short_all"))
    )
    if managed_long == managed_short == commercial_long == commercial_short == swap_long == swap_short == other_long == other_short == 0:
        return None
    return {
        **base,
        "managedMoneyLong": managed_long,
        "managedMoneyShort": managed_short,
        "managedMoneyNet": _net(managed_long, managed_short),
        "commercialLong": commercial_long,
        "commercialShort": commercial_short,
        "commercialNet": _net(commercial_long, commercial_short),
        "swapDealerLong": swap_long,
        "swapDealerShort": swap_short,
        "swapDealerNet": _net(swap_long, swap_short),
        "otherReportableLong": other_long,
        "otherReportableShort": other_short,
        "otherReportableNet": _net(other_long, other_short),
        "nonReportableLong": nonreportable_long,
        "nonReportableShort": nonreportable_short,
        "nonReportableNet": _net(nonreportable_long, nonreportable_short),
        "scope": "COMMODITY_REGIME_ONLY",
    }


def _parse_disaggregated_headerless_rows(text: str) -> list[dict[str, Any]]:
    """Parse CFTC f_disagg.txt rows, which are official CSV rows without a header."""
    positions: list[dict[str, Any]] = []
    try:
        reader = csv.reader(io.StringIO(text))
        raw_rows = list(reader)
    except csv.Error:
        return positions

    for raw in raw_rows:
        if len(raw) < 23:
            continue
        market = raw[0].strip().strip('"')
        if not _is_relevant_market(market):
            continue
        report_date = raw[2].strip() or None
        open_interest = parse_float(raw[7])
        commercial_long = parse_float(raw[8])
        commercial_short = parse_float(raw[9])
        swap_long = parse_float(raw[10])
        swap_short = parse_float(raw[11])
        swap_spread = parse_float(raw[12])
        mm_long = parse_float(raw[13])
        mm_short = parse_float(raw[14])
        mm_spread = parse_float(raw[15])
        other_long = parse_float(raw[16])
        other_short = parse_float(raw[17])
        other_spread = parse_float(raw[18])
        nonrep_long = parse_float(raw[21])
        nonrep_short = parse_float(raw[22])
        if (
            mm_long
            == mm_short
            == commercial_long
            == commercial_short
            == swap_long
            == swap_short
            == other_long
            == other_short
            == 0
        ):
            continue
        positions.append(
            {
                "market": market,
                "contractMarketCode": raw[3].strip() or None,
                "reportDate": report_date,
                "openInterest": open_interest,
                "managedMoneyLong": mm_long,
                "managedMoneyShort": mm_short,
                "managedMoneyNet": _net(mm_long, mm_short),
                "managedMoneySpread": mm_spread,
                "commercialLong": commercial_long,
                "commercialShort": commercial_short,
                "commercialNet": _net(commercial_long, commercial_short),
                "swapDealerLong": swap_long,
                "swapDealerShort": swap_short,
                "swapDealerNet": _net(swap_long, swap_short),
                "swapDealerSpread": swap_spread,
                "otherReportableLong": other_long,
                "otherReportableShort": other_short,
                "otherReportableNet": _net(other_long, other_short),
                "otherReportableSpread": other_spread,
                "nonReportableLong": nonrep_long,
                "nonReportableShort": nonrep_short,
                "nonReportableNet": _net(nonrep_long, nonrep_short),
                "scope": "COMMODITY_REGIME_ONLY",
                "sourceLayout": "CFTC_DISAGGREGATED_HEADERLESS",
            }
        )
    return positions


def parse_cftc_cot_positions(
    content: bytes, *, url: str | None = None, last_modified: str | None = None
) -> dict[str, Any]:
    text = decode_bytes(content)
    if "<html" in text[:500].lower():
        extractor = _LinkExtractor(url or "https://www.cftc.gov/")
        extractor.feed(text)
        links = [
            link
            for link in extractor.links
            if "#" not in link["url"]
            and "exit/index" not in link["url"].lower()
            and any(
                token in link["url"].lower()
                for token in (
                    "dea/",
                    "newcot",
                    "historical",
                    "txt",
                    "csv",
                    "zip",
                    "publicreporting.cftc.gov",
                )
            )
            and any(
                token in (link["text"] + link["url"]).lower()
                for token in (
                    "cot",
                    "commitment",
                    "dea",
                    "newcot",
                    "historical",
                    "txt",
                    "csv",
                    "zip",
                )
            )
        ][:100]
        return source_result(
            parser_state="PARSED_METADATA_ONLY",
            data_date=last_modified,
            record_count=len(links),
            summary="CFTC COT page metadata/report links parsed. Position-level COT file not present in this snapshot.",
            output={
                "scope": "COMMODITY_REGIME_ONLY",
                "reportLinks": links,
                "warning": "Metadata-only CFTC output cannot pass MCX context.",
            },
        )

    data_date, date_source = extract_data_date(text, url, last_modified)
    rows, source_name = rows_from_content(content)
    positions: list[dict[str, Any]] = []
    for row in rows:
        position = _structured_position(row, data_date)
        if position:
            positions.append(position)

    if not positions:
        positions = _parse_disaggregated_headerless_rows(text)
        if positions:
            source_name = "cftc_disaggregated_headerless"

    if not positions:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=data_date,
            record_count=0,
            summary="No relevant CFTC COT commodity positions found in latest raw snapshot.",
            output={"scope": "COMMODITY_REGIME_ONLY", "dateSource": date_source},
        )

    report_dates = [
        str(item["reportDate"]) for item in positions if item.get("reportDate")
    ]
    latest = max(report_dates) if report_dates else data_date
    latest_positions = [
        item for item in positions if not latest or item.get("reportDate") == latest
    ]
    if latest:
        data_date = str(latest)[:10]
    regimes = []
    for item in latest_positions:
        layout = item.get("sourceLayout", "CFTC_DISAGGREGATED")
        if layout == "CFTC_LEGACY":
            signal_family = "NON_COMMERCIAL"
            signal_net = item["nonCommercialNet"]
            context_net = item["commercialNet"]
        elif layout == "CFTC_TFF":
            signal_family = "LEVERAGED_MONEY"
            signal_net = item["leveragedMoneyNet"]
            context_net = item["dealerNet"]
        else:
            signal_family = "MANAGED_MONEY"
            signal_net = item["managedMoneyNet"]
            context_net = item["commercialNet"]
        if signal_net > 0:
            regime = f"{signal_family}_NET_LONG"
        elif signal_net < 0:
            regime = f"{signal_family}_NET_SHORT"
        else:
            regime = f"{signal_family}_BALANCED"
        market_history = [
            row.get(
                {
                    "CFTC_LEGACY": "nonCommercialNet",
                    "CFTC_TFF": "leveragedMoneyNet",
                }.get(layout, "managedMoneyNet")
            )
            for row in positions
            if row["market"] == item["market"]
            and row.get("sourceLayout", "CFTC_DISAGGREGATED") == layout
        ]
        market_history = [value for value in market_history if value is not None]
        percentile = None
        if len(market_history) >= 20:
            percentile = round(
                sum(value <= signal_net for value in market_history)
                / len(market_history),
                4,
            )
        regime_row = {
            "market": item["market"],
            "regime": regime,
            "signalFamily": signal_family,
            "signalNet": signal_net,
            "contextNet": context_net,
            "signalPercentile": percentile,
            "contextInterpretation": "CATEGORY_CONTEXT_ONLY",
            "crowdingInterpretation": "AVAILABLE"
            if percentile is not None
            else "WITHHELD_INSUFFICIENT_HISTORY",
            "scope": item["scope"],
            "sourceLayout": layout,
        }
        if layout == "CFTC_DISAGGREGATED" or layout == "CFTC_DISAGGREGATED_HEADERLESS":
            regime_row.update(
                {
                    "managedMoneyNet": signal_net,
                    "commercialNet": context_net,
                    "managedMoneyPercentile": percentile,
                    "commercialInterpretation": "HEDGING_CATEGORY_CONTEXT_ONLY",
                }
            )
        regimes.append(regime_row)

    scopes = {item["scope"] for item in latest_positions}
    output_scope = scopes.pop() if len(scopes) == 1 else "MIXED_CFTC_POSITIONING_CONTEXT"

    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=data_date,
        record_count=len(latest_positions),
        summary=f"CFTC COT positions parsed from {source_name}; weekly delayed positioning context only.",
        output={
            "scope": output_scope,
            "dateSource": date_source,
            "warning": "CFTC COT is weekly delayed and cannot be an intraday trigger.",
            "positions": latest_positions,
            "positionHistory": positions,
            "historyCount": len(positions),
            "regimes": regimes,
        },
    )
