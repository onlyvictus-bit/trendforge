"""Generate the reviewed coverage seed; this is not a repository scanner or plan."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from collections import Counter
from datetime import date
from pathlib import Path

OUT = Path(__file__).with_name("PLAN_REQUIREMENT_COVERAGE.csv")
ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LAST_VERIFIED = "2026-07-20"
VALID_STATUSES = {
    "CONFLICT",
    "IMPLEMENTED",
    "PARTIAL",
    "PLANNED",
    "POSTPONED",
    "REJECTED",
}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_EVIDENCE_LEVELS = {
    "CODE_PRESENT",
    "DOCUMENTED",
    "LIVE_SOURCE_VERIFIED",
    "OBSERVED_RUNTIME",
    "TESTED_OFFLINE",
}
VALID_R_OWNERS = frozenset(f"R{i}" for i in range(19))
EXPECTED_FMR_OWNERS = {
    "FMR-001": frozenset({"R0", "R2", "R16"}),
    "FMR-002": frozenset({"R0", "R2", "R3", "R8", "R9", "R15", "R16"}),
    "FMR-003": frozenset({"R12"}),
    "FMR-004": frozenset({"R12", "R16"}),
    "FMR-005": frozenset({"R12", "R16"}),
    "FMR-006": frozenset({"R12", "R16"}),
    "FMR-007": frozenset({"R3", "R12", "R15"}),
    "FMR-008": frozenset({"R4", "R7", "R12", "R17"}),
    "FMR-009": frozenset({"R15"}),
    "FMR-010": VALID_R_OWNERS,
    "FMR-011": frozenset({"R15", "R16", "R18"}),
}
EXPECTED_FMR_LINKED = {
    **{rid: frozenset() for rid in EXPECTED_FMR_OWNERS},
    "FMR-011": frozenset({"FTR-034", "STO-017", "UI-009"}),
}
VALID_FMR_REFS = frozenset(EXPECTED_FMR_OWNERS)
EXPECTED_DETAIL_TAGS = frozenset(
    {
        *(f"M{i}" for i in range(24)),
        *(f"T{i}" for i in range(5)),
        "PK-A",
        "PK-B",
        "PK-C",
        "PK-D",
    }
)
FILE_A_SELECTOR_TOKENS = ("R0-R18", "CROSS-###", "TDG-GAP-###")
NEXT_DETAIL_ACTION_PATTERN = re.compile(
    r"\b(?:(?P<negation>do not|don't|never|must not|cannot|can not)\s+)?"
    r"(?P<action>"
    r"pick(?: the)? next milestone(?:\s+M\d+)?|"
    r"next milestone\s+M\d+|"
    r"choose(?: the)? next\s+M\d+|"
    r"do next\s+M\d+"
    r")\b",
    flags=re.IGNORECASE,
)
RUNTIME_FRONTEND_FILES = (
    "frontend/app.js",
    "frontend/index.html",
    "frontend/q5-contract.js",
    "frontend/styles.css",
)
GOVERNANCE_CLEANUP_ALLOWLIST = frozenset(
    {
        "docs/fable/new_merge_PLAN_2026-07-18.md",
        "docs/fable/FINAL_MERGE_PLAN.md",
        "docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md",
        "docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md",
        "fileindex.md",
        "TREND_FORGE_ARCHITECTURE.md",
        "docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md",
        "docs/OPTIONS_INTELLIGENCE_PLAN.md",
        "docs/DECISIONS.md",
        "docs/fable/remaining_build/README.md",
        "docs/fable/remaining_build/REMAINING_PROJECT_BUILD_FILES.md",
        "docs/fable/remaining_build/build_coverage_csv.py",
        "docs/fable/remaining_build/test_build_coverage_csv.py",
        "docs/fable/remaining_build/PLAN_REQUIREMENT_COVERAGE.csv",
        "docs/BUILD_STATUS.md",
        "docs/VALIDATION.md",
    }
)
FORBIDDEN_DETAIL_INSTRUCTIONS = {
    "Discovery Detail Plan": (
        r"code in this order",
        r"milestones? M0\s*[–-]\s*M9 first",
        r"recommended build sequence",
        r"immediate next step",
        r"PK-A only",
        r"prefer this over",
        r"update BUILD_STATUS when each M-id closes",
        r"^### Phase T[0-4]",
        r"UNMAPPED_STOP",
        r"single self-contained coding spine",
        r"^## 6\. Implementation phases",
        r"^### Phase PK-[A-D]",
        r"ready to implement T0",
        r"this plan proposes sequence",
        r"unified milestone board",
    ),
    "Options Detail Plan": (
        r"after M0\s*[–-]\s*M9",
        r"then M10\s*[→>-]+\s*M11",
        r"follow .*M0\s*[–-]\s*M9.*product plan",
        r"when coding starts:\s*\*\*M10",
        r"options SSOT",
        r"coding spine",
        r"shortlist first; M10 chain gate",
        r"^## 16\. What to do",
        r"this file as the options bible",
    ),
}
ID_PATTERNS = (
    re.compile(r"Q5-R[0-7]"),
    re.compile(r"R(?:[0-9]|1[0-8])"),
    re.compile(r"CROSS-\d{3}"),
    re.compile(r"TDG-GAP-\d{3}"),
    re.compile(r"HYBRID-\d+-\d+"),
    re.compile(r"FMR-\d{3}"),
    re.compile(r"CONFLICT-\d{3}"),
)
SINGLETON_IDS = {
    "DAT-010",
    "DAT-011",
    "FUS-008",
    "FUS-011",
    "GOV-002",
    "GOV-003",
    "GOV-TRACE-001",
    "PK-019",
    "POST-HYB-01",
    "REJ-011",
    "STA-001",
    "T-028",
    "T-029",
    "T-030",
    "T-194",
    "T-195",
}
HYBRID_IDS = {
    "HYBRID-1-1",
    "HYBRID-2-1",
    "HYBRID-4-1",
    "HYBRID-5-1",
    "HYBRID-5-2",
    "HYBRID-6-1",
    "HYBRID-7-1",
    "HYBRID-7-2",
    "HYBRID-8-1",
    "HYBRID-9-1",
    "HYBRID-9-2",
    "HYBRID-10-1",
    "HYBRID-11-1",
    "HYBRID-15-1",
    *(f"HYBRID-16-{i}" for i in range(1, 11)),
    *(f"HYBRID-17-{i}" for i in range(1, 7)),
    *(f"HYBRID-18-{i}" for i in range(1, 4)),
    *(f"HYBRID-19-{i}" for i in range(1, 12)),
}
EXPECTED_IDS = frozenset(
    {
        *(f"Q5-R{i}" for i in range(8)),
        *(f"R{i}" for i in range(19)),
        *(f"CROSS-{i:03d}" for i in range(1, 25)),
        *(f"TDG-GAP-{i:03d}" for i in range(1, 27)),
        *(f"CONFLICT-{i:03d}" for i in range(1, 8)),
        *HYBRID_IDS,
        *(f"FMR-{i:03d}" for i in range(1, 12)),
        *SINGLETON_IDS,
    }
)
CODE_EVIDENCE_FILES = {
    "DAT-010": ("backend/trendforge_api/feature_registry.py",),
    "DAT-011": (
        "backend/trendforge_api/indicator_engine.py",
        "backend/trendforge_api/selection/contracts.py",
    ),
    "R0": ("backend/trendforge_api/source_contracts.py",),
    "R1": (
        "backend/trendforge_api/selection/inventory_source_bundle.py",
        "backend/trendforge_api/selection/store.py",
        "backend/trendforge_api/selection/cash_post_commit.py",
    ),
    "R2": (
        "backend/trendforge_api/selection/attention_order.py",
        "backend/trendforge_api/selection/cash_post_commit.py",
    ),
    "R9": ("backend/trendforge_api/selection/history_validation.py",),
    "R14": ("backend/trendforge_api/corporate_actions.py",),
    "R16": (
        "backend/trendforge_api/selection/s8_service.py",
        "backend/trendforge_api/selection/r16_pit.py",
        "backend/trendforge_api/selection/r16_metrics.py",
        "backend/trendforge_api/selection/r16_store.py",
        "backend/trendforge_api/selection/r16_service.py",
        "backend/tests/test_r16_pit.py",
        "frontend/r16-pit-validation.js",
    ),
    "CROSS-001": (
        "backend/trendforge_api/source_inventory_compiler.py",
        "backend/trendforge_api/source_overlap_resolutions.py",
        "backend/trendforge_api/source_registry_contracts.py",
    ),
    "CROSS-002": (
        "backend/trendforge_api/source_inventory_compiler.py",
        "backend/trendforge_api/source_key_map_review.py",
        "backend/trendforge_api/source_registry_contracts.py",
    ),
    "CROSS-003": ("backend/trendforge_api/source_inventory_compiler.py",),
    "CROSS-004": (
        "backend/trendforge_api/selection/profile_source_contracts.py",
        "backend/tests/test_profile_source_contracts.py",
    ),
    "CROSS-006": (
        "backend/trendforge_api/source_inventory_compiler.py",
        "backend/trendforge_api/source_registry_contracts.py",
        "backend/trendforge_api/source_monitor.py",
    ),
    "CROSS-007": (
        "backend/trendforge_api/source_inventory_compiler.py",
        "backend/trendforge_api/source_registry_contracts.py",
    ),
    "CROSS-008": (
        "backend/trendforge_api/parsers/nse_mwpl_parser.py",
        "backend/trendforge_api/gate_readiness.py",
        "backend/trendforge_api/source_inventory_compiler.py",
    ),
    "CROSS-009": ("backend/trendforge_api/commodity_context.py",),
    "CROSS-012": ("backend/trendforge_api/source_monitor.py",),
    "CROSS-014": ("backend/trendforge_api/intraday_stock_details.py",),
    "CROSS-015": (
        "backend/trendforge_api/selection/tradability.py",
        "backend/trendforge_api/selection/s7_state_gates.py",
        "backend/trendforge_api/selection/s8_persist_run.py",
        "backend/tests/test_tradability_gate.py",
        "frontend/s7-state.js",
    ),
    "CROSS-016": ("backend/trendforge_api/parsers/corporate_events_parser.py",),
    "CROSS-018": ("frontend/q5-contract.js",),
    "CROSS-019": ("backend/trendforge_api/selection/contracts.py",),
    "CROSS-020": ("backend/trendforge_api/parquet_store.py",),
    "CROSS-021": ("backend/trendforge_api/selection/resolver.py",),
    "CROSS-022": ("backend/trendforge_api/openalgo_client.py",),
    "CROSS-023": ("backend/trendforge_api/selection/history_validation.py",),
    "CROSS-024": ("backend/tests/test_q5_selection_contracts.py",),
    "TDG-GAP-001": ("backend/trendforge_api/source_inventory_compiler.py",),
    "TDG-GAP-011": ("backend/trendforge_api/source_inventory_compiler.py",),
    "TDG-GAP-012": ("backend/trendforge_api/source_inventory_compiler.py",),
    "TDG-GAP-013": ("backend/trendforge_api/source_inventory_compiler.py",),
    "TDG-GAP-014": (
        "backend/trendforge_api/selection/profile_source_contracts.py",
        "backend/tests/test_profile_source_contracts.py",
    ),
    "HYBRID-6-1": (
        "backend/trendforge_api/selection/profile_source_contracts.py",
        "backend/tests/test_profile_source_contracts.py",
    ),
    "HYBRID-16-6": (
        "backend/trendforge_api/selection/profile_source_contracts.py",
        "backend/tests/test_profile_source_contracts.py",
    ),
    "TDG-GAP-024": ("backend/trendforge_api/source_inventory_compiler.py",),
    "TDG-GAP-025": ("backend/trendforge_api/source_inventory_compiler.py",),
    "GOV-002": ("backend/tests/test_q5_openalgo_boundary.py",),
    "GOV-003": ("frontend/tests/q5-contract.test.js",),
    "STA-001": ("backend/tests/test_q5_selection_contracts.py",),
    "FUS-008": ("backend/tests/test_q5_selection_contracts.py",),
    "FUS-011": ("backend/tests/test_q5_family_resolver.py",),
    "PK-019": ("backend/tests/test_q5_pk_compatibility.py",),
    "T-028": ("backend/tests/test_feature_registry.py",),
    "T-029": ("backend/tests/test_feature_registry.py",),
    "T-030": ("backend/tests/test_feature_registry.py",),
    "T-194": ("backend/tests/test_feature_registry.py",),
    "T-195": ("backend/tests/test_feature_registry.py",),
    "GOV-TRACE-001": ("docs/fable/remaining_build/build_coverage_csv.py",),
}
RUNTIME_EVIDENCE = {
    "DAT-010": (
        "GET /api/v1/selection/feature-registry",
        "test_feature_registry.py",
    ),
    "DAT-011": (
        "GET /api/v1/selection/feature-registry/lint",
        "test_feature_registry.py",
    ),
    "CROSS-001": (
        "GET /api/source-inventory/compiler-report",
        "test_source_inventory_compiler.py",
    ),
    "HYBRID-16-3": (
        "GET /api/source-inventory/compiler-report",
        "test_source_inventory_compiler.py",
    ),
    "CROSS-003": (
        "GET /api/source-inventory/compiler-report",
        "test_source_inventory_compiler.py",
    ),
    "TDG-GAP-011": (
        "GET /api/source-inventory/compiler-report",
        "test_source_inventory_compiler.py",
    ),
    "TDG-GAP-012": (
        "GET /api/source-inventory/compiler-report",
        "test_source_inventory_compiler.py",
    ),
    "TDG-GAP-025": (
        "GET /api/source-inventory/compiler-report",
        "test_source_inventory_compiler.py",
    ),
    "Q5-R1": ("GET /api/v1/selection/fixtures/q5-r1", "test_q5_selection_contracts.py"),
    "Q5-R2": ("GET /api/v1/selection/fixtures/q5-r2", "test_q5_family_resolver.py"),
    "Q5-R3": (
        "GET /api/v1/selection/fixtures/q5-r3",
        "test_q5_closed_bar_structure.py",
    ),
    "Q5-R4": ("GET /api/v1/selection/fixtures/q5-r4", "test_q5_bounded_enrichment.py"),
    "Q5-R6": ("GET /api/v1/selection/fixtures/q5-r6", "test_q5_history_validation.py"),
    "Q5-R7": (
        "GET /api/v1/integrations/openalgo/capability",
        "test_q5_openalgo_boundary.py",
    ),
    "R1": ("GET /api/v1/selection/evidence", "test_inventory_source_bundle.py"),
    "R2": ("GET /api/v1/selection/attention", "test_attention_order.py"),
    "R3": (
        "GET /api/v1/selection/resolution",
        "test_cash_post_commit_pipeline.py",
    ),
    "R5": ("GET /api/v1/selection/fixtures/q5-r3", "test_q5_closed_bar_structure.py"),
    "R13": ("GET /api/v1/scanners/native-core", "test_r13_remaining_scanners.py"),
    "R16": (
        "GET /api/v1/selection/pit/status",
        "test_r16_pit.py",
    ),
    "R17": (
        "GET /api/v1/integrations/openalgo/capability",
        "test_q5_openalgo_boundary.py",
    ),
}
COLS = [
    "requirement_id",
    "source_file",
    "source_section",
    "requirement",
    "status",
    "merge_milestone",
    "hybrid_reference",
    "backend_module",
    "api_route",
    "frontend_location",
    "test_ids",
    "decision",
    "reason",
    "evidence_level",
    "product_scope",
    "priority",
    "last_verified",
]


def row(**kw: str) -> dict[str, str]:
    unknown = sorted(set(kw) - set(COLS))
    if unknown:
        raise ValueError(f"Unknown coverage columns: {unknown}")
    result = {column: "" for column in COLS}
    result.update(kw)
    result["last_verified"] = result["last_verified"] or DEFAULT_LAST_VERIFIED
    return result


def attach_reviewed_code_evidence(rows: list[dict[str, str]]) -> None:
    """Attach reviewed, repository-relative proof paths without erasing descriptions."""
    for item in rows:
        for relative in CODE_EVIDENCE_FILES.get(item["requirement_id"], ()):
            if relative.startswith("frontend/"):
                field = "frontend_location"
            elif relative.startswith("backend/tests/"):
                field = "test_ids"
            else:
                field = "backend_module"
            current = item[field].strip()
            if relative not in current:
                item[field] = "; ".join(part for part in (current, relative) if part)


def _read_text(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        raise ValueError(f"Missing required governance file: {relative}")
    return path.read_text(encoding="utf-8")


def _clean_md_cell(value: str) -> str:
    return value.replace("**", "").replace("`", "").strip()


def _expand_r_owners(value: str) -> frozenset[str]:
    cleaned = _clean_md_cell(value).replace("–", "-")
    if re.fullmatch(r"(?i)(?:applicable\s+)?R0\s*-\s*R18", cleaned):
        return VALID_R_OWNERS
    return frozenset(re.findall(r"\bR(?:1[0-8]|[0-9])\b", cleaned))


def _expand_linked_requirements(value: str) -> frozenset[str]:
    cleaned = _clean_md_cell(value)
    if cleaned.lower() in {"", "none", "n/a"}:
        return frozenset()
    return frozenset(re.findall(r"\b(?:FTR|STO|UI)-\d{3}\b", cleaned))


def _expand_fmr_refs(value: str) -> frozenset[str]:
    """Expand explicit FMR IDs and inclusive forms such as FMR-003..008."""
    cleaned = _clean_md_cell(value).replace("–", "-")
    refs: set[str] = set()
    matches = list(
        re.finditer(r"\bFMR-(\d{3})(?:\s*\.\.\s*(?:FMR-)?(\d{3}))?\b", cleaned)
    )
    if not matches:
        return frozenset()
    for match in matches:
        start = int(match.group(1))
        end = int(match.group(2) or match.group(1))
        if end < start:
            raise ValueError(f"Descending FMR range is invalid: {match.group(0)}")
        refs.update(f"FMR-{number:03d}" for number in range(start, end + 1))
    invalid = refs - VALID_FMR_REFS
    if invalid:
        raise ValueError(f"Invalid FMR references: {sorted(invalid)}")
    return frozenset(refs)

def parse_fmr_table(
    text: str,
    *,
    owner_column: int,
    linked_column: int,
    label: str,
) -> tuple[dict[str, frozenset[str]], dict[str, frozenset[str]]]:
    """Parse the first complete FMR-001..011 Markdown table in a document."""
    lines = text.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^\|\s*`?FMR-001`?\s*\|", line.strip())
    ]
    for start in starts:
        owners: dict[str, frozenset[str]] = {}
        linked: dict[str, frozenset[str]] = {}
        for line in lines[start:]:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not cells:
                break
            rid_match = re.fullmatch(r"`?(FMR-\d{3})`?", cells[0])
            if not rid_match:
                break
            if len(cells) <= max(owner_column, linked_column):
                raise ValueError(f"{label} has a malformed {rid_match.group(1)} row")
            rid = rid_match.group(1)
            if rid in owners:
                raise ValueError(f"{label} has duplicate FMR row {rid}")
            owners[rid] = _expand_r_owners(cells[owner_column])
            linked[rid] = _expand_linked_requirements(cells[linked_column])
        if set(owners) == set(EXPECTED_FMR_OWNERS):
            return owners, linked
    raise ValueError(f"{label} lacks one complete FMR-001..011 ownership table")


def parse_discovery_owner_table(
    text: str,
) -> dict[str, tuple[frozenset[str], frozenset[str]]]:
    """Validate exactly one machine row for every M/T/PK detail tag."""
    parsed_rows: dict[str, tuple[frozenset[str], frozenset[str]]] = {}
    row_pattern = re.compile(
        r"^\|\s*\*\*(M\d+|T\d+|PK-[A-D])\*\*\s*\|"
        r"\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|$"
    )
    lines = text.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if (match := row_pattern.match(line.strip())) and match.group(1) == "M0"
    ]
    if not starts:
        raise ValueError("Discovery Detail Plan lacks the four-column detail-owner table")

    for line in lines[starts[0] :]:
        match = row_pattern.match(line.strip())
        if not match:
            break
        tag, owner_cell, fmr_cell, notes = match.groups()
        if tag in parsed_rows:
            raise ValueError(f"Discovery Detail Plan has duplicate owner row for {tag}")

        raw_owners = frozenset(re.findall(r"\bR\d+\b", _clean_md_cell(owner_cell)))
        invalid_owners = raw_owners - VALID_R_OWNERS
        if invalid_owners:
            raise ValueError(
                f"Discovery Detail Plan detail tag {tag} has invalid owners: "
                f"{sorted(invalid_owners)}"
            )
        owners = _expand_r_owners(owner_cell)
        if not owners:
            raise ValueError(f"Discovery Detail Plan detail tag {tag} has no R owner")

        refs = _expand_fmr_refs(fmr_cell)
        if not refs:
            raise ValueError(f"Discovery Detail Plan detail tag {tag} has no FMR_refs")
        covered_owners = frozenset().union(
            *(EXPECTED_FMR_OWNERS[ref] for ref in refs)
        )
        uncovered = owners - covered_owners
        if uncovered:
            raise ValueError(
                f"Discovery Detail Plan detail tag {tag} owners are not covered by "
                f"FMR_refs: {sorted(uncovered)}"
            )
        if not notes.strip() or "depends_on:" not in notes:
            raise ValueError(
                f"Discovery Detail Plan detail tag {tag} lacks a depends_on note"
            )
        parsed_rows[tag] = (owners, refs)

    missing = sorted(EXPECTED_DETAIL_TAGS - set(parsed_rows))
    unexpected = sorted(set(parsed_rows) - EXPECTED_DETAIL_TAGS)
    if missing or unexpected or len(parsed_rows) != 33:
        raise ValueError(
            "Discovery detail-owner table drift: "
            f"rows={len(parsed_rows)}, missing={missing}, unexpected={unexpected}"
        )
    return parsed_rows

def validate_no_competing_detail_order(discovery: str, options: str) -> None:
    extra_patterns = {
        "Discovery Detail Plan": (
            r"start(?: with)? phase T0",
            r"^\|\s*Sprint\s*\|",
            r"M\d+\s*→\s*M\d+",
            r"prefer this file",
        ),
        "Options Detail Plan": (r"prefer this file",),
    }
    for label, text in (
        ("Discovery Detail Plan", discovery),
        ("Options Detail Plan", options),
    ):
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in NEXT_DETAIL_ACTION_PATTERN.finditer(line):
                if match.group("negation"):
                    continue
                raise ValueError(
                    f"{label} contains competing build instruction at line "
                    f"{line_number}: {match.group('action')!r}"
                )
        patterns = (*FORBIDDEN_DETAIL_INSTRUCTIONS[label], *extra_patterns[label])
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                raise ValueError(
                    f"{label} contains competing build instruction at line {line}: "
                    f"{match.group(0)!r}"
                )


def validate_file_a_selection_language(
    readme: str,
    discovery: str,
    options: str,
) -> None:
    """Require one File A selector vocabulary while keeping M/T/PK subordinate."""
    for label, text in (
        ("remaining_build README", readme),
        ("Discovery Detail Plan", discovery),
        ("Options Detail Plan", options),
    ):
        matching_lines: list[str] = []
        for line in text.splitlines():
            normalized = (
                _clean_md_cell(line)
                .replace("–", "-")
                .replace(chr(96), "")
                .upper()
            )
            if all(token in normalized for token in FILE_A_SELECTOR_TOKENS):
                matching_lines.append(normalized)
        if not matching_lines:
            raise ValueError(
                f"{label} lacks the unified File A requirement selector "
                f"{FILE_A_SELECTOR_TOKENS}"
            )
        if not any("M/T/PK" in line for line in matching_lines):
            raise ValueError(
                f"{label} does not make M/T/PK subordinate on its unified "
                "File A selector line"
            )


def validate_conditional_activation_claims(discovery: str, options: str) -> None:
    """Reject permanent activation ceilings while allowing observed-state conditions."""
    for label, text in (
        ("Discovery Detail Plan", discovery),
        ("Options Detail Plan", options),
    ):
        for line_number, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            if "sourceactivationready=false" not in lowered:
                continue
            if any(
                marker in lowered
                for marker in (
                    "current observed runtime",
                    "current observed code",
                    "observed runtime",
                    "runtime reports",
                )
            ):
                continue
            raise ValueError(
                f"{label} contains a permanent activation claim at line "
                f"{line_number}: {line.strip()!r}"
            )


def decision_inventory(decisions: str) -> dict[str, object]:
    ids = re.findall(r"(?m)^##\s+(D-\d{3})\b", decisions)
    duplicates = sorted(rid for rid, count in Counter(ids).items() if count > 1)
    numbers = [int(rid.split("-", 1)[1]) for rid in ids]
    maximum = max(numbers, default=0)
    return {
        "count": len(ids),
        "ids": tuple(ids),
        "duplicates": tuple(duplicates),
        "max_id": f"D-{maximum:03d}" if maximum else None,
        "next_free": f"D-{maximum + 1:03d}",
    }


def validate_decision_ids(decisions: str) -> None:
    inventory = decision_inventory(decisions)
    if inventory["duplicates"]:
        raise ValueError(
            f"DECISIONS.md has duplicate decision IDs: {list(inventory['duplicates'])}"
        )
    if not re.search(r"(?m)^##\s+D-025\s+Canonical Inventory Compiler\b", decisions):
        raise ValueError("D-025 must remain Canonical Inventory Compiler")
    if not re.search(r"(?m)^##\s+D-029\s+Single Build Spine\b", decisions):
        raise ValueError("D-029 must own Single Build Spine governance")
    if not re.search(
        r"(?m)^##\s+D-030\s+Professional Mathematics Is A Mapped Research Detail\b",
        decisions,
    ):
        raise ValueError("D-030 must own professional mathematics governance")

def parse_documented_cleanup_allowlist(readme: str) -> frozenset[str]:
    marker = "### 10.2 Governance-cleanup changed-file boundary"
    if marker not in readme:
        raise ValueError("remaining_build README lacks changed-file boundary")
    section = readme.split(marker, 1)[1]
    match = re.search(r"```text\s*(.*?)\s*```", section, flags=re.DOTALL)
    if not match:
        raise ValueError("remaining_build README lacks changed-file allowlist block")
    return frozenset(
        line.strip().replace("\\", "/")
        for line in match.group(1).splitlines()
        if line.strip()
    )

def validate_changed_files(changed_files: list[str]) -> None:
    """Fail closed when an explicitly supplied changed path leaves the cleanup scope."""
    for supplied in changed_files:
        candidate = Path(supplied)
        resolved = candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
        try:
            relative = resolved.relative_to(ROOT.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError(f"Changed file is outside TrendForge: {supplied}") from exc
        if relative not in GOVERNANCE_CLEANUP_ALLOWLIST:
            raise ValueError(
                f"Changed file is outside governance-cleanup allowlist: {relative}"
            )


def runtime_manifest_files() -> tuple[Path, ...]:
    """Return the exact runtime source surface protected by governance cleanup."""
    backend_root = ROOT / "backend" / "trendforge_api"
    backend = [
        path
        for path in backend_root.rglob("*.py")
        if "__pycache__" not in path.parts and path.suffix != ".pyc"
    ]
    frontend = [ROOT / relative for relative in RUNTIME_FRONTEND_FILES]
    missing = [path for path in frontend if not path.is_file()]
    if missing:
        raise ValueError(f"Missing protected runtime files: {missing}")
    return tuple(
        sorted(
            (*backend, *frontend),
            key=lambda path: path.relative_to(ROOT).as_posix(),
        )
    )


def runtime_manifest_hash() -> str:
    digest = hashlib.sha256()
    for path in runtime_manifest_files():
        relative = path.relative_to(ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest().upper()


def validate_runtime_manifest(
    expected_hash: str | None,
    changed_files: list[str],
) -> str:
    """Require a baseline manifest whenever changed-file containment is asserted."""
    if changed_files and not expected_hash:
        raise ValueError("--changed-file requires --expected-runtime-manifest-hash")
    actual = runtime_manifest_hash()
    if expected_hash and actual != expected_hash.strip().upper():
        raise ValueError(
            f"Runtime manifest mismatch: expected={expected_hash.strip().upper()}, "
            f"actual={actual}"
        )
    return actual

def validate_mathematics_reconciliation(
    file_a: str,
    hybrid: str,
    final_merge: str,
    discovery: str,
    options: str,
    architecture: str,
    mathematics: str,
    decisions: str,
    fileindex: str,
) -> None:
    """Keep research mathematics mapped, explicit, and non-authoritative."""
    required_math = {
        "research authority": "This file is a research mathematics detail reference",
        "general EV": "p * E[G | target_first]",
        "conservative EV": "EV_conservative",
        "finite-horizon barrier": "P(tau_b < tau_a and tau_b <= H)",
        "factor alpha": "- alpha",
        "observable OI": "OI_RISE_PRICE_RISE",
        "production resolver": "Current ranking uses File A `FUS-009`",
        "cash Gamma": "cash_gamma_1pct_inr",
        "corporate action": "rights_factor = TERP / pre_ex_close",
        "full dividend-aware Theta": "Theta_call =",
        "delta-hedged variance attribution": "dPi_long_delta_hedged approximately =",
        "VRP context": "### 17.6 Volatility risk premium as scanner context",
    }
    for label, token in required_math.items():
        if token not in mathematics:
            raise ValueError(f"Professional mathematics lacks {label}: {token}")

    required_cross_references = {
        "File A": (file_a, "### 25.22 Professional trade-decision mathematics detail reference"),
        "Hybrid": (hybrid, "## 21. Professional Mathematics Cross-Reference"),
        "Final Merge": (final_merge, "## Mathematics detail boundary (mandatory)"),
        "Discovery": (discovery, "## Professional mathematics navigation (detail only)"),
        "Options": (
            options,
            "### Theta, delta-hedged variance and VRP wording (mandatory)",
        ),
        "Architecture": (
            architecture,
            "## Professional Trade-Decision Mathematics Boundary",
        ),
        "Decisions": (
            decisions,
            "## D-030 Professional Mathematics Is A Mapped Research Detail",
        ),        "File index": (
            fileindex,
            "### `docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md`",
        ),
    }
    for label, (text, token) in required_cross_references.items():
        if token not in text:
            raise ValueError(f"{label} lacks professional mathematics mapping: {token}")
    required_vrp_cross_references = {
        "File A": (file_a, "| Variance-risk-premium research context |"),
        "Hybrid": (hybrid, "| Variance-risk-premium context |"),
        "Final Merge": (final_merge, "VRP_UNKNOWN"),
        "Discovery": (discovery, "VRP_UNKNOWN"),
        "Options": (options, "VRP_UNKNOWN"),
        "Architecture": (
            architecture,
            "The variance-risk-premium contract is research-only",
        ),
        "Decisions": (
            decisions,
            "Variance-risk-premium context is accepted only as postponed research context",
        ),
        "File index": (fileindex, "Want professional trading math?"),
    }
    for label, (text, token) in required_vrp_cross_references.items():
        if token not in text:
            raise ValueError(f"{label} lacks VRP/Theta reconciliation: {token}")

    unsafe_vrp_commands = (
        re.compile(r"positive\s+VRP\s+means\s+(?:sell|short)", re.IGNORECASE),
        re.compile(r"negative\s+VRP\s+means\s+(?:buy|long)", re.IGNORECASE),
        re.compile(r"if\s+IV\s*>\s*RV\s*,?\s*(?:sell|short)", re.IGNORECASE),
        re.compile(r"if\s+IV\s*<\s*RV\s*,?\s*(?:buy|long)", re.IGNORECASE),
    )
    for label, text in (
        ("File A", file_a),
        ("Hybrid", hybrid),
        ("Final Merge", final_merge),
        ("Discovery", discovery),
        ("Options", options),
        ("Architecture", architecture),
        ("Mathematics", mathematics),
        ("Decisions", decisions),
    ):
        for pattern in unsafe_vrp_commands:
            if pattern.search(text):
                raise ValueError(
                    f"{label} contains unsafe automatic VRP trade command: "
                    f"{pattern.pattern}"
                )

    oi_codes = (
        "OI_RISE_PRICE_RISE",
        "OI_RISE_PRICE_FALL",
        "OI_FALL_PRICE_RISE",
        "OI_FALL_PRICE_FALL",
    )
    for label, text in (
        ("File A", file_a),
        ("Discovery", discovery),
        ("Architecture", architecture),
        ("Mathematics", mathematics),
    ):
        missing = [code for code in oi_codes if code not in text]
        if missing:
            raise ValueError(f"{label} lacks observable OI codes: {missing}")

    if "State: LONG_BUILD_UP" in architecture:
        raise ValueError("Architecture still presents inferred LONG_BUILD_UP as state fact")
    if "Action state: WATCH, WAIT, or REJECT as governed" in mathematics:
        raise ValueError("Mathematics incorrectly removes evidence-based CONFIRMED")
    if not re.search(
        r"Covariance-based research cannot\s+replace\s+FUS-009",
        mathematics,
    ):
        raise ValueError("Mathematics must keep covariance research below FUS-009")

def validate_governance_docs(rows: list[dict[str, str]]) -> None:
    """Structurally validate the single build spine and cross-file ownership."""
    fmr_csv = {
        item["requirement_id"]: _expand_r_owners(item["merge_milestone"])
        for item in rows
        if item["requirement_id"].startswith("FMR-")
    }
    if fmr_csv != EXPECTED_FMR_OWNERS:
        raise ValueError(
            f"CSV FMR owner map mismatch: got={fmr_csv}, expected={EXPECTED_FMR_OWNERS}"
        )

    file_a = _read_text("docs/fable/new_merge_PLAN_2026-07-18.md")
    hybrid = _read_text(
        "docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md"
    )
    final_merge = _read_text("docs/fable/FINAL_MERGE_PLAN.md")
    readme = _read_text("docs/fable/remaining_build/README.md")
    discovery = _read_text("docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md")
    options = _read_text("docs/OPTIONS_INTELLIGENCE_PLAN.md")
    architecture = _read_text("TREND_FORGE_ARCHITECTURE.md")
    mathematics = _read_text("docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md")
    fileindex = _read_text("fileindex.md")
    product_html = _read_text("docs/TRENDFORGE_FINAL_PRODUCT.html")
    decisions = _read_text("docs/DECISIONS.md")

    maps = {
        "File A": parse_fmr_table(
            file_a, owner_column=1, linked_column=2, label="File A"
        ),
        "FINAL_MERGE_PLAN": parse_fmr_table(
            final_merge, owner_column=1, linked_column=2, label="FINAL_MERGE_PLAN"
        ),
        "remaining_build README": parse_fmr_table(
            readme, owner_column=2, linked_column=3, label="remaining_build README"
        ),
    }
    for label, (owners, linked) in maps.items():
        if owners != EXPECTED_FMR_OWNERS:
            raise ValueError(f"{label} FMR owner map differs from File A contract")
        if linked != EXPECTED_FMR_LINKED:
            raise ValueError(f"{label} FMR linked-requirement map differs from File A contract")
        if owners != fmr_csv:
            raise ValueError(f"{label} FMR owner map differs from coverage CSV")

    parse_discovery_owner_table(discovery)
    documented_allowlist = parse_documented_cleanup_allowlist(readme)
    if documented_allowlist != GOVERNANCE_CLEANUP_ALLOWLIST:
        raise ValueError(
            "README changed-file allowlist differs from executable allowlist: "
            f"documented={sorted(documented_allowlist)}, "
            f"executable={sorted(GOVERNANCE_CLEANUP_ALLOWLIST)}"
        )
    validate_no_competing_detail_order(discovery, options)
    validate_file_a_selection_language(readme, discovery, options)
    validate_conditional_activation_claims(discovery, options)
    validate_decision_ids(decisions)
    validate_mathematics_reconciliation(
        file_a,
        hybrid,
        final_merge,
        discovery,
        options,
        architecture,
        mathematics,
        decisions,
        fileindex,
    )

    if "___KEEP" in fileindex:
        raise ValueError("fileindex.md still contains ___KEEP placeholders")
    if "FINAL_MERGE_PLAN" not in product_html:
        raise ValueError("Product HTML must mention FINAL_MERGE_PLAN.md")
    if "new_merge_PLAN" not in product_html and "File A" not in product_html:
        raise ValueError("Product HTML must mention File A / new_merge_PLAN")
    if "SCENARIO_ONLY_NOT_OBSERVED_POSITION" not in options and "SCENARIO_ONLY_NOT_OBSERVED_POSITION" not in final_merge:
        raise ValueError("Signed GEX scenario label missing from Options/Final Merge")
    if len(re.findall(r"(?m)^## 10\. ", readme)) > 1:
        raise ValueError("remaining_build README has duplicate pure '## 10.' headings")
    if re.search(r"File B,\s*`DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN", final_merge):
        raise ValueError("FINAL_MERGE_PLAN still names Discovery as File B")

def validate_rows(rows: list[dict[str, str]]) -> None:
    """Fail before overwrite when coverage or claim metadata is incomplete."""
    ids = [item["requirement_id"] for item in rows]
    duplicates = sorted(
        {requirement_id for requirement_id in ids if ids.count(requirement_id) > 1}
    )
    if duplicates:
        raise ValueError(f"Duplicate requirement IDs: {duplicates}")

    missing = sorted(EXPECTED_IDS - set(ids))
    unexpected = sorted(set(ids) - EXPECTED_IDS)
    if missing:
        raise ValueError(f"Missing required coverage IDs: {missing}")
    if unexpected:
        raise ValueError(
            f"Unreviewed coverage IDs are absent from the manifest: {unexpected}"
        )

    required = {
        "requirement_id",
        "source_file",
        "source_section",
        "requirement",
        "status",
        "decision",
        "reason",
        "evidence_level",
        "product_scope",
        "priority",
        "last_verified",
    }
    for csv_line, item in enumerate(rows, start=2):
        requirement_id = item["requirement_id"]
        if requirement_id != requirement_id.strip().upper():
            raise ValueError(f"CSV row {csv_line} has a non-normalized requirement ID")
        if requirement_id not in SINGLETON_IDS and not any(
            pattern.fullmatch(requirement_id) for pattern in ID_PATTERNS
        ):
            raise ValueError(f"CSV row {csv_line} has an unsupported requirement ID")
        try:
            verified = date.fromisoformat(item["last_verified"])
        except ValueError as exc:
            raise ValueError(
                f"CSV row {csv_line} has an invalid last_verified date"
            ) from exc
        if verified.isoformat() != item["last_verified"]:
            raise ValueError(f"CSV row {csv_line} last_verified is not canonical ISO")
        if verified > date.today():
            raise ValueError(
                f"CSV row {csv_line} last_verified cannot be in the future"
            )
        blank = sorted(key for key in required if not item[key].strip())
        if blank:
            raise ValueError(f"CSV row {csv_line} has blank required fields: {blank}")
        if item["status"] not in VALID_STATUSES:
            raise ValueError(f"CSV row {csv_line} has invalid status: {item['status']}")
        if item["priority"] not in VALID_PRIORITIES:
            raise ValueError(
                f"CSV row {csv_line} has invalid priority: {item['priority']}"
            )
        if item["evidence_level"] not in VALID_EVIDENCE_LEVELS:
            raise ValueError(
                f"CSV row {csv_line} has invalid evidence level: {item['evidence_level']}"
            )
        if item["evidence_level"] in {"TESTED_OFFLINE", "OBSERVED_RUNTIME"}:
            test_name = Path(item["test_ids"].strip().replace("\\", "/")).name
            if not test_name:
                raise ValueError(f"CSV row {csv_line} claims tests without test IDs")
            if not test_name.endswith(".py"):
                test_name += ".py"
            if not (ROOT / "backend" / "tests" / test_name).is_file():
                raise ValueError(
                    f"CSV row {csv_line} references a missing test file: {test_name}"
                )
        if item["evidence_level"] == "OBSERVED_RUNTIME":
            expected_runtime = RUNTIME_EVIDENCE.get(requirement_id)
            if expected_runtime is None:
                raise ValueError(f"CSV row {csv_line} lacks reviewed runtime evidence")
            expected_route, expected_test = expected_runtime
            actual_test = Path(item["test_ids"].strip().replace("\\", "/")).name
            if item["api_route"] != expected_route or actual_test != expected_test:
                raise ValueError(
                    f"CSV row {csv_line} runtime evidence differs from its manifest"
                )
            route_path = expected_route.removeprefix("GET ")
            main_source = (ROOT / "backend" / "trendforge_api" / "main.py").read_text(
                encoding="utf-8"
            )
            if f'"{route_path}"' not in main_source:
                raise ValueError(
                    f"CSV row {csv_line} runtime route is absent from main.py"
                )
        if item["evidence_level"] == "CODE_PRESENT":
            reviewed_paths = CODE_EVIDENCE_FILES.get(requirement_id)
            if not reviewed_paths:
                raise ValueError(f"CSV row {csv_line} lacks reviewed code evidence")
            references = " | ".join(
                item[key] for key in ("backend_module", "frontend_location", "test_ids")
            )
            for relative in reviewed_paths:
                if relative not in references:
                    raise ValueError(
                        f"CSV row {csv_line} omits reviewed code path: {relative}"
                    )
                if not (ROOT / relative).is_file():
                    raise ValueError(
                        f"CSV row {csv_line} references missing code: {relative}"
                    )


def read_existing() -> tuple[list[dict[str, str]], list[str]]:
    if not OUT.exists():
        return [], list(COLS)
    with OUT.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return rows, list(reader.fieldnames or [])


def validate_existing(
    rows: list[dict[str, str]], fieldnames: list[str], generated_ids: set[str]
) -> None:
    if fieldnames != COLS:
        unknown = sorted(set(fieldnames) - set(COLS))
        missing = sorted(set(COLS) - set(fieldnames))
        raise ValueError(
            f"Existing CSV columns differ from the generator; unknown={unknown}, missing={missing}"
        )
    ids = [item.get("requirement_id", "") for item in rows]
    duplicates = sorted(
        {requirement_id for requirement_id in ids if ids.count(requirement_id) > 1}
    )
    if duplicates:
        raise ValueError(f"Existing CSV has duplicate requirement IDs: {duplicates}")
    unknown_ids = sorted(set(ids) - generated_ids)
    if unknown_ids:
        raise ValueError(f"Existing CSV has unknown/manual IDs: {unknown_ids}")


def compare_rows(
    existing: list[dict[str, str]], generated: list[dict[str, str]]
) -> tuple[list[str], list[str], list[str]]:
    old = {item["requirement_id"]: item for item in existing}
    new = {item["requirement_id"]: item for item in generated}
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(
        requirement_id
        for requirement_id in set(old) & set(new)
        if old[requirement_id] != new[requirement_id]
    )
    return added, removed, changed


def require_review_acceptance(
    added: list[str], changed: list[str], accepted: bool
) -> None:
    """Require an explicit flag for every new or modified reviewed row."""
    if (added or changed) and not accepted:
        reviewed = sorted({*added, *changed})
        raise ValueError(
            "Refusing to write added or changed rows without "
            "--accept-reviewed-changes: " + ", ".join(reviewed)
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate and diff without writing the coverage CSV",
    )
    parser.add_argument(
        "--accept-reviewed-changes",
        action="store_true",
        help="allow reviewed changes to existing known rows during regeneration",
    )
    parser.add_argument(
        "--changed-file",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "repeat for each file changed by the single-spine governance cleanup; "
            "paths outside the exact allowlist fail closed"
        ),
    )
    parser.add_argument(
        "--expected-runtime-manifest-hash",
        metavar="SHA256",
        help="required baseline hash whenever --changed-file is supplied",
    )
    parser.add_argument(
        "--print-runtime-manifest-hash",
        action="store_true",
        help="print the protected runtime-source manifest hash",
    )
    parser.add_argument(
        "--decision-inventory",
        action="store_true",
        help="print the current D-ID inventory without minting a new decision",
    )
    args = parser.parse_args(argv)
    validate_changed_files(args.changed_file)
    manifest_hash = validate_runtime_manifest(
        args.expected_runtime_manifest_hash,
        args.changed_file,
    )
    if args.print_runtime_manifest_hash:
        print(manifest_hash)
    if args.decision_inventory:
        inventory = decision_inventory(_read_text("docs/DECISIONS.md"))
        print(
            f"count={inventory['count']} max={inventory['max_id']} "
            f"next_free={inventory['next_free']} "
            f"duplicates={list(inventory['duplicates'])}"
        )
    if (args.print_runtime_manifest_hash or args.decision_inventory) and not (
        args.check or args.accept_reviewed_changes
    ):
        return 0
    rows: list[dict[str, str]] = []

    # Q5 milestones (File A §24.13)
    for item in [
        (
            "Q5-R0",
            "Contract freeze docs only",
            "IMPLEMENTED",
            "docs",
            "",
            "",
            "",
            "KEEP",
            "DOCUMENTED",
        ),
        (
            "Q5-R1",
            "Source identity PIT four-state fixture",
            "IMPLEMENTED",
            "selection/contracts.py fixtures.py",
            "GET /api/v1/selection/fixtures/q5-r1",
            "q5-contract.js",
            "test_q5_selection_contracts.py",
            "KEEP",
            "OBSERVED_RUNTIME",
        ),
        (
            "Q5-R2",
            "Family resolver zero corroboration",
            "IMPLEMENTED",
            "selection/resolver.py r2_fixtures.py",
            "GET /api/v1/selection/fixtures/q5-r2",
            "",
            "test_q5_family_resolver.py",
            "KEEP",
            "OBSERVED_RUNTIME",
        ),
        (
            "Q5-R3",
            "Closed-bar structure EOD CONFIRMED fixture",
            "IMPLEMENTED",
            "selection/structure.py r3_fixtures.py",
            "GET /api/v1/selection/fixtures/q5-r3",
            "",
            "test_q5_closed_bar_structure.py",
            "KEEP",
            "OBSERVED_RUNTIME",
        ),
        (
            "Q5-R4",
            "Enrichment MCX options gates",
            "IMPLEMENTED",
            "enrichment.py mcx_contracts.py options_domain.py",
            "GET /api/v1/selection/fixtures/q5-r4",
            "",
            "test_q5_bounded_enrichment.py",
            "KEEP",
            "OBSERVED_RUNTIME",
        ),
        (
            "Q5-R5",
            "Offline PK harness zero authority",
            "IMPLEMENTED",
            "scanners/pk_compatibility.py",
            "CLI only",
            "",
            "test_q5_pk_compatibility.py",
            "KEEP",
            "TESTED_OFFLINE",
        ),
        (
            "Q5-R6",
            "Inspector history PIT drift",
            "IMPLEMENTED",
            "history_validation.py pit_path.py r6_fixtures.py",
            "GET /api/v1/selection/fixtures/q5-r6",
            "index.html inspector",
            "test_q5_history_validation.py",
            "KEEP",
            "OBSERVED_RUNTIME",
        ),
        (
            "Q5-R7",
            "OpenAlgo RO capability boundary",
            "IMPLEMENTED",
            "openalgo_client.py",
            "GET /api/v1/integrations/openalgo/capability",
            "",
            "test_q5_openalgo_boundary.py",
            "KEEP",
            "OBSERVED_RUNTIME",
        ),
    ]:
        rid, req, st, mod, api, fe, tests, dec, ev = item
        rows.append(
            row(
                requirement_id=rid,
                source_file="new_merge_PLAN_2026-07-18.md",
                source_section="24.13",
                requirement=req,
                status=st,
                merge_milestone=rid,
                backend_module=mod,
                api_route=api,
                frontend_location=fe,
                test_ids=tests,
                decision=dec,
                reason="Q5 research/fixture ceiling",
                evidence_level=ev,
                product_scope="RESEARCH",
                priority="P0",
            )
        )

    # R0-R18
    for rid, req, st, href, mod, api, tests, reason, ev, pri in [
        (
            "R0",
            "Contract freeze residuals inventory pin lint",
            "PARTIAL",
            "Hybrid 16.3-16.6",
            "source_inventory_compiler.py; source_cohort_r0c.py; source_contracts.py; feature_registry.py; indicator_engine.py",
            "GET /api/source-inventory/compiler-report; GET /api/source-inventory/r0c-cohort; GET /api/v1/selection/feature-registry; GET /api/v1/selection/feature-registry/lint",
            "test_r0c_source_cohort.py",
            "Feature and engine contracts pass; H1A0 is 6/6; R0-C now partitions the complete compiler remainder and exposes it read-only with every member quarantined and zero-authority. Source-specific extended fields, maturity transition history, unresolved mirror/resolver proof and live activation remain separate residuals",
            "TESTED_OFFLINE",
            "P0",
        ),
        (
            "R1",
            "Selection DTO radar",
            "IMPLEMENTED",
            "Hybrid 9",
            "",
            "GET /api/v1/selection/evidence",
            "test_inventory_source_bundle.py",
            "Live 123-contract cadence-aware evidence DTO is persisted fail-closed at WATCH/WAIT/REJECT ceiling",
            "OBSERVED_RUNTIME",
            "P0",
        ),
        (
            "R2",
            "Live S0-S3 cheap pipeline",
            "IMPLEMENTED",
            "Hybrid 5 16.7",
            "",
            "GET /api/v1/selection/attention",
            "test_attention_order.py",
            "Live 2,463-row attention order is cadence-gated; non-current rows cannot rank and no CONFIRMED or geometry exists",
            "OBSERVED_RUNTIME",
            "P0",
        ),
        (
            "R3",
            "Family resolver",
            "IMPLEMENTED",
            "Hybrid 16.9",
            "selection/r3_claim_adapter.py; selection/r3_live.py; selection/resolver.py; selection/cash_post_commit.py",
            "GET /api/v1/selection/resolution",
            "test_cash_post_commit_pipeline.py",
            "FTR-040 binds only exact current NSE EOD cash facts to PARTICIPATION; R3 is hash-scoped, anti-double-counted, immutable over R2 and capped at WAIT with no geometry or execution",
            "OBSERVED_RUNTIME",
            "P0",
        ),
        (
            "R4",
            "PK pin delist fixtures",
            "PARTIAL",
            "",
            "scanners/pk_compatibility.py",
            "CLI",
            "test_q5_pk_compatibility",
            "Delist set incomplete",
            "TESTED_OFFLINE",
            "P1",
        ),
        (
            "R5",
            "Structure pack first CONFIRMED",
            "IMPLEMENTED",
            "Hybrid 16.8",
            "selection/structure.py",
            "GET /api/v1/selection/fixtures/q5-r3",
            "test_q5_closed_bar_structure.py",
            "Maps Q5-R3 fixture",
            "OBSERVED_RUNTIME",
            "P0",
        ),
        (
            "R6",
            "Shortlist enrichment live",
            "PARTIAL",
            "Hybrid 16.7",
            "selection/enrichment.py",
            "q5-r4",
            "test_q5_bounded_enrichment",
            "Live wiring incomplete",
            "TESTED_OFFLINE",
            "P1",
        ),
        (
            "R7",
            "PK shadow CLI",
            "IMPLEMENTED",
            "",
            "scanners/",
            "CLI",
            "test_q5_pk_compatibility",
            "Maps Q5-R5",
            "TESTED_OFFLINE",
            "P0",
        ),
        (
            "R8",
            "Native core scanner registry",
            "IMPLEMENTED",
            "Hybrid 16.8",
            "scanners/registry.py + scanners/native_core.py + main.py routes",
            "native-core.js #nativeCorePanel",
            "test_r8_native_core",
            "Wraps R5 FTR-006/007/017 claims; one representative per group (FUS-009); PK shadow isolated; confirmedCount pinned 0; S3 nativeCoreMatches rank-safe",
            "TESTED_OFFLINE",
            "P1",
        ),
        (
            "R9",
            "Lifecycle ORB VWAP",
            "PARTIAL",
            "Hybrid 16.8",
            "history_validation.py",
            "q5-r6",
            "",
            "ORB/VWAP needs live bars",
            "CODE_PRESENT",
            "P2",
        ),
        ("R10", "Pipe DSL", "IMPLEMENTED", "Hybrid 16.9", "scanners/pipe_dsl.py + main.py routes", "pipes.js #pipeLabPanel", "test_r10_pipes", "FUS-010 zero-claim composition over R8 native cores; UNION/INTERSECTION/FILTER_STATE/ENRICH_S7; invalid stage fails run; deterministic stage counts; twins cannot inflate", "TESTED_OFFLINE", "P2"),
        (
            "R11",
            "Swing RS delivery MCX master live",
            "PARTIAL",
            "Hybrid 16.7 MCX",
            "mcx_contracts.py + selection/r11_mcx_live.py + main.py routes",
            "mcx-master.js #mcxMasterPanel",
            "test_r11_mcx_live.py",
            "Readiness board live (WAIT without official master+local bars; tender veto; FBIL/CFTC context-only); PRF-005/006/007 profiles still empty until named MCX activation",
            "TESTED_OFFLINE",
            "P1",
        ),
        (
            "R12",
            "Options timeline API",
            "PARTIAL",
            "Hybrid 16.8",
            "options_domain.py",
            "q5-r4",
            "test_q5_bounded_enrichment.py",
            "No production timeline API",
            "TESTED_OFFLINE",
            "P1",
        ),
        (
            "R13",
            "Remaining scanners",
            "IMPLEMENTED",
            "Hybrid 16.8",
            "scanners/registry.py + native_core.py + native_extended.py + r5_live.py + s8_persist_run.py + scan_orchestrator.py (chips-only)",
            "GET /api/v1/scanners/native-core",
            "test_r13_remaining_scanners.py",
            "Pinned VCP/TTM/trend/Wilder-RSI/reversal/extremes guidance over adjusted closed hash-matched PIT bars; one bulk query; separate claimless representatives with inspectable suppression; S8 native hash attachment; zero claims/confirmation/state/rank/direction mutations; R9 remains skipped; stored pre-closure S8 honestly WAIT_S8_LINEAGE",
            "OBSERVED_RUNTIME",
            "P2",
        ),
        (
            "R14",
            "CA sponsor PK reconcile",
            "PARTIAL",
            "Hybrid 18.6 19.8",
            "corporate_actions.py",
            "",
            "",
            "Not full PK join",
            "CODE_PRESENT",
            "P2",
        ),
        (
            "R15",
            "Scanner Lab UI",
            "PARTIAL",
            "",
            "scanners/lab-bundle route in main.py",
            "scanner-lab.js #scannerLabPanel (inspector tab) + #pipeLabPanel + #nativeCorePanel",
            "test_r15_lab.py",
            "Lab tab DONE 2026-08-25 (definitions, pipe flow, symbol drill-down, PK parity chips; radar columns frozen; refresh=GET). Full FMR-009/011 workspace layout still open",
            "TESTED_OFFLINE",
            "P2",
        ),
        (
            "R16",
            "PIT before performance UI",
            "IMPLEMENTED",
            "Hybrid 15.5 16.11; File A 25.28",
            "selection/s8_service.py + r16_pit.py + r16_metrics.py + r16_store.py + r16_service.py",
            "GET /api/v1/selection/pit/status",
            "test_r16_pit.py",
            "R16 v1 code, 0013 migration and populated idempotent replay are verified; one real S8 date keeps PIT_NOT_APPROVED, and rendered browser inspection remains a tooling caveat",
            "OBSERVED_RUNTIME",
            "P1",
        ),
        (
            "R17",
            "OpenAlgo live RO shadow",
            "PARTIAL",
            "Hybrid 16.13 15.2",
            "openalgo_client.py",
            "GET /api/v1/integrations/openalgo/capability",
            "test_q5_openalgo_boundary.py",
            "ABSENT boundary observed; no live feed",
            "OBSERVED_RUNTIME",
            "P2",
        ),
        (
            "R18",
            "Model governance upgrades",
            "PARTIAL",
            "Hybrid 15.5",
            "drift contracts",
            "",
            "",
            "Contracts only",
            "DOCUMENTED",
            "P3",
        ),
    ]:
        rows.append(
            row(
                requirement_id=rid,
                source_file="new_merge_PLAN_2026-07-18.md",
                source_section="15",
                requirement=req,
                status=st,
                merge_milestone=rid,
                hybrid_reference=href,
                backend_module=mod,
                api_route=api,
                test_ids=tests,
                decision="KEEP",
                reason=reason,
                evidence_level=ev,
                product_scope="RESEARCH",
                frontend_location=(
                    "scanner-lab.js #scannerLabPanel (inspector tab); "
                    "pipes.js #pipeLabPanel; native-core.js #nativeCorePanel"
                    if rid == "R15"
                    else "scanner-lab.js #scannerLabPanel; native-core.js #nativeCorePanel"
                    if rid == "R13"
                    else ""
                ),
                priority=pri,
                last_verified=(
                    "2026-09-02"
                    if rid == "R0"
                    else "2026-08-16"
                    if rid in {"R1", "R2", "R3"}
                    else "2026-08-25"
                    if rid == "R15"
                    else "2026-08-27"
                    if rid == "R13"
                    else "2026-08-29"
                    if rid == "R16"
                    else "2026-08-26"
                    if rid in {"R8", "R10", "R11"}
                    else ""
                ),
            )
        )

    # CROSS-001..024
    for rid, req, ms, href, mod, st, dec, pri in [
        (
            "CROSS-001",
            "Inventory compiler H1A0 defects",
            "R0",
            "Hybrid 16.4",
            "source_inventory_compiler.py; source_overlap_resolutions.py",
            "IMPLEMENTED",
            "LINK_TO_B",
            "P0",
        ),
        (
            "CROSS-002",
            "Current living source-key map and endpoint dispositions",
            "R0/R2",
            "Hybrid 16.6 18.4",
            "source_inventory_compiler.py; source_key_map_review.py",
            "IMPLEMENTED",
            "LINK_TO_B",
            "P0",
        ),
        (
            "CROSS-003",
            "J01-J14 decision jobs",
            "R0",
            "Hybrid 19.2",
            "source_inventory_compiler.py",
            "IMPLEMENTED",
            "ADD",
            "P0",
        ),
        (
            "CROSS-004",
            "PRF named mandatory sources",
            "R2/R6",
            "Hybrid 16.7",
            "selection/profile_source_contracts.py",
            "IMPLEMENTED",
            "LINK_TO_B",
            "P0",
        ),
        (
            "CROSS-005",
            "Priority activation backlog 1-20",
            "R2",
            "Hybrid 16.16",
            "source activation",
            "PLANNED",
            "LINK_TO_B",
            "P1",
        ),
        (
            "CROSS-006",
            "Maturity ladder stage counts",
            "R0",
            "Hybrid 16.3",
            "source_inventory_compiler.py",
            "PARTIAL",
            "ADD",
            "P0",
        ),
        (
            "CROSS-007",
            "dataset_root transport mirror fields",
            "R0",
            "Hybrid 18.4",
            "source_inventory_compiler.py",
            "PARTIAL",
            "ADD",
            "P0",
        ),
        (
            "CROSS-008",
            "nse_fno_ban vs mwpl split",
            "R0/R6",
            "Hybrid 19.4",
            "parsers/nse_mwpl_parser.py; gate_readiness.py; source_inventory_compiler.py",
            "IMPLEMENTED",
            "IMPROVE",
            "P0",
        ),
        (
            "CROSS-009",
            "FBIL vs live USD/INR",
            "R11",
            "Hybrid 19.5",
            "commodity_context",
            "PARTIAL",
            "IMPROVE",
            "P1",
        ),
        (
            "CROSS-010",
            "Two-speed four lanes",
            "R17",
            "Hybrid 15.2",
            "source_scheduler",
            "PLANNED",
            "LINK_TO_B",
            "P1",
        ),
        (
            "CROSS-011",
            "Trust-producing combinations",
            "FUS",
            "Hybrid 15.4",
            "",
            "PLANNED",
            "LINK_TO_B",
            "P2",
        ),
        (
            "CROSS-012",
            "Per-source recovery SM",
            "ops",
            "Hybrid 16.12",
            "source_monitor",
            "PARTIAL",
            "LINK_TO_B",
            "P1",
        ),
        (
            "CROSS-013",
            "Four E2E vertical slices",
            "delivery",
            "Hybrid 16.17",
            "",
            "PLANNED",
            "LINK_TO_B",
            "P1",
        ),
        (
            "CROSS-014",
            "Legacy scorer FUS-008",
            "R0/Q5",
            "Hybrid 16.10 19.11",
            "intraday_stock_details.py",
            "PARTIAL",
            "IMPROVE",
            "P0",
        ),
        (
            "CROSS-015",
            "TradabilityRestriction full fields",
            "R6",
            "Hybrid 17.2 P0.1",
            "selection/tradability.py + S7/S8 integration",
            "IMPLEMENTED",
            "IMPROVE",
            "P0",
        ),
        (
            "CROSS-016",
            "Event MATCHED/POSSIBLE_MATCH",
            "R14",
            "Hybrid 19.8",
            "event claims",
            "PARTIAL",
            "ADD",
            "P1",
        ),
        (
            "CROSS-017",
            "Productivity FOMO compare journal",
            "UI",
            "Hybrid 9-10",
            "frontend",
            "PLANNED",
            "LINK_TO_B",
            "P2",
        ),
        (
            "CROSS-018",
            "Confidence vs evidence rank labels",
            "UI",
            "Hybrid 15.5 16.9",
            "q5-contract.js",
            "PARTIAL",
            "KEEP",
            "P1",
        ),
        (
            "CROSS-019",
            "EvidenceClaim timestamps",
            "R1",
            "Hybrid 7 17.2",
            "selection/contracts.py",
            "PARTIAL",
            "IMPROVE",
            "P0",
        ),
        (
            "CROSS-020",
            "Raw vs AdjustedMarketSeries",
            "R1",
            "Hybrid 17.2 P0.2",
            "storage candles",
            "PARTIAL",
            "IMPROVE",
            "P0",
        ),
        (
            "CROSS-021",
            "MARKET_FLOW parent cap",
            "FUS",
            "Hybrid 17.2 P0.4",
            "resolver.py",
            "PARTIAL",
            "IMPROVE",
            "P1",
        ),
        (
            "CROSS-022",
            "OpenAlgo interface methods",
            "Q5-R7/R17",
            "Hybrid 16.13",
            "openalgo_client.py",
            "PARTIAL",
            "KEEP",
            "P1",
        ),
        (
            "CROSS-023",
            "PIT calibration guards",
            "R16",
            "Hybrid 15.5 16.11",
            "selection/r16_pit.py + selection/r16_metrics.py + selection/r16_store.py + selection/r16_service.py",
            "IMPLEMENTED",
            "POSTPONE_UI",
            "P1",
        ),
        (
            "CROSS-024",
            "Extra failure narratives",
            "tests",
            "Hybrid 17.10 18.11",
            "tests/",
            "PARTIAL",
            "KEEP",
            "P1",
        ),
    ]:
        compiler_ids = {
            "CROSS-001",
            "CROSS-002",
            "CROSS-003",
            "CROSS-006",
            "CROSS-007",
            "CROSS-008",
        }
        compiler_reasons = {
            "CROSS-001": (
                "Compiler exposes all 11 Hybrid defect classes, preserves 370-row lineage, "
                "binds 29 current overlap groups to exact reviewed typed dispositions, and "
                "passes H1A0 6/6 with zero unexplained, invalid or stale resolutions"
            ),
            "CROSS-002": (
                "Compiler machine-enforces the current reviewed 118 inventory plus 74 "
                "runtime key sets as a 129-key union, keeps 197 generated identities as "
                "endpoint lineage, dispositions all 351 endpoints, and grants no gate authority"
            ),
            "CROSS-003": (
                "All J01-J14 jobs are typed, exposed through the compiler API and "
                "assigned to compiled contracts without execution authority"
            ),
            "CROSS-006": (
                "The ten-state ladder and counts are compiled fail-closed, but the "
                "source-health UI has not yet migrated to this contract"
            ),
            "CROSS-007": (
                "Dataset-root fields exist, but mirror/resolver identities and authority "
                "caps remain explicitly UNSPECIFIED pending source-by-source proof"
            ),
            "CROSS-008": (
                "Canonical ban and percentage contracts are separate; ban is a hard veto, "
                "missing percentages remain WAIT_MWPL_PERCENTAGES"
            ),
        }
        rows.append(
            row(
                requirement_id=rid,
                source_file="new_merge_PLAN_2026-07-18.md",
                source_section="25.5",
                requirement=req,
                status=st,
                merge_milestone=ms,
                hybrid_reference=href,
                backend_module=mod,
                api_route=(
                    "GET /api/v1/selection/tradability"
                    if rid == "CROSS-015"
                    else
                    "GET /api/gates/readiness; POST /api/source-parser/run; "
                    "GET /api/source-inventory/compiler-report"
                    if rid == "CROSS-008"
                    else "GET /api/source-inventory/compiler-report"
                    if rid in compiler_ids
                    else ""
                ),
                test_ids=(
                    "test_tradability_gate.py"
                    if rid == "CROSS-015"
                    else
                    "test_source_contract_hardening.py"
                    if rid == "CROSS-008"
                    else "test_source_inventory_compiler.py"
                    if rid in compiler_ids
                    else ""
                ),
                decision=dec,
                reason=compiler_reasons.get(rid, "Dual-file CROSS pointer"),
                evidence_level=(
                    "OBSERVED_RUNTIME"
                    if rid in {"CROSS-001", "CROSS-003"}
                    else "TESTED_OFFLINE"
                    if rid in compiler_ids
                    else "TESTED_OFFLINE"
                    if rid == "CROSS-015"
                    else ("DOCUMENTED" if st == "PLANNED" else "CODE_PRESENT")
                ),
                product_scope="RESEARCH",
                priority=pri,
                last_verified=(
                    "2026-07-23"
                    if rid == "CROSS-001"
                    else "2026-07-22"
                    if rid == "CROSS-003"
                    else "2026-09-02"
                    if rid == "CROSS-004"
                    else "2026-09-03"
                    if rid == "CROSS-015"
                    else ""
                ),
            )
        )

    # TDG-GAP-001..026
    for rid, req, ms, href, st, dec, pri in [
        (
            "TDG-GAP-001",
            "Source contract 15 extra fields",
            "R0",
            "Hybrid 15.3",
            "PARTIAL",
            "ADD",
            "P0",
        ),
        (
            "TDG-GAP-002",
            "Regime labels and size multipliers",
            "S2",
            "Hybrid 5 Stage 3",
            "PLANNED",
            "LINK_TO_B",
            "P2",
        ),
        (
            "TDG-GAP-003",
            "ESOP inter-se gift enrichment rules",
            "R6",
            "Hybrid 5 Stage 5",
            "PLANNED",
            "LINK_TO_B",
            "P1",
        ),
        (
            "TDG-GAP-004",
            "EvidenceClaim 19 base fields plus File A PIT fields",
            "R1",
            "Hybrid 7",
            "PARTIAL",
            "ADD",
            "P0",
        ),
        (
            "TDG-GAP-005",
            "Guidance contract 19 fields qty postpone",
            "UI",
            "Hybrid 7",
            "PARTIAL",
            "POSTPONE_QTY",
            "P2",
        ),
        (
            "TDG-GAP-006",
            "Productivity 10 requirements",
            "UI",
            "Hybrid 10",
            "PLANNED",
            "LINK_TO_B",
            "P2",
        ),
        (
            "TDG-GAP-007",
            "4-lane reliability architecture",
            "R17",
            "Hybrid 15.2",
            "PLANNED",
            "LINK_TO_B",
            "P1",
        ),
        (
            "TDG-GAP-008",
            "Trust combinations table",
            "FUS",
            "Hybrid 15.4",
            "PLANNED",
            "LINK_TO_B",
            "P2",
        ),
        (
            "TDG-GAP-009",
            "Probability promotion Brier ECE 200",
            "R16",
            "Hybrid 15.5",
            "POSTPONED",
            "POSTPONE",
            "P2",
        ),
        (
            "TDG-GAP-010",
            "Execution preflight tick lot freeze",
            "future",
            "Hybrid 15.6",
            "POSTPONED",
            "POSTPONE",
            "P3",
        ),
        (
            "TDG-GAP-011",
            "10-state source maturity ladder",
            "R0",
            "Hybrid 16.3",
            "PARTIAL",
            "ADD",
            "P0",
        ),
        (
            "TDG-GAP-012",
            "11 inventory defects enumeration",
            "R0",
            "Hybrid 16.4",
            "IMPLEMENTED",
            "LINK_TO_B",
            "P0",
        ),
        (
            "TDG-GAP-013",
            "Living source-key enumeration and endpoint disposition",
            "R0",
            "Hybrid 16.6",
            "IMPLEMENTED",
            "LINK_TO_B",
            "P0",
        ),
        (
            "TDG-GAP-014",
            "Exact contract names per profile",
            "R2/R6",
            "Hybrid 16.7",
            "IMPLEMENTED",
            "ADD",
            "P0",
        ),
        (
            "TDG-GAP-015",
            "Exact feature calculation formulas",
            "R5/R8",
            "Hybrid 16.8",
            "PARTIAL",
            "LINK_TO_B",
            "P0",
        ),
        (
            "TDG-GAP-016",
            "q_i quality formula",
            "R3/FUS",
            "Hybrid 16.9",
            "PARTIAL",
            "ADD",
            "P0",
        ),
        (
            "TDG-GAP-017",
            "PIT feature store schema labels metrics",
            "R16",
            "Hybrid 16.11",
            "IMPLEMENTED",
            "LINK_TO_B",
            "P1",
        ),
        (
            "TDG-GAP-018",
            "14-state breakage recovery SM",
            "R17",
            "Hybrid 16.12",
            "PLANNED",
            "LINK_TO_B",
            "P1",
        ),
        (
            "TDG-GAP-019",
            "OpenAlgo 9+5 methods",
            "R17",
            "Hybrid 16.13",
            "PARTIAL",
            "POSTPONE_EXEC",
            "P1",
        ),
        (
            "TDG-GAP-020",
            "Risk sizing INR formula",
            "H10",
            "Hybrid 16.14",
            "POSTPONED",
            "REJECT_CURRENT",
            "P3",
        ),
        (
            "TDG-GAP-021",
            "Priority activation backlog 1-20",
            "R2",
            "Hybrid 16.16",
            "PLANNED",
            "ADD",
            "P1",
        ),
        (
            "TDG-GAP-022",
            "Per-profile tradability checks",
            "R6",
            "Hybrid 17.4",
            "IMPLEMENTED",
            "IMPROVE",
            "P0",
        ),
        (
            "TDG-GAP-023",
            "Versioned cost STT GST list",
            "R16",
            "Hybrid 17.7",
            "PLANNED",
            "LINK_TO_B",
            "P2",
        ),
        (
            "TDG-GAP-024",
            "11-field dataset-root model plus File A business keys",
            "R0",
            "Hybrid 18.4",
            "PARTIAL",
            "ADD",
            "P0",
        ),
        (
            "TDG-GAP-025",
            "J01-J14 taxonomy",
            "R0",
            "Hybrid 19.2",
            "IMPLEMENTED",
            "ADD",
            "P0",
        ),
        (
            "TDG-GAP-026",
            "Cross-exchange event match states",
            "R14",
            "Hybrid 19.8",
            "PARTIAL",
            "ADD",
            "P1",
        ),
    ]:
        scope = "RESEARCH"
        if "POSTPONE" in dec or "REJECT" in dec:
            scope = "POSTPONE_OR_REJECT"
        tdg_compiler = {
            "TDG-GAP-001",
            "TDG-GAP-011",
            "TDG-GAP-012",
            "TDG-GAP-013",
            "TDG-GAP-024",
            "TDG-GAP-025",
        }
        tdg_reasons = {
            "TDG-GAP-001": (
                "All 15 fields are exposed, but every current contract remains unresolved "
                "until source-specific values and proofs are supplied"
            ),
            "TDG-GAP-011": (
                "The complete ten-state maturity ladder is typed, counted and exposed "
                "without status-text promotion, but source transitions are not separately "
                "persisted with history"
            ),
            "TDG-GAP-012": (
                "All 11 Hybrid defect classes are first-class compiler/API codes with "
                "zero-inclusive counts, migration actions and adversarial fixtures"
            ),
            "TDG-GAP-013": (
                "Current 118 inventory and 74 runtime keys compile to one reviewed "
                "129-key union; 197 hash IDs remain lineage-only, all 351 endpoints "
                "have explicit dispositions, and drift fails closed"
            ),
            "TDG-GAP-024": (
                "The 11-field model is present, but mirror, resolver and authority-cap "
                "values remain UNSPECIFIED pending evidence"
            ),
            "TDG-GAP-025": (
                "J01-J14 are typed, described, assigned and exposed by the compiler API"
            ),
        }
        rows.append(
            row(
                requirement_id=rid,
                source_file="new_merge_PLAN 25.16 + TWO_DOCUMENT_GOVERNANCE",
                source_section="25.16",
                requirement=req,
                status=st,
                merge_milestone=ms,
                hybrid_reference=href,
                backend_module=(
                    "selection/tradability.py; selection/s7_state_gates.py; "
                    "selection/s8_persist_run.py"
                    if rid == "TDG-GAP-022"
                    else "source_inventory_compiler.py"
                    if rid in tdg_compiler
                    else ""
                ),
                api_route=(
                    "GET /api/v1/selection/tradability; "
                    "GET /api/v1/selection/tradability/{symbol}"
                    if rid == "TDG-GAP-022"
                    else
                    "GET /api/source-inventory/compiler-report"
                    if rid in tdg_compiler
                    else ""
                ),
                test_ids=(
                    "test_tradability_gate.py"
                    if rid == "TDG-GAP-022"
                    else "test_source_inventory_compiler.py"
                    if rid in tdg_compiler
                    else ""
                ),
                decision=dec,
                reason=tdg_reasons.get(rid, "TDG-GAP dual-file governance"),
                evidence_level=(
                    "OBSERVED_RUNTIME"
                    if rid in {"TDG-GAP-011", "TDG-GAP-012", "TDG-GAP-025"}
                    else "TESTED_OFFLINE"
                    if rid in tdg_compiler
                    else "CODE_PRESENT"
                    if rid == "TDG-GAP-014"
                    else "TESTED_OFFLINE"
                    if rid == "TDG-GAP-022"
                    else "DOCUMENTED"
                ),
                product_scope=scope,
                priority=pri,
                last_verified=(
                    "2026-07-22"
                    if rid in {"TDG-GAP-011", "TDG-GAP-012", "TDG-GAP-025"}
                    else "2026-09-02"
                    if rid == "TDG-GAP-014"
                    else "2026-09-03"
                    if rid == "TDG-GAP-022"
                    else ""
                ),
            )
        )

    # HYBRID-* aliases governed by File A section 25; File B supplies detail.
    for rid, sec, req, st, ms, dec, reason, scope, pri in [
        (
            "HYBRID-1-1",
            "1",
            "Quantity/risk sizing objective",
            "POSTPONED",
            "POST-HYB-01",
            "POSTPONE",
            "Executable quantity is outside current scope; REJ-011 is broker execution/OMS/account routes",
            "POSTPONE_SIZING",
            "P3",
        ),
        (
            "HYBRID-2-1",
            "2",
            "Inventory 370/354/105/231/18 baseline",
            "PARTIAL",
            "R0",
            "ADD",
            "Compiler recomputes workbook row counts/hashes",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-4-1",
            "4",
            "Source contract decision_jobs fields",
            "PARTIAL",
            "DAT-021/R0",
            "IMPROVE",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-5-1",
            "5.8",
            "Risk sizing ATR/spread/gap pipeline",
            "POSTPONED",
            "POST-HYB-01",
            "POSTPONE",
            "Research rationale retained; executable sizing remains outside current scope",
            "POSTPONE_SIZING",
            "P3",
        ),
        (
            "HYBRID-5-2",
            "5.9",
            "OpenAlgo promotion sequence",
            "PARTIAL",
            "OPN/Q5-R7",
            "IMPROVE",
            "RO only",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-6-1",
            "6",
            "Strategy mandatory combinations",
            "IMPLEMENTED",
            "PRF-001..007",
            "IMPROVE",
            "Named mandatory, confirmation and veto source groups are implemented for all seven profiles",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-7-1",
            "7",
            "EvidenceClaim complete schema",
            "PARTIAL",
            "DAT-019",
            "IMPROVE",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-7-2",
            "7",
            "Guidance contract entry/stop/qty",
            "PARTIAL",
            "UI",
            "POSTPONE",
            "qty fields out of scope",
            "POSTPONE_SIZING",
            "P2",
        ),
        (
            "HYBRID-8-1",
            "8",
            "Storage model rationale",
            "PARTIAL",
            "STO 14",
            "LINK_TO_B",
            "",
            "RESEARCH",
            "P2",
        ),
        (
            "HYBRID-9-1",
            "9",
            "UI command bar radar risk rail",
            "PARTIAL",
            "UI-001..009",
            "IMPROVE",
            "no qty rail",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-9-2",
            "9",
            "Inspector tabs content",
            "PARTIAL",
            "13.2/Q5-R6",
            "KEEP",
            "",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-10-1",
            "10",
            "Productivity 10 features",
            "PLANNED",
            "CROSS-017",
            "ADD",
            "",
            "RESEARCH",
            "P2",
        ),
        (
            "HYBRID-11-1",
            "11",
            "API risk/guidance endpoint proposals",
            "POSTPONED",
            "POST-HYB-01/02",
            "POSTPONE",
            "No executable sizing endpoint; retain evidence and no-action guidance concepts only",
            "POSTPONE_SIZING",
            "P2",
        ),
        (
            "HYBRID-15-1",
            "15",
            "Fable audit gaps",
            "PARTIAL",
            "File A 20-23",
            "IMPROVE",
            "",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-16-1",
            "16.1",
            "Workbook paths and SHA-256",
            "PLANNED",
            "R0",
            "ADD",
            "Recompute live hashes",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-16-2",
            "16.3",
            "Source-state ladder 10 states",
            "PARTIAL",
            "CROSS-006",
            "ADD",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-16-3",
            "16.4",
            "Inventory defects 11",
            "IMPLEMENTED",
            "CROSS-001",
            "LINK_TO_B",
            "All 11 defect classes remain explicit and H1A0 6/6 passes with complete lineage plus exact reviewed semantic-overlap dispositions",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-16-4",
            "16.5",
            "URL roles 10 counts",
            "PLANNED",
            "R0",
            "ADD",
            "",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-16-5",
            "16.6",
            "Living source-key map and endpoint dispositions",
            "IMPLEMENTED",
            "CROSS-002",
            "LINK_TO_B",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-16-6",
            "16.7",
            "Strategy source combos exact keys",
            "IMPLEMENTED",
            "CROSS-004",
            "LINK_TO_B",
            "Exact keys are exposed by the zero-authority profile-source contract registry",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-16-7",
            "16.8",
            "Feature formula derivations",
            "PARTIAL",
            "FTR-001..039",
            "LINK_TO_B",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-16-8",
            "16.9",
            "q_i claim-quality formula",
            "PARTIAL",
            "R3/FUS-009",
            "MERGE",
            "Use q_i only as claim quality input; File A FUS-009 controls family fusion and anti-double-counting",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-16-9",
            "16.10",
            "Legacy scorer lines 887-931",
            "PARTIAL",
            "FUS-008/CROSS-014",
            "IMPROVE",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-16-10",
            "16.11",
            "ML PIT Brier ECE plan",
            "PARTIAL",
            "R16/VAL",
            "IMPROVE",
            "No P(win) UI early",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-17-1",
            "17.2 P0.1",
            "Tradability T2T ESM ban MWPL",
            "PARTIAL",
            "FTR-035",
            "IMPROVE",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-17-2",
            "17.2 P0.2",
            "Raw/adjusted layers",
            "PARTIAL",
            "STO-020",
            "IMPROVE",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-17-3",
            "17.2 P0.3",
            "Timestamps revision",
            "PARTIAL",
            "DAT-019",
            "IMPROVE",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-17-4",
            "17.2 P0.4",
            "Family hierarchy caps",
            "PARTIAL",
            "FUS/CROSS-021",
            "IMPROVE",
            "",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-17-5",
            "17.2 P0.5",
            "Realizable unit risk",
            "POSTPONED",
            "POST-HYB-03",
            "POSTPONE",
            "Keep as future research; current product cannot calculate executable quantity",
            "POSTPONE_SIZING",
            "P3",
        ),
        (
            "HYBRID-17-6",
            "17.2 P0.6",
            "Legacy quarantine flags",
            "PARTIAL",
            "FUS-008",
            "IMPROVE",
            "can_size false",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-18-1",
            "18.4",
            "Dataset-root identity model",
            "PLANNED",
            "TDG-GAP-024",
            "ADD",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-18-2",
            "18.5",
            "Four decision chains",
            "PARTIAL",
            "PRF",
            "IMPROVE",
            "",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-18-3",
            "18.6",
            "Code corrections 9 items",
            "PARTIAL",
            "impl notes",
            "IMPROVE",
            "",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-19-1",
            "19.2",
            "J01-J14 taxonomy",
            "IMPLEMENTED",
            "CROSS-003",
            "ADD",
            "J01-J14 are typed, exposed and covered by the inventory compiler contract",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-19-2",
            "19.3",
            "NSE transport 9 behaviors",
            "PARTIAL",
            "DAT-020",
            "IMPROVE",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-19-3",
            "19.4",
            "F&O ban MWPL split",
            "IMPLEMENTED",
            "CROSS-008",
            "KEEP",
            "Canonical split verified; percentages remain explicitly unavailable",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-19-4",
            "19.5",
            "USD/INR role split",
            "PARTIAL",
            "CROSS-009",
            "IMPROVE",
            "",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-19-5",
            "19.6",
            "Legacy state mapping",
            "PARTIAL",
            "STA-005",
            "ADD",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-19-6",
            "19.7",
            "PIT outcome worker",
            "PARTIAL",
            "R16/STO",
            "IMPROVE",
            "",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-19-7",
            "19.8",
            "Event matching states",
            "PARTIAL",
            "CROSS-016",
            "IMPROVE",
            "",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-19-8",
            "19.9",
            "True P0 priority",
            "PARTIAL",
            "R0-R18",
            "IMPROVE",
            "",
            "RESEARCH",
            "P1",
        ),
        (
            "HYBRID-19-9",
            "19.11",
            "Legacy quarantine controls",
            "PARTIAL",
            "FUS-008",
            "IMPROVE",
            "",
            "RESEARCH",
            "P0",
        ),
        (
            "HYBRID-19-10",
            "19.12",
            "Risk policy percentages",
            "POSTPONED",
            "POST-HYB-01",
            "POSTPONE",
            "Research-only until a separately approved sizing scope exists",
            "POSTPONE_SIZING",
            "P3",
        ),
        (
            "HYBRID-19-11",
            "19.13",
            "H-series milestones",
            "PLANNED",
            "R0-R18 map",
            "KEEP",
            "Advisory only",
            "RESEARCH",
            "P1",
        ),
    ]:
        rows.append(
            row(
                requirement_id=rid,
                source_file="new_merge_PLAN_2026-07-18.md + TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md",
                source_section=sec,
                requirement=req,
                status=st,
                merge_milestone=ms,
                hybrid_reference=f"Section {sec}",
                backend_module=(
                    "source_inventory_compiler.py; source_overlap_resolutions.py"
                    if rid == "HYBRID-16-3"
                    else ""
                ),
                api_route=(
                    "GET /api/source-inventory/compiler-report"
                    if rid == "HYBRID-16-3"
                    else ""
                ),
                test_ids=(
                    "test_source_inventory_compiler.py"
                    if rid == "HYBRID-16-3"
                    else ""
                ),
                decision=dec,
                reason=reason
                or "Preserved Hybrid requirement; implementation or evidence remains incomplete",
                evidence_level=(
                    "OBSERVED_RUNTIME"
                    if rid == "HYBRID-16-3"
                    else "CODE_PRESENT"
                    if rid in {"HYBRID-6-1", "HYBRID-16-6"}
                    else "DOCUMENTED"
                ),
                product_scope=scope,
                priority=pri,
                last_verified=(
                    "2026-07-23"
                    if rid == "HYBRID-16-3"
                    else "2026-09-02"
                    if rid in {"HYBRID-6-1", "HYBRID-16-6"}
                    else ""
                ),
            )
        )

    # Final Merge FMR aliases mapped by File A section 25.21.
    for rid, req, milestone, decision, reason, priority in [
        (
            "FMR-001",
            "Use every permitted source and every resolved stock for research",
            "R0/R2/R16",
            "ADD",
            "Dynamic source bindings, complete research universe, PIT coverage and explicit unknowns",
            "P0",
        ),
        (
            "FMR-002",
            "Complete cheap-to-expensive all-stock research flow",
            "R0/R2/R3/R8/R9/R15/R16",
            "MERGE",
            "All-stock cheap pass, transparent shortlist, closed structure, one resolver, radar and journal",
            "P0",
        ),
        (
            "FMR-003",
            "Option-chain truth and feature-specific eligibility",
            "R12",
            "ADD",
            "Identity, timing, contract master, chain quality and snapshot proof must precede interpretation",
            "P1",
        ),
        (
            "FMR-004",
            "Strike OI PCR walls max-pain skew term and migration research",
            "R12/R16",
            "MERGE",
            "One strike/expiry laboratory with PIT sensitivity and explicit coverage",
            "P1",
        ),
        (
            "FMR-005",
            "Gamma concentration and signed GEX scenario research",
            "R12/R16",
            "ADD",
            "Canonical Gamma stays unsigned; signed GEX and flip remain labeled scenarios pending PIT proof",
            "P1",
        ),
        (
            "FMR-006",
            "IV Greeks expiry and research-contract inspection",
            "R12/R16",
            "MERGE",
            "Model, carry, settlement, quote quality and near-expiry stability remain explicit",
            "P1",
        ),
        (
            "FMR-007",
            "Combine one derivatives package with governed stock selection",
            "R3/R12/R15",
            "MERGE",
            "Options may support weaken conflict or remain unknown but cannot independently confirm",
            "P1",
        ),
        (
            "FMR-008",
            "PKScreener open-source calculators and OpenAlgo read-only comparison",
            "R4/R7/R12/R17",
            "MERGE",
            "Pinned audited shadow tools only; dependencies and licenses require proof and OpenAlgo remains read-only",
            "P1",
        ),
        (
            "FMR-009",
            "All Stocks radar and Strike Expiry inspector",
            "R15",
            "ADD",
            "Show every resolved stock, shortlist reasons, calculations, missing proof, conflicts and lineage",
            "P1",
        ),
        (
            "FMR-010",
            "Final Merge acceptance tests lineage PIT and build ceilings",
            "R0-R18",
            "ADD",
            "Every mapped vertical must adopt applicable adversarial tests before completion",
            "P0",
        ),        (
            "FMR-011",
            "Local Paper Lab objective outcomes and governed ML relearning",
            "R15/R16/R18",
            "ADD",
            "Deterministic no-broker replay feeds PIT labels and batch challenger learning with drift review human promotion and rollback",
            "P0",
        ),
    ]:
        rows.append(
            row(
                requirement_id=rid,
                source_file="FINAL_MERGE_PLAN.md + new_merge_PLAN_2026-07-18.md",
                source_section=f"{rid}; File A 25.21",
                requirement=req,
                status=("PARTIAL" if rid in {"FMR-009", "FMR-011"} else "PLANNED"),
                merge_milestone=milestone,
                hybrid_reference="Open Final Merge FMR section plus Hybrid sections mapped by File A",
                frontend_location=(
                    "docs/TRENDFORGE_FINAL_PRODUCT.html (static fixture); frontend runtime pending"
                    if rid in {"FMR-009", "FMR-011"}
                    else ""
                ),
                decision=decision,
                reason=(
                    reason
                    + "; static presentation fixture exists but canonical runtime/PIT/model ownership remains open"
                    if rid in {"FMR-009", "FMR-011"}
                    else reason
                ),
                evidence_level=(
                    "DOCUMENTED"
                ),
                product_scope="RESEARCH",
                priority=priority,
                last_verified=(
                    "2026-08-14" if rid in {"FMR-009", "FMR-011"} else "2026-07-29"
                ),
            )
        )
    # Conflicts
    for rid, req, reason, scope in [
        (
            "CONFLICT-001",
            "Public NSE routes vs live intraday authority",
            "Public routes remain research-only until licensed/OpenAlgo integrity gates pass",
            "RESEARCH",
        ),
        (
            "CONFLICT-002",
            "Hybrid WAIT/READY variants vs four public states",
            "Expose WATCH/WAIT/CONFIRMED/REJECT only; variants are reason codes",
            "RESEARCH",
        ),
        (
            "CONFLICT-003",
            "Hybrid H1-H10 order vs File A R0-R18/Q5",
            "File A sequence controls; H-series labels are detail aliases only",
            "RESEARCH",
        ),
        (
            "CONFLICT-004",
            "Hybrid quantity/risk rail vs current no-quantity scope",
            "Postpone under POST-HYB-01..03; no executable quantity",
            "POSTPONE_SIZING",
        ),
        (
            "CONFLICT-005",
            "Online or automatic ML promotion vs governed relearning",
            "Offline batch relearning is allowed under FMR-011; no silent promotion; R16/R18 control",
            "RESEARCH",
        ),
        (
            "CONFLICT-006",
            "External proposal to keep all domain detail out of File A",
            "File A keeps short FTR contracts; File B remains the long-form recipe library",
            "RESEARCH",
        ),
    ]:
        rows.append(
            row(
                requirement_id=rid,
                source_file="new_merge_PLAN_2026-07-18.md",
                source_section="25.8",
                requirement=req,
                status="CONFLICT",
                merge_milestone="N/A",
                decision="CONFLICT_RESOLVED",
                reason=reason,
                evidence_level="DOCUMENTED",
                product_scope=scope,
                priority="P0",
            )
        )

    # Retained solely for traceability: the advisory draft minted a seventh
    # conflict ID for a topic now governed by File A CONFLICT-003.
    rows.append(
        row(
            requirement_id="CONFLICT-007",
            source_file="TRENDFORGE_GOVERNANCE_SYSTEM_ai.md",
            source_section="legacy duplicate conflict registry",
            requirement="Legacy R0-R18 vs H1-H10 conflict alias",
            status="REJECTED",
            merge_milestone="CONFLICT-003",
            decision="MERGE",
            reason="Not a File A conflict; retained only as a non-authoritative alias of CONFLICT-003",
            evidence_level="DOCUMENTED",
            product_scope="REJECTED",
            priority="P3",
        )
    )

    # R0 feature registry and indicator-engine pin
    for rid, req, section, api in [
        (
            "DAT-010",
            "Mandatory 22-field feature contract and build lint",
            "6; 17.1",
            "GET /api/v1/selection/feature-registry",
        ),
        (
            "DAT-011",
            "One pinned indicator engine and dependency manifest per run",
            "17.1",
            "GET /api/v1/selection/feature-registry/lint",
        ),
    ]:
        rows.append(
            row(
                requirement_id=rid,
                source_file="new_merge_PLAN_2026-07-18.md",
                source_section=section,
                requirement=req,
                status="IMPLEMENTED",
                merge_milestone="R0",
                api_route=api,
                test_ids="test_feature_registry.py",
                decision="KEEP",
                reason="Contract-level R0 ceiling; registry presence does not prove feature activation or live authority",
                evidence_level="OBSERVED_RUNTIME",
                product_scope="RESEARCH",
                priority="P0",
            )
        )

    for rid, req in [
        ("T-028", "Insufficient indicator warm-up returns INPUT_INCOMPLETE"),
        ("T-029", "Mixed indicator engines fail the run manifest"),
        ("T-030", "Indicator parity divergence is recorded explicitly"),
        ("T-194", "Missing or mixed engine identity fails closed"),
        ("T-195", "Insufficient warm-up history cannot emit indicator evidence"),
    ]:
        rows.append(
            row(
                requirement_id=rid,
                source_file="new_merge_PLAN_2026-07-18.md",
                source_section="16.3; 25.12",
                requirement=req,
                status="IMPLEMENTED",
                merge_milestone="R0",
                test_ids="test_feature_registry.py",
                decision="KEEP",
                reason="Observed in deterministic offline fixtures",
                evidence_level="TESTED_OFFLINE",
                product_scope="RESEARCH",
                priority="P0",
            )
        )
    # Controlling File A IDs
    for rid, req, st, tests, pri in [
        (
            "GOV-002",
            "No execution OMS account routes",
            "IMPLEMENTED",
            "test_q5_openalgo_boundary",
            "P0",
        ),
        (
            "GOV-003",
            "Evidence strength not probability",
            "IMPLEMENTED",
            "q5-contract frontend",
            "P0",
        ),
        (
            "STA-001",
            "Four product states only",
            "IMPLEMENTED",
            "test_q5_selection_contracts",
            "P0",
        ),
        (
            "FUS-008",
            "detail_score discovery quarantine",
            "PARTIAL",
            "test_q5 + call-graph open",
            "P0",
        ),
        (
            "FUS-011",
            "Zero corroboration bonus",
            "IMPLEMENTED",
            "test_q5_family_resolver",
            "P0",
        ),
        (
            "PK-019",
            "Finite offline PK no production sidecar",
            "IMPLEMENTED",
            "test_q5_pk_compatibility",
            "P0",
        ),
        ("REJ-011", "Broker execution rejected", "REJECTED", "", "P0"),
        ("POST-HYB-01", "INR 1L quantity tables postponed", "POSTPONED", "", "P3"),
        (
            "GOV-TRACE-001",
            "This CSV is traceability only not a third plan",
            "IMPLEMENTED",
            "build_coverage_csv.py validation",
            "P0",
        ),
    ]:
        rows.append(
            row(
                requirement_id=rid,
                source_file="new_merge_PLAN_2026-07-18.md",
                source_section="ledger",
                requirement=req,
                status=st,
                merge_milestone="governance",
                test_ids=tests,
                decision="KEEP"
                if st in ("IMPLEMENTED", "PARTIAL")
                else ("POSTPONE" if st == "POSTPONED" else "REJECT"),
                reason="File A controlling",
                evidence_level="CODE_PRESENT"
                if st in ("IMPLEMENTED", "PARTIAL")
                else "DOCUMENTED",
                product_scope="RESEARCH" if st != "REJECTED" else "REJECTED",
                priority=pri,
            )
        )

    attach_reviewed_code_evidence(rows)
    validate_rows(rows)
    validate_governance_docs(rows)
    existing, fieldnames = read_existing()
    generated_ids = {item["requirement_id"] for item in rows}
    validate_existing(existing, fieldnames, generated_ids)
    added, removed, changed = compare_rows(existing, rows)
    print(f"Rows: {len(rows)}; added={added}; removed={removed}; changed={changed}")
    p0_build_rows = sum(
        item["priority"] == "P0" and item["status"] in {"PLANNED", "PARTIAL"}
        for item in rows
    )
    p0_not_implemented = sum(
        item["priority"] == "P0" and item["status"] != "IMPLEMENTED" for item in rows
    )
    print(f"P0 build rows={p0_build_rows}; P0 not implemented={p0_not_implemented}")

    if removed:
        raise ValueError(
            "Refusing to remove existing requirement IDs. Reconcile them manually: "
            + ", ".join(removed)
        )
    if args.check:
        return 1 if added or changed else 0
    require_review_acceptance(added, changed, args.accept_reviewed_changes)

    temporary = OUT.with_suffix(OUT.suffix + ".tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLS)
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(OUT)
    finally:
        if temporary.exists():
            temporary.unlink()

    counts = Counter(item["status"] for item in rows)
    evidence_counts = Counter(item["evidence_level"] for item in rows)
    print(f"Wrote {len(rows)} rows to {OUT}")
    print(dict(counts))
    print(dict(evidence_counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
