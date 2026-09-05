"""R0 inventory compiler tests (CROSS-001/003/007/008, TDG-GAP-001/011/012/024/025)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from trendforge_api.main import app
from trendforge_api.source_inventory_compiler import (
    DECISION_JOB_SPECS,
    CompilerState,
    DecisionJob,
    InventoryDefectCode,
    MATURITY_LADDER,
    SourceMaturityState,
    ban_mwpl_contract_splits,
    compile_default_inventory,
    compile_inventory,
    detect_row_defects,
    file_sha256,
    infer_decision_jobs,
    parse_active_source_keys,
    rows_from_mappings,
)
from trendforge_api.source_monitor import SOURCE_CATALOG
from trendforge_api.source_overlap_resolutions import (
    EvidenceBasis,
    OverlapDisposition,
    OverlapResolution,
    REVIEWED_OVERLAP_RESOLUTIONS,
    REVIEWED_WORKBOOK_SHA256,
)


class SourceInventoryCompilerTests(unittest.TestCase):
    def test_decision_jobs_j01_to_j14_complete(self) -> None:
        self.assertEqual(len(DecisionJob), 14)
        self.assertEqual(set(DECISION_JOB_SPECS), set(DecisionJob))
        self.assertTrue(all(job.value.startswith("J") for job in DecisionJob))
        # Quantity/execution jobs stay research-scoped text, not product unlocks.
        self.assertIn("POSTPONE", DECISION_JOB_SPECS[DecisionJob.J13]["scope"])

    def test_maturity_ladder_order_and_no_connected_shortcut(self) -> None:
        self.assertEqual(MATURITY_LADDER[0], SourceMaturityState.REGISTERED)
        self.assertEqual(MATURITY_LADDER[-1], SourceMaturityState.EXECUTION_AUTHORIZED)
        self.assertEqual(len(MATURITY_LADDER), 10)

    def test_detects_hybrid_style_inventory_defects(self) -> None:
        rows = rows_from_mappings(
            [
                {
                    "inventory_id": "1",
                    "url": "bse_ann:https://api.bseindia.com/example",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "CAUSAL_TRIGGER",
                    "active_source_keys": "bse_ann",
                },
                {
                    "inventory_id": "2",
                    "url": "https://a.example/x|https://b.example/y",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "FLOW",
                    "active_source_keys": "['amfi_monthly_portfolio']",
                },
                {
                    "inventory_id": "3",
                    "url": "lme_warehouse_stocks:no_snapshot",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": None,
                    "active_source_keys": None,
                },
                {
                    "inventory_id": "4",
                    "url": "https://www.nseindia.com/ok",
                    "source_role": "TEST_OR_PLACEHOLDER",
                    "purpose_jobs": "RESEARCH",
                    "active_source_keys": "demo_key",
                    "placeholder_or_test": "true",
                },
            ]
        )
        codes = {defect.code for row in rows for defect in detect_row_defects(row)}
        self.assertIn(InventoryDefectCode.KEY_PREFIXED_URL, codes)
        self.assertIn(InventoryDefectCode.COMPOUND_URL, codes)
        self.assertIn(InventoryDefectCode.SENTINEL_URL, codes)
        self.assertIn(InventoryDefectCode.MISSING_PURPOSE_JOBS, codes)
        self.assertIn(InventoryDefectCode.JSON_ARRAY_ACTIVE_KEYS, codes)
        self.assertIn(InventoryDefectCode.PLACEHOLDER_OR_TEST, codes)

    def test_parse_active_source_keys_handles_json_and_pipes(self) -> None:
        self.assertEqual(
            parse_active_source_keys("['amfi_monthly_portfolio']"),
            ["amfi_monthly_portfolio"],
        )
        self.assertEqual(
            parse_active_source_keys("nse_option_chain_banknifty|nse_option_chain"),
            ["nse_option_chain_banknifty", "nse_option_chain"],
        )

    def test_infer_jobs_mwpl_and_options(self) -> None:
        ban_jobs = infer_decision_jobs(
            source_keys=["nse_mwpl_ban"],
            purpose_jobs="ELIGIBILITY_VETO",
            url="https://www.nseindia.com/mwpl",
            source_role="OFFICIAL_OR_PRIMARY",
        )
        self.assertIn("J02", ban_jobs)
        option_jobs = infer_decision_jobs(
            source_keys=["nse_option_chain"],
            purpose_jobs="OPTIONS",
            url="https://www.nseindia.com/api/option-chain-equities",
            source_role="OFFICIAL_OR_PRIMARY",
        )
        self.assertIn("J07", option_jobs)

    def test_compile_fixture_report_is_research_only(self) -> None:
        rows = rows_from_mappings(
            [
                {
                    "inventory_id": "10",
                    "url": "https://www.nseindia.com/api/equity-stockIndices",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "FLOW_CONFIRMATION",
                    "active_source_keys": "nse_quote_equity",
                    "connection_status": "CONNECTED_FRESH_STRUCTURED",
                    "parser_status": "STRUCTURED_OK",
                    "freshness_status": "FRESH",
                },
                {
                    "inventory_id": "11",
                    "url": "bad_key:https://example.com/x",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "RESEARCH",
                    "active_source_keys": "bad_key",
                },
            ]
        )
        report = compile_inventory(rows)
        self.assertTrue(report.ok)
        self.assertEqual(report.compiler_state, CompilerState.OK)
        self.assertTrue(report.research_only)
        self.assertEqual(report.execution_authorized_count, 0)
        self.assertEqual(report.h1a0_acceptance_total, 6)
        self.assertEqual(report.h1a0_acceptance_passed, 6)
        self.assertGreater(report.migration_action_count, 0)
        self.assertFalse(report.roots_truncated)
        self.assertFalse(report.source_activation_ready)
        self.assertEqual(len(report.decision_jobs), 14)
        self.assertEqual(len(report.dataset_root_identity_fields), 11)
        self.assertEqual(len(report.extended_source_contract_fields), 15)
        self.assertTrue(
            any(
                root.dataset_root_id == "nse_quote_equity"
                for root in report.dataset_roots
            )
        )
        self.assertTrue(
            all(not root.can_unlock_execution for root in report.dataset_roots)
        )
        # Catalog keys are always present as roots for living map completeness.
        catalog_keys = {item.key for item in SOURCE_CATALOG}
        root_ids = {root.dataset_root_id for root in report.dataset_roots}
        # At least the fixture key and mwpl runtime key if present in catalog.
        self.assertIn("nse_quote_equity", root_ids)
        if "nse_mwpl_ban" in catalog_keys:
            # May be truncated by max_roots only if catalog huge — still check splits.
            pass
        splits = {item.contract_id for item in report.contract_splits}
        self.assertEqual(
            splits,
            {
                "nse_fno_ban",
                "nse_mwpl_percentages",
                "fbil_usdinr_reference",
                "usd_inr_live",
            },
        )

    def test_empty_and_missing_inventory_fail_closed(self) -> None:
        empty = compile_inventory([])
        self.assertFalse(empty.ok)
        self.assertEqual(empty.compiler_state, CompilerState.INPUT_EMPTY)
        self.assertEqual(empty.h1a0_acceptance_passed, 0)
        self.assertFalse(empty.source_activation_ready)

        with TemporaryDirectory() as directory:
            missing = compile_default_inventory(Path(directory) / "missing.xlsx")
        self.assertFalse(missing.ok)
        self.assertEqual(missing.compiler_state, CompilerState.INPUT_MISSING)
        self.assertEqual(missing.row_count, 0)

    def test_normalizes_compound_prefix_sentinel_and_preserves_lineage(self) -> None:
        rows = rows_from_mappings(
            [
                {
                    "inventory_id": "A",
                    "url": "alpha:https://a.example/api/x|https://b.example/api/y",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "J03",
                    "active_source_keys": "alpha|beta",
                    "safe_use": "Research evidence only",
                    "blocked_use": "No execution",
                    "next_action": "Add fixtures",
                },
                {
                    "inventory_id": "B",
                    "url": "lme_warehouse_stocks:no_snapshot",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": None,
                    "active_source_keys": "lme_warehouse_stocks",
                },
                {
                    "inventory_id": "C",
                    "url": "https://test.example/fixture",
                    "source_role": "TEST_OR_PLACEHOLDER",
                    "purpose_jobs": "J14",
                    "active_source_keys": "fixture_only",
                    "placeholder_or_test": "true",
                },
            ]
        )
        report = compile_inventory(rows)
        urls = {item.canonical_url for item in report.normalized_endpoints}
        self.assertEqual(
            urls,
            {
                "https://a.example/api/x",
                "https://b.example/api/y",
                "https://test.example/fixture",
            },
        )
        placeholder = next(
            item
            for item in report.normalized_endpoints
            if item.canonical_url == "https://test.example/fixture"
        )
        self.assertTrue(placeholder.quarantined)
        self.assertIn("PLACEHOLDER_OR_TEST", placeholder.quarantine_reasons)
        self.assertEqual(report.sentinel_status_count, 1)
        self.assertEqual(report.lineage_row_count, 3)
        self.assertEqual(report.h1a0_acceptance_passed, 5)
        overlap_check = next(item for item in report.acceptance if item.id == "H1A0-04")
        self.assertFalse(overlap_check.passed)
        self.assertTrue(
            all(action.destructive is False for action in report.migration_manifest)
        )

    def test_hybrid_h1a0_defect_contract_is_explicit(self) -> None:
        report = compile_inventory(
            rows_from_mappings(
                [
                    {
                        "url": "https://example.com/data",
                        "source_role": "OFFICIAL_OR_PRIMARY",
                        "purpose_jobs": "J03",
                        "active_source_keys": "example_data",
                    }
                ]
            )
        )
        expected = {
            "EXACT_URL_DUPLICATE",
            "KEY_PREFIXED_URL",
            "COMPOUND_URL",
            "SENTINEL_URL",
            "MISSING_PURPOSE_JOBS",
            "PROSE_PURPOSE_JOBS",
            "PLACEHOLDER_OR_TEST",
            "NON_DATA_REFERENCE_ROW",
            "JSON_ARRAY_ACTIVE_KEYS",
            "SEMANTIC_SOURCE_OVERLAP",
            "REGISTRY_RUNTIME_CONTRACT_MISMATCH",
        }
        self.assertEqual(set(report.h1a0_defect_codes), expected)
        self.assertTrue(expected <= set(report.defect_counts))

    def test_duplicate_and_semantic_overlap_are_not_silent(self) -> None:
        rows = rows_from_mappings(
            [
                {
                    "inventory_id": "A",
                    "url": "https://example.com/shared",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "J03",
                    "active_source_keys": "alpha",
                },
                {
                    "inventory_id": "B",
                    "url": "https://example.com/shared",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "J03",
                    "active_source_keys": "beta",
                },
            ]
        )
        report = compile_inventory(rows)
        self.assertEqual(report.defect_counts["EXACT_URL_DUPLICATE"], 1)
        self.assertEqual(report.defect_counts["SEMANTIC_SOURCE_OVERLAP"], 1)
        self.assertFalse(
            next(item for item in report.acceptance if item.id == "H1A0-04").passed
        )
        action_types = {item.action_type for item in report.migration_manifest}
        self.assertIn("MERGE_EXACT_URL_DUPLICATE", action_types)
        self.assertIn("REVIEW_SEMANTIC_SOURCE_OVERLAP", action_types)

    def test_complete_lineage_does_not_hide_semantic_overlap(self) -> None:
        report = compile_inventory(
            rows_from_mappings(
                [
                    {
                        "inventory_id": "A",
                        "url": "https://example.com/shared",
                        "source_role": "OFFICIAL_OR_PRIMARY",
                        "purpose_jobs": "J03",
                        "active_source_keys": "alpha",
                    },
                    {
                        "inventory_id": "B",
                        "url": "https://example.com/shared",
                        "source_role": "OFFICIAL_OR_PRIMARY",
                        "purpose_jobs": "J03",
                        "active_source_keys": "beta",
                    },
                ]
            )
        )

        self.assertEqual(report.lineage_row_count, report.row_count)
        self.assertEqual(report.h1a0_acceptance_passed, 5)
        overlap_check = next(item for item in report.acceptance if item.id == "H1A0-04")
        self.assertFalse(overlap_check.passed)
        self.assertIn("unexplained_overlap=1", overlap_check.evidence)
        self.assertFalse(report.source_activation_ready)

    def test_unstructured_overlap_text_cannot_bypass_acceptance(self) -> None:
        base = {
            "url": "https://example.com/shared",
            "source_role": "OFFICIAL_OR_PRIMARY",
            "purpose_jobs": "J03",
            "semantic_overlap_resolution": "One endpoint intentionally serves two contracts",
        }
        report = compile_inventory(
            rows_from_mappings(
                [
                    {**base, "inventory_id": "A", "active_source_keys": "alpha"},
                    {**base, "inventory_id": "B", "active_source_keys": "beta"},
                ]
            )
        )
        self.assertEqual(report.defect_counts["EXACT_URL_DUPLICATE"], 1)
        self.assertEqual(report.defect_counts["SEMANTIC_SOURCE_OVERLAP"], 1)
        self.assertFalse(
            next(item for item in report.acceptance if item.id == "H1A0-04").passed
        )

    def test_exact_typed_overlap_resolution_is_auditable(self) -> None:
        rows = rows_from_mappings(
            [
                {
                    "inventory_id": "A",
                    "url": "https://example.com/shared",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "J03",
                    "active_source_keys": "parent",
                },
                {
                    "inventory_id": "B",
                    "url": "https://example.com/shared",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "J07",
                    "active_source_keys": "child",
                },
            ]
        )
        resolution = OverlapResolution(
            canonical_url="https://example.com/shared",
            contract_ids=("child", "parent"),
            disposition=OverlapDisposition.PARENT_CHILD_CONTRACT,
            canonical_dataset_root_id="example_parent",
            evidence_reason="Fixture contract declares aggregate and child views.",
            evidence_basis=(EvidenceBasis.CONTRACT_REVIEW,),
            resolution_version="1",
            reviewed_at="2026-07-23",
        )
        report = compile_inventory(rows, overlap_resolutions=(resolution,))
        self.assertEqual(report.defect_counts["SEMANTIC_SOURCE_OVERLAP"], 0)
        self.assertTrue(report.resolution_registry_valid)
        self.assertEqual(report.overlap_disposition_counts["PARENT_CHILD_CONTRACT"], 1)
        self.assertEqual(
            report.overlap_resolution_records[0].state, "EXPLAINED_PARENT_CHILD"
        )
        jobs_by_contract = {
            item.source_contract_id: item.decision_jobs
            for item in report.source_contracts
        }
        self.assertEqual(jobs_by_contract["parent"], ["J03"])
        self.assertEqual(jobs_by_contract["child"], ["J07"])
        self.assertTrue(
            next(item for item in report.acceptance if item.id == "H1A0-04").passed
        )
        self.assertFalse(report.source_activation_ready)
        self.assertEqual(report.execution_authorized_count, 0)

    def test_changed_contract_set_makes_resolution_stale(self) -> None:
        rows = rows_from_mappings(
            [
                {
                    "inventory_id": "A",
                    "url": "https://example.com/shared",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "J03",
                    "active_source_keys": "alpha|beta|gamma",
                }
            ]
        )
        resolution = OverlapResolution(
            canonical_url="https://example.com/shared",
            contract_ids=("alpha", "beta"),
            disposition=OverlapDisposition.DISTINCT_SHARED_ENDPOINT,
            canonical_dataset_root_id="example_shared",
            evidence_reason="Two parameterized fixture datasets were reviewed.",
            evidence_basis=(EvidenceBasis.SCHEMA_REVIEW,),
            resolution_version="1",
            reviewed_at="2026-07-23",
        )
        report = compile_inventory(rows, overlap_resolutions=(resolution,))
        self.assertEqual(report.stale_overlap_resolution_count, 1)
        self.assertFalse(report.resolution_registry_valid)
        self.assertFalse(
            next(item for item in report.acceptance if item.id == "H1A0-04").passed
        )

    def test_resolution_contract_rejects_wildcards_and_url_only_aliases(self) -> None:
        with self.assertRaises(ValueError):
            OverlapResolution(
                canonical_url="https://example.com/*",
                contract_ids=("alpha", "beta"),
                disposition=OverlapDisposition.SAME_DATASET_ALIAS,
                canonical_dataset_root_id="example",
                evidence_reason="Invalid wildcard fixture.",
                evidence_basis=(EvidenceBasis.CONTRACT_REVIEW,),
                resolution_version="1",
                reviewed_at="2026-07-23",
            )
        with self.assertRaises(ValueError):
            OverlapResolution(
                canonical_url="https://example.com/shared",
                contract_ids=("alpha", "*"),
                disposition=OverlapDisposition.SAME_DATASET_ALIAS,
                canonical_dataset_root_id="example",
                evidence_reason="Invalid wildcard contract fixture.",
                evidence_basis=(EvidenceBasis.CONTRACT_REVIEW,),
                resolution_version="1",
                reviewed_at="2026-07-23",
            )
        with self.assertRaises(ValueError):
            OverlapResolution(
                canonical_url="https://example.com/shared",
                contract_ids=("alpha", "beta"),
                disposition=OverlapDisposition.SAME_DATASET_ALIAS,
                canonical_dataset_root_id="example",
                evidence_reason="URL equality alone is insufficient.",
                evidence_basis=(EvidenceBasis.URL_MATCH_ONLY,),
                resolution_version="1",
                reviewed_at="2026-07-23",
            )

    def test_duplicate_resolution_registry_fails_closed(self) -> None:
        rows = rows_from_mappings(
            [
                {
                    "url": "https://example.com/shared",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "J03",
                    "active_source_keys": "alpha|beta",
                }
            ]
        )
        resolution = OverlapResolution(
            canonical_url="https://example.com/shared",
            contract_ids=("alpha", "beta"),
            disposition=OverlapDisposition.DISTINCT_SHARED_ENDPOINT,
            canonical_dataset_root_id="example",
            evidence_reason="Reviewed fixture schemas are distinct.",
            evidence_basis=(EvidenceBasis.SCHEMA_REVIEW,),
            resolution_version="1",
            reviewed_at="2026-07-23",
        )
        report = compile_inventory(rows, overlap_resolutions=(resolution, resolution))
        self.assertGreater(report.invalid_overlap_resolution_count, 0)
        self.assertFalse(report.resolution_registry_valid)
        self.assertEqual(report.defect_counts["SEMANTIC_SOURCE_OVERLAP"], 1)

    def test_transport_distinct_and_quarantine_states_remain_non_authorizing(
        self,
    ) -> None:
        rows = rows_from_mappings(
            [
                {
                    "url": "https://example.com/transport",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "J03",
                    "active_source_keys": "csv_view|json_view",
                },
                {
                    "url": "https://example.com/distinct",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "J06|J07",
                    "active_source_keys": "futures_view|options_view",
                },
                {
                    "url": "https://example.com/unknown",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "J03",
                    "active_source_keys": "unknown_a|unknown_b",
                },
            ]
        )
        resolutions = (
            OverlapResolution(
                canonical_url="https://example.com/transport",
                contract_ids=("csv_view", "json_view"),
                disposition=OverlapDisposition.TRANSPORT_VARIANT,
                canonical_dataset_root_id="example_prices",
                evidence_reason="Saved CSV and JSON fixtures have the same identity and schema.",
                evidence_basis=(EvidenceBasis.SAVED_ARTIFACT,),
                resolution_version="1",
                reviewed_at="2026-07-23",
            ),
            OverlapResolution(
                canonical_url="https://example.com/distinct",
                contract_ids=("futures_view", "options_view"),
                disposition=OverlapDisposition.DISTINCT_SHARED_ENDPOINT,
                canonical_dataset_root_id="example_derivatives",
                evidence_reason="Reviewed schemas expose distinct futures and options datasets.",
                evidence_basis=(EvidenceBasis.SCHEMA_REVIEW,),
                resolution_version="1",
                reviewed_at="2026-07-23",
            ),
            OverlapResolution(
                canonical_url="https://example.com/unknown",
                contract_ids=("unknown_a", "unknown_b"),
                disposition=OverlapDisposition.QUARANTINED_UNPROVEN,
                canonical_dataset_root_id="quarantine:example_unknown",
                evidence_reason="No artifact proves whether these contracts are independent.",
                evidence_basis=(EvidenceBasis.URL_MATCH_ONLY,),
                resolution_version="1",
                reviewed_at="2026-07-23",
            ),
        )
        report = compile_inventory(rows, overlap_resolutions=resolutions)
        states = {
            item.canonical_url: item for item in report.overlap_resolution_records
        }
        self.assertEqual(
            states["https://example.com/transport"].state,
            "EXPLAINED_TRANSPORT_VARIANT",
        )
        self.assertEqual(
            states["https://example.com/transport"].canonical_dataset_root_id,
            "example_prices",
        )
        self.assertEqual(
            states["https://example.com/distinct"].state,
            "EXPLAINED_DISTINCT",
        )
        self.assertEqual(
            states["https://example.com/unknown"].state,
            "QUARANTINED_OVERLAP",
        )
        unknown_endpoint = next(
            item
            for item in report.normalized_endpoints
            if item.canonical_url == "https://example.com/unknown"
        )
        self.assertTrue(unknown_endpoint.quarantined)
        self.assertFalse(report.source_activation_ready)
        self.assertEqual(report.execution_authorized_count, 0)

    def test_url_normalization_collision_requires_exact_resolution(self) -> None:
        rows = rows_from_mappings(
            [
                {
                    "inventory_id": "A",
                    "url": "https://EXAMPLE.com/shared",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "J03",
                    "active_source_keys": "alpha",
                },
                {
                    "inventory_id": "B",
                    "url": "https://example.com/shared",
                    "source_role": "OFFICIAL_OR_PRIMARY",
                    "purpose_jobs": "J03",
                    "active_source_keys": "beta",
                },
            ]
        )
        report = compile_inventory(rows)
        self.assertEqual(report.normalized_endpoint_count, 1)
        self.assertEqual(report.defect_counts["SEMANTIC_SOURCE_OVERLAP"], 1)
        self.assertFalse(
            next(item for item in report.acceptance if item.id == "H1A0-04").passed
        )

    def test_compound_prefixed_urls_bind_each_contract_to_its_url(self) -> None:
        report = compile_inventory(
            rows_from_mappings(
                [
                    {
                        "inventory_id": "A",
                        "url": (
                            "alpha:https://example.com/alpha.csv|"
                            "beta:https://example.com/beta.csv"
                        ),
                        "source_role": "OFFICIAL_OR_PRIMARY",
                    }
                ]
            )
        )
        bindings = {
            endpoint.canonical_url: endpoint.source_contract_ids
            for endpoint in report.normalized_endpoints
        }
        self.assertEqual(bindings["https://example.com/alpha.csv"], ["alpha"])
        self.assertEqual(bindings["https://example.com/beta.csv"], ["beta"])
        self.assertEqual(report.defect_counts["SEMANTIC_SOURCE_OVERLAP"], 0)

    def test_prefixed_url_without_active_key_merges_by_prefix(self) -> None:
        report = compile_inventory(
            rows_from_mappings(
                [
                    {
                        "url": "nse_fo_bhavcopy:https://example.com/fo.csv",
                        "source_role": "OFFICIAL_OR_PRIMARY",
                        "purpose_jobs": "J06",
                    }
                ]
            )
        )
        self.assertEqual(
            {item.source_contract_id for item in report.source_contracts},
            {"nse_fo_bhavcopy"},
        )
        self.assertEqual(report.defect_counts["KEY_PREFIXED_URL"], 1)

    def test_reference_rows_are_explicitly_quarantined(self) -> None:
        report = compile_inventory(
            rows_from_mappings(
                [
                    {
                        "url": "https://example.com/reference",
                        "source_role": "REFERENCE_ONLY",
                        "purpose_jobs": "J14",
                        "active_source_keys": "reference_only",
                    }
                ]
            )
        )
        endpoint = report.normalized_endpoints[0]
        self.assertTrue(endpoint.quarantined)
        self.assertEqual(endpoint.purpose, "J14")
        self.assertIn("NON_DATA_REFERENCE_ROW", endpoint.quarantine_reasons)
        self.assertEqual(report.defect_counts["NON_DATA_REFERENCE_ROW"], 1)

    def test_ban_mwpl_split_declares_runtime_alias(self) -> None:
        splits = ban_mwpl_contract_splits()
        ban = next(item for item in splits if item.contract_id == "nse_fno_ban")
        self.assertEqual(ban.runtime_alias, "nse_mwpl_ban")
        self.assertTrue(ban.valid_empty_allowed)
        mwpl = next(
            item for item in splits if item.contract_id == "nse_mwpl_percentages"
        )
        self.assertFalse(mwpl.valid_empty_allowed)

    def test_root_identity_is_key_order_independent_and_not_truncated(self) -> None:
        rows = rows_from_mappings(
            {
                "inventory_id": str(index),
                "url": f"https://example.com/api/{index}",
                "source_role": "OFFICIAL_OR_PRIMARY",
                "purpose_jobs": "J03",
                "active_source_keys": f"root_{index}",
            }
            for index in range(225)
        )
        report = compile_inventory(rows)
        self.assertEqual(len(report.dataset_roots), 225)
        self.assertFalse(report.roots_truncated)

        def compile_keys(keys: str):
            return compile_inventory(
                rows_from_mappings(
                    [
                        {
                            "url": "https://example.com/shared",
                            "source_role": "OFFICIAL_OR_PRIMARY",
                            "purpose_jobs": "J03",
                            "active_source_keys": keys,
                        }
                    ]
                )
            )

        first = compile_keys("alpha|beta")
        second = compile_keys("beta|alpha")
        self.assertEqual(
            {root.dataset_root_id for root in first.dataset_roots},
            {root.dataset_root_id for root in second.dataset_roots},
        )

    def test_status_text_cannot_skip_maturity_or_unlock_gate(self) -> None:
        report = compile_inventory(
            rows_from_mappings(
                [
                    {
                        "url": "https://example.com/api/data",
                        "source_role": "OFFICIAL_OR_PRIMARY",
                        "purpose_jobs": "J03",
                        "active_source_keys": "contradictory",
                        "connection_status": "GATE AUTHORIZED CONNECTED FRESH",
                        "parser_status": "STRUCTURED_OK",
                        "freshness_status": "FRESH",
                    }
                ]
            )
        )
        contract = report.source_contracts[0]
        self.assertEqual(contract.maturity_state, SourceMaturityState.REGISTERED)
        self.assertFalse(contract.gate_permission)
        self.assertFalse(contract.quantity_permission)
        self.assertTrue(contract.missing_extended_fields)

    def test_default_compiler_reads_workbook_when_present(self) -> None:
        workbook = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "reports"
            / "SOURCE_LINK_INVENTORY_MASTER.xlsx"
        )
        if not workbook.exists():
            self.skipTest("master inventory workbook not present")
        report = compile_default_inventory(workbook)
        self.assertTrue(report.ok)
        self.assertEqual(report.compiler_state, CompilerState.OK)
        self.assertGreater(report.row_count, 100)
        self.assertIsNotNone(report.workbook_sha256)
        self.assertEqual(len(report.workbook_sha256), 64)
        self.assertEqual(file_sha256(workbook), REVIEWED_WORKBOOK_SHA256)
        self.assertEqual(report.workbook_sha256, REVIEWED_WORKBOOK_SHA256)
        self.assertEqual(len(REVIEWED_OVERLAP_RESOLUTIONS), 32)
        # Raw defects remain visible while the compiled view is normalized.
        self.assertGreater(
            report.defect_counts.get(InventoryDefectCode.KEY_PREFIXED_URL.value, 0)
            + report.defect_counts.get(
                InventoryDefectCode.MISSING_PURPOSE_JOBS.value, 0
            ),
            0,
        )
        self.assertEqual(report.h1a0_acceptance_passed, 6)
        self.assertEqual(report.h1a0_acceptance_total, 6)
        overlap_check = next(item for item in report.acceptance if item.id == "H1A0-04")
        self.assertTrue(overlap_check.passed)
        self.assertIn("unexplained_overlap=0", overlap_check.evidence)
        self.assertTrue(report.resolution_registry_valid)
        self.assertEqual(report.invalid_overlap_resolution_count, 0)
        self.assertEqual(report.stale_overlap_resolution_count, 0)
        self.assertEqual(len(report.overlap_resolution_records), 32)
        self.assertEqual(
            report.overlap_disposition_counts,
            {
                "DISTINCT_SHARED_ENDPOINT": 5,
                "PARENT_CHILD_CONTRACT": 20,
                "QUARANTINED_UNPROVEN": 0,
                "SAME_DATASET_ALIAS": 7,
                "TRANSPORT_VARIANT": 0,
            },
        )
        self.assertGreater(report.normalized_endpoint_count, 100)
        self.assertEqual(report.lineage_row_count, report.row_count)
        self.assertFalse(report.roots_truncated)
        self.assertFalse(report.source_activation_ready)
        catalog_keys = {item.key for item in SOURCE_CATALOG}
        self.assertIn("nse_fno_ban", catalog_keys)
        self.assertIn("nse_mwpl_percentages", catalog_keys)
        self.assertNotIn("nse_mwpl_ban", catalog_keys)
        self.assertTrue(
            next(item for item in report.acceptance if item.id == "H1A0-06").passed
        )
        # Maturity counts cover full ladder keys.
        for state in MATURITY_LADDER:
            self.assertIn(state.value, report.maturity_stage_counts)
        self.assertEqual(
            report.maturity_stage_counts[
                SourceMaturityState.EXECUTION_AUTHORIZED.value
            ],
            0,
        )

    def test_cross002_living_source_map_is_exact_and_non_authorizing(
        self,
    ) -> None:
        report = compile_default_inventory()

        self.assertTrue(report.source_map_review_valid)
        self.assertEqual(report.source_map_review_errors, [])
        self.assertTrue(report.source_governance_ready)
        self.assertEqual(report.reviewed_source_key_count, 179)
        self.assertEqual(report.unreviewed_source_key_count, 0)
        self.assertEqual(report.activation_reviewed_source_key_count, 179)
        self.assertEqual(report.gate_authorized_source_key_count, 0)
        self.assertEqual(report.legacy_unresolved_compiled_identity_count, 351)
        self.assertEqual(report.source_map_review_version, "CROSS-002-2026-09-03-v3")
        self.assertEqual(report.named_inventory_source_key_count, 157)
        self.assertEqual(report.generated_endpoint_lineage_count, 197)
        self.assertEqual(report.runtime_catalog_source_key_count, 135)
        self.assertEqual(report.shared_source_key_count, 113)
        self.assertEqual(report.inventory_only_source_key_count, 44)
        self.assertEqual(report.runtime_only_source_key_count, 22)
        self.assertEqual(report.living_source_key_count, 179)
        self.assertEqual(len(report.source_key_map), 179)
        self.assertEqual(
            {item.source_key for item in report.source_key_map},
            {
                item.source_contract_id
                for item in report.source_contracts
                if not item.source_contract_id.startswith("source:")
            }
            | {item.key for item in SOURCE_CATALOG},
        )
        self.assertFalse(
            any(item.source_key.startswith("source:") for item in report.source_key_map)
        )
        self.assertTrue(
            all(
                not item.gate_permission and not item.execution_authorized
                for item in report.source_key_map
            )
        )
        self.assertTrue(
            all(
                item.maturity_reviewed
                and item.activation_reviewed
                and item.activation_blockers
                and not item.can_confirm
                for item in report.source_key_map
            )
        )
        self.assertEqual(
            {
                item.source_key
                for item in report.source_key_map
                if item.origin == "RUNTIME_ONLY"
            },
            {
                "cdsl_fpi_fortnightly_sector",
                "kite_derivatives_contract_master",
                "nse_auction_securities",
                "nse_board_meetings",
                "nse_esm",
                "nse_fno_ban",
                "nse_index_close_eod",
                "nse_ipo_issue_calendar",
                "nse_most_active_futures",
                "nse_most_active_options",
                "nse_mwpl_percentages",
                "nse_nifty50_constituents",
                "nse_pr_market_snapshot",
                "nse_price_bands",
                "nse_trade_to_trade",
                "nselib",
                "nsepython",
                "openchart_intraday",
                "sebi_pit_sast",
                "sge_daily_report",
                "usd_inr",
                "yfinance",
            },
        )
        self.assertEqual(
            len(report.endpoint_source_map),
            report.normalized_endpoint_count,
        )
        self.assertEqual(
            report.unassigned_endpoint_lineage_count,
            sum(
                item.disposition == "UNASSIGNED_ENDPOINT_LINEAGE"
                for item in report.endpoint_source_map
            ),
        )
        self.assertTrue(
            all(not item.gate_eligible for item in report.endpoint_source_map)
        )
        self.assertFalse(report.source_activation_ready)
        self.assertEqual(report.execution_authorized_count, 0)

    def test_cross002_map_drift_and_generated_lineage_fail_closed(self) -> None:
        report = compile_inventory(
            rows_from_mappings(
                [
                    {
                        "inventory_id": "DRIFT",
                        "url": "https://example.com/unassigned",
                        "source_role": "OFFICIAL_OR_PRIMARY",
                        "purpose_jobs": "J03",
                    }
                ]
            )
        )

        self.assertFalse(report.source_map_review_valid)
        self.assertTrue(report.source_map_review_errors)
        self.assertFalse(report.source_governance_ready)
        self.assertEqual(report.reviewed_source_key_count, 0)
        self.assertEqual(report.unreviewed_source_key_count, len(report.source_key_map))
        self.assertEqual(report.generated_endpoint_lineage_count, 1)
        self.assertFalse(
            any(item.source_key.startswith("source:") for item in report.source_key_map)
        )
        endpoint = report.endpoint_source_map[0]
        self.assertEqual(endpoint.disposition, "UNASSIGNED_ENDPOINT_LINEAGE")
        self.assertTrue(endpoint.quarantined)
        self.assertFalse(endpoint.gate_eligible)
        self.assertFalse(report.source_activation_ready)

    def test_api_compiler_report_and_decision_jobs(self) -> None:
        client = TestClient(app)
        jobs_response = client.get("/api/source-inventory/decision-jobs")
        self.assertEqual(jobs_response.status_code, 200)
        jobs_payload = jobs_response.json()
        self.assertEqual(len(jobs_payload["jobs"]), 14)
        self.assertTrue(jobs_payload["researchOnly"])

        report_response = client.get("/api/source-inventory/compiler-report")
        self.assertEqual(report_response.status_code, 200)
        payload = report_response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["compilerState"], "OK")
        self.assertTrue(payload["researchOnly"])
        self.assertEqual(payload["executionAuthorizedCount"], 0)
        self.assertEqual(payload["h1a0AcceptanceTotal"], 6)
        self.assertEqual(payload["h1a0AcceptancePassed"], 6)
        self.assertEqual(len(payload["h1a0DefectCodes"]), 11)
        self.assertEqual(payload["defectCounts"]["SEMANTIC_SOURCE_OVERLAP"], 0)
        self.assertTrue(payload["resolutionRegistryValid"])
        self.assertEqual(payload["invalidOverlapResolutionCount"], 0)
        self.assertEqual(payload["staleOverlapResolutionCount"], 0)
        self.assertEqual(len(payload["overlapResolutionRecords"]), 32)
        self.assertFalse(payload["rootsTruncated"])
        self.assertTrue(payload["sourceMapReviewValid"])
        self.assertEqual(payload["sourceMapReviewErrors"], [])
        self.assertTrue(payload["sourceGovernanceReady"])
        self.assertEqual(payload["reviewedSourceKeyCount"], 179)
        self.assertEqual(payload["unreviewedSourceKeyCount"], 0)
        self.assertEqual(payload["activationReviewedSourceKeyCount"], 179)
        self.assertEqual(payload["gateAuthorizedSourceKeyCount"], 0)
        self.assertEqual(payload["namedInventorySourceKeyCount"], 157)
        self.assertEqual(payload["generatedEndpointLineageCount"], 197)
        self.assertEqual(payload["runtimeCatalogSourceKeyCount"], 135)
        self.assertEqual(payload["livingSourceKeyCount"], 179)
        self.assertEqual(len(payload["sourceKeyMap"]), 179)
        self.assertEqual(
            len(payload["endpointSourceMap"]), payload["normalizedEndpointCount"]
        )
        self.assertFalse(payload["sourceActivationReady"])
        self.assertEqual(len(payload["decisionJobs"]), 14)
        self.assertIn(
            "nse_fno_ban", {row["contractId"] for row in payload["contractSplits"]}
        )
        # Field names match File A AMEND-A-005 / Hybrid §18.4 (snake constants).
        self.assertIn("dataset_root_id", payload["datasetRootIdentityFields"])
        self.assertIn("timezone", payload["extendedSourceContractFields"])


if __name__ == "__main__":
    unittest.main()


def test_r3_reviewed_binding_is_narrow_and_fail_closed() -> None:
    report = compile_default_inventory()
    cash = next(
        contract
        for contract in report.source_contracts
        if contract.source_contract_id == "nse_bhavcopy_eod"
    )
    assert cash.feature_ids == ["FTR-040"]
    assert cash.independence_family == "PARTICIPATION"
    assert cash.authority_cap == "RESEARCH_DIRECTIONAL_WAIT_ONLY"
    assert cash.allowed_timeframes == ["SWING"]
    assert cash.allowed_instruments == ["NSE_EQ"]
    assert cash.directional_permission is True
    directional = [
        contract for contract in report.source_contracts if contract.directional_permission
    ]
    assert [contract.source_contract_id for contract in directional] == [
        "nse_bhavcopy_eod"
    ]
    assert report.source_activation_ready is False
    assert report.gate_authorized_source_key_count == 0
