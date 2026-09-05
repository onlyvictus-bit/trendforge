from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Mapping

from .parsers.source_freshness import is_data_date_fresh, stale_reason
from .source_contracts import VALID_EMPTY_SOURCES
from .source_inventory_compiler import DEFAULT_WORKBOOK, compile_default_inventory
from .storage import (
    get_latest_source_parse_result,
    get_latest_source_snapshot,
    list_current_surveillance_actions,
    source_has_symbol_evidence,
)


@dataclass(frozen=True)
class GateDependency:
    code: str
    name: str
    source_keys: tuple[str, ...]
    purpose: str
    needs_structured_parser: bool = True


GATE_DEPENDENCIES: tuple[GateDependency, ...] = (
    GateDependency(
        "G03_STOCK_SAFETY",
        "ASM/GSM surveillance safety",
        ("nse_asm", "nse_gsm"),
        "Current official ASM and GSM lists are checked before a stock can become READY.",
    ),
    GateDependency(
        "G01_INSTITUTIONAL_REGIME",
        "Institutional cash-flow regime",
        ("nse_fii_dii", "nse_participant_oi", "nsdl_fpi_daily"),
        "Aggregate FII/DII cash flow plus participant derivatives context; market regime only.",
    ),
    GateDependency(
        "G12_SMART_MONEY",
        "Smart money confirmation",
        (
            "amfi_monthly_portfolio",
            "amfi_scheme_wise",
            "nse_large_deals",
            "sebi_pit_sast",
            "bse_buyback_tender",
            "bse_takeover_open_offer",
            "nse_pledge_data",
        ),
        "AMFI holdings, large deals, insider/PIT/SAST, buyback/open-offer context.",
    ),
    GateDependency(
        "G13_OI_CONFIRMS",
        "OI/MWPL/basis confirmation",
        (
            "nse_participant_oi",
            "nse_fno_ban",
            "nse_mwpl_percentages",
            "nse_slb",
            "nse_fo_bhavcopy",
            "nse_oi_spurts",
        ),
        "Derivatives positioning, MWPL/F&O ban risk, borrow pressure, and EOD validation.",
    ),
    GateDependency(
        "MCX_CONTEXT",
        "MCX commodity confirmation",
        (
            "mcx_bhavcopy",
            "cftc_cot",
            "world_gold_council_oi",
            "wgc_gold_etf_holdings",
            "wgc_gold_etf_flows",
            "sge_daily_report",
            "usd_inr",
        ),
        "MCX EOD/OI, CFTC positioning, global gold OI, ETF demand, SGE physical context, and USD/INR translation.",
    ),
)


PASS_REQUIREMENTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "G03_STOCK_SAFETY": (("nse_asm", "nse_gsm"),),
    "G01_INSTITUTIONAL_REGIME": (("nse_fii_dii",),),
    "G12_SMART_MONEY": (("nse_large_deals",),),
    "G13_OI_CONFIRMS": (("nse_fno_ban", "nse_mwpl_percentages", "nse_fo_bhavcopy"),),
    "MCX_CONTEXT": (("mcx_bhavcopy", "cftc_cot", "usd_inr"),),
}


@lru_cache(maxsize=4)
def _compiler_gate_context_cached(
    workbook_signature: tuple[int, int],
) -> tuple[bool, dict[str, bool]]:
    """Return the compiler activation ceiling and per-source gate permissions."""
    report = compile_default_inventory()
    permissions = {
        contract.source_contract_id: bool(
            report.source_activation_ready and contract.gate_permission
        )
        for contract in report.source_contracts
    }
    return report.source_activation_ready, permissions


def compiler_gate_context() -> tuple[bool, dict[str, bool]]:
    try:
        stat = DEFAULT_WORKBOOK.stat()
        signature = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        signature = (0, 0)
    return _compiler_gate_context_cached(signature)


def _symbol_has_fno_ban(symbol: str) -> bool:
    target = symbol.strip().upper()
    for source_key in ("nse_fno_ban", "nse_mwpl_ban"):
        parsed = get_latest_source_parse_result(source_key)
        if (
            parsed is None
            or parsed.parser_state != "PARSED_STRUCTURED"
            or parsed.output.get("evidenceCoverage") != "FNO_BAN_ONLY"
        ):
            continue
        if any(
            str(row.get("symbol", "")).strip().upper() == target
            and row.get("isBanned") is True
            for row in parsed.output.get("rows", [])
        ):
            return True
    return False


def _surveillance_matches(symbol: str) -> list[dict[str, str]]:
    return [
        {
            "sourceKey": str(row["source_key"]),
            "measure": str(row["measure"] or row["source_key"]).upper(),
            "stage": str(row["stage"] or "UNKNOWN"),
        }
        for row in list_current_surveillance_actions(symbol)
    ]


