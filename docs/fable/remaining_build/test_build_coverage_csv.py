from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).with_name("build_coverage_csv.py")
SPEC = importlib.util.spec_from_file_location("trendforge_build_coverage", MODULE_PATH)
assert SPEC and SPEC.loader
coverage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coverage)


def _fmr_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for rid, owners in coverage.EXPECTED_FMR_OWNERS.items():
        if owners == coverage.VALID_R_OWNERS:
            value = "Applicable R0-R18"
        else:
            value = "/".join(sorted(owners, key=lambda item: int(item[1:])))
        rows.append({"requirement_id": rid, "merge_milestone": value})
    return rows


def _discovery() -> str:
    return coverage._read_text("docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md")


def test_current_fmr_maps_are_structurally_equal() -> None:
    file_a = coverage.parse_fmr_table(
        coverage._read_text("docs/fable/new_merge_PLAN_2026-07-18.md"),
        owner_column=1,
        linked_column=2,
        label="File A",
    )
    final_merge = coverage.parse_fmr_table(
        coverage._read_text("docs/fable/FINAL_MERGE_PLAN.md"),
        owner_column=1,
        linked_column=2,
        label="FINAL_MERGE_PLAN",
    )
    readme = coverage.parse_fmr_table(
        coverage._read_text("docs/fable/remaining_build/README.md"),
        owner_column=2,
        linked_column=3,
        label="remaining_build README",
    )
    assert file_a == final_merge == readme
    assert file_a == (coverage.EXPECTED_FMR_OWNERS, coverage.EXPECTED_FMR_LINKED)


def test_fmr_owner_mismatch_fails_full_governance_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_reader = coverage._read_text
    canonical = original_reader("docs/fable/new_merge_PLAN_2026-07-18.md")
    bad = re.sub(
        r"(\|\s*`FMR-001`\s*\|\s*)`R0`,\s*`R2`,\s*`R16`",
        r"\1`R0`, `R16`",
        canonical,
        count=1,
    )
    assert bad != canonical

    def read_with_bad_file_a(relative: str) -> str:
        if relative == "docs/fable/new_merge_PLAN_2026-07-18.md":
            return bad
        return original_reader(relative)

    monkeypatch.setattr(coverage, "_read_text", read_with_bad_file_a)
    with pytest.raises(ValueError, match="File A FMR owner map"):
        coverage.validate_governance_docs(_fmr_rows())


def test_documented_and_executable_changed_file_allowlists_match() -> None:
    readme = coverage._read_text("docs/fable/remaining_build/README.md")
    documented = coverage.parse_documented_cleanup_allowlist(readme)
    assert documented == coverage.GOVERNANCE_CLEANUP_ALLOWLIST

    unsafe = readme.replace(
        "docs/VALIDATION.md\n```",
        "docs/VALIDATION.md\nbackend/trendforge_api/main.py\n```",
        1,
    )
    assert (
        coverage.parse_documented_cleanup_allowlist(unsafe)
        != coverage.GOVERNANCE_CLEANUP_ALLOWLIST
    )


def test_changed_file_allowlist_has_safe_and_unsafe_traps() -> None:
    coverage.validate_changed_files(
        [
            "docs/DECISIONS.md",
            "docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md",
            "docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md",
            str(coverage.ROOT / "TREND_FORGE_ARCHITECTURE.md"),
            str(coverage.ROOT / "docs" / "VALIDATION.md"),
        ]
    )
    with pytest.raises(ValueError, match="outside governance-cleanup allowlist"):
        coverage.validate_changed_files(["backend/trendforge_api/main.py"])
    with pytest.raises(ValueError, match="outside TrendForge"):
        coverage.validate_changed_files([str(coverage.ROOT.parent / "outside.md")])


def test_decision_inventory_and_duplicate_trap() -> None:
    current = coverage._read_text("docs/DECISIONS.md")
    inventory = coverage.decision_inventory(current)
    assert inventory["count"] == 54
    assert inventory["max_id"] == "D-059"
    assert inventory["next_free"] == "D-060"
    assert inventory["duplicates"] == ()

    good = (
        "## D-025 Canonical Inventory Compiler\n"
        "## D-029 Single Build Spine\n"
        "## D-030 Professional Mathematics Is A Mapped Research Detail\n"
    )
    coverage.validate_decision_ids(good)
    with pytest.raises(ValueError, match="duplicate decision IDs"):
        coverage.validate_decision_ids(good + "## D-029 Reused\n")


