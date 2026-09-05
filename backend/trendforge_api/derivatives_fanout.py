"""Fan-out aggregator for the NSE liveEquity-derivatives route family.

The bare URL without `index` is an alias only. Usable screener data comes from
child index routes. This module preserves each child identity and deduplicates
by contract identifier.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .institutional_sources import AsyncEndpointClient, EndpointFetchResult, FetchState

# Canonical child endpoints (already registered in config.yaml).
DERIVATIVES_CHILD_KEYS: tuple[str, ...] = (
    "nse_live_equity_derivatives_stock_opt",
    "nse_live_equity_derivatives_stock_fut",
    "nse_live_equity_derivatives_index_opt",
    "nse_live_equity_derivatives_index_fut",
    "nse_live_equity_derivatives_banknifty_opt",
    "nse_live_equity_derivatives_banknifty_fut",
)

CHILD_INDEX: dict[str, str] = {
    "nse_live_equity_derivatives_stock_opt": "stock_opt",
    "nse_live_equity_derivatives_stock_fut": "stock_fut",
    "nse_live_equity_derivatives_index_opt": "nse50_opt",
    "nse_live_equity_derivatives_index_fut": "nse50_fut",
    "nse_live_equity_derivatives_banknifty_opt": "nifty_bank_opt",
    "nse_live_equity_derivatives_banknifty_fut": "nifty_bank_fut",
}

ALIAS_KEY = "nse_live_equity_derivatives"
ALIAS_URL = "https://www.nseindia.com/api/liveEquity-derivatives"


@dataclass
class DerivativesFanoutResult:
    alias_key: str = ALIAS_KEY
    alias_only: bool = True
    fetched_at: str = ""
    child_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)
    record_count: int = 0
    classification: str = "ALIAS_ONLY"
    summary: str = ""


def _contract_id(row: dict[str, Any]) -> str:
    identifier = str(row.get("identifier") or "").strip()
    if identifier:
        return identifier
    parts = [
        str(row.get("underlying") or row.get("symbol") or "").upper(),
        str(row.get("instrumentType") or row.get("instrument") or ""),
        str(row.get("expiryDate") or row.get("expiry") or ""),
        str(row.get("optionType") or ""),
        str(row.get("strikePrice") or row.get("strike") or ""),
    ]
    return "|".join(parts)


def _rows_from_payload(payload: Any, child_key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    index_name = CHILD_INDEX.get(child_key, child_key)
    timestamp = str(payload.get("timestamp") or "")
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        row["_source_key"] = child_key
        row["_index"] = index_name
        row["_contract_id"] = _contract_id(item)
        row["_timestamp"] = timestamp
        rows.append(row)
    return rows


async def fetch_derivatives_fanout(
    client: AsyncEndpointClient,
) -> DerivativesFanoutResult:
    """Fetch all child liveEquity-derivatives indexes; never treat alias as independent."""
    fetched_at = datetime.now(UTC).isoformat()
    child_meta: dict[str, dict[str, Any]] = {}
    combined: list[dict[str, Any]] = []
    seen: set[str] = set()

    for child_key in DERIVATIVES_CHILD_KEYS:
        result: EndpointFetchResult = await client.fetch(child_key, {})
        state = result.state.value if hasattr(result.state, "value") else str(result.state)
        rows = _rows_from_payload(result.payload, child_key)
        usable = len(rows) if state == FetchState.RAW_ARCHIVED.value or state == "RAW_ARCHIVED" else 0
        # Count rows from fresh archive only; stale fallback is not populated usable.
        if state == "STALE_FALLBACK":
            usable = 0
        child_meta[child_key] = {
            "index": CHILD_INDEX[child_key],
            "url": result.url,
            "state": state,
            "status_code": result.status_code,
            "raw_path": result.raw_path,
            "record_count_raw": result.record_count,
            "usable_rows": usable,
            "sample_rows": rows[:2],
        }
        if usable <= 0:
            continue
        for row in rows:
            cid = str(row.get("_contract_id") or "")
            if cid and cid in seen:
                continue
            if cid:
                seen.add(cid)
            combined.append(row)

    classification = "POPULATED_USABLE" if combined else "VALID_EMPTY_OR_CHILDREN_EMPTY"
    summary = (
        f"Alias {ALIAS_KEY} is not a standalone endpoint. "
        f"Fan-out over {len(DERIVATIVES_CHILD_KEYS)} child indexes produced "
        f"{len(combined)} unique contracts."
    )
    return DerivativesFanoutResult(
        alias_key=ALIAS_KEY,
        alias_only=True,
        fetched_at=fetched_at,
        child_results=child_meta,
        rows=combined,
        record_count=len(combined),
        classification=classification,
        summary=summary,
    )


def fanout_to_dict(result: DerivativesFanoutResult) -> dict[str, Any]:
    return {
        "alias_key": result.alias_key,
        "alias_url": ALIAS_URL,
        "alias_only": result.alias_only,
        "classification": result.classification,
        "fetched_at": result.fetched_at,
        "record_count": result.record_count,
        "summary": result.summary,
        "child_results": result.child_results,
        "sample_rows": result.rows[:2],
        "rows": result.rows,
    }