def stock_safety_state(
    symbol: str, source_states: list[dict] | None = None
) -> dict[str, object]:
    if source_states is None:
        compiler_context = compiler_gate_context()
        sources = [
            dependency_state(source_key, compiler_context=compiler_context)
            for source_key in ("nse_asm", "nse_gsm")
        ]
    else:
        sources = source_states
    state, reason = gate_state("G03_STOCK_SAFETY", sources)
    matches: list[dict[str, str]] = []
    source_data_is_current = all(
        row["state"]
        in {"PASS", "WAIT_SOURCE_ACTIVATION", "WAIT_SOURCE_GATE_PERMISSION"}
        for row in sources
    )
    if source_data_is_current:
        matches = _surveillance_matches(symbol)
        if matches:
            labels = ", ".join(
                f"{item['measure']} ({item['stage']})" for item in matches
            )
            state = "BLOCKED_SURVEILLANCE"
            reason = f"{symbol.upper()} is under official surveillance: {labels}."
    return {
        "state": state,
        "reason": reason,
        "matches": matches,
        "sources": sources,
    }


def dependency_state(
    source_key: str,
    *,
    compiler_context: tuple[bool, Mapping[str, bool]] | None = None,
) -> dict:
    source_activation_ready, gate_permissions = (
        compiler_context if compiler_context is not None else compiler_gate_context()
    )
    snapshot = get_latest_source_snapshot(source_key)
    parsed = get_latest_source_parse_result(source_key)
    if snapshot is None:
        if source_key == "nse_mwpl_percentages":
            state = "WAIT_MWPL_PERCENTAGES"
            reason = (
                "No separately verified official symbol-level MWPL percentage "
                "artifact exists."
            )
        else:
            state = "WAIT_SOURCE_SNAPSHOT"
            reason = "No raw source snapshot exists."
    elif snapshot.check_state == "BROKEN":
        state = "REJECT_SOURCE_BROKEN"
        reason = snapshot.error or "Latest source fetch is BROKEN."
    elif parsed is None:
        state = "WAIT_STRUCTURED_PARSE"
        reason = "No parser result exists for latest source."
    elif parsed.snapshot_id != snapshot.id:
        state = "WAIT_PARSE_LATEST_SNAPSHOT"
        reason = "The latest raw snapshot has not been parsed; an older parse cannot unlock READY."
    elif parsed.parser_state == "PARSED_STRUCTURED":
        if (
            source_key == "nse_mwpl_percentages"
            and parsed.output.get("evidenceCoverage") != "FULL_MWPL_PERCENTAGES"
        ):
            state = "WAIT_MWPL_PERCENTAGES"
            reason = "Official F&O ban evidence is available, but symbol-level MWPL percentages are not."
        elif parsed.record_count <= 0 and not (
            source_key in VALID_EMPTY_SOURCES
            and parsed.output.get("validEmpty") is True
        ):
            state = "WAIT_EMPTY_PARSE"
            reason = "Structured parser returned zero rows."
        elif not is_data_date_fresh(source_key, parsed.data_date):
            state = "WAIT_STALE_DATA"
            reason = stale_reason(source_key, parsed.data_date)
        else:
            state = "PASS"
            reason = (
                "Structured parser returned a fresh, valid empty official list."
                if parsed.record_count <= 0
                else "Structured parser returned non-empty fresh data."
            )
    elif parsed.parser_state == "PARSED":
        state = "WAIT_STRUCTURED_PARSE"
        reason = "Legacy PARSED state is not accepted; use PARSED_STRUCTURED."
    elif parsed.parser_state == "PARSED_METADATA_ONLY":
        state = "WAIT_STRUCTURED_PARSE"
        reason = "Metadata-only parser output cannot pass READY."
    elif parsed.parser_state in {
        "WAIT_SOURCE_SNAPSHOT",
        "WAIT_FETCH_REQUIRED",
        "NO_PARSER",
    }:
        state = parsed.parser_state
        reason = parsed.summary
    elif parsed.parser_state == "WAIT_EMPTY_PARSE":
        state = "WAIT_EMPTY_PARSE"
        reason = parsed.summary
    elif parsed.parser_state == "WAIT_STALE_DATA":
        state = "WAIT_STALE_DATA"
        reason = parsed.summary
    elif parsed.parser_state == "WAIT_SCHEMA_MISMATCH":
        state = "WAIT_SCHEMA_MISMATCH"
        reason = parsed.summary
    elif parsed.parser_state == "WAIT_SOURCE_DATE":
        state = "WAIT_SOURCE_DATE"
        reason = parsed.summary
    elif parsed.parser_state == "WAIT_PARSE_ERROR":
        state = "WAIT_PARSE_ERROR"
        reason = parsed.error or parsed.summary
    elif parsed.parser_state == "BROKEN":
        state = "REJECT_SOURCE_BROKEN"
        reason = parsed.error or parsed.summary
    else:
        state = "WAIT_STRUCTURED_PARSE"
        reason = "Unknown parser state; fail-closed."
    if state == "PASS" and not source_activation_ready:
        state = "WAIT_SOURCE_ACTIVATION"
        reason = (
            "The source data is structured and fresh, but the inventory compiler "
            "has not authorized global source activation."
        )
    elif state == "PASS" and not gate_permissions.get(source_key, False):
        state = "WAIT_SOURCE_GATE_PERMISSION"
        reason = (
            "The source data is structured and fresh, but its compiled contract "
            "does not authorize gate use."
        )
    return {
        "sourceKey": source_key,
        "state": state,
        "reason": reason,
        "snapshotState": snapshot.check_state if snapshot else "MISSING",
        "snapshotCheckedAt": snapshot.checked_at if snapshot else None,
        "parserState": parsed.parser_state if parsed else "MISSING",
        "dataDate": parsed.data_date if parsed else None,
        "parsedAt": parsed.parsed_at if parsed else None,
        "recordCount": parsed.record_count if parsed else 0,
        "compilerActivationReady": source_activation_ready,
        "contractGatePermission": gate_permissions.get(source_key, False),
    }