@pytest.mark.parametrize(
    "unsafe",
    [
        "Start Phase T0 now",
        "Start with Phase T0 now",
        "| Sprint | Theme |",
        "M0 → M1",
        "PK-A only",
        "Prefer this file over File A",
        "Pick next milestone M10 now",
        "Next milestone M10",
        "Choose the next M10",
        "Do next M10",
    ],
)
def test_competing_detail_order_traps(unsafe: str) -> None:
    coverage.validate_no_competing_detail_order(
        "File A selects R12; M10 is a detail tag only.",
        "R12 selects work; M10 and M11 are navigation tags.",
    )
    with pytest.raises(ValueError, match="competing build instruction"):
        coverage.validate_no_competing_detail_order(
            "File A selects R12 safely.\n" + unsafe,
            "R12 selects work.",
        )


def test_safe_and_unsafe_order_content_cannot_hide_the_trap() -> None:
    mixed = (
        "File A selects R12; all tags are catalog references only.\n"
        "Prefer this file over File A."
    )
    with pytest.raises(ValueError, match="competing build instruction"):
        coverage.validate_no_competing_detail_order(mixed, "R12 selects work.")


def test_negated_pick_next_is_safe_but_mixed_pick_next_fails() -> None:
    safe = "Do not pick next milestone M10; File A selects the work item."
    coverage.validate_no_competing_detail_order(safe, "R12 selects work.")

    mixed = safe + "\nPick next milestone M10 now."
    with pytest.raises(ValueError, match="competing build instruction"):
        coverage.validate_no_competing_detail_order(mixed, "R12 selects work.")


def test_file_a_selector_language_includes_r_cross_tdg_and_subordinates_tags() -> None:
    safe = (
        "Select one File A requirement ID: R0-R18, CROSS-###, or "
        "TDG-GAP-###; never M/T/PK."
    )
    coverage.validate_file_a_selection_language(safe, safe, safe)

    unsafe = "Select one File A requirement ID from R0-R18; never M/T/PK."
    with pytest.raises(ValueError, match="unified File A requirement selector"):
        coverage.validate_file_a_selection_language(unsafe, safe, safe)


def test_discovery_detail_tags_have_exact_valid_owner_and_fmr_rows() -> None:
    parsed = coverage.parse_discovery_owner_table(_discovery())
    assert set(parsed) == coverage.EXPECTED_DETAIL_TAGS
    assert len(parsed) == 33
    assert parsed["M17"] == (
        frozenset({"R0"}),
        frozenset({"FMR-010"}),
    )


def test_missing_and_duplicate_detail_tag_traps() -> None:
    discovery = _discovery()
    missing = re.sub(r"(?m)^\| \*\*M17\*\* .*\n", "", discovery, count=1)
    with pytest.raises(ValueError, match="detail-owner table drift"):
        coverage.parse_discovery_owner_table(missing)

    line = re.search(r"(?m)^\| \*\*M17\*\* .*\n", discovery)
    assert line
    duplicate = discovery.replace(line.group(0), line.group(0) * 2, 1)
    with pytest.raises(ValueError, match="duplicate owner row for M17"):
        coverage.parse_discovery_owner_table(duplicate)


def test_invalid_r_owner_and_invalid_fmr_reference_traps() -> None:
    discovery = _discovery()
    invalid_owner = discovery.replace("| **M17** | R0 |", "| **M17** | R19 |", 1)
    with pytest.raises(ValueError, match="invalid owners"):
        coverage.parse_discovery_owner_table(invalid_owner)

    invalid_fmr = discovery.replace(
        "| **M17** | R0 | FMR-010 |",
        "| **M17** | R0 | FMR-999 |",
        1,
    )
    with pytest.raises(ValueError, match="Invalid FMR references"):
        coverage.parse_discovery_owner_table(invalid_fmr)


def test_detail_owner_must_be_covered_by_referenced_fmr_owners() -> None:
    discovery = _discovery().replace(
        "| **M17** | R0 | FMR-010 |",
        "| **M17** | R0 | FMR-009 |",
        1,
    )
    with pytest.raises(ValueError, match="owners are not covered by FMR_refs"):
        coverage.parse_discovery_owner_table(discovery)


