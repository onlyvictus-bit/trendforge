"""One run-scoped Source Operations projection for the Inventory Workbench."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from .source_inventory_compiler import compile_default_inventory
from .source_monitor import SOURCE_KEY_ALIASES, source_catalog_records
from .storage import (
    DATA_DIR,
    DB_PATH,
    list_source_fetch_attempts,
    list_source_freshness_status,
    list_source_parser_outputs,
)


SOURCE_OPERATIONS_CONTRACT = "trendforge.sourceOperations.v1"
SOURCE_STATES = (
    "HEALTHY",
    "VALID_EMPTY",
    "STALE_PARTIAL",
    "BLOCKED",
    "FAILED",
    "NOT_ATTEMPTED",
)
_DEFAULT_STALE_HOURS = {
    "intraday": 8,
    "daily": 72,
    "weekly": 240,
    "fortnightly": 480,
    "monthly": 1080,
    "quarterly": 2640,
    "annual": 9600,
    "event_based": 720,
}


def _latest(rows: list[dict[str, Any]], key: str, time_key: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        source_key = str(row.get(key) or "").strip()
        if not source_key:
            continue
        previous = output.get(source_key)
        current_time = str(row.get(time_key) or "")
        previous_time = str(previous.get(time_key) or "") if previous else ""
        if previous is None or (current_time, int(row.get("id") or 0)) > (
            previous_time,
            int(previous.get("id") or 0),
        ):
            output[source_key] = row
    return output


def _expired(
    timestamp: str | None,
    *,
    stale_after_hours: int | float | None,
    frequency: str | None,
    now: datetime,
) -> bool:
    if not timestamp:
        return True
    try:
        observed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return True
    if observed.tzinfo is None or observed.utcoffset() is None:
        return True
    declared = float(stale_after_hours or 0)
    allowed = declared if declared > 0 else _DEFAULT_STALE_HOURS.get(
        str(frequency or "").casefold(), 72
    )
    return (now - observed.astimezone(UTC)).total_seconds() > allowed * 3600


def _classify(
    source: dict[str, Any],
    freshness: dict[str, Any] | None,
    parser: dict[str, Any] | None,
    attempt: dict[str, Any] | None,
    *,
    now: datetime,
) -> dict[str, Any]:
    reason = str(
        (freshness or {}).get("reason")
        or (parser or {}).get("parser_status")
        or (attempt or {}).get("result_state")
        or "No observed fetch or parser proof"
    )
    proof_at = (
        (freshness or {}).get("checked_at")
        or (parser or {}).get("created_at")
        or (attempt or {}).get("attempted_at")
    )
    data_date = (freshness or {}).get("latest_data_date") or (parser or {}).get(
        "data_date"
    )
    if freshness is None and parser is None and attempt is None:
        return {"state": "NOT_ATTEMPTED", "reason": reason, "proofAt": None, "dataDate": None}
    if _expired(
        proof_at,
        stale_after_hours=source.get("staleAfterHours"),
        frequency=(freshness or {}).get("expected_frequency")
        or source.get("expectedFrequency"),
        now=now,
    ):
        return {
            "state": "STALE_PARTIAL",
            "reason": f"Monitor observation expired. Last result: {reason}",
            "proofAt": proof_at,
            "dataDate": data_date,
        }
    upper = reason.upper()
    status_code = int((attempt or {}).get("status_code") or 0)
    if re.search(r"BLOCK|ACCESS_DENIED|CAPTCHA|WAF|RATE_LIMIT|HTTP 403|HTTP 429", upper) or status_code in {401, 403, 429}:
        state = "BLOCKED"
    elif re.search(r"PARSED_EMPTY|VALID_EMPTY|SOFT_EMPTY", upper):
        state = "VALID_EMPTY"
    elif re.search(r"SCHEMA_MISMATCH|METADATA_ONLY|PARSE_FAIL|FETCH_FAIL|MALFORMED|INVALID|ERROR", upper):
        state = "FAILED"
    elif re.search(r"WAIT_FETCH_REQUIRED|NOT_ATTEMPTED|NO_FETCH", upper):
        state = "NOT_ATTEMPTED"
    elif int((freshness or {}).get("is_fresh") or 0) == 1 and "FRESH STRUCTURED DATA" in upper:
        state = "HEALTHY"
    else:
        state = "STALE_PARTIAL"
    return {"state": state, "reason": reason, "proofAt": proof_at, "dataDate": data_date}


def collector_key_families(
    contracts: list[Any] | tuple[Any, ...] | None = None,
) -> tuple[dict[str, frozenset[str]], int]:
    """Map catalog/normalized keys onto the registry jobs that actually download.

    Inventory cards often use the normalized family name
    (`nse_block_deal_live`) while last-good is stored under the contract key
    (`nse_block_deal`). Companion cards are not extra fetch jobs.
    """
    families: dict[str, set[str]] = {}
    contract_count = 0
    loaded = contracts
    if loaded is None:
        try:
            from .market_data_registry import load_market_data_registry

            loaded = load_market_data_registry().contracts
        except Exception:
            loaded = ()
    for contract in loaded:
        source_key = str(getattr(contract, "source_key", "") or "").strip()
        normalized = str(
            getattr(contract, "normalized_source_key", "") or source_key
        ).strip()
        if not source_key:
            continue
        contract_count += 1
        group = {source_key, normalized} if normalized else {source_key}
        for key in group:
            families.setdefault(key, set()).update(group)
    for source, destination in SOURCE_KEY_ALIASES.items():
        group = {str(source).strip(), str(destination).strip()}
        group.discard("")
        for key in group:
            families.setdefault(key, set()).update(group)
    return {key: frozenset(group) for key, group in families.items()}, contract_count


def last_good_match(
    key: str,
    last_good_keys: set[str],
    families: dict[str, frozenset[str]],
) -> tuple[bool, str | None, str | None]:
    """Return (hit, via, matched_store_key). HTTP 200 is not consulted here."""
    clean = str(key or "").strip()
    if not clean:
        return False, None, None
    if clean in last_good_keys:
        return True, "exact", clean
    for alias in families.get(clean, frozenset()):
        if alias in last_good_keys:
            return True, "alias", alias
    return False, None, None


def _research_effect(key: str, state: str) -> str:
    if state in {"HEALTHY", "VALID_EMPTY"}:
        return "No failure impact. Valid-empty is not a positive family."
    effects = {
        "nse_bhavcopy_eod": "Cash price fact unavailable; A1-C1 cannot create a new rank run.",
        "nse_fo_bhavcopy": "Futures OI enrichment unavailable; cash names are not penalized.",
        "nse_fno_ban": "F&O restriction gate unknown; dependent rows remain WAIT.",
        "nse_mwpl_ban": "F&O restriction gate unknown; dependent rows remain WAIT.",
        "nse_mwpl_percentages": "MWPL_MISSING is retained; no percentage gate is invented.",
        "nse_index_close_eod": "Index context unavailable; no stock state is inferred.",
        "nse_corporate_filings_actions": "Corporate-action integrity unresolved; affected symbols remain WAIT.",
    }
    return effects.get(key, "Research fact unavailable; no stock impact is inferred.")


def build_source_operations_snapshot(scheduler: Any | None) -> dict[str, Any]:
    now = datetime.now(UTC)
    compiler = compile_default_inventory()
    catalog_models = source_catalog_records()
    catalog = [item.model_dump(mode="json", by_alias=True) for item in catalog_models]
    attempts = list_source_fetch_attempts(limit=5000)
    parser_outputs = list_source_parser_outputs(limit=5000)
    freshness_rows = list_source_freshness_status()
    latest_attempt = _latest(attempts, "source_key", "attempted_at")
    latest_parser = _latest(parser_outputs, "source_key", "created_at")
    freshness = {
        str(item.get("source_key") or "").strip(): item for item in freshness_rows
    }
    compiler_keys = {
        str(item.source_key or "").strip()
        for item in compiler.source_key_map
        if str(item.source_key or "").strip()
    }
    store = scheduler.store if scheduler is not None else None
    if store is None:
        from .market_data_store import MarketDataStore

        store = MarketDataStore(
            root=DATA_DIR / "market_data",
            db_path=DB_PATH,
        )
    try:
        last_good_keys = set(store.latest_all())
    except Exception:
        last_good_keys = set()
    families, collector_contracts = collector_key_families()

    rows: list[dict[str, Any]] = []
    for source in catalog:
        key = str(source.get("key") or "").strip()
        family = families.get(key, frozenset({key} if key else ()))
        attempt = latest_attempt.get(key)
        if attempt is None:
            for alias in family:
                attempt = latest_attempt.get(alias)
                if attempt is not None:
                    break
        parser = latest_parser.get(key)
        if parser is None:
            for alias in family:
                parser = latest_parser.get(alias)
                if parser is not None:
                    break
        fresh = freshness.get(key)
        if fresh is None:
            for alias in family:
                fresh = freshness.get(alias)
                if fresh is not None:
                    break
        observed = _classify(source, fresh, parser, attempt, now=now)
        parsed = bool(
            parser
            and int(parser.get("record_count") or 0) > 0
            and "STRUCTURED" in str(parser.get("parser_status") or "").upper()
        )
        research_usable = bool(
            observed["state"] == "HEALTHY"
            and fresh
            and fresh.get("latest_parser_output_id")
            and (key in compiler_keys or any(alias in compiler_keys for alias in family))
        )
        hit, via, matched = last_good_match(key, last_good_keys, families)
        rows.append(
            {
                "key": key,
                "name": source.get("name") or key,
                "url": source.get("url") or "",
                "authority": source.get("authority") or "UNSPECIFIED",
                **observed,
                "attempted": attempt is not None,
                "observed": any(value is not None for value in (attempt, parser, fresh)),
                "parsed": parsed,
                "lastGood": hit,
                "lastGoodVia": via,
                "lastGoodStoreKey": matched,
                "collectorJob": key in families,
                "researchUsable": research_usable,
                "effect": _research_effect(key, observed["state"]),
                "fetchPolicy": "Shared HTTP / breaker unspecified; no automatic retry claim.",
            }
        )
    state_counts = {state: 0 for state in SOURCE_STATES}
    for row in rows:
        state_counts[row["state"]] += 1

    source_track = {
        "compilerContracts": int(compiler.normalized_source_contract_count),
        "runtimeCatalogKeys": len(catalog),
        "collectorContracts": collector_contracts,
        "attemptedKeys": sum(row["observed"] for row in rows),
        "parsedKeys": sum(row["parsed"] for row in rows),
        "lastGoodKeys": sum(row["lastGood"] for row in rows),
        "lastGoodExact": sum(row.get("lastGoodVia") == "exact" for row in rows),
        "lastGoodViaAlias": sum(row.get("lastGoodVia") == "alias" for row in rows),
        "currentFacts": state_counts["HEALTHY"],
        "researchUsableFacts": sum(row["researchUsable"] for row in rows),
        "stateCounts": state_counts,
        "rows": rows,
    }
    post_commit = None
    if scheduler is not None:
        post_commit = scheduler.status().get("postCommit")
    elif store is not None:
        from .selection.cash_post_commit import CashPostCommitOrchestrator

        persisted = CashPostCommitOrchestrator(store=store).snapshot()
        if persisted is not None:
            post_commit = persisted.model_dump(mode="json", by_alias=True)
    return {
        "contract": SOURCE_OPERATIONS_CONTRACT,
        "asOf": now.isoformat(),
        "sourceTrack": source_track,
        "cashTrack": post_commit,
        "permissions": {
            "sourceActivationReady": bool(compiler.source_activation_ready),
            "gateAuthorized": int(compiler.gate_authorized_source_key_count),
            "researchCeiling": "WATCH_WAIT_REJECT",
            "canUnlockConfirmed": False,
            "executable": False,
        },
        "catalogTopologyOwnedByFrontend": True,
        "note": (
            "Refresh downloads the collector registry (126 jobs), not 165 catalog cards. "
            "Normalized aliases share a parent job. Companion/provenance cards are not "
            "extra fetches. HTTP 200 / junk HTML / empty / stale is not usable. "
            "Inventory topology stays on links_105.json."
        ),
    }