def gate_state(code: str, source_states: list[dict]) -> tuple[str, str]:
    by_key = {row["sourceKey"]: row["state"] for row in source_states}
    requirements = PASS_REQUIREMENTS.get(code, ())
    for requirement in requirements:
        if all(by_key.get(key) == "PASS" for key in requirement):
            if any(
                row["state"] == "REJECT_SOURCE_BROKEN"
                for row in source_states
                if row["sourceKey"] in requirement
            ):
                return "BLOCKED_SOURCE_BROKEN", "A required source is broken."
            return (
                "PASS",
                f"Required structured source set passed: {', '.join(requirement)}.",
            )
    if any(row["state"] == "REJECT_SOURCE_BROKEN" for row in source_states):
        return "BLOCKED_SOURCE_BROKEN", "At least one source is broken."
    priority = (
        "WAIT_MWPL_PERCENTAGES",
        "WAIT_SOURCE_SNAPSHOT",
        "WAIT_FETCH_REQUIRED",
        "WAIT_PARSE_ERROR",
        "WAIT_PARSE_LATEST_SNAPSHOT",
        "WAIT_STALE_DATA",
        "WAIT_SOURCE_DATE",
        "WAIT_SCHEMA_MISMATCH",
        "WAIT_EMPTY_PARSE",
        "WAIT_STRUCTURED_PARSE",
        "WAIT_SOURCE_ACTIVATION",
        "WAIT_SOURCE_GATE_PERMISSION",
        "NO_PARSER",
    )
    for state in priority:
        if any(row["state"] == state for row in source_states):
            return (
                state,
                f"Required structured source set not ready; current blocker: {state}.",
            )
    return "WAIT_DATA", "Structured data is not ready."


def gate_readiness(symbol: str | None = None) -> dict:
    rows = []
    compiler_context = compiler_gate_context()
    for dependency in GATE_DEPENDENCIES:
        sources = [
            dependency_state(key, compiler_context=compiler_context)
            for key in dependency.source_keys
        ]
        state, reason = gate_state(dependency.code, sources)
        if not compiler_context[0]:
            state = "WAIT_SOURCE_ACTIVATION"
            reason = (
                "The inventory compiler has not authorized global source activation; "
                "fresh parser output remains research data only."
            )
        if (
            symbol
            and dependency.code == "G13_OI_CONFIRMS"
            and _symbol_has_fno_ban(symbol)
        ):
            state = "BLOCKED_FNO_BAN"
            reason = f"{symbol.upper()} is present in the official NSE F&O ban file. Derivative-dependent entry is blocked."
        if symbol and dependency.code == "G03_STOCK_SAFETY":
            safety = stock_safety_state(symbol, sources)
            if safety["state"] == "BLOCKED_SURVEILLANCE" or state == "PASS":
                state = str(safety["state"])
                reason = str(safety["reason"])
        if symbol and state == "PASS" and dependency.code != "G03_STOCK_SAFETY":
            required_sets = PASS_REQUIREMENTS.get(dependency.code, ())
            matching_set = next(
                (
                    requirement
                    for requirement in required_sets
                    if all(
                        source_has_symbol_evidence(key, symbol)
                        for key in requirement
                        if key not in {"cftc_cot", "nse_fno_ban"}
                    )
                ),
                None,
            )
            if matching_set is None:
                state = "WAIT_SYMBOL_EVIDENCE"
                reason = f"Fresh source files exist, but no matching structured evidence exists for {symbol.upper()}."
        if symbol:
            for source in sources:
                source["symbolEvidence"] = source_has_symbol_evidence(
                    source["sourceKey"], symbol
                )

        rows.append(
            {
                "code": dependency.code,
                "name": dependency.name,
                "state": state,
                "reason": reason,
                "purpose": dependency.purpose,
                "tradeGateEffect": "DO_NOT_PASS_READY"
                if state != "PASS"
                else "CAN_CONFIRM",
                "sources": sources,
            }
        )
    return {
        "symbol": symbol,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "gates": rows,
        "rule": "CONFIRMED requires compiler activation, per-contract gate permission, and structured fresh source parses. Only explicitly valid dated empty official lists may pass; metadata-only, stale, invalid-empty, broken, unofficial-only, or compiler-unapproved evidence cannot pass CONFIRMED.",
    }