def test_activation_claim_requires_observed_runtime_condition() -> None:
    safe = "When the current observed runtime reports sourceActivationReady=false, WAIT."
    coverage.validate_conditional_activation_claims(safe, safe)

    unsafe = "sourceActivationReady=false -> WAIT ceiling"
    with pytest.raises(ValueError, match="permanent activation claim"):
        coverage.validate_conditional_activation_claims(safe + "\n" + unsafe, safe)


def test_runtime_manifest_hash_and_changed_file_gate() -> None:
    actual = coverage.runtime_manifest_hash()
    assert len(actual) == 64
    assert coverage.validate_runtime_manifest(actual.lower(), ["docs/DECISIONS.md"]) == actual

    with pytest.raises(ValueError, match="requires --expected-runtime-manifest-hash"):
        coverage.validate_runtime_manifest(None, ["docs/DECISIONS.md"])
    with pytest.raises(ValueError, match="Runtime manifest mismatch"):
        coverage.validate_runtime_manifest("0" * 64, ["docs/DECISIONS.md"])
    with pytest.raises(ValueError, match="requires --expected-runtime-manifest-hash"):
        coverage.main(["--check", "--changed-file", "docs/DECISIONS.md"])



def test_professional_mathematics_reconciliation_and_traps() -> None:
    file_a = coverage._read_text("docs/fable/new_merge_PLAN_2026-07-18.md")
    hybrid = coverage._read_text(
        "docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md"
    )
    final_merge = coverage._read_text("docs/fable/FINAL_MERGE_PLAN.md")
    discovery = coverage._read_text("docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md")
    options = coverage._read_text("docs/OPTIONS_INTELLIGENCE_PLAN.md")
    architecture = coverage._read_text("TREND_FORGE_ARCHITECTURE.md")
    mathematics = coverage._read_text("docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md")
    decisions = coverage._read_text("docs/DECISIONS.md")
    fileindex = coverage._read_text("fileindex.md")

    args = (
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
    coverage.validate_mathematics_reconciliation(*args)

    missing_horizon = mathematics.replace(
        "P(tau_b < tau_a and tau_b <= H)",
        "P(finite_horizon_definition_removed)",
        1,
    )
    with pytest.raises(ValueError, match="finite-horizon barrier"):
        coverage.validate_mathematics_reconciliation(
            file_a,
            hybrid,
            final_merge,
            discovery,
            options,
            architecture,
            missing_horizon,
            decisions,
            fileindex,
        )

    unsafe_architecture = architecture + "\nState: LONG_BUILD_UP\n"
    with pytest.raises(ValueError, match="LONG_BUILD_UP"):
        coverage.validate_mathematics_reconciliation(
            file_a,
            hybrid,
            final_merge,
            discovery,
            options,
            unsafe_architecture,
            mathematics,
            decisions,
            fileindex,
        )
    missing_vrp_math = mathematics.replace(
        "### 17.6 Volatility risk premium as scanner context",
        "### 17.6 Removed volatility context",
        1,
    )
    with pytest.raises(ValueError, match="VRP context"):
        coverage.validate_mathematics_reconciliation(
            file_a,
            hybrid,
            final_merge,
            discovery,
            options,
            architecture,
            missing_vrp_math,
            decisions,
            fileindex,
        )

    missing_options_unknown = options.replace("VRP_UNKNOWN", "VRP_REMOVED")
    with pytest.raises(ValueError, match="Options lacks VRP/Theta reconciliation"):
        coverage.validate_mathematics_reconciliation(
            file_a,
            hybrid,
            final_merge,
            discovery,
            missing_options_unknown,
            architecture,
            mathematics,
            decisions,
            fileindex,
        )

    unsafe_auto_trade = final_merge + "\nPositive VRP means sell options.\n"
    with pytest.raises(ValueError, match="unsafe automatic VRP trade command"):
        coverage.validate_mathematics_reconciliation(
            file_a,
            hybrid,
            unsafe_auto_trade,
            discovery,
            options,
            architecture,
            mathematics,
            decisions,
            fileindex,
        )

def test_current_documents_pass_complete_governance_contract() -> None:
    coverage.validate_governance_docs(_fmr_rows())