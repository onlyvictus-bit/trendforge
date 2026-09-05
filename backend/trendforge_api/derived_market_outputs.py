from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, date, datetime
from math import isfinite
from pathlib import Path
from typing import Any, Iterable

from .derivatives_engine import black_scholes_greeks
from .market_data_store import MarketDataStore


CALCULATED_OUTPUT_KEYS = frozenset(
    {
        "fundamental_ratios_v1",
        "option_greeks_calculated_v1",
        "pcr_max_pain_history_v1",
        "industry_peer_group_v1",
    }
)
ZERO_AUTHORITY = {
    "derived": True,
    "scoreEligible": False,
    "voteEligible": False,
    "canUnlockReady": False,
}


def _float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) else None


def _positive(value: Any) -> float | None:
    parsed = _float(value)
    return parsed if parsed is not None and parsed > 0 else None


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    for pattern in ("%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def _canonical_hashes(values: Iterable[str]) -> list[str]:
    return sorted(
        {
            str(value).strip().casefold()
            for value in values
            if len(str(value).strip()) == 64
        }
    )


def _base_output(
    key: str,
    *,
    data_date: date | None,
    records: list[dict[str, Any]],
    lineage_hashes: Iterable[str],
    state: str = "CALCULATED",
    **extra: Any,
) -> dict[str, Any]:
    if key not in CALCULATED_OUTPUT_KEYS:
        raise ValueError(f"unknown calculated output key: {key}")
    return {
        "key": key,
        "sourceKey": key,
        "normalizedSourceKey": key,
        "dataDate": data_date.isoformat() if data_date else None,
        "state": state,
        "recordsScope": "CALCULATED_INFORMATIONAL",
        "records": records,
        "normalizedRowCount": len(records),
        "lineageHashes": _canonical_hashes(lineage_hashes),
        **ZERO_AUTHORITY,
        **extra,
    }


def build_industry_peer_groups(
    records: list[dict[str, Any]],
    *,
    data_date: date,
    lineage_hash: str,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in records:
        symbol = str(record.get("symbol") or "").strip().upper()
        isin = str(record.get("isin") or "").strip().upper()
        company = str(record.get("company") or "").strip()
        industry = str(record.get("industry") or "").strip()
        if symbol and isin and company and industry:
            grouped[industry].append(
                {"symbol": symbol, "isin": isin, "company": company}
            )

    rows: list[dict[str, Any]] = []
    for industry in sorted(grouped):
        members = sorted(grouped[industry], key=lambda item: item["symbol"])
        for member in members:
            rows.append(
                {
                    **member,
                    "industry": industry,
                    "peerSymbols": [
                        item["symbol"]
                        for item in members
                        if item["symbol"] != member["symbol"]
                    ],
                    "peerMethod": "EXACT_NSE_NIFTY500_INDUSTRY",
                    "lineageHashes": _canonical_hashes((lineage_hash,)),
                    **ZERO_AUTHORITY,
                }
            )
    return _base_output(
        "industry_peer_group_v1",
        data_date=data_date,
        records=rows,
        lineage_hashes=(lineage_hash,),
        sourceKeys=["nse_nifty500_constituents"],
        rejectedRowCount=max(0, len(records) - len(rows)),
    )


def _select_risk_free_rate(
    rows: list[dict[str, Any]], days_to_expiry: int
) -> tuple[int, float] | None:
    candidates: list[tuple[int, float]] = []
    for row in rows:
        tenor = _positive(row.get("tenorDays"))
        rate = _float(row.get("annualRateDecimal"))
        if tenor is None or rate is None or not -0.05 <= rate <= 0.5:
            continue
        candidates.append((int(tenor), rate))
    if not candidates:
        return None
    return min(candidates, key=lambda item: (abs(item[0] - days_to_expiry), item[0]))


def build_option_greeks(
    option_rows: list[dict[str, Any]],
    *,
    rbi_rate_rows: list[dict[str, Any]],
    valuation_date: date,
    lineage_hashes: Iterable[str],
) -> dict[str, Any]:
    hashes = _canonical_hashes(lineage_hashes)
    rows: list[dict[str, Any]] = []
    rejected = 0
    for record in option_rows:
        symbol = str(record.get("symbol") or "").strip().upper()
        expiry = _parse_date(record.get("expiry"))
        spot = _positive(record.get("underlyingValue"))
        strike = _positive(record.get("strike"))
        iv_pct = _positive(record.get("iv"))
        option_code = str(record.get("optionType") or "").strip().upper()
        option_type = "call" if option_code == "CE" else "put" if option_code == "PE" else None
        days_to_expiry = (expiry - valuation_date).days if expiry else 0
        selected_rate = _select_risk_free_rate(rbi_rate_rows, days_to_expiry)
        if (
            not symbol
            or expiry is None
            or days_to_expiry <= 0
            or spot is None
            or strike is None
            or iv_pct is None
            or iv_pct > 500
            or option_type is None
            or selected_rate is None
        ):
            rejected += 1
            continue
        tenor, rate = selected_rate
        volatility = iv_pct / 100.0
        calculated = black_scholes_greeks(
            spot=spot,
            strike=strike,
            time_years=days_to_expiry / 365.0,
            rate=rate,
            volatility=volatility,
            option_type=option_type,
            dividend_yield=0.0,
        )
        rows.append(
            {
                "symbol": symbol,
                "expiry": expiry.isoformat(),
                "strike": strike,
                "optionType": option_code,
                "valuationDate": valuation_date.isoformat(),
                "daysToExpiry": days_to_expiry,
                "spot": spot,
                "sourceIvPct": iv_pct,
                "volatilityDecimal": volatility,
                "riskFreeRate": rate,
                "riskFreeRateTenorDays": tenor,
                "rateSourceKey": "rbi_tbill_yield",
                "dividendYieldAssumption": 0.0,
                "model": "BLACK_SCHOLES_MERTON",
                "modelVersion": "1.0.0",
                "delta": round(calculated.delta, 8),
                "gamma": round(calculated.gamma, 8),
                "thetaPerDay": round(calculated.theta_per_day, 8),
                "vegaPerVolPoint": round(calculated.vega_per_vol_point, 8),
                "rhoPerRatePoint": round(calculated.rho_per_rate_point, 8),
                "lineageHashes": hashes,
                **ZERO_AUTHORITY,
            }
        )
    state = "CALCULATED" if rows else "WAIT_REQUIRED_INPUT"
    return _base_output(
        "option_greeks_calculated_v1",
        data_date=valuation_date,
        records=rows,
        lineage_hashes=hashes,
        state=state,
        sourceKeys=["nse_option_chain_equity", "rbi_tbill_yield"],
        rejectedRowCount=rejected,
        assumptions={"dividendYield": 0.0, "ivUnit": "PERCENT_TO_DECIMAL"},
    )


def _max_pain(rows: list[dict[str, Any]]) -> float | None:
    strikes = sorted(
        {
            value
            for row in rows
            if (value := _positive(row.get("strike"))) is not None
        }
    )
    best: tuple[float, float] | None = None
    for candidate in strikes:
        pain = 0.0
        for row in rows:
            strike = _positive(row.get("strike"))
            oi = _positive(row.get("openInterest"))
            option_type = str(row.get("optionType") or "").upper()
            if strike is None or oi is None:
                continue
            if option_type == "CE" and candidate > strike:
                pain += (candidate - strike) * oi
            elif option_type == "PE" and candidate < strike:
                pain += (strike - candidate) * oi
        if best is None or pain < best[1]:
            best = (candidate, pain)
    return best[0] if best else None


def build_pcr_max_pain_observation(
    option_rows: list[dict[str, Any]],
    *,
    data_date: date,
    lineage_hash: str,
) -> dict[str, Any]:
    grouped: dict[tuple[str, date], list[dict[str, Any]]] = defaultdict(list)
    rejected = 0
    for row in option_rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        expiry = _parse_date(row.get("expiry"))
        if not symbol or expiry is None:
            rejected += 1
            continue
        grouped[(symbol, expiry)].append(row)

    rows: list[dict[str, Any]] = []
    canonical_hash = _canonical_hashes((lineage_hash,))
    hash_token = canonical_hash[0] if canonical_hash else "NO_HASH"
    for (symbol, expiry), group in sorted(grouped.items()):
        call_oi = sum(
            _positive(row.get("openInterest")) or 0.0
            for row in group
            if str(row.get("optionType") or "").upper() == "CE"
        )
        put_oi = sum(
            _positive(row.get("openInterest")) or 0.0
            for row in group
            if str(row.get("optionType") or "").upper() == "PE"
        )
        if call_oi <= 0 and put_oi <= 0:
            rejected += len(group)
            continue
        rows.append(
            {
                "symbol": symbol,
                "expiry": expiry.isoformat(),
                "observedDate": data_date.isoformat(),
                "callOiTotal": call_oi,
                "putOiTotal": put_oi,
                "pcrOi": round(put_oi / call_oi, 6) if call_oi > 0 else None,
                "maxPainStrike": _max_pain(group),
                "observationId": f"{symbol}|{expiry.isoformat()}|{data_date.isoformat()}|{hash_token}",
                "lineageHashes": canonical_hash,
                **ZERO_AUTHORITY,
            }
        )
    return _base_output(
        "pcr_max_pain_history_v1",
        data_date=data_date,
        records=rows,
        lineage_hashes=(lineage_hash,),
        sourceKeys=["nse_option_chain_equity"],
        historyPolicy="PROSPECTIVE_OBSERVED_SNAPSHOTS_ONLY",
        rejectedRowCount=rejected,
    )


def build_fundamental_ratios(
    financial_rows: list[dict[str, Any]],
    *,
    market_rows: list[dict[str, Any]],
    data_date: date,
    lineage_hashes: Iterable[str],
) -> dict[str, Any]:
    market_by_symbol = {
        str(row.get("symbol") or row.get("SYMBOL") or "").strip().upper(): row
        for row in market_rows
        if str(row.get("symbol") or row.get("SYMBOL") or "").strip()
    }
    hashes = _canonical_hashes(lineage_hashes)
    rows: list[dict[str, Any]] = []
    rejected = 0
    for facts in financial_rows:
        symbol = str(facts.get("symbol") or "").strip().upper()
        market = market_by_symbol.get(symbol)
        pat = _float(facts.get("profitAfterTaxCr"))
        equity = _positive(facts.get("totalEquityCr"))
        assets = _positive(facts.get("totalAssetsCr"))
        debt = _float(facts.get("totalDebtCr"))
        eps = _float(facts.get("eps"))
        price = _positive((market or {}).get("close") or (market or {}).get("lastPrice"))
        market_cap = _positive((market or {}).get("marketCapCr"))
        required = (symbol, market, pat, equity, assets, debt, eps, price, market_cap)
        if any(value is None or value == "" for value in required):
            rejected += 1
            continue
        assert pat is not None and equity is not None and assets is not None
        assert debt is not None and eps is not None and price is not None and market_cap is not None
        if eps == 0:
            rejected += 1
            continue
        rows.append(
            {
                "symbol": symbol,
                "periodEnd": str(facts.get("periodEnd") or data_date.isoformat()),
                "pe": round(price / eps, 6),
                "pb": round(market_cap / equity, 6),
                "roePct": round(pat / equity * 100, 6),
                "roaPct": round(pat / assets * 100, 6),
                "debtToEquity": round(debt / equity, 6),
                "missingMetrics": [],
                "calculationVersion": "1.0.0",
                "lineageHashes": hashes,
                **ZERO_AUTHORITY,
            }
        )
    state = "CALCULATED" if rows else "WAIT_REQUIRED_INPUT"
    return _base_output(
        "fundamental_ratios_v1",
        data_date=data_date,
        records=rows,
        lineage_hashes=hashes,
        state=state,
        sourceKeys=[
            "bse_financial_results_xbrl",
            "nse_bhavcopy_eod",
            "nse_pr_market_snapshot",
        ],
        rejectedRowCount=rejected,
        missingValuePolicy="REJECT_ROW_NEVER_ZERO_FILL",
    )


class DerivedMarketOutputService:
    """Materialize available calculations from committed last-good objects.

    Derived outputs intentionally do not enter the source registry or manifest.
    They are content-addressed calculated objects with immutable zero-score flags.
    """

    def __init__(self, *, store: MarketDataStore) -> None:
        self.store = store

    def _load(self, source_key: str) -> tuple[dict[str, Any], str, date | None] | None:
        latest = self.store.latest_for(source_key)
        if latest is None or not latest.object_path or not latest.content_hash:
            return None
        try:
            payload = json.loads(Path(latest.object_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        return payload, latest.content_hash, latest.data_date

    @staticmethod
    def _records(loaded: tuple[dict[str, Any], str, date | None] | None) -> list[dict[str, Any]]:
        if loaded is None:
            return []
        records = loaded[0].get("records")
        return [row for row in records if isinstance(row, dict)] if isinstance(records, list) else []

    def _persist(
        self,
        output: dict[str, Any],
        *,
        run_id: str,
        at: datetime,
        trading_date: date,
        slot: str,
    ) -> None:
        records = output.get("records")
        if not isinstance(records, list) or not records:
            return
        payload = json.dumps(
            output, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        output_date = _parse_date(output.get("dataDate")) or trading_date
        self.store.commit_success(
            run_id=run_id,
            source_key=str(output["key"]),
            trading_date=trading_date,
            slot=slot,
            attempted_at=at.astimezone(UTC),
            fetched_at=at.astimezone(UTC),
            data_date=output_date,
            source_url=f"calculated://trendforge/{output['key']}",
            http_status=200,
            media_type="application/vnd.trendforge.calculated+json",
            content=payload,
            extension="json",
            normalized_row_count=len(records),
            retry_count=0,
        )

    def materialize(
        self,
        *,
        run_id: str,
        at: datetime,
        trading_date: date,
        slot: str,
    ) -> dict[str, dict[str, Any]]:
        outputs: dict[str, dict[str, Any]] = {}
        constituents = self._load("nse_nifty500_constituents")
        if constituents and self._records(constituents):
            output = build_industry_peer_groups(
                self._records(constituents),
                data_date=constituents[2] or trading_date,
                lineage_hash=constituents[1],
            )
            outputs[output["key"]] = output

        option_chain = self._load("nse_option_chain_equity")
        rbi_rates = self._load("rbi_tbill_yield")
        if option_chain and self._records(option_chain):
            observation = build_pcr_max_pain_observation(
                self._records(option_chain),
                data_date=option_chain[2] or trading_date,
                lineage_hash=option_chain[1],
            )
            outputs[observation["key"]] = observation
            if rbi_rates and self._records(rbi_rates):
                greeks = build_option_greeks(
                    self._records(option_chain),
                    rbi_rate_rows=self._records(rbi_rates),
                    valuation_date=option_chain[2] or trading_date,
                    lineage_hashes=(option_chain[1], rbi_rates[1]),
                )
                if greeks["records"]:
                    outputs[greeks["key"]] = greeks

        financial = self._load("bse_financial_results_xbrl")
        bhavcopy = self._load("nse_bhavcopy_eod")
        market_cap = self._load("nse_pr_market_snapshot")
        if financial and bhavcopy:
            combined_market = self._records(bhavcopy) + self._records(market_cap)
            ratios = build_fundamental_ratios(
                self._records(financial),
                market_rows=combined_market,
                data_date=financial[2] or trading_date,
                lineage_hashes=(
                    financial[1],
                    bhavcopy[1],
                    *((market_cap[1],) if market_cap else ()),
                ),
            )
            if ratios["records"]:
                outputs[ratios["key"]] = ratios

        for output in outputs.values():
            self._persist(
                output,
                run_id=run_id,
                at=at,
                trading_date=trading_date,
                slot=slot,
            )
        return outputs
