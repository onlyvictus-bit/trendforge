from __future__ import annotations

import json
import sqlite3
import hashlib
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import (
    CommandBar,
    DataTrust,
    FreshnessState,
    HarmonicAlertRecord,
    HarmonicPatternResult,
    HarmonicPoint,
    MLScanCandidate,
    MLScanRun,
    MLScanStatus,
    OHLCVCandle,
    PairRow,
    RadarCandidate,
    ResearchCreate,
    ResearchRecord,
    SourceHealth,
    SourceParseResult,
    SourceRegistryRecord,
    SourceSnapshotRecord,
    SourceState,
)
from .parsers.source_freshness import is_data_date_fresh, stale_reason
from .corporate_actions import (
    AdjustmentIntegrityAssessment,
    ReconciledCorporateAction,
    apply_reconciled_actions_at_ingestion,
    assess_adjustment_integrity,
    reconcile_corporate_actions,
)
from .source_contracts import freshness_status_for, normalize_parser_status
from .risk_engine import RiskSettings
from .records import (
    AlertCreate,
    AlertRecord,
    JournalCreate,
    JournalOutcomeUpdate,
    JournalRecord,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = (
    Path(os.environ["TRENDFORGE_DB_PATH"]).expanduser().resolve()
    if os.getenv("TRENDFORGE_DB_PATH", "").strip()
    else DATA_DIR / "trendforge_research.db"
)
_INIT_LOCK = threading.RLock()
_INITIALIZED_DB_PATHS: set[Path] = set()


def _lastrowid(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise sqlite3.IntegrityError("SQLite insert completed without a row id")
    return int(cursor.lastrowid)


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _ensure_column(
    conn: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    columns = {
        row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _initialize_db() -> None:
    conn = connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                title TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                candidate_json TEXT NOT NULL,
                command_bar_json TEXT NOT NULL,
                source_health_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_research_symbol_created ON research_records(symbol, created_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ml_scan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_hash TEXT NOT NULL,
                trigger TEXT NOT NULL,
                candidate_count INTEGER NOT NULL,
                command_bar_json TEXT NOT NULL,
                source_health_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ml_scan_runs_created ON ml_scan_runs(created_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ml_scan_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                candidate_type TEXT NOT NULL,
                state TEXT NOT NULL,
                status_group TEXT NOT NULL,
                quality INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                outcome_label TEXT,
                false_screen_reason TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES ml_scan_runs(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ml_scan_candidates_symbol_created ON ml_scan_candidates(symbol, created_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ohlcv_candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                source TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                trust_level TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                bar_state TEXT NOT NULL DEFAULT 'COMPLETE',
                session_date TEXT,
                completeness REAL NOT NULL DEFAULT 1.0,
                adjustment_status TEXT NOT NULL DEFAULT 'UNKNOWN',
                adjustment_factor REAL NOT NULL DEFAULT 1.0,
                UNIQUE(symbol, timeframe, source, timestamp)
            )
            """
        )
        _ensure_column(
            conn, "ohlcv_candles", "bar_state", "TEXT NOT NULL DEFAULT 'COMPLETE'"
        )
        _ensure_column(conn, "ohlcv_candles", "session_date", "TEXT")
        _ensure_column(
            conn, "ohlcv_candles", "completeness", "REAL NOT NULL DEFAULT 1.0"
        )
        _ensure_column(
            conn,
            "ohlcv_candles",
            "adjustment_status",
            "TEXT NOT NULL DEFAULT 'UNKNOWN'",
        )
        _ensure_column(
            conn,
            "ohlcv_candles",
            "adjustment_factor",
            "REAL NOT NULL DEFAULT 1.0",
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timeframe_timestamp
            ON ohlcv_candles(symbol, timeframe, timestamp)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candle_quality_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                source TEXT NOT NULL,
                candle_timestamp TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                quality_state TEXT NOT NULL,
                bar_state TEXT NOT NULL,
                completeness REAL NOT NULL,
                issues_json TEXT NOT NULL,
                checked_at TEXT NOT NULL,
                UNIQUE(symbol, timeframe, source, candle_timestamp, content_hash)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_candle_quality_symbol_timestamp
            ON candle_quality_records(symbol, timeframe, candle_timestamp)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candle_adjustment_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                source TEXT NOT NULL,
                first_timestamp TEXT NOT NULL,
                last_timestamp TEXT NOT NULL,
                state TEXT NOT NULL,
                required_action_count INTEGER NOT NULL,
                event_ids_json TEXT NOT NULL,
                reason TEXT NOT NULL,
                assessment_hash TEXT NOT NULL UNIQUE,
                checked_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_adjustment_assessment_symbol_checked
            ON candle_adjustment_assessments(symbol, timeframe, checked_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candle_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                source TEXT NOT NULL,
                candle_timestamp TEXT NOT NULL,
                old_hash TEXT NOT NULL,
                new_hash TEXT NOT NULL,
                old_payload_json TEXT NOT NULL,
                new_payload_json TEXT NOT NULL,
                reason TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                UNIQUE(symbol, timeframe, source, candle_timestamp, old_hash, new_hash)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_candle_revisions_symbol_timestamp
            ON candle_revisions(symbol, timeframe, candle_timestamp)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_hash TEXT NOT NULL UNIQUE,
                symbol TEXT NOT NULL,
                layer TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                source_key TEXT,
                source_row_id INTEGER,
                source_date TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                trust_level TEXT NOT NULL,
                contribution REAL NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evidence_claims_symbol_date
            ON evidence_claims(symbol, source_date, layer)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS harmonic_lifecycle_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_key TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                state TEXT NOT NULL,
                event_at TEXT NOT NULL,
                price REAL,
                reason TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(pattern_key, sequence, state, event_at)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_harmonic_lifecycle_pattern_sequence
            ON harmonic_lifecycle_events(pattern_key, sequence)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS general_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dedupe_key TEXT NOT NULL UNIQUE,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                symbol TEXT,
                state TEXT NOT NULL,
                reason TEXT NOT NULL,
                risk_json TEXT NOT NULL,
                acknowledged INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_general_alerts_symbol_created
            ON general_alerts(symbol, created_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                mode TEXT NOT NULL,
                direction TEXT NOT NULL,
                decision_state TEXT NOT NULL,
                setup TEXT NOT NULL,
                quantity INTEGER,
                entry_price REAL,
                stop_price REAL,
                opened_at TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                outcome_state TEXT NOT NULL DEFAULT 'OPEN',
                exit_price REAL,
                closed_at TEXT,
                pnl REAL,
                r_multiple REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS safety_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                state TEXT NOT NULL,
                reason TEXT NOT NULL,
                active_positions INTEGER NOT NULL DEFAULT 0,
                realized_pnl REAL NOT NULL DEFAULT 0,
                unrealized_risk REAL NOT NULL DEFAULT 0,
                trade_attempted TEXT,
                system_action TEXT NOT NULL,
                override_attempted INTEGER NOT NULL DEFAULT 0,
                cooldown_until TEXT,
                next_allowed_action TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_safety_events_active_created ON safety_events(active, created_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS harmonic_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                direction TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                state TEXT NOT NULL,
                source_engine TEXT NOT NULL,
                points_json TEXT NOT NULL,
                prz_low REAL,
                prz_high REAL,
                invalidation_price REAL,
                target1 REAL,
                target2 REAL,
                confidence INTEGER NOT NULL,
                confirmation_state TEXT NOT NULL,
                final_state TEXT NOT NULL,
                reasons_json TEXT NOT NULL,
                gates_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_harmonic_symbol_timeframe_created
            ON harmonic_patterns(symbol, timeframe, created_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_registry (
                name TEXT PRIMARY KEY,
                adapter TEXT NOT NULL,
                authority TEXT NOT NULL,
                freshness TEXT NOT NULL,
                status TEXT NOT NULL,
                last_success_at TEXT,
                last_error TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS harmonic_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                message TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_harmonic_alerts_symbol_created
            ON harmonic_alerts(symbol, created_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                check_state TEXT NOT NULL,
                status_code INTEGER,
                content_hash TEXT,
                content_length INTEGER,
                last_modified TEXT,
                etag TEXT,
                raw_path TEXT,
                error TEXT,
                checked_at TEXT NOT NULL,
                previous_hash TEXT,
                changed INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source_snapshots_key_checked
            ON source_snapshots(source_key, checked_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_fetch_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT NOT NULL,
                attempt_group_id TEXT NOT NULL,
                url TEXT NOT NULL,
                fetcher TEXT NOT NULL,
                stage TEXT NOT NULL,
                result_state TEXT NOT NULL,
                status_code INTEGER,
                content_type TEXT,
                content_length INTEGER,
                duration_ms INTEGER,
                error TEXT,
                can_unlock_ready INTEGER NOT NULL DEFAULT 0,
                attempted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source_fetch_attempts_key_time
            ON source_fetch_attempts(source_key, attempted_at, id)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_inventory_audit_runs (
                run_id TEXT PRIMARY KEY,
                manifest_hash TEXT NOT NULL,
                total_rows INTEGER NOT NULL,
                selected_fetch_rows INTEGER NOT NULL,
                fetch_enabled INTEGER NOT NULL DEFAULT 0,
                browser_enabled INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                error TEXT,
                report_path TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source_inventory_audit_runs_started
            ON source_inventory_audit_runs(started_at, run_id)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_inventory_audit_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                inventory_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                canonical_url TEXT NOT NULL,
                hostname TEXT NOT NULL,
                source_role TEXT NOT NULL,
                allowed_jobs_json TEXT NOT NULL,
                provisional_family_id TEXT NOT NULL,
                duplicate_of_inventory_id INTEGER,
                disposition TEXT NOT NULL,
                fetch_state TEXT NOT NULL,
                status_code INTEGER,
                content_type TEXT,
                content_length INTEGER,
                content_hash TEXT,
                raw_path TEXT,
                scraper_state TEXT NOT NULL,
                discovered_urls_json TEXT NOT NULL,
                resolved_url TEXT,
                mapped_source_keys_json TEXT NOT NULL DEFAULT '[]',
                attempts_json TEXT NOT NULL DEFAULT '[]',
                normalization_state TEXT NOT NULL DEFAULT 'NOT_EVALUATED',
                payload_profile_json TEXT NOT NULL DEFAULT '{}',
                quality_issues_json TEXT NOT NULL DEFAULT '[]',
                error TEXT,
                can_unlock_ready INTEGER NOT NULL DEFAULT 0,
                audited_at TEXT NOT NULL,
                UNIQUE(run_id, inventory_id),
                FOREIGN KEY(run_id) REFERENCES source_inventory_audit_runs(run_id)
            )
            """
        )
        _ensure_column(conn, "source_inventory_audit_rows", "resolved_url", "TEXT")
        _ensure_column(
            conn,
            "source_inventory_audit_rows",
            "mapped_source_keys_json",
            "TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            conn,
            "source_inventory_audit_rows",
            "attempts_json",
            "TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            conn,
            "source_inventory_audit_rows",
            "normalization_state",
            "TEXT NOT NULL DEFAULT 'NOT_EVALUATED'",
        )
        _ensure_column(
            conn,
            "source_inventory_audit_rows",
            "payload_profile_json",
            "TEXT NOT NULL DEFAULT '{}'",
        )
        _ensure_column(
            conn,
            "source_inventory_audit_rows",
            "quality_issues_json",
            "TEXT NOT NULL DEFAULT '[]'",
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source_inventory_audit_rows_run
            ON source_inventory_audit_rows(run_id, inventory_id)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_parse_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT NOT NULL,
                snapshot_id INTEGER,
                parser_state TEXT NOT NULL,
                data_date TEXT,
                record_count INTEGER NOT NULL,
                summary TEXT NOT NULL,
                output_json TEXT NOT NULL,
                error TEXT,
                parsed_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source_parse_results_key_parsed
            ON source_parse_results(source_key, parsed_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_parser_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT NOT NULL,
                parser_name TEXT NOT NULL,
                parser_version TEXT NOT NULL,
                raw_snapshot_id INTEGER,
                data_date TEXT,
                source_published_at TEXT,
                parser_status TEXT NOT NULL,
                freshness_status TEXT NOT NULL,
                record_count INTEGER NOT NULL DEFAULT 0,
                schema_hash TEXT,
                content_hash TEXT,
                output_path TEXT,
                error_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source_parser_outputs_latest
            ON source_parser_outputs(source_key, data_date, created_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_freshness_status (
                source_key TEXT PRIMARY KEY,
                expected_frequency TEXT NOT NULL,
                latest_data_date TEXT,
                latest_parser_output_id INTEGER,
                is_fresh INTEGER NOT NULL DEFAULT 0,
                reason TEXT NOT NULL,
                checked_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gate_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                symbol TEXT,
                gate_key TEXT NOT NULL,
                decision TEXT NOT NULL,
                state TEXT NOT NULL,
                required_sources_json TEXT NOT NULL,
                reasons_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_gate_decisions_run_gate
            ON gate_decisions(run_id, gate_key, created_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_replacement_map (
                source_key TEXT PRIMARY KEY,
                source_role TEXT NOT NULL,
                rejected_reason TEXT NOT NULL,
                lost_function TEXT NOT NULL,
                safe_use TEXT NOT NULL,
                blocked_use TEXT NOT NULL,
                primary_replacement TEXT NOT NULL,
                secondary_replacement TEXT,
                can_unlock_ready INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_source_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                content_length INTEGER,
                raw_path TEXT,
                last_modified TEXT,
                etag TEXT,
                parser_state_after_parse TEXT,
                data_date TEXT,
                UNIQUE(source_key, content_hash)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mwpl_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT,
                symbol TEXT NOT NULL,
                mwpl_percent REAL,
                total_oi INTEGER,
                mwpl INTEGER,
                ban_status TEXT,
                is_banned INTEGER,
                oi_reliable INTEGER,
                parsed_at TEXT NOT NULL,
                UNIQUE(data_date, symbol)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cftc_cot_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                market TEXT NOT NULL,
                report_date TEXT,
                open_interest REAL,
                managed_money_long REAL,
                managed_money_short REAL,
                managed_money_net REAL,
                commercial_long REAL,
                commercial_short REAL,
                commercial_net REAL,
                non_reportable_long REAL,
                non_reportable_short REAL,
                non_reportable_net REAL,
                parsed_at TEXT NOT NULL,
                UNIQUE(market, report_date)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS macro_series_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                source_key TEXT NOT NULL,
                series_id TEXT NOT NULL,
                observation_date TEXT NOT NULL,
                value REAL NOT NULL,
                units TEXT NOT NULL,
                parsed_at TEXT NOT NULL,
                UNIQUE(source_key, observation_date)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_macro_series_date
            ON macro_series_observations(source_key, observation_date)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS amfi_nav_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                scheme_code TEXT NOT NULL,
                isin_growth TEXT,
                isin_reinvestment TEXT,
                scheme_name TEXT NOT NULL,
                fund_house TEXT,
                category TEXT,
                nav REAL NOT NULL,
                nav_date TEXT NOT NULL,
                parsed_at TEXT NOT NULL,
                UNIQUE(scheme_code, nav_date)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_amfi_nav_date
            ON amfi_nav_observations(nav_date, scheme_code)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS institutional_cash_flows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT NOT NULL,
                category TEXT NOT NULL,
                buy_value_crore REAL NOT NULL,
                sell_value_crore REAL NOT NULL,
                net_value_crore REAL NOT NULL,
                parsed_at TEXT NOT NULL,
                UNIQUE(data_date, category)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS option_chain_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                source_row_index INTEGER NOT NULL,
                data_date TEXT,
                symbol TEXT,
                expiry TEXT,
                strike REAL,
                option_type TEXT,
                open_interest INTEGER,
                oi_change INTEGER,
                volume INTEGER,
                iv REAL,
                last_price REAL,
                underlying_value REAL,
                observed_timestamp TEXT,
                parsed_at TEXT NOT NULL,
                UNIQUE(source_parse_id, source_row_index)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nse_pit_current_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                source_row_index INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                company TEXT,
                entity TEXT,
                transaction_type TEXT,
                security_type TEXT,
                quantity INTEGER,
                value REAL,
                post_shares INTEGER,
                post_holding_percent REAL,
                event_date TEXT NOT NULL,
                xbrl_link TEXT,
                parsed_at TEXT NOT NULL,
                UNIQUE(source_parse_id, source_row_index)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bse_cash_eod (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT NOT NULL,
                scrip_code TEXT NOT NULL,
                name TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                turnover REAL,
                parsed_at TEXT NOT NULL,
                UNIQUE(data_date, scrip_code)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nse_block_deal_live_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                source_row_index INTEGER NOT NULL,
                data_date TEXT,
                symbol TEXT NOT NULL,
                session TEXT,
                last_price REAL,
                quantity INTEGER,
                value REAL,
                order_type TEXT,
                observed_timestamp TEXT,
                parsed_at TEXT NOT NULL,
                UNIQUE(source_parse_id, source_row_index)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS surveillance_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                source_key TEXT NOT NULL,
                data_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                company TEXT,
                isin TEXT,
                measure TEXT NOT NULL,
                stage TEXT,
                surveillance_code TEXT,
                description TEXT,
                effective_date TEXT,
                parsed_at TEXT NOT NULL,
                UNIQUE(source_key, data_date, symbol, measure)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_surveillance_symbol_date
            ON surveillance_actions(symbol, data_date)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS promoter_pledge_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                reporting_date TEXT NOT NULL,
                company TEXT NOT NULL,
                broadcast_date TEXT,
                pledged_shares INTEGER,
                pledged_percent REAL,
                promoter_holding_percent REAL,
                promoter_holding_shares INTEGER,
                issued_shares INTEGER,
                symbol_mapping_status TEXT NOT NULL DEFAULT 'PENDING',
                parsed_at TEXT NOT NULL,
                UNIQUE(reporting_date, company)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS promoter_pledge_source_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER NOT NULL,
                source_row_index INTEGER NOT NULL,
                reporting_date TEXT NOT NULL,
                company TEXT NOT NULL,
                broadcast_date TEXT,
                pledged_shares INTEGER,
                pledged_percent REAL,
                promoter_holding_percent REAL,
                promoter_holding_shares INTEGER,
                issued_shares INTEGER,
                symbol_mapping_status TEXT NOT NULL DEFAULT 'PENDING',
                parsed_at TEXT NOT NULL,
                UNIQUE(source_parse_id, source_row_index)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_pledge_company_date
            ON promoter_pledge_snapshots(company, reporting_date)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS oi_spurt_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                latest_oi INTEGER,
                previous_oi INTEGER,
                oi_change INTEGER,
                oi_change_percent REAL,
                volume INTEGER,
                underlying_value REAL,
                previous_trading_date TEXT,
                parsed_at TEXT NOT NULL,
                UNIQUE(data_date, symbol)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_oi_spurt_symbol_date
            ON oi_spurt_snapshots(symbol, data_date)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nsdl_fpi_daily_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT NOT NULL,
                table_index INTEGER NOT NULL,
                row_index INTEGER NOT NULL,
                table_type TEXT NOT NULL,
                category TEXT,
                route_or_product TEXT,
                gross_purchases_crore REAL,
                gross_sales_crore REAL,
                net_investment_crore REAL,
                net_investment_usd_million REAL,
                conversion_usd_inr REAL,
                buy_contracts REAL,
                buy_value_crore REAL,
                sell_contracts REAL,
                sell_value_crore REAL,
                open_interest_contracts REAL,
                open_interest_value_crore REAL,
                cells_json TEXT NOT NULL,
                parsed_at TEXT NOT NULL,
                UNIQUE(source_parse_id, table_index, row_index)
            )
            """
        )
        for column, definition in (
            ("category", "TEXT"),
            ("route_or_product", "TEXT"),
            ("gross_purchases_crore", "REAL"),
            ("gross_sales_crore", "REAL"),
            ("net_investment_crore", "REAL"),
            ("net_investment_usd_million", "REAL"),
            ("conversion_usd_inr", "REAL"),
            ("buy_contracts", "REAL"),
            ("buy_value_crore", "REAL"),
            ("sell_contracts", "REAL"),
            ("sell_value_crore", "REAL"),
            ("open_interest_contracts", "REAL"),
            ("open_interest_value_crore", "REAL"),
        ):
            _ensure_column(conn, "nsdl_fpi_daily_rows", column, definition)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS eia_petroleum_weekly (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                source_key TEXT NOT NULL,
                data_date TEXT NOT NULL,
                metric_key TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                previous_week_date TEXT NOT NULL,
                year_ago_date TEXT NOT NULL,
                current_value REAL NOT NULL,
                previous_week_value REAL NOT NULL,
                weekly_change REAL NOT NULL,
                weekly_percent_change REAL NOT NULL,
                year_ago_value REAL NOT NULL,
                year_change REAL NOT NULL,
                year_percent_change REAL NOT NULL,
                units TEXT NOT NULL,
                parsed_at TEXT NOT NULL,
                UNIQUE(source_key, data_date, metric_key)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_eia_petroleum_date
            ON eia_petroleum_weekly(data_date, metric_key)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wgc_gold_oi_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                venue TEXT NOT NULL,
                observation_date TEXT NOT NULL,
                open_interest_usd_bn REAL NOT NULL,
                frequency TEXT NOT NULL,
                units TEXT NOT NULL,
                parsed_at TEXT NOT NULL,
                UNIQUE(venue, observation_date)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_wgc_gold_oi_date
            ON wgc_gold_oi_observations(observation_date, venue)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wgc_gold_etf_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                source_key TEXT NOT NULL,
                dataset TEXT NOT NULL,
                period TEXT NOT NULL,
                observation_date TEXT NOT NULL,
                region TEXT NOT NULL,
                value REAL NOT NULL,
                units TEXT NOT NULL,
                gold_price_usd_oz REAL,
                is_derived INTEGER NOT NULL DEFAULT 0,
                parsed_at TEXT NOT NULL,
                UNIQUE(dataset, period, observation_date, region)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_wgc_gold_etf_date
            ON wgc_gold_etf_observations(dataset, observation_date, region)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sge_daily_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                trade_date TEXT NOT NULL,
                contract TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                change REAL,
                change_percent REAL,
                weighted_average_price REAL,
                volume_kg REAL,
                amount_cny REAL,
                open_interest_lots INTEGER,
                direction TEXT,
                delivery_volume_lots INTEGER,
                parsed_at TEXT NOT NULL,
                UNIQUE(trade_date, contract)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sge_daily_date
            ON sge_daily_observations(trade_date, contract)
            """
        )
        for column, definition in (
            ("contract_market_code", "TEXT"),
            ("swap_dealer_long", "REAL"),
            ("swap_dealer_short", "REAL"),
            ("swap_dealer_net", "REAL"),
            ("other_reportable_long", "REAL"),
            ("other_reportable_short", "REAL"),
            ("other_reportable_net", "REAL"),
        ):
            _ensure_column(conn, "cftc_cot_positions", column, definition)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cftc_cot_features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market TEXT NOT NULL,
                contract_market_code TEXT,
                report_date TEXT NOT NULL,
                feature_version TEXT NOT NULL,
                observation_count INTEGER NOT NULL,
                position_state TEXT NOT NULL,
                crowding_state TEXT NOT NULL,
                position_price_divergence TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                computed_at TEXT NOT NULL,
                UNIQUE(market, report_date, feature_version)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cftc_features_market_date ON cftc_cot_features(market, report_date DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS participant_oi_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT,
                participant TEXT NOT NULL,
                futures_long_oi REAL,
                futures_short_oi REAL,
                futures_net_oi REAL,
                options_long_oi REAL,
                options_short_oi REAL,
                options_net_oi REAL,
                total_net_oi REAL,
                parsed_at TEXT NOT NULL,
                UNIQUE(data_date, participant)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bulk_block_deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT,
                symbol TEXT NOT NULL,
                deal_type TEXT,
                buyer TEXT,
                seller TEXT,
                quantity INTEGER,
                price REAL,
                value REAL,
                close_price REAL,
                premium_pct REAL,
                deal_mode TEXT,
                parsed_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS amfi_scheme_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                disclosure_month TEXT,
                amc TEXT,
                scheme TEXT,
                isin TEXT,
                stock TEXT NOT NULL,
                quantity INTEGER,
                market_value REAL,
                percent_aum REAL,
                parsed_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_amfi_holding_identity
            ON amfi_scheme_holdings(disclosure_month, amc, scheme, isin, stock)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS amfi_stock_deltas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disclosure_month TEXT,
                stock TEXT NOT NULL,
                isin TEXT,
                schemes_added INTEGER DEFAULT 0,
                schemes_reduced INTEGER DEFAULT 0,
                schemes_exited INTEGER DEFAULT 0,
                net_quantity_change INTEGER DEFAULT 0,
                parsed_at TEXT NOT NULL,
                UNIQUE(disclosure_month, stock)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS amfi_scheme_exposure_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                source_row_index INTEGER NOT NULL,
                quarter_date TEXT NOT NULL,
                quarter_name TEXT,
                mf_id TEXT NOT NULL,
                amc TEXT,
                scheme_id TEXT NOT NULL,
                scheme TEXT NOT NULL,
                isin TEXT,
                company_name TEXT NOT NULL,
                security_type TEXT,
                market_value REAL,
                market_value_percentage REAL,
                parsed_at TEXT NOT NULL,
                UNIQUE(source_parse_id, source_row_index)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_amfi_exposure_isin_quarter
            ON amfi_scheme_exposure_rows(isin, quarter_date)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mcx_bhavcopy_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT,
                symbol TEXT NOT NULL,
                expiry TEXT,
                close_price REAL,
                volume INTEGER,
                open_interest INTEGER,
                oi_change INTEGER,
                parsed_at TEXT NOT NULL,
                UNIQUE(data_date, symbol, expiry)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fo_derivatives_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT,
                symbol TEXT NOT NULL,
                instrument TEXT,
                expiry TEXT,
                strike REAL,
                option_type TEXT,
                close_price REAL,
                previous_close REAL,
                underlying_price REAL,
                basis REAL,
                basis_percent REAL,
                open_interest INTEGER,
                oi_change INTEGER,
                volume INTEGER,
                oi_quadrant TEXT,
                parsed_at TEXT NOT NULL,
                UNIQUE(data_date, symbol, instrument, expiry, strike, option_type)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS slb_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT,
                symbol TEXT NOT NULL,
                open_positions INTEGER,
                volume INTEGER,
                borrow_rate REAL,
                turnover REAL,
                pressure TEXT,
                parsed_at TEXT NOT NULL,
                UNIQUE(data_date, symbol)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS corporate_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                source_key TEXT NOT NULL,
                data_date TEXT,
                symbol TEXT,
                company TEXT,
                action_type TEXT,
                announcement_date TEXT,
                ex_date TEXT,
                record_date TEXT,
                start_date TEXT,
                end_date TEXT,
                offer_price REAL,
                quantity INTEGER,
                action_class TEXT,
                ratio_numerator REAL,
                ratio_denominator REAL,
                cash_amount REAL,
                adjustment_factor REAL,
                predecessor_symbol TEXT,
                successor_symbol TEXT,
                continuity_confirmed INTEGER,
                revision_status TEXT NOT NULL DEFAULT 'UNKNOWN',
                parsed_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nse_instruments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                company TEXT NOT NULL,
                series TEXT NOT NULL,
                listing_date TEXT,
                paid_up_value REAL,
                market_lot INTEGER,
                isin TEXT NOT NULL,
                face_value REAL,
                active INTEGER NOT NULL DEFAULT 1,
                parsed_at TEXT NOT NULL,
                UNIQUE(data_date, symbol, series)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nse_instruments_symbol_date ON nse_instruments(symbol, data_date DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nse_sector_membership (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                company TEXT NOT NULL,
                industry TEXT NOT NULL,
                series TEXT NOT NULL,
                isin TEXT NOT NULL,
                index_membership TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                parsed_at TEXT NOT NULL,
                UNIQUE(data_date, symbol, series, index_membership)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nse_sector_symbol_date ON nse_sector_membership(symbol, data_date DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_context_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                as_of TEXT NOT NULL,
                source_date TEXT NOT NULL,
                state TEXT NOT NULL,
                gate_outcome TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(as_of, source_date, state, gate_outcome)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nse_cash_eod (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                trade_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                series TEXT NOT NULL,
                isin TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL NOT NULL,
                previous_close REAL NOT NULL,
                volume INTEGER NOT NULL DEFAULT 0,
                traded_value REAL NOT NULL DEFAULT 0,
                trade_count INTEGER NOT NULL DEFAULT 0,
                advance_state TEXT NOT NULL,
                parsed_at TEXT NOT NULL,
                UNIQUE(trade_date, symbol, series)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nse_cash_eod_date_series ON nse_cash_eod(trade_date DESC, series)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nse_index_eod (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                index_name TEXT NOT NULL,
                index_date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL NOT NULL,
                points_change REAL NOT NULL DEFAULT 0,
                change_percent REAL NOT NULL DEFAULT 0,
                volume INTEGER NOT NULL DEFAULT 0,
                turnover_crore REAL NOT NULL DEFAULT 0,
                parsed_at TEXT NOT NULL,
                UNIQUE(index_name, index_date)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nse_index_eod_name_date ON nse_index_eod(index_name, index_date DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sector_context_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sector TEXT NOT NULL,
                direction TEXT NOT NULL,
                as_of TEXT NOT NULL,
                source_date TEXT NOT NULL,
                rrg_state TEXT NOT NULL,
                gate_outcome TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(sector, direction, as_of, source_date)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exchange_calendar_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                exchange TEXT NOT NULL,
                segment TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                state TEXT NOT NULL,
                description TEXT NOT NULL,
                weekday TEXT,
                morning_session TEXT,
                evening_session TEXT,
                data_date TEXT NOT NULL,
                parsed_at TEXT NOT NULL,
                UNIQUE(exchange, segment, trading_date, state, data_date)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_exchange_calendar_lookup
            ON exchange_calendar_days(exchange, segment, trading_date, data_date DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exchange_calendar_coverage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                exchange TEXT NOT NULL,
                segment TEXT NOT NULL,
                calendar_year INTEGER NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT NOT NULL,
                data_date TEXT NOT NULL,
                parsed_at TEXT NOT NULL,
                UNIQUE(exchange, segment, calendar_year, data_date)
            )
            """
        )
        _ensure_column(conn, "corporate_events", "adjustment_factor", "REAL")
        _ensure_column(conn, "corporate_events", "predecessor_symbol", "TEXT")
        _ensure_column(conn, "corporate_events", "successor_symbol", "TEXT")
        _ensure_column(conn, "corporate_events", "continuity_confirmed", "INTEGER")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bse_offer_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_source_key TEXT NOT NULL,
                company_id TEXT,
                offer_type TEXT NOT NULL,
                phase TEXT NOT NULL,
                document_url TEXT NOT NULL,
                published_date TEXT,
                revision_status TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                status_code INTEGER,
                content_hash TEXT NOT NULL,
                raw_path TEXT NOT NULL,
                parser_state TEXT NOT NULL,
                data_date TEXT,
                payload_json TEXT NOT NULL,
                error TEXT,
                UNIQUE(document_url, content_hash)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_bse_offer_documents_source_date
            ON bse_offer_documents(parent_source_key, data_date, fetched_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS corporate_offer_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                parent_source_key TEXT NOT NULL,
                company_id TEXT,
                symbol TEXT,
                scrip_code TEXT,
                isin TEXT NOT NULL,
                company TEXT NOT NULL,
                offer_type TEXT NOT NULL,
                phase TEXT NOT NULL,
                announcement_date TEXT,
                record_date TEXT,
                start_date TEXT,
                end_date TEXT,
                offer_price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                consideration REAL,
                acquirers_json TEXT NOT NULL,
                revision_status TEXT NOT NULL,
                document_url TEXT NOT NULL,
                document_hash TEXT NOT NULL,
                data_date TEXT NOT NULL,
                parsed_at TEXT NOT NULL,
                is_current INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(document_id) REFERENCES bse_offer_documents(id),
                UNIQUE(parent_source_key, company_id, offer_type, phase, document_hash)
            )
            """
        )
        _ensure_column(
            conn,
            "corporate_offer_events",
            "is_current",
            "INTEGER NOT NULL DEFAULT 1",
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_corporate_offer_symbol_date
            ON corporate_offer_events(symbol, data_date, parsed_at)
            """
        )
        _ensure_column(conn, "corporate_events", "action_class", "TEXT")
        _ensure_column(conn, "corporate_events", "ratio_numerator", "REAL")
        _ensure_column(conn, "corporate_events", "ratio_denominator", "REAL")
        _ensure_column(conn, "corporate_events", "cash_amount", "REAL")
        _ensure_column(
            conn,
            "corporate_events",
            "revision_status",
            "TEXT NOT NULL DEFAULT 'UNKNOWN'",
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sebi_disclosures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_parse_id INTEGER,
                data_date TEXT,
                symbol TEXT,
                isin TEXT,
                entity TEXT NOT NULL,
                relationship TEXT,
                transaction_type TEXT,
                event_date TEXT,
                disclosure_date TEXT,
                quantity INTEGER,
                price REAL,
                pre_holding REAL,
                post_holding REAL,
                parsed_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scanner_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_hash TEXT NOT NULL,
                universe TEXT NOT NULL,
                trigger TEXT NOT NULL,
                status TEXT NOT NULL,
                paused_reason TEXT,
                candidate_count INTEGER DEFAULT 0,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                gate_readiness_json TEXT NOT NULL,
                source_health_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scanner_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                candidate_type TEXT,
                final_state TEXT NOT NULL,
                status_group TEXT NOT NULL,
                quality_score REAL,
                gate_ratio REAL,
                payload_json TEXT NOT NULL,
                outcome_label TEXT,
                false_screen_reason TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_risk_settings (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                settings_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                source TEXT,
                data_cutoff TEXT,
                validation_method TEXT NOT NULL,
                observation_count INTEGER NOT NULL,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduler_config (
                scheduler_key TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                interval_seconds INTEGER NOT NULL,
                universe TEXT NOT NULL,
                fetch INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_validation_runs_symbol_created
            ON validation_runs(symbol, timeframe, created_at)
            """
        )
        seed_source_replacement_map_rows(conn)
        applied_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0001_existing_baseline",
                "Existing TrendForge SQLite schema baseline",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0010_nse_instrument_universe",
                "Point-in-time NSE equity identity and Nifty 500 industry membership",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0011_market_sector_context",
                "Point-in-time market regime and sector RRG context snapshots",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0012_nse_trading_calendar",
                "Official NSE holiday coverage and explicit special-session calendar",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0013_nse_official_market_context_inputs",
                "Official NSE cash breadth and all-index EOD history",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0014_source_fetch_attempt_ledger",
                "Per-URL source resolution results including optional VYOM discovery",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0015_source_inventory_audit",
                "Complete URL inventory audit runs, canonical duplicates and bounded fetch results",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0016_fred_macro_series",
                "Normalized FRED real-yield and broad-dollar delayed context observations",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0017_eia_petroleum_weekly",
                "Normalized EIA weekly petroleum stock context for MCX crude",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0018_gold_physical_context",
                "Normalized WGC futures OI, WGC ETF and SGE daily physical-market context",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0009_safety_state_events",
                "Persisted panic, cooldown, recovery and safety-event audit ledger",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0008_corporate_reconstruction_terms",
                "Explicit merger and demerger reconstruction terms with symbol lineage",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0007_bse_offer_xbrl_lineage",
                "Versioned BSE offer XBRL documents and normalized offer terms",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0002_candle_quality_lineage",
                "Candle quality and revision lineage",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0003_normalized_evidence_claims",
                "Normalized causal evidence claim persistence",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0004_harmonic_lifecycle_events",
                "Chronological harmonic lifecycle transition events",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0005_alerts_and_manual_journal",
                "General alerts and manual journal outcome records",
                applied_at,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0006_corporate_action_adjustment_lineage",
                "Corporate action reconciliation and candle adjustment lineage",
                applied_at,
            ),
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS selection_scan_runs (
                run_id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                as_of TEXT NOT NULL,
                persisted_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_selection_scan_runs_persisted ON selection_scan_runs(persisted_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS selection_candidates (
                run_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                state TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (run_id, candidate_id),
                FOREIGN KEY (run_id) REFERENCES selection_scan_runs(run_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_selection_candidates_symbol ON selection_candidates(symbol, run_id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS selection_state_events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                prior_state TEXT NOT NULL,
                resulting_state TEXT NOT NULL,
                accepted INTEGER NOT NULL,
                reason_code TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES selection_scan_runs(run_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_selection_state_events_candidate ON selection_state_events(candidate_id, sequence)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0007_selection_r1_runs",
                "R1 selection scan runs, candidate projection and append-only state events",
                applied_at,
            ),
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_source_results (
                result_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                artifact_hash TEXT,
                data_date TEXT,
                received_at TEXT NOT NULL,
                available_at TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                state TEXT NOT NULL,
                freshness TEXT NOT NULL,
                record_count INTEGER NOT NULL,
                last_good_status TEXT,
                payload_json TEXT NOT NULL,
                persisted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cash_source_results_persisted ON cash_source_results(persisted_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_staging_rows (
                result_id TEXT NOT NULL,
                row_index INTEGER NOT NULL,
                trade_date TEXT,
                symbol TEXT,
                series TEXT,
                isin TEXT,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (result_id, row_index),
                FOREIGN KEY (result_id) REFERENCES cash_source_results(result_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cash_staging_rows_symbol ON cash_staging_rows(symbol, trade_date)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0008_cash_a1_staging",
                "A1 cash SourceResult plus source-specific staging rows",
                applied_at,
            ),
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_identity_runs (
                batch_id TEXT PRIMARY KEY,
                staging_result_id TEXT,
                calendar_state TEXT NOT NULL,
                restriction_json TEXT NOT NULL,
                fact_count INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                persisted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cash_identity_runs_persisted ON cash_identity_runs(persisted_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_normalized_facts (
                batch_id TEXT NOT NULL,
                fact_id TEXT NOT NULL,
                instrument_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                series TEXT,
                public_state TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (batch_id, fact_id),
                FOREIGN KEY (batch_id) REFERENCES cash_identity_runs(batch_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cash_normalized_facts_symbol ON cash_normalized_facts(symbol, batch_id)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0009_cash_a2_identity",
                "A2 cash NormalizedFact identity and S0/S1 safety",
                applied_at,
            ),
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_discovery_runs (
                batch_id TEXT PRIMARY KEY,
                identity_batch_id TEXT,
                profile_id TEXT NOT NULL,
                eligible_count INTEGER NOT NULL,
                watch_count INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                persisted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cash_discovery_runs_persisted ON cash_discovery_runs(persisted_at)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0010_cash_a3_discovery",
                "A3 cash-EOD discovery WATCH reasons",
                applied_at,
            ),
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_raw_session_bars (
                bar_id TEXT PRIMARY KEY,
                instrument_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                artifact_hash TEXT NOT NULL,
                series_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                UNIQUE(instrument_id, trade_date, artifact_hash)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cash_raw_session_symbol_date ON cash_raw_session_bars(symbol, trade_date)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_ca_vintages (
                event_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                action_class TEXT NOT NULL,
                effective_date TEXT NOT NULL,
                available_at TEXT NOT NULL,
                revision_id TEXT NOT NULL,
                adjustment_factor REAL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_history_runs (
                batch_id TEXT PRIMARY KEY,
                identity_batch_id TEXT,
                decision_at TEXT NOT NULL,
                raw_bar_count INTEGER NOT NULL,
                row_count INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                persisted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cash_history_runs_persisted ON cash_history_runs(persisted_at)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0011_cash_a4_history",
                "A4 raw cash session bars, CA vintages and history runs",
                applied_at,
            ),
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_context_runs (
                batch_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                persisted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fo_enrichment_runs (
                batch_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                persisted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_use_matrices (
                matrix_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                persisted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mwpl_assessments (
                assessment_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                persisted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_rank_runs (
                batch_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                persisted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
            (
                "0012_cash_a5_c1",
                "A5 context, A6 FO enrich, C0 use matrix, B MWPL, C1 rank",
                applied_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    seed_source_registry()


def init_db() -> None:
    db_key = DB_PATH.expanduser().resolve()
    with _INIT_LOCK:
        if db_key in _INITIALIZED_DB_PATHS and db_key.exists():
            return
        _initialize_db()
        _INITIALIZED_DB_PATHS.add(db_key)


def encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def decode_json(value: str) -> Any:
    return json.loads(value)


def list_schema_migrations() -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT version, description, applied_at FROM schema_migrations ORDER BY version"
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def save_evidence_claims(symbol: str, claims: list[dict[str, Any]]) -> int:
    init_db()
    normalized_symbol = symbol.upper().strip()
    conn = connect()
    try:
        inserted = 0
        for claim in claims:
            payload_json = encode_json(claim)
            claim_hash = hashlib.sha256(
                f"{normalized_symbol}:{payload_json}".encode("utf-8")
            ).hexdigest()
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO evidence_claims (
                    claim_hash, symbol, layer, signal_type, source_key, source_row_id,
                    source_date, observed_at, trust_level, contribution, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim_hash,
                    normalized_symbol,
                    claim.get("layer"),
                    claim.get("signalType"),
                    claim.get("sourceKey"),
                    claim.get("sourceRowId"),
                    claim.get("sourceDate"),
                    claim.get("observedAt"),
                    claim.get("trustLevel"),
                    claim.get("contribution"),
                    payload_json,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            inserted += max(cursor.rowcount, 0)
        conn.commit()
        return inserted
    finally:
        conn.close()


def list_evidence_claims(
    *, symbol: str | None = None, limit: int = 500
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if symbol:
            rows = conn.execute(
                """
                SELECT * FROM evidence_claims WHERE symbol = ?
                ORDER BY source_date DESC, id DESC LIMIT ?
                """,
                (symbol.upper().strip(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM evidence_claims ORDER BY source_date DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["payload"] = decode_json(item.pop("payload_json"))
        output.append(item)
    return output


def save_harmonic_lifecycle_events(result: dict[str, Any]) -> int:
    init_db()
    conn = connect()
    try:
        inserted = 0
        for event in result.get("transitions", []):
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO harmonic_lifecycle_events (
                    pattern_key, symbol, timeframe, sequence, state, event_at,
                    price, reason, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.get("patternKey"),
                    result.get("symbol"),
                    result.get("timeframe"),
                    event.get("sequence"),
                    event.get("state"),
                    event.get("eventAt"),
                    event.get("price"),
                    event.get("reason"),
                    encode_json(event),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            inserted += max(cursor.rowcount, 0)
        conn.commit()
        return inserted
    finally:
        conn.close()


def list_harmonic_lifecycle_events(
    *, pattern_key: str | None = None, limit: int = 1000
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if pattern_key:
            rows = conn.execute(
                """
                SELECT * FROM harmonic_lifecycle_events WHERE pattern_key = ?
                ORDER BY sequence ASC, event_at ASC, id ASC LIMIT ?
                """,
                (pattern_key, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM harmonic_lifecycle_events
                ORDER BY created_at DESC, id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def _row_to_alert(row: sqlite3.Row) -> AlertRecord:
    return AlertRecord(
        id=row["id"],
        alertType=row["alert_type"],
        severity=row["severity"],
        symbol=row["symbol"],
        state=row["state"],
        reason=row["reason"],
        risk=decode_json(row["risk_json"]),
        acknowledged=bool(row["acknowledged"]),
        createdAt=row["created_at"],
    )


def save_general_alert(alert: AlertCreate) -> AlertRecord:
    init_db()
    payload = alert.model_dump(mode="json", by_alias=True)
    dedupe_key = hashlib.sha256(encode_json(payload).encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    conn = connect()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO general_alerts (
                dedupe_key, alert_type, severity, symbol, state, reason,
                risk_json, acknowledged, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                dedupe_key,
                alert.alert_type,
                alert.severity,
                alert.symbol,
                alert.state,
                alert.reason,
                encode_json(alert.risk),
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM general_alerts WHERE dedupe_key = ?", (dedupe_key,)
        ).fetchone()
        if row is None:
            raise sqlite3.IntegrityError("general alert was not persisted")
        return _row_to_alert(row)
    finally:
        conn.close()


def list_general_alerts(
    *, symbol: str | None = None, acknowledged: bool | None = None, limit: int = 500
) -> list[AlertRecord]:
    init_db()
    conditions: list[str] = []
    values: list[Any] = []
    if symbol:
        conditions.append("UPPER(symbol) = ?")
        values.append(symbol.upper().strip())
    if acknowledged is not None:
        conditions.append("acknowledged = ?")
        values.append(int(acknowledged))
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    values.append(limit)
    conn = connect()
    try:
        rows = conn.execute(
            f"SELECT * FROM general_alerts {where} ORDER BY created_at DESC, id DESC LIMIT ?",
            values,
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_alert(row) for row in rows]


def acknowledge_general_alert(alert_id: int) -> AlertRecord | None:
    init_db()
    conn = connect()
    try:
        conn.execute(
            "UPDATE general_alerts SET acknowledged = 1 WHERE id = ?", (alert_id,)
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM general_alerts WHERE id = ?", (alert_id,)
        ).fetchone()
        return _row_to_alert(row) if row is not None else None
    finally:
        conn.close()


def create_safety_event(
    *,
    event_type: str,
    state: str,
    reason: str,
    system_action: str,
    next_allowed_action: str,
    active_positions: int = 0,
    realized_pnl: float = 0,
    unrealized_risk: float = 0,
    trade_attempted: str | None = None,
    override_attempted: bool = False,
    cooldown_until: str | None = None,
    metadata: dict[str, Any] | None = None,
    active: bool = True,
    created_at: str | None = None,
) -> int:
    init_db()
    conn = connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO safety_events (
                event_type, state, reason, active_positions, realized_pnl,
                unrealized_risk, trade_attempted, system_action,
                override_attempted, cooldown_until, next_allowed_action,
                metadata_json, active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                state,
                reason,
                active_positions,
                realized_pnl,
                unrealized_risk,
                trade_attempted,
                system_action,
                int(override_attempted),
                cooldown_until,
                next_allowed_action,
                encode_json(metadata or {}),
                int(active),
                created_at or datetime.now(timezone.utc).isoformat(),
            ),
        )
        event_id = _lastrowid(cursor)
        conn.commit()
        return event_id
    finally:
        conn.close()


def list_safety_events(
    *, active: bool | None = None, limit: int = 500
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if active is None:
            rows = conn.execute(
                "SELECT * FROM safety_events ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM safety_events WHERE active = ?
                ORDER BY created_at DESC, id DESC LIMIT ?
                """,
                (int(active), limit),
            ).fetchall()
    finally:
        conn.close()
    output = []
    for row in rows:
        item = dict(row)
        item["active"] = bool(item["active"])
        item["override_attempted"] = bool(item["override_attempted"])
        item["metadata"] = decode_json(item.pop("metadata_json"))
        output.append(item)
    return output


def resolve_safety_event(event_id: int, *, resolved_at: str | None = None) -> bool:
    init_db()
    conn = connect()
    try:
        cursor = conn.execute(
            """
            UPDATE safety_events SET active = 0, resolved_at = ?
            WHERE id = ? AND active = 1
            """,
            (resolved_at or datetime.now(timezone.utc).isoformat(), event_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def _row_to_journal(row: sqlite3.Row) -> JournalRecord:
    return JournalRecord(
        id=row["id"],
        symbol=row["symbol"],
        mode=row["mode"],
        direction=row["direction"],
        decisionState=row["decision_state"],
        setup=row["setup"],
        quantity=row["quantity"],
        entryPrice=row["entry_price"],
        stopPrice=row["stop_price"],
        openedAt=row["opened_at"],
        notes=row["notes"],
        outcomeState=row["outcome_state"],
        exitPrice=row["exit_price"],
        closedAt=row["closed_at"],
        pnl=row["pnl"],
        rMultiple=row["r_multiple"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def save_journal_entry(payload: JournalCreate) -> JournalRecord:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    conn = connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO journal_entries (
                symbol, mode, direction, decision_state, setup, quantity,
                entry_price, stop_price, opened_at, notes, outcome_state,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
            """,
            (
                payload.symbol.upper().strip(),
                payload.mode,
                payload.direction,
                payload.decision_state,
                payload.setup,
                payload.quantity,
                payload.entry_price,
                payload.stop_price,
                payload.opened_at.isoformat(),
                payload.notes,
                now,
                now,
            ),
        )
        entry_id = _lastrowid(cursor)
        conn.commit()
        row = conn.execute(
            "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if row is None:
            raise sqlite3.IntegrityError("journal entry was not persisted")
        return _row_to_journal(row)
    finally:
        conn.close()


def update_journal_outcome(
    entry_id: int, payload: JournalOutcomeUpdate
) -> JournalRecord | None:
    init_db()
    conn = connect()
    try:
        existing = conn.execute(
            "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if existing is None:
            return None
        if payload.closed_at and payload.closed_at < datetime.fromisoformat(
            existing["opened_at"]
        ):
            raise ValueError("closedAt cannot be earlier than openedAt")
        conn.execute(
            """
            UPDATE journal_entries
            SET outcome_state = ?, exit_price = ?, closed_at = ?, pnl = ?, r_multiple = ?,
                notes = COALESCE(?, notes), updated_at = ?
            WHERE id = ?
            """,
            (
                payload.outcome_state,
                payload.exit_price,
                payload.closed_at.isoformat() if payload.closed_at else None,
                payload.pnl,
                payload.r_multiple,
                payload.notes,
                datetime.now(timezone.utc).isoformat(),
                entry_id,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return _row_to_journal(row) if row is not None else None
    finally:
        conn.close()


def list_journal_entries(
    *, symbol: str | None = None, limit: int = 500
) -> list[JournalRecord]:
    init_db()
    conn = connect()
    try:
        if symbol:
            rows = conn.execute(
                """
                SELECT * FROM journal_entries WHERE symbol = ?
                ORDER BY opened_at DESC, id DESC LIMIT ?
                """,
                (symbol.upper().strip(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM journal_entries ORDER BY opened_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [_row_to_journal(row) for row in rows]


def get_risk_settings() -> RiskSettings:
    init_db()
    conn = connect()
    try:
        row = conn.execute(
            "SELECT settings_json FROM user_risk_settings WHERE id = 1"
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return RiskSettings()
    return RiskSettings.model_validate(decode_json(row["settings_json"]))


def save_risk_settings(settings: RiskSettings) -> RiskSettings:
    init_db()
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO user_risk_settings (id, settings_json, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                settings_json = excluded.settings_json,
                updated_at = excluded.updated_at
            """,
            (
                encode_json(settings.model_dump(mode="json")),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return settings


def save_validation_report(report: dict[str, Any], *, source: str | None) -> int:
    init_db()
    conn = connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO validation_runs (
                symbol, timeframe, source, data_cutoff, validation_method,
                observation_count, report_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report["symbol"],
                report["timeframe"],
                source,
                report.get("observations", [{}])[-1].get("detectedAt")
                if report.get("observations")
                else None,
                report["validationMethod"],
                report["observationCount"],
                encode_json(report),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return _lastrowid(cursor)
    finally:
        conn.close()


def list_validation_runs(
    *, symbol: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if symbol:
            rows = conn.execute(
                "SELECT * FROM validation_runs WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
                (symbol.upper(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM validation_runs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    output = []
    for row in rows:
        item = dict(row)
        item["report"] = decode_json(item.pop("report_json"))
        output.append(item)
    return output


def save_scheduler_config(
    scheduler_key: str,
    *,
    enabled: bool,
    interval_seconds: int,
    universe: str,
    fetch: bool,
) -> None:
    init_db()
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO scheduler_config (
                scheduler_key, enabled, interval_seconds, universe, fetch, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(scheduler_key) DO UPDATE SET
                enabled = excluded.enabled,
                interval_seconds = excluded.interval_seconds,
                universe = excluded.universe,
                fetch = excluded.fetch,
                updated_at = excluded.updated_at
            """,
            (
                scheduler_key,
                1 if enabled else 0,
                interval_seconds,
                universe,
                1 if fetch else 0,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_scheduler_config(scheduler_key: str) -> dict[str, Any] | None:
    init_db()
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM scheduler_config WHERE scheduler_key = ?",
            (scheduler_key,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def row_to_record(row: sqlite3.Row) -> ResearchRecord:
    return ResearchRecord(
        id=row["id"],
        symbol=row["symbol"],
        title=row["title"],
        note=row["note"],
        tags=decode_json(row["tags_json"]),
        createdAt=row["created_at"],
        candidate=decode_json(row["candidate_json"]),
        commandBar=decode_json(row["command_bar_json"]),
        sourceHealth=decode_json(row["source_health_json"]),
    )


def save_research_record(
    payload: ResearchCreate,
    candidate: RadarCandidate,
    command_bar: CommandBar,
    source_health: list[SourceHealth],
) -> ResearchRecord:
    init_db()
    title = payload.title or f"{candidate.symbol} - {candidate.state}"
    created_at = datetime.now(timezone.utc).isoformat()
    candidate_json = candidate.model_dump(mode="json", by_alias=True)
    command_bar_json = command_bar.model_dump(mode="json", by_alias=True)
    source_health_json = [
        row.model_dump(mode="json", by_alias=True) for row in source_health
    ]

    conn = connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO research_records (
                symbol, title, note, tags_json, candidate_json,
                command_bar_json, source_health_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate.symbol,
                title,
                payload.note,
                encode_json(payload.tags),
                encode_json(candidate_json),
                encode_json(command_bar_json),
                encode_json(source_health_json),
                created_at,
            ),
        )
        record_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM research_records WHERE id = ?", (record_id,)
        ).fetchone()
        conn.commit()
    finally:
        conn.close()
    return row_to_record(row)


def list_research_records(limit: int = 100) -> list[ResearchRecord]:
    init_db()
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM research_records ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [row_to_record(row) for row in rows]


def get_research_record(record_id: int) -> ResearchRecord | None:
    init_db()
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM research_records WHERE id = ?", (record_id,)
        ).fetchone()
    finally:
        conn.close()
    return row_to_record(row) if row else None


def delete_research_record(record_id: int) -> bool:
    init_db()
    conn = connect()
    try:
        cursor = conn.execute("DELETE FROM research_records WHERE id = ?", (record_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def build_scan_hash(
    candidates: list[RadarCandidate],
    command_bar: CommandBar,
    source_health: list[SourceHealth],
) -> str:
    payload = {
        "candidates": [
            row.model_dump(mode="json", by_alias=True) for row in candidates
        ],
        "commandBar": command_bar.model_dump(mode="json", by_alias=True),
        "sourceHealth": [
            row.model_dump(mode="json", by_alias=True) for row in source_health
        ],
    }
    encoded = encode_json(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def row_to_ml_run(row: sqlite3.Row) -> MLScanRun:
    return MLScanRun(
        id=row["id"],
        runHash=row["run_hash"],
        trigger=row["trigger"],
        candidateCount=row["candidate_count"],
        createdAt=row["created_at"],
        commandBar=decode_json(row["command_bar_json"]),
        sourceHealth=decode_json(row["source_health_json"]),
    )


def row_to_ml_candidate(row: sqlite3.Row) -> MLScanCandidate:
    return MLScanCandidate(
        id=row["id"],
        runId=row["run_id"],
        symbol=row["symbol"],
        candidateType=row["candidate_type"],
        state=row["state"],
        statusGroup=row["status_group"],
        quality=row["quality"],
        payload=decode_json(row["payload_json"]),
        outcomeLabel=row["outcome_label"],
        falseScreenReason=row["false_screen_reason"],
        createdAt=row["created_at"],
    )


def latest_ml_run() -> MLScanRun | None:
    init_db()
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM ml_scan_runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    return row_to_ml_run(row) if row else None


def save_ml_scan_snapshot(
    candidates: list[RadarCandidate],
    command_bar: CommandBar,
    source_health: list[SourceHealth],
    trigger: str,
    *,
    dedupe: bool = True,
) -> MLScanRun:
    init_db()
    run_hash = build_scan_hash(candidates, command_bar, source_health)
    latest = latest_ml_run() if dedupe else None
    if latest and latest.run_hash == run_hash:
        return latest

    created_at = datetime.now(timezone.utc).isoformat()
    command_bar_json = command_bar.model_dump(mode="json", by_alias=True)
    source_health_json = [
        row.model_dump(mode="json", by_alias=True) for row in source_health
    ]

    conn = connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO ml_scan_runs (
                run_hash, trigger, candidate_count, command_bar_json,
                source_health_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_hash,
                trigger,
                len(candidates),
                encode_json(command_bar_json),
                encode_json(source_health_json),
                created_at,
            ),
        )
        run_id = cursor.lastrowid

        for candidate in candidates:
            payload = candidate.model_dump(mode="json", by_alias=True)
            conn.execute(
                """
                INSERT INTO ml_scan_candidates (
                    run_id, symbol, candidate_type, state, status_group,
                    quality, payload_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    candidate.symbol,
                    candidate.type.value,
                    candidate.state,
                    candidate.status_group.value,
                    candidate.quality,
                    encode_json(payload),
                    created_at,
                ),
            )

        row = conn.execute(
            "SELECT * FROM ml_scan_runs WHERE id = ?", (run_id,)
        ).fetchone()
        conn.commit()
    finally:
        conn.close()
    return row_to_ml_run(row)


def get_ml_scan_status() -> MLScanStatus:
    init_db()
    conn = connect()
    try:
        run_count = conn.execute(
            "SELECT COUNT(*) AS count FROM ml_scan_runs"
        ).fetchone()["count"]
        candidate_count = conn.execute(
            "SELECT COUNT(*) AS count FROM ml_scan_candidates"
        ).fetchone()["count"]
        latest_row = conn.execute(
            "SELECT * FROM ml_scan_runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    return MLScanStatus(
        totalRuns=run_count,
        totalCandidates=candidate_count,
        latestRun=row_to_ml_run(latest_row) if latest_row else None,
    )


def list_ml_scan_runs(limit: int = 50) -> list[MLScanRun]:
    init_db()
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM ml_scan_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [row_to_ml_run(row) for row in rows]


def list_ml_scan_candidates(
    run_id: int | None = None, limit: int = 500
) -> list[MLScanCandidate]:
    init_db()
    conn = connect()
    try:
        if run_id is None:
            rows = conn.execute(
                "SELECT * FROM ml_scan_candidates ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM ml_scan_candidates
                WHERE run_id = ?
                ORDER BY symbol ASC
                LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
    finally:
        conn.close()
    return [row_to_ml_candidate(row) for row in rows]


def row_to_ohlcv_candle(row: sqlite3.Row) -> OHLCVCandle:
    return OHLCVCandle(
        symbol=row["symbol"],
        timeframe=row["timeframe"],
        source=row["source"],
        timestamp=row["timestamp"],
        open=row["open"],
        high=row["high"],
        low=row["low"],
        close=row["close"],
        volume=row["volume"],
        trustLevel=DataTrust(row["trust_level"]),
        fetchedAt=row["fetched_at"],
        barState=row["bar_state"],
        sessionDate=row["session_date"],
        completeness=row["completeness"],
        adjustmentStatus=row["adjustment_status"],
        adjustmentFactor=row["adjustment_factor"],
    )


def _candle_payload(candle: OHLCVCandle) -> dict[str, Any]:
    return candle.model_dump(mode="json", by_alias=True)


def _candle_content_hash(payload: dict[str, Any]) -> str:
    stable_payload = {
        key: value for key, value in payload.items() if key != "fetchedAt"
    }
    return hashlib.sha256(encode_json(stable_payload).encode("utf-8")).hexdigest()


def _candle_quality(candle: OHLCVCandle) -> tuple[str, list[str]]:
    issues: list[str] = []
    if candle.bar_state != "COMPLETE":
        issues.append(candle.bar_state)
    if candle.completeness < 0.8:
        issues.append("LOW_COMPLETENESS")
    if candle.trust_level in {
        DataTrust.OPEN_SOURCE_UNOFFICIAL,
        DataTrust.UNOFFICIAL_WRAPPER,
        DataTrust.UNOFFICIAL_TEMP,
        DataTrust.SYNTHETIC_TEST,
    }:
        issues.append("RESEARCH_ONLY_SOURCE")
    return ("WARN" if issues else "PASS"), issues


def _save_candle_quality(
    conn: sqlite3.Connection,
    candle: OHLCVCandle,
    content_hash: str,
) -> None:
    quality_state, issues = _candle_quality(candle)
    conn.execute(
        """
        INSERT OR IGNORE INTO candle_quality_records (
            symbol, timeframe, source, candle_timestamp, content_hash,
            quality_state, bar_state, completeness, issues_json, checked_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            candle.symbol,
            candle.timeframe,
            candle.source,
            candle.timestamp,
            content_hash,
            quality_state,
            candle.bar_state,
            candle.completeness,
            encode_json(issues),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def _known_corporate_actions(
    conn: sqlite3.Connection, candles: list[OHLCVCandle]
) -> list[ReconciledCorporateAction]:
    if not candles:
        return []
    symbol = candles[0].symbol.upper().strip()
    rows = [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM corporate_events WHERE UPPER(symbol) = ? ORDER BY parsed_at, id",
            (symbol,),
        ).fetchall()
    ]
    if not rows:
        return []
    cutoffs = [
        datetime.fromisoformat(candle.timestamp.replace("Z", "+00:00"))
        for candle in candles
    ]
    if any(cutoff.utcoffset() is None for cutoff in cutoffs):
        return []
    return reconcile_corporate_actions(rows, as_of=max(cutoffs))


def _save_adjustment_assessment(
    conn: sqlite3.Connection,
    candles: list[OHLCVCandle],
    assessment: AdjustmentIntegrityAssessment,
) -> None:
    if not candles:
        return
    payload = assessment.model_dump(mode="json", by_alias=True)
    identity = {
        **payload,
        "firstTimestamp": candles[0].timestamp,
        "lastTimestamp": candles[-1].timestamp,
    }
    assessment_hash = hashlib.sha256(encode_json(identity).encode("utf-8")).hexdigest()
    conn.execute(
        """
        INSERT OR IGNORE INTO candle_adjustment_assessments (
            symbol, timeframe, source, first_timestamp, last_timestamp, state,
            required_action_count, event_ids_json, reason, assessment_hash, checked_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            assessment.symbol,
            assessment.timeframe,
            assessment.source,
            candles[0].timestamp,
            candles[-1].timestamp,
            assessment.state,
            assessment.required_action_count,
            encode_json(assessment.event_ids),
            assessment.reason,
            assessment_hash,
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def save_ohlcv_candles(candles: list[OHLCVCandle]) -> int:
    init_db()
    if not candles:
        return 0

    conn = connect()
    try:
        actions = _known_corporate_actions(conn, candles)
        candles = apply_reconciled_actions_at_ingestion(candles, actions)
        assessment = assess_adjustment_integrity(candles, actions)
        affected = 0
        for candle in candles:
            new_payload = _candle_payload(candle)
            new_hash = _candle_content_hash(new_payload)
            _save_candle_quality(conn, candle, new_hash)
            existing = conn.execute(
                """
                SELECT * FROM ohlcv_candles
                WHERE symbol = ? AND timeframe = ? AND source = ? AND timestamp = ?
                """,
                (candle.symbol, candle.timeframe, candle.source, candle.timestamp),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO ohlcv_candles (
                        symbol, timeframe, source, timestamp, open, high, low,
                        close, volume, trust_level, fetched_at, bar_state,
                        session_date, completeness, adjustment_status, adjustment_factor
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        candle.symbol,
                        candle.timeframe,
                        candle.source,
                        candle.timestamp,
                        candle.open,
                        candle.high,
                        candle.low,
                        candle.close,
                        candle.volume,
                        candle.trust_level.value,
                        candle.fetched_at,
                        candle.bar_state,
                        candle.session_date,
                        candle.completeness,
                        candle.adjustment_status,
                        candle.adjustment_factor,
                    ),
                )
                affected += 1
                continue

            old_payload = row_to_ohlcv_candle(existing).model_dump(
                mode="json", by_alias=True
            )
            old_hash = _candle_content_hash(old_payload)
            if old_hash == new_hash:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO candle_revisions (
                    symbol, timeframe, source, candle_timestamp, old_hash, new_hash,
                    old_payload_json, new_payload_json, reason, detected_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candle.symbol,
                    candle.timeframe,
                    candle.source,
                    candle.timestamp,
                    old_hash,
                    new_hash,
                    encode_json(old_payload),
                    encode_json(new_payload),
                    "SOURCE_VALUE_CHANGED",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.execute(
                """
                UPDATE ohlcv_candles
                SET open = ?, high = ?, low = ?, close = ?, volume = ?, trust_level = ?,
                    fetched_at = ?, bar_state = ?, session_date = ?, completeness = ?,
                    adjustment_status = ?, adjustment_factor = ?
                WHERE symbol = ? AND timeframe = ? AND source = ? AND timestamp = ?
                """,
                (
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume,
                    candle.trust_level.value,
                    candle.fetched_at,
                    candle.bar_state,
                    candle.session_date,
                    candle.completeness,
                    candle.adjustment_status,
                    candle.adjustment_factor,
                    candle.symbol,
                    candle.timeframe,
                    candle.source,
                    candle.timestamp,
                ),
            )
            affected += 1
        _save_adjustment_assessment(conn, candles, assessment)
        conn.commit()
        return affected
    finally:
        conn.close()


def list_ohlcv_candles(
    symbol: str,
    timeframe: str,
    *,
    source: str | None = None,
    limit: int = 500,
) -> list[OHLCVCandle]:
    init_db()
    normalized_symbol = symbol.upper().strip()
    conn = connect()
    try:
        if source:
            rows = conn.execute(
                """
                SELECT * FROM ohlcv_candles
                WHERE symbol = ? AND timeframe = ? AND source = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (normalized_symbol, timeframe, source, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM ohlcv_candles
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (normalized_symbol, timeframe, limit),
            ).fetchall()
    finally:
        conn.close()
    return [row_to_ohlcv_candle(row) for row in reversed(rows)]


def list_candle_revisions(
    *, symbol: str | None = None, limit: int = 500
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if symbol:
            rows = conn.execute(
                """
                SELECT * FROM candle_revisions WHERE symbol = ?
                ORDER BY detected_at DESC, id DESC LIMIT ?
                """,
                (symbol.upper().strip(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM candle_revisions ORDER BY detected_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["old_payload"] = decode_json(item.pop("old_payload_json"))
        item["new_payload"] = decode_json(item.pop("new_payload_json"))
        output.append(item)
    return output


def list_candle_adjustment_assessments(
    *, symbol: str | None = None, limit: int = 500
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if symbol:
            rows = conn.execute(
                """
                SELECT * FROM candle_adjustment_assessments
                WHERE UPPER(symbol) = ? ORDER BY checked_at, id LIMIT ?
                """,
                (symbol.upper().strip(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM candle_adjustment_assessments
                ORDER BY checked_at DESC, id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["event_ids"] = decode_json(item.pop("event_ids_json"))
        output.append(item)
    return output


def reconcile_stored_candle_adjustments(
    symbol: str, timeframe: str, source: str
) -> dict[str, Any]:
    candles = list_ohlcv_candles(
        symbol.upper().strip(), timeframe, source=source, limit=100_000
    )
    if not candles:
        return {
            "status": "WAIT_DATA_WEAK",
            "symbol": symbol.upper().strip(),
            "timeframe": timeframe,
            "source": source,
            "candleCount": 0,
            "updatedCount": 0,
            "reason": "No stored candles match the requested series.",
            "executable": False,
        }
    updated = save_ohlcv_candles(candles)
    assessments = list_candle_adjustment_assessments(symbol=symbol, limit=1000)
    matching = [
        row
        for row in assessments
        if row["timeframe"] == timeframe and row["source"] == source
    ]
    latest = matching[-1] if matching else None
    return {
        "status": latest["state"] if latest else "WAIT_DATA_WEAK",
        "symbol": symbol.upper().strip(),
        "timeframe": timeframe,
        "source": source,
        "candleCount": len(candles),
        "updatedCount": updated,
        "assessment": latest,
        "executable": False,
    }


def save_corporate_event_observations(
    source_key: str,
    *,
    data_date: str | None,
    rows: list[dict[str, Any]],
    parsed_at: str | None = None,
) -> int:
    init_db()
    observed_at = parsed_at or datetime.now(timezone.utc).isoformat()
    conn = connect()
    try:
        inserted = 0
        for item in rows:
            cursor = conn.execute(
                """
                INSERT INTO corporate_events (
                    source_parse_id, source_key, data_date, symbol, company,
                    action_type, announcement_date, ex_date, record_date,
                    start_date, end_date, offer_price, quantity, action_class,
                    ratio_numerator, ratio_denominator, cash_amount,
                    adjustment_factor, predecessor_symbol, successor_symbol,
                    continuity_confirmed, revision_status, parsed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    None,
                    source_key,
                    data_date,
                    item.get("symbol"),
                    item.get("company"),
                    item.get("actionType"),
                    item.get("announcementDate"),
                    item.get("exDate"),
                    item.get("recordDate"),
                    item.get("startDate"),
                    item.get("endDate"),
                    item.get("offerPrice"),
                    item.get("quantity"),
                    item.get("actionClass"),
                    item.get("ratioNumerator"),
                    item.get("ratioDenominator"),
                    item.get("cashAmount"),
                    item.get("priceAdjustmentFactor"),
                    item.get("predecessorSymbol"),
                    item.get("successorSymbol"),
                    1
                    if item.get("continuityConfirmed") is True
                    else 0
                    if item.get("continuityConfirmed") is False
                    else None,
                    item.get("revisionStatus", "UNKNOWN"),
                    observed_at,
                ),
            )
            inserted += max(cursor.rowcount, 0)
        conn.commit()
        return inserted
    finally:
        conn.close()


def list_corporate_event_observations(
    *, symbol: str | None = None, limit: int = 1000
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if symbol:
            rows = conn.execute(
                """
                SELECT * FROM corporate_events WHERE UPPER(symbol) = ?
                ORDER BY parsed_at, id LIMIT ?
                """,
                (symbol.upper().strip(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM corporate_events ORDER BY parsed_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def list_nse_instruments(
    *, symbol: str | None = None, as_of: str | None = None, limit: int = 5000
) -> list[dict[str, Any]]:
    init_db()
    cutoff = (as_of or datetime.now(timezone.utc).date().isoformat())[:10]
    values: list[Any] = [cutoff]
    symbol_filter = ""
    if symbol:
        symbol_filter = "AND UPPER(i.symbol) = ?"
        values.append(symbol.upper().strip())
    values.append(limit)
    conn = connect()
    try:
        rows = conn.execute(
            f"""
            SELECT i.*, s.industry, s.index_membership
            FROM nse_instruments i
            LEFT JOIN nse_sector_membership s
              ON s.symbol = i.symbol AND s.series = i.series
             AND s.active = 1
             AND s.data_date = (
                 SELECT MAX(s2.data_date) FROM nse_sector_membership s2
                 WHERE s2.symbol = i.symbol AND s2.series = i.series
                   AND s2.active = 1
                   AND s2.data_date <= ?
             )
            WHERE i.data_date = (
                SELECT MAX(i2.data_date) FROM nse_instruments i2
                WHERE i2.symbol = i.symbol AND i2.series = i.series
                  AND i2.active = 1
                  AND i2.data_date <= ?
            )
            AND i.active = 1
            {symbol_filter}
            ORDER BY i.symbol, i.series
            LIMIT ?
            """,
            [cutoff, *values],
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def list_index_constituents(
    index_membership: str, *, as_of: str | None = None, limit: int = 1000
) -> list[dict[str, Any]]:
    init_db()
    cutoff = (as_of or datetime.now(timezone.utc).date().isoformat())[:10]
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT * FROM nse_sector_membership
            WHERE index_membership = ? AND active = 1 AND data_date = (
                SELECT MAX(s2.data_date) FROM nse_sector_membership s2
                WHERE s2.index_membership = ? AND s2.active = 1
                  AND s2.data_date <= ?
            )
            ORDER BY symbol
            LIMIT ?
            """,
            (index_membership.upper(), index_membership.upper(), cutoff, limit),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def nse_instrument_universe_status() -> dict[str, Any]:
    init_db()
    conn = connect()
    try:
        instrument_date = conn.execute(
            "SELECT MAX(data_date) FROM nse_instruments WHERE active = 1"
        ).fetchone()[0]
        sector_date = conn.execute(
            "SELECT MAX(data_date) FROM nse_sector_membership WHERE active = 1"
        ).fetchone()[0]
        instrument_count = (
            conn.execute(
                "SELECT COUNT(*) FROM nse_instruments WHERE active = 1 AND data_date = ?",
                (instrument_date,),
            ).fetchone()[0]
            if instrument_date
            else 0
        )
        sector_count = (
            conn.execute(
                "SELECT COUNT(*) FROM nse_sector_membership WHERE active = 1 AND data_date = ?",
                (sector_date,),
            ).fetchone()[0]
            if sector_date
            else 0
        )
    finally:
        conn.close()
    return {
        "state": "STRUCTURED_OK" if instrument_count else "WAIT_UNIVERSE_DATA",
        "instrumentCount": instrument_count,
        "instrumentDataDate": instrument_date,
        "nifty500MembershipCount": sector_count,
        "sectorDataDate": sector_date,
        "executable": False,
    }


def save_market_context_snapshot(payload: dict[str, Any]) -> int:
    init_db()
    conn = connect()
    try:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO market_context_snapshots (
                as_of, source_date, state, gate_outcome, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload["asOf"],
                payload["sourceDate"],
                payload["state"],
                payload["gateOutcome"],
                encode_json(payload),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        if cursor.rowcount > 0:
            return _lastrowid(cursor)
        row = conn.execute(
            """
            SELECT id FROM market_context_snapshots
            WHERE as_of = ? AND source_date = ? AND state = ? AND gate_outcome = ?
            """,
            (
                payload["asOf"],
                payload["sourceDate"],
                payload["state"],
                payload["gateOutcome"],
            ),
        ).fetchone()
        return int(row["id"])
    finally:
        conn.close()


def latest_market_context_snapshot() -> dict[str, Any] | None:
    init_db()
    conn = connect()
    try:
        row = conn.execute(
            "SELECT payload_json FROM market_context_snapshots ORDER BY as_of DESC, id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    return decode_json(row["payload_json"]) if row else None


def list_exchange_calendar_days(
    *,
    exchange: str = "NSE",
    segment: str = "CM",
    trading_date: str | None = None,
    year: int | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    init_db()
    clauses = ["d.exchange = ?", "d.segment = ?"]
    values: list[Any] = [exchange.upper(), segment.upper()]
    if trading_date:
        clauses.append("d.trading_date = ?")
        values.append(trading_date[:10])
    if year is not None:
        clauses.append("substr(d.trading_date, 1, 4) = ?")
        values.append(f"{year:04d}")
    values.append(limit)
    conn = connect()
    try:
        rows = conn.execute(
            f"""
            SELECT d.* FROM exchange_calendar_days d
            WHERE {" AND ".join(clauses)}
              AND d.data_date = (
                SELECT MAX(c2.data_date) FROM exchange_calendar_days c2
                WHERE c2.exchange = d.exchange AND c2.segment = d.segment
              )
            ORDER BY d.trading_date, d.id
            LIMIT ?
            """,
            values,
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def list_nse_index_eod(
    *, index_name: str, as_of: str | None = None, limit: int = 200
) -> list[dict[str, Any]]:
    init_db()
    cutoff = (as_of or datetime.now(timezone.utc).date().isoformat())[:10]
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT * FROM nse_index_eod
            WHERE index_name = ? AND index_date <= ?
            ORDER BY index_date DESC
            LIMIT ?
            """,
            (index_name.strip().upper(), cutoff, limit),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in reversed(rows)]


def latest_nse_cash_eod_date(*, as_of: str | None = None) -> str | None:
    init_db()
    cutoff = (as_of or datetime.now(timezone.utc).date().isoformat())[:10]
    conn = connect()
    try:
        row = conn.execute(
            "SELECT MAX(trade_date) AS trade_date FROM nse_cash_eod WHERE trade_date <= ?",
            (cutoff,),
        ).fetchone()
    finally:
        conn.close()
    return str(row["trade_date"]) if row and row["trade_date"] else None


def list_nse_cash_eod(
    *,
    trade_date: str,
    series: str | None = "EQ",
    limit: int = 10000,
) -> list[dict[str, Any]]:
    init_db()
    clauses = ["trade_date = ?"]
    values: list[Any] = [trade_date[:10]]
    if series:
        clauses.append("series = ?")
        values.append(series.upper())
    values.append(limit)
    conn = connect()
    try:
        rows = conn.execute(
            f"SELECT * FROM nse_cash_eod WHERE {' AND '.join(clauses)} ORDER BY symbol LIMIT ?",
            values,
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def official_market_input_status() -> dict[str, Any]:
    init_db()
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM nse_index_eod WHERE index_name = 'NIFTY 50') AS nifty_count,
              (SELECT COUNT(*) FROM nse_index_eod WHERE index_name = 'INDIA VIX') AS vix_count,
              (SELECT MAX(index_date) FROM nse_index_eod WHERE index_name = 'NIFTY 50') AS latest_index_date,
              (SELECT COUNT(*) FROM nse_cash_eod WHERE trade_date = (SELECT MAX(trade_date) FROM nse_cash_eod)) AS latest_cash_count,
              (SELECT MAX(trade_date) FROM nse_cash_eod) AS latest_cash_date,
              (SELECT COUNT(DISTINCT index_name) FROM nse_index_eod) AS index_count
            """
        ).fetchone()
    finally:
        conn.close()
    payload = dict(row)
    payload["marketContextReady"] = bool(
        payload["nifty_count"] >= 200
        and payload["vix_count"] >= 2
        and payload["latest_index_date"] == payload["latest_cash_date"]
        and payload["latest_cash_count"] > 0
    )
    return payload


def exchange_calendar_coverage(
    *, exchange: str = "NSE", segment: str = "CM", year: int
) -> dict[str, Any] | None:
    init_db()
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT * FROM exchange_calendar_coverage
            WHERE exchange = ? AND segment = ? AND calendar_year = ?
            ORDER BY data_date DESC, id DESC
            LIMIT 1
            """,
            (exchange.upper(), segment.upper(), year),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def save_sector_context_snapshot(payload: dict[str, Any]) -> int:
    init_db()
    conn = connect()
    try:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO sector_context_snapshots (
                sector, direction, as_of, source_date, rrg_state,
                gate_outcome, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["sector"],
                payload["direction"],
                payload["asOf"],
                payload["sourceDate"],
                payload["rrgState"],
                payload["gateOutcome"],
                encode_json(payload),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return _lastrowid(cursor) if cursor.rowcount > 0 else 0
    finally:
        conn.close()


def latest_sector_context_snapshot(
    *, sector: str | None = None, direction: str | None = None
) -> dict[str, Any] | None:
    init_db()
    conditions = []
    values: list[Any] = []
    if sector:
        conditions.append("UPPER(sector) = ?")
        values.append(sector.upper().strip())
    if direction:
        conditions.append("direction = ?")
        values.append(direction.upper().strip())
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    conn = connect()
    try:
        row = conn.execute(
            f"""
            SELECT payload_json FROM sector_context_snapshots {where}
            ORDER BY as_of DESC, id DESC LIMIT 1
            """,
            values,
        ).fetchone()
    finally:
        conn.close()
    return decode_json(row["payload_json"]) if row else None


def save_bse_offer_document(artifact: dict[str, Any]) -> int:
    """Persist one immutable BSE XBRL artifact and its normalized offer terms."""
    init_db()
    payload = artifact.get("payload") or {}
    conn = connect()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO bse_offer_documents (
                parent_source_key, company_id, offer_type, phase, document_url,
                published_date, revision_status, fetched_at, status_code,
                content_hash, raw_path, parser_state, data_date, payload_json, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact["parent_source_key"],
                artifact.get("company_id"),
                artifact["offer_type"],
                artifact["phase"],
                artifact["document_url"],
                artifact.get("published_date"),
                artifact.get("revision_status", "UNKNOWN"),
                artifact["fetched_at"],
                artifact.get("status_code"),
                artifact["content_hash"],
                artifact["raw_path"],
                artifact["parser_state"],
                artifact.get("data_date"),
                encode_json(payload),
                artifact.get("error"),
            ),
        )
        document = conn.execute(
            """
            SELECT * FROM bse_offer_documents
            WHERE document_url = ? AND content_hash = ?
            """,
            (artifact["document_url"], artifact["content_hash"]),
        ).fetchone()
        if document is None:
            raise sqlite3.IntegrityError("BSE offer document was not persisted")
        document_id = int(document["id"])
        if artifact["parser_state"] == "PARSED_STRUCTURED":
            for row in payload.get("rows", []):
                symbol = str(row.get("symbol") or artifact.get("symbol") or "").upper()
                scrip_code = str(
                    row.get("scripCode") or artifact.get("scrip_code") or ""
                )
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO corporate_offer_events (
                        document_id, parent_source_key, company_id, symbol,
                        scrip_code, isin, company, offer_type, phase,
                        announcement_date, record_date, start_date, end_date,
                        offer_price, quantity, consideration, acquirers_json,
                        revision_status, document_url, document_hash, data_date,
                        parsed_at, is_current
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        artifact["parent_source_key"],
                        artifact.get("company_id"),
                        symbol,
                        scrip_code,
                        row.get("isin"),
                        row.get("company"),
                        row.get("offerType") or artifact["offer_type"],
                        row.get("phase") or artifact["phase"],
                        row.get("announcementDate"),
                        row.get("recordDate"),
                        row.get("startDate"),
                        row.get("endDate"),
                        row.get("offerPrice"),
                        row.get("quantity"),
                        row.get("consideration"),
                        encode_json(row.get("acquirers") or []),
                        artifact.get("revision_status", "UNKNOWN"),
                        artifact["document_url"],
                        artifact["content_hash"],
                        artifact.get("data_date") or row.get("announcementDate"),
                        artifact["fetched_at"],
                        0,
                    ),
                )
                if cursor.rowcount > 0:
                    group = (
                        artifact["parent_source_key"],
                        artifact.get("company_id"),
                        row.get("offerType") or artifact["offer_type"],
                        row.get("phase") or artifact["phase"],
                    )
                    conn.execute(
                        """
                        UPDATE corporate_offer_events SET is_current = 0
                        WHERE parent_source_key = ?
                          AND COALESCE(company_id, '') = COALESCE(?, '')
                          AND offer_type = ? AND phase = ?
                        """,
                        group,
                    )
                    current = conn.execute(
                        """
                        SELECT id FROM corporate_offer_events
                        WHERE parent_source_key = ?
                          AND COALESCE(company_id, '') = COALESCE(?, '')
                          AND offer_type = ? AND phase = ?
                        ORDER BY data_date DESC, parsed_at DESC, id DESC LIMIT 1
                        """,
                        group,
                    ).fetchone()
                    if current:
                        conn.execute(
                            "UPDATE corporate_offer_events SET is_current = 1 WHERE id = ?",
                            (current["id"],),
                        )
        conn.commit()
        return document_id
    finally:
        conn.close()


def list_bse_offer_documents(
    *, parent_source_key: str | None = None, limit: int = 500
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if parent_source_key:
            rows = conn.execute(
                """
                SELECT * FROM bse_offer_documents WHERE parent_source_key = ?
                ORDER BY fetched_at DESC, id DESC LIMIT ?
                """,
                (parent_source_key, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM bse_offer_documents
                ORDER BY fetched_at DESC, id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["payload"] = decode_json(item.pop("payload_json"))
        output.append(item)
    return output


def bse_offer_document_version_exists(
    *, document_url: str, published_date: str | None, revision_status: str
) -> bool:
    init_db()
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT 1 FROM bse_offer_documents
            WHERE document_url = ?
              AND COALESCE(published_date, '') = COALESCE(?, '')
              AND revision_status = ?
            LIMIT 1
            """,
            (document_url, published_date, revision_status),
        ).fetchone()
    finally:
        conn.close()
    return row is not None


def save_raw_source_artifact(
    *,
    source_key: str,
    fetched_at: str,
    content_hash: str,
    content_length: int,
    raw_path: str,
    last_modified: str | None,
    etag: str | None,
    parser_state: str,
    data_date: str | None,
) -> int:
    init_db()
    conn = connect()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO raw_source_archive (
                source_key, fetched_at, content_hash, content_length, raw_path,
                last_modified, etag, parser_state_after_parse, data_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_key,
                fetched_at,
                content_hash,
                content_length,
                raw_path,
                last_modified,
                etag,
                parser_state,
                data_date,
            ),
        )
        row = conn.execute(
            """
            SELECT id FROM raw_source_archive
            WHERE source_key = ? AND content_hash = ?
            """,
            (source_key, content_hash),
        ).fetchone()
        conn.commit()
        if row is None:
            raise sqlite3.IntegrityError("raw source artifact was not persisted")
        return int(row["id"])
    finally:
        conn.close()


def list_corporate_offer_events(
    *,
    symbol: str | None = None,
    parent_source_key: str | None = None,
    current_only: bool = True,
    limit: int = 500,
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if symbol:
            rows = conn.execute(
                """
                SELECT * FROM corporate_offer_events
                WHERE UPPER(symbol) = ?
                  AND (? IS NULL OR parent_source_key = ?)
                  AND (? = 0 OR is_current = 1)
                ORDER BY data_date DESC, parsed_at DESC, id DESC LIMIT ?
                """,
                (
                    symbol.upper().strip(),
                    parent_source_key,
                    parent_source_key,
                    1 if current_only else 0,
                    limit,
                ),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM corporate_offer_events
                WHERE (? IS NULL OR parent_source_key = ?)
                  AND (? = 0 OR is_current = 1)
                ORDER BY data_date DESC, parsed_at DESC, id DESC LIMIT ?
                """,
                (
                    parent_source_key,
                    parent_source_key,
                    1 if current_only else 0,
                    limit,
                ),
            ).fetchall()
    finally:
        conn.close()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["acquirers"] = decode_json(item.pop("acquirers_json"))
        output.append(item)
    return output


def list_candle_quality_records(
    *, symbol: str | None = None, limit: int = 500
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if symbol:
            rows = conn.execute(
                """
                SELECT * FROM candle_quality_records WHERE symbol = ?
                ORDER BY checked_at DESC, id DESC LIMIT ?
                """,
                (symbol.upper().strip(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM candle_quality_records ORDER BY checked_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["issues"] = decode_json(item.pop("issues_json"))
        output.append(item)
    return output


def list_ohlcv_series(
    *, min_candles: int = 40, limit: int = 1000
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT symbol, timeframe, source, trust_level,
                   COUNT(*) AS candle_count,
                   MIN(timestamp) AS first_timestamp,
                   MAX(timestamp) AS last_timestamp,
                   MAX(fetched_at) AS last_fetched_at
            FROM ohlcv_candles
            GROUP BY symbol, timeframe, source, trust_level
            HAVING COUNT(*) >= ?
            ORDER BY last_timestamp DESC, symbol ASC, timeframe ASC
            LIMIT ?
            """,
            (min_candles, limit),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def row_to_harmonic_pattern(row: sqlite3.Row) -> HarmonicPatternResult:
    points = [HarmonicPoint(**point) for point in decode_json(row["points_json"])]
    gates = [PairRow.model_validate(item) for item in decode_json(row["gates_json"])]
    return HarmonicPatternResult(
        id=row["id"],
        symbol=row["symbol"],
        timeframe=row["timeframe"],
        direction=row["direction"],
        patternName=row["pattern_name"],
        state=row["state"],
        sourceEngine=row["source_engine"],
        points=points,
        przLow=row["prz_low"],
        przHigh=row["prz_high"],
        invalidationPrice=row["invalidation_price"],
        target1=row["target1"],
        target2=row["target2"],
        confidence=row["confidence"],
        confirmationState=row["confirmation_state"],
        finalState=row["final_state"],
        reasons=decode_json(row["reasons_json"]),
        gates=gates,
        createdAt=row["created_at"],
    )


def save_harmonic_patterns(
    patterns: list[HarmonicPatternResult],
) -> list[HarmonicPatternResult]:
    init_db()
    if not patterns:
        return []

    created_at = datetime.now(timezone.utc).isoformat()
    conn = connect()
    saved_ids: list[int] = []
    try:
        for pattern in patterns:
            points = [point.model_dump(mode="json") for point in pattern.points]
            gates = [gate.model_dump(mode="json") for gate in pattern.gates]
            cursor = conn.execute(
                """
                INSERT INTO harmonic_patterns (
                    symbol, timeframe, direction, pattern_name, state,
                    source_engine, points_json, prz_low, prz_high,
                    invalidation_price, target1, target2, confidence,
                    confirmation_state, final_state, reasons_json,
                    gates_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pattern.symbol,
                    pattern.timeframe,
                    pattern.direction,
                    pattern.pattern_name,
                    pattern.state,
                    pattern.source_engine,
                    encode_json(points),
                    pattern.prz_low,
                    pattern.prz_high,
                    pattern.invalidation_price,
                    pattern.target1,
                    pattern.target2,
                    pattern.confidence,
                    pattern.confirmation_state,
                    pattern.final_state,
                    encode_json(pattern.reasons),
                    encode_json(gates),
                    created_at,
                ),
            )
            saved_ids.append(_lastrowid(cursor))

        placeholders = ",".join("?" for _ in saved_ids)
        rows = conn.execute(
            f"SELECT * FROM harmonic_patterns WHERE id IN ({placeholders}) ORDER BY id ASC",
            saved_ids,
        ).fetchall()
        conn.commit()
    finally:
        conn.close()
    return [row_to_harmonic_pattern(row) for row in rows]


def list_harmonic_patterns(
    symbol: str | None = None,
    timeframe: str | None = None,
    *,
    limit: int = 100,
) -> list[HarmonicPatternResult]:
    init_db()
    clauses: list[str] = []
    params: list[Any] = []
    if symbol:
        clauses.append("symbol = ?")
        params.append(symbol.upper().strip())
    if timeframe:
        clauses.append("timeframe = ?")
        params.append(timeframe)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)

    conn = connect()
    try:
        rows = conn.execute(
            f"""
            SELECT * FROM harmonic_patterns
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    finally:
        conn.close()
    return [row_to_harmonic_pattern(row) for row in rows]


DEFAULT_SOURCE_REGISTRY = [
    (
        "yfinance",
        "yfinance",
        DataTrust.UNOFFICIAL_TEMP.value,
        FreshnessState.UNKNOWN.value,
        SourceState.AMBER.value,
    ),
    (
        "nsepython",
        "nsepython",
        DataTrust.UNOFFICIAL_WRAPPER.value,
        FreshnessState.UNKNOWN.value,
        SourceState.AMBER.value,
    ),
    (
        "nselib",
        "nselib",
        DataTrust.UNOFFICIAL_WRAPPER.value,
        FreshnessState.UNKNOWN.value,
        SourceState.WARN.value,
    ),
    (
        "openchart",
        "openchart",
        DataTrust.OPEN_SOURCE_UNOFFICIAL.value,
        FreshnessState.UNKNOWN.value,
        SourceState.WARN.value,
    ),
    (
        "static_csv",
        "static_csv",
        DataTrust.SYNTHETIC_TEST.value,
        FreshnessState.UNKNOWN.value,
        SourceState.NA.value,
    ),
    (
        "licensed_feed",
        "broker_or_data_vendor",
        DataTrust.OFFICIAL_OR_LICENSED.value,
        FreshnessState.UNKNOWN.value,
        SourceState.RED.value,
    ),
]


DEFAULT_SOURCE_REPLACEMENT_MAP = [
    {
        "source_key": "openchart",
        "source_role": "UNUSABLE_FAIL_CLOSED",
        "rejected_reason": "Installed but did not return usable candles in local smoke testing.",
        "lost_function": "Temporary intraday candles for 30m/1h/4H prototyping.",
        "safe_use": "Smoke-test only after stable fixture/schema passes.",
        "blocked_use": "Official READY, production intraday scanning.",
        "primary_replacement": "licensed_intraday_feed",
        "secondary_replacement": "nselib_or_direct_nse_bhavcopy_for_eod",
        "can_unlock_ready": 0,
        "notes": "Keep fail-closed until timestamp and OHLCV schema are proven.",
    },
    {
        "source_key": "yfinance",
        "source_role": "PROTOTYPE_ONLY",
        "rejected_reason": "Unofficial temporary feed; schema and availability can change.",
        "lost_function": "Fast prototype OHLCV and global proxy candles if removed.",
        "safe_use": "UI, harmonic development, smoke tests, research-only experiments.",
        "blocked_use": "Official READY, final intraday trade authority.",
        "primary_replacement": "licensed_intraday_feed",
        "secondary_replacement": "direct_nse_bhavcopy_or_nselib_for_eod",
        "can_unlock_ready": 0,
        "notes": "Must remain UNOFFICIAL_TEMP.",
    },
    {
        "source_key": "nselib",
        "source_role": "PROTOTYPE_EOD_WRAPPER",
        "rejected_reason": "Wrapper depends on public NSE behavior even when installed.",
        "lost_function": "Convenient EOD daily/weekly bootstrap if removed.",
        "safe_use": "EOD research, adapter/schema tests, daily/weekly harmonic development.",
        "blocked_use": "Intraday READY and smart-money/OI gate proof by itself.",
        "primary_replacement": "direct_nse_bhavcopy",
        "secondary_replacement": "licensed_feed",
        "can_unlock_ready": 0,
        "notes": "Installed and EOD-smoke verified, but still not a gate source alone.",
    },
    {
        "source_key": "nsepython",
        "source_role": "PROTOTYPE_WRAPPER",
        "rejected_reason": "Wrapper behavior depends on NSE public website behavior.",
        "lost_function": "Rapid NSE report/candle discovery if removed.",
        "safe_use": "Discovery and wrapper experiments behind adapter contracts.",
        "blocked_use": "Bypassing official parser/freshness contracts.",
        "primary_replacement": "direct_official_nse_downloads",
        "secondary_replacement": "nselib_for_eod",
        "can_unlock_ready": 0,
        "notes": "Never claims official gate truth alone.",
    },
    {
        "source_key": "tradingview_harmonic_scripts",
        "source_role": "REFERENCE_ONLY",
        "rejected_reason": "Pine scripts/platform scanners are not backend all-NSE data sources.",
        "lost_function": "Pattern state, PRZ, alert, and UI behavior examples.",
        "safe_use": "Ratio, UI, lifecycle, alert grammar reference.",
        "blocked_use": "Backend scanner data, official signal, copied code.",
        "primary_replacement": "internal_trendforge_ratio_validator",
        "secondary_replacement": "trendforge_harmonic_gates",
        "can_unlock_ready": 0,
        "notes": "Use ideas only; no runtime authority.",
    },
    {
        "source_key": "commercial_harmonic_scanners",
        "source_role": "REFERENCE_ONLY",
        "rejected_reason": "No legal/stable backend API in the current project.",
        "lost_function": "Professional UX, PRZ/target/stop display, alert workflow examples.",
        "safe_use": "Benchmark and product-design reference.",
        "blocked_use": "Scraping or using as final trade authority.",
        "primary_replacement": "internal_trendforge_harmonic_scanner",
        "secondary_replacement": "licensed_market_data_feed",
        "can_unlock_ready": 0,
        "notes": "Patterns Hunters, HarmonicPattern, Investar, Chartink, MotiveWave, TrendSpider, and similar tools stay reference-only.",
    },
    {
        "source_key": "stock_pattern",
        "source_role": "REFERENCE_ONLY_LICENSE_RISK",
        "rejected_reason": "GPL-3.0 license risk for direct code inclusion.",
        "lost_function": "Ready-made chart-pattern and backtest ideas.",
        "safe_use": "Conceptual comparison only.",
        "blocked_use": "Copying code into core.",
        "primary_replacement": "internal_trendforge_ratio_validator",
        "secondary_replacement": "trendforge_backtest_module",
        "can_unlock_ready": 0,
        "notes": "Do not import into core without explicit license acceptance.",
    },
    {
        "source_key": "amfi_monthly_portfolio",
        "source_role": "OFFICIAL_DELAYED_CONTEXT",
        "rejected_reason": "Monthly lag makes it unsuitable for intraday buying proof.",
        "lost_function": "Stock-level DII/mutual-fund sponsorship if skipped.",
        "safe_use": "Swing sponsor evidence with MONTHLY_LAG label.",
        "blocked_use": "Live intraday buying proof.",
        "primary_replacement": "none_exact_use_amfi_with_lag",
        "secondary_replacement": "delivery_t1_large_deals_filings",
        "can_unlock_ready": 0,
        "notes": "Can support G12 only with delayed/swing context and other fresh confirmations.",
    },
    {
        "source_key": "nse_participant_oi",
        "source_role": "OFFICIAL_DELAYED_CONTEXT",
        "rejected_reason": "Aggregate derivative data, not stock-level FII proof.",
        "lost_function": "Market/index regime positioning if skipped.",
        "safe_use": "Regime context for FII/DII/Pro/Client positioning.",
        "blocked_use": "Claiming stock-specific FII buying.",
        "primary_replacement": "bulk_block_deals_filings_amfi_delivery",
        "secondary_replacement": "stock_futures_oi_and_basis",
        "can_unlock_ready": 0,
        "notes": "Correctly scoped as aggregate context only.",
    },
    {
        "source_key": "cftc_cot",
        "source_role": "OFFICIAL_DELAYED_CONTEXT",
        "rejected_reason": "Weekly delayed commodity positioning, not intraday flow.",
        "lost_function": "Commodity regime positioning if skipped.",
        "safe_use": "MCX macro/regime context with WEEKLY_DELAYED label.",
        "blocked_use": "Live MCX intraday trigger or individual trader identity.",
        "primary_replacement": "official_cftc_direct_files",
        "secondary_replacement": "barchart_cot_visual_reference",
        "can_unlock_ready": 0,
        "notes": "Parser is built for f_disagg.txt, but CFTC alone cannot READY MCX.",
    },
    {
        "source_key": "secondary_aggregators",
        "source_role": "SECONDARY_DISCOVERY",
        "rejected_reason": "Aggregator data is not ground truth.",
        "lost_function": "Fast lead generation and manual discovery if skipped.",
        "safe_use": "Discovery/watchlist/manual cross-check leads.",
        "blocked_use": "Final scoring without official reconciliation.",
        "primary_replacement": "nse_bse_sebi_amfi_official_sources",
        "secondary_replacement": "manual_research_queue",
        "can_unlock_ready": 0,
        "notes": "Trendlyne, Moneycontrol, Tickertape, and similar sources are discovery-only. StockEdge is NOT_IN_USE until a stable public API contract is verified.",
    },
    {
        "source_key": "sebi_pit_sast",
        "source_role": "OFFICIAL_GATE_SOURCE_LIVE_UNVERIFIED",
        "rejected_reason": "Parser is fixture-tested, but live PDF/XBRL contracts are not yet verified.",
        "lost_function": "Promoter, insider, pledge, acquirer, and FPI evidence if skipped.",
        "safe_use": "Structured rows only after a fresh live snapshot passes the parser contract.",
        "blocked_use": "G12 unlock from metadata-only output.",
        "primary_replacement": "structured_sebi_pdf_xbrl_parser",
        "secondary_replacement": "exchange_filings",
        "can_unlock_ready": 0,
        "notes": "HTML/PDF metadata remains blocked; only compiler-authorized validated structured rows can contribute.",
    },
    {
        "source_key": "mca_master_data",
        "source_role": "OFFICIAL_BACKGROUND_CONTEXT",
        "rejected_reason": "Lower priority and form-based, not live trade evidence.",
        "lost_function": "SBO, charges, and company background context if skipped.",
        "safe_use": "Background risk enrichment after stable parser exists.",
        "blocked_use": "MVP READY unlock.",
        "primary_replacement": "exchange_filings_sebi_sast_pit",
        "secondary_replacement": "mca_parser_future",
        "can_unlock_ready": 0,
        "notes": "Useful later for hidden ownership/charge context.",
    },
    {
        "source_key": "rbi_fpi_monitoring",
        "source_role": "OFFICIAL_CONTEXT",
        "rejected_reason": "Aggregate ownership-limit context, not stock-level FII buying.",
        "lost_function": "FPI cap/caution threshold context if skipped.",
        "safe_use": "Constraint/regime context.",
        "blocked_use": "Stock-specific FII proof.",
        "primary_replacement": "rbi_fpi_monitoring_parser",
        "secondary_replacement": "shareholding_and_bulk_deal_sources",
        "can_unlock_ready": 0,
        "notes": "Important when foreign ownership caps constrain buying.",
    },
    {
        "source_key": "mcx_bhavcopy",
        "source_role": "OFFICIAL_GATE_SOURCE_PENDING_LIVE_ROWS",
        "rejected_reason": "Official target, but dynamic page/download contract must be proven.",
        "lost_function": "Official MCX EOD OHLC/OI if skipped.",
        "safe_use": "Official EOD commodity confirmation after parser and stable download pass.",
        "blocked_use": "MCX READY without CFTC/global/USDINR context.",
        "primary_replacement": "mcx_bhavcopy_direct_download_parser",
        "secondary_replacement": "broker_or_licensed_mcx_feed",
        "can_unlock_ready": 0,
        "notes": "Parser exists, but live MCX rows are not populated yet.",
    },
    {
        "source_key": "nse_fo_bhavcopy",
        "source_role": "OFFICIAL_GATE_SOURCE_EOD_VERIFIED",
        "rejected_reason": "Live EOD UDiFF is verified, but it is not synchronized intraday IV/Greeks evidence.",
        "lost_function": "Stock futures/options EOD OI, basis, and contract context.",
        "safe_use": "Fresh official EOD OI, volume, basis and contract confirmation with immutable artifact lineage.",
        "blocked_use": "Live IV/Greeks or intraday OI claims.",
        "primary_replacement": "verified_nse_udiff_download",
        "secondary_replacement": "openalgo_live_derivatives_feed",
        "can_unlock_ready": 0,
        "notes": "Live artifact was verified, but compiler activation and symbol-level MWPL evidence are still required.",
    },
    {
        "source_key": "nse_slb",
        "source_role": "OFFICIAL_GATE_SOURCE_PROXY_LIVE_UNVERIFIED",
        "rejected_reason": "Fixture parser exists; live report contract is not verified.",
        "lost_function": "Borrow-pressure and squeeze context.",
        "safe_use": "Proxy context after fresh structured parse.",
        "blocked_use": "Exact stock short-interest claims or standalone READY.",
        "primary_replacement": "verified_nse_slb_report",
        "secondary_replacement": "futures_oi_and_basis_context",
        "can_unlock_ready": 0,
        "notes": "SLB remains a proxy, never exact total short interest.",
    },
    {
        "source_key": "nse_corporate_filings_actions",
        "source_role": "OFFICIAL_DATA_INTEGRITY_LIVE_UNVERIFIED",
        "rejected_reason": "Fixture parser exists; live corporate-action contract is pending verification.",
        "lost_function": "Split, bonus, rights, merger, and event adjustment context.",
        "safe_use": "Data-integrity and event-risk checks after structured parse.",
        "blocked_use": "Unadjusted historical READY across a corporate action.",
        "primary_replacement": "verified_nse_corporate_actions",
        "secondary_replacement": "bse_corporate_actions",
        "can_unlock_ready": 0,
        "notes": "Missing required adjustment can block price-derived evidence.",
    },
    {
        "source_key": "bse_buyback_tender",
        "source_role": "OFFICIAL_EVENT_CONTEXT_XBRL_VERIFIED",
        "rejected_reason": "Official index and linked XBRL are verified, but event terms are contextual rather than directional proof.",
        "lost_function": "Tender buyback and offer-price anchors.",
        "safe_use": "Event context after structured parse.",
        "blocked_use": "Standalone smart-money READY.",
        "primary_replacement": "bse_official_index_plus_xbrl",
        "secondary_replacement": "nse_buyback_filings",
        "can_unlock_ready": 0,
        "notes": "Raw XBRL hashes and revision lineage are persisted; price acceptance and structure remain mandatory.",
    },
    {
        "source_key": "nse_fno_ban",
        "source_role": "OFFICIAL_HARD_VETO_LIVE_VERIFIED",
        "rejected_reason": "None for ban membership; the artifact does not include MWPL utilization.",
        "lost_function": "Official symbol-level F&O ban protection.",
        "safe_use": "Hard veto or valid dated empty-list evidence only.",
        "blocked_use": "Near-MWPL inference or OI reliability percentages.",
        "primary_replacement": "official_nse_fo_secban_artifact",
        "secondary_replacement": "none_hard_gate",
        "can_unlock_ready": 0,
        "notes": "Ban membership is a hard veto; it cannot independently authorize confirmation. MWPL utilization is a separate dataset root.",
    },
    {
        "source_key": "nse_mwpl_percentages",
        "source_role": "OFFICIAL_GATE_SOURCE_UNAVAILABLE",
        "rejected_reason": "No separately verified official symbol-level percentage artifact is registered.",
        "lost_function": "Near-MWPL warning and utilization-based OI reliability.",
        "safe_use": "WAIT_MWPL_PERCENTAGES until a dated schema-valid official artifact is verified.",
        "blocked_use": "Deriving percentages from the ban file or guessed endpoints.",
        "primary_replacement": "separately_verified_official_mwpl_percentage_artifact",
        "secondary_replacement": "none_fail_closed",
        "can_unlock_ready": 0,
        "notes": "The official F&O ban artifact cannot satisfy this contract.",
    },
    {
        "source_key": "nse_large_deals",
        "source_role": "OFFICIAL_GATE_SOURCE_LIVE_UNVERIFIED",
        "rejected_reason": "Fixture parser exists; live official client/side/schema verification is pending.",
        "lost_function": "Deal anchors and large buyer/seller context.",
        "safe_use": "G12 evidence after fresh structured symbol-level parse.",
        "blocked_use": "Standalone READY or unidentified smart-money claims.",
        "primary_replacement": "verified_nse_large_deals_artifact",
        "secondary_replacement": "exchange_filings",
        "can_unlock_ready": 0,
        "notes": "A deal is evidence, not a complete sponsor or price-acceptance decision; compiler authorization is mandatory.",
    },
    {
        "source_key": "amfi_scheme_wise",
        "source_role": "OFFICIAL_DELAYED_CONTEXT",
        "rejected_reason": "Monthly disclosure lag prevents live-flow use.",
        "lost_function": "Scheme-level mutual-fund sponsorship changes.",
        "safe_use": "Swing context with disclosure month and lag label.",
        "blocked_use": "Intraday DII buying proof.",
        "primary_replacement": "verified_amfi_scheme_disclosure",
        "secondary_replacement": "amfi_monthly_portfolio",
        "can_unlock_ready": 0,
        "notes": "Use true prior-month deltas; the first observed month has no inferred change.",
    },
    {
        "source_key": "nse_daily_buyback",
        "source_role": "OFFICIAL_EVENT_CONTEXT_LIVE_UNVERIFIED",
        "rejected_reason": "Fixture parser exists; live daily disclosure contract is pending verification.",
        "lost_function": "Observed open-market buyback execution context.",
        "safe_use": "Corporate demand/event context after structured parse.",
        "blocked_use": "Standalone READY or assumption that all authorized quantity was purchased.",
        "primary_replacement": "verified_nse_daily_buyback",
        "secondary_replacement": "nse_corporate_filings_actions",
        "can_unlock_ready": 0,
        "notes": "Issuer-uploaded disclosure remains contextual and must retain its source disclaimer.",
    },
    {
        "source_key": "bse_takeover_open_offer",
        "source_role": "OFFICIAL_EVENT_CONTEXT_XBRL_VERIFIED",
        "rejected_reason": "Official index and linked pre/post XBRL are verified, but an open offer cannot establish trade direction alone.",
        "lost_function": "Open-offer price anchors and ownership-event context.",
        "safe_use": "Event context after structured offer and date extraction.",
        "blocked_use": "Standalone direction or execution authority.",
        "primary_replacement": "bse_official_index_plus_xbrl",
        "secondary_replacement": "sebi_sast_filings",
        "can_unlock_ready": 0,
        "notes": "Incomplete XBRL remains WAIT_BSE_DETAIL; complete terms create a dated event-price anchor only.",
    },
    {
        "source_key": "kustex_cftc_cot_report",
        "source_role": "REFERENCE_ONLY_ANALYTICS",
        "rejected_reason": "It derives analytics from CFTC data and is not independent market evidence.",
        "lost_function": "Historical COT dashboard, rolling averages, z-scores, and update workflow ideas.",
        "safe_use": "MIT-licensed analytics and regression-reference concepts with attribution.",
        "blocked_use": "Runtime authority, independent proof, source freshness, or READY unlock.",
        "primary_replacement": "trendforge_cftc_point_in_time_analytics",
        "secondary_replacement": "official_cftc_disaggregated_archives",
        "can_unlock_ready": 0,
        "notes": "Do not install its Dash stack or downloader; reproduce useful calculations against official archived rows.",
    },
]


def seed_source_replacement_map_rows(conn: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for row in DEFAULT_SOURCE_REPLACEMENT_MAP:
        conn.execute(
            """
            INSERT OR REPLACE INTO source_replacement_map (
                source_key, source_role, rejected_reason, lost_function, safe_use,
                blocked_use, primary_replacement, secondary_replacement,
                can_unlock_ready, notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["source_key"],
                row["source_role"],
                row["rejected_reason"],
                row["lost_function"],
                row["safe_use"],
                row["blocked_use"],
                row["primary_replacement"],
                row.get("secondary_replacement"),
                row["can_unlock_ready"],
                row.get("notes"),
                now,
            ),
        )


def seed_source_registry() -> None:
    conn = connect()
    now = datetime.now(timezone.utc).isoformat()
    try:
        for name, adapter, authority, freshness, status in DEFAULT_SOURCE_REGISTRY:
            conn.execute(
                """
                INSERT OR IGNORE INTO source_registry (
                    name, adapter, authority, freshness, status, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, adapter, authority, freshness, status, now),
            )
        conn.commit()
    finally:
        conn.close()


def row_to_source_registry(row: sqlite3.Row) -> SourceRegistryRecord:
    return SourceRegistryRecord(
        name=row["name"],
        adapter=row["adapter"],
        authority=DataTrust(row["authority"]),
        freshness=FreshnessState(row["freshness"]),
        status=SourceState(row["status"]),
        lastSuccessAt=row["last_success_at"],
        lastError=row["last_error"],
        updatedAt=row["updated_at"],
    )


def list_source_registry_records() -> list[SourceRegistryRecord]:
    init_db()
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM source_registry ORDER BY name ASC"
        ).fetchall()
    finally:
        conn.close()
    return [row_to_source_registry(row) for row in rows]


def list_source_replacement_map() -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM source_replacement_map ORDER BY source_key ASC"
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def update_source_registry_status(
    name: str,
    *,
    freshness: FreshnessState,
    status: SourceState,
    last_error: str | None = None,
    success: bool = False,
) -> None:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    conn = connect()
    try:
        conn.execute(
            """
            UPDATE source_registry
            SET freshness = ?,
                status = ?,
                last_success_at = CASE WHEN ? THEN ? ELSE last_success_at END,
                last_error = ?,
                updated_at = ?
            WHERE name = ?
            """,
            (
                freshness.value,
                status.value,
                1 if success else 0,
                now,
                last_error,
                now,
                name,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def row_to_source_snapshot(row: sqlite3.Row) -> SourceSnapshotRecord:
    return SourceSnapshotRecord(
        id=row["id"],
        sourceKey=row["source_key"],
        name=row["name"],
        url=row["url"],
        checkState=row["check_state"],
        statusCode=row["status_code"],
        contentHash=row["content_hash"],
        contentLength=row["content_length"],
        lastModified=row["last_modified"],
        etag=row["etag"],
        rawPath=row["raw_path"],
        error=row["error"],
        checkedAt=row["checked_at"],
        previousHash=row["previous_hash"],
        changed=bool(row["changed"]),
    )


def save_source_snapshot(snapshot: SourceSnapshotRecord) -> SourceSnapshotRecord:
    init_db()
    conn = connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO source_snapshots (
                source_key, name, url, check_state, status_code, content_hash,
                content_length, last_modified, etag, raw_path, error,
                checked_at, previous_hash, changed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.source_key,
                snapshot.name,
                snapshot.url,
                snapshot.check_state,
                snapshot.status_code,
                snapshot.content_hash,
                snapshot.content_length,
                snapshot.last_modified,
                snapshot.etag,
                snapshot.raw_path,
                snapshot.error,
                snapshot.checked_at,
                snapshot.previous_hash,
                1 if snapshot.changed else 0,
            ),
        )
        row = conn.execute(
            "SELECT * FROM source_snapshots WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        if snapshot.content_hash:
            conn.execute(
                """
                INSERT OR IGNORE INTO raw_source_archive (
                    source_key, fetched_at, content_hash, content_length,
                    raw_path, last_modified, etag
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.source_key,
                    snapshot.checked_at,
                    snapshot.content_hash,
                    snapshot.content_length,
                    snapshot.raw_path,
                    snapshot.last_modified,
                    snapshot.etag,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return row_to_source_snapshot(row)


def get_latest_source_snapshot(source_key: str) -> SourceSnapshotRecord | None:
    init_db()
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT * FROM source_snapshots
            WHERE source_key = ?
            ORDER BY checked_at DESC, id DESC
            LIMIT 1
            """,
            (source_key,),
        ).fetchone()
    finally:
        conn.close()
    return row_to_source_snapshot(row) if row else None


def get_latest_populated_source_snapshot(
    source_key: str,
) -> SourceSnapshotRecord | None:
    """Return the newest archived payload, ignoring later empty/broken checks."""
    init_db()
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT * FROM source_snapshots
            WHERE source_key = ?
              AND content_hash IS NOT NULL
              AND raw_path IS NOT NULL
              AND check_state NOT IN ('BROKEN', 'SKIPPED')
            ORDER BY checked_at DESC, id DESC
            LIMIT 1
            """,
            (source_key,),
        ).fetchone()
    finally:
        conn.close()
    return row_to_source_snapshot(row) if row else None


def list_source_snapshots(
    source_key: str | None = None, limit: int = 100
) -> list[SourceSnapshotRecord]:
    init_db()
    conn = connect()
    try:
        if source_key:
            rows = conn.execute(
                """
                SELECT * FROM source_snapshots
                WHERE source_key = ?
                ORDER BY checked_at DESC, id DESC
                LIMIT ?
                """,
                (source_key, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM source_snapshots
                ORDER BY checked_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [row_to_source_snapshot(row) for row in rows]


def save_source_fetch_attempts(
    source_key: str, attempt_group_id: str, attempts: list[dict[str, Any]]
) -> int:
    if not attempts:
        return 0
    init_db()
    attempted_at = datetime.now(timezone.utc).isoformat()
    conn = connect()
    try:
        conn.executemany(
            """
            INSERT INTO source_fetch_attempts (
                source_key, attempt_group_id, url, fetcher, stage, result_state,
                status_code, content_type, content_length, duration_ms, error,
                can_unlock_ready, attempted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    source_key,
                    attempt_group_id,
                    str(item["url"]),
                    str(item["fetcher"]),
                    str(item["stage"]),
                    str(item["result_state"]),
                    item.get("status_code"),
                    item.get("content_type"),
                    item.get("content_length"),
                    item.get("duration_ms"),
                    item.get("error"),
                    1 if item.get("can_unlock_ready") else 0,
                    str(item.get("attempted_at") or attempted_at),
                )
                for item in attempts
            ],
        )
        conn.commit()
        return len(attempts)
    finally:
        conn.close()


def list_source_fetch_attempts(
    *, source_key: str | None = None, limit: int = 500
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if source_key:
            rows = conn.execute(
                """
                SELECT * FROM source_fetch_attempts
                WHERE source_key = ?
                ORDER BY attempted_at DESC, id DESC
                LIMIT ?
                """,
                (source_key, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM source_fetch_attempts
                ORDER BY attempted_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def start_source_inventory_audit_run(
    *,
    run_id: str,
    manifest_hash: str,
    total_rows: int,
    selected_fetch_rows: int,
    fetch_enabled: bool,
    browser_enabled: bool,
    started_at: str,
) -> None:
    init_db()
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO source_inventory_audit_runs (
                run_id, manifest_hash, total_rows, selected_fetch_rows,
                fetch_enabled, browser_enabled, status, started_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'RUNNING', ?)
            """,
            (
                run_id,
                manifest_hash,
                total_rows,
                selected_fetch_rows,
                1 if fetch_enabled else 0,
                1 if browser_enabled else 0,
                started_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def save_source_inventory_audit_rows(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    init_db()
    conn = connect()
    try:
        conn.executemany(
            """
            INSERT INTO source_inventory_audit_rows (
                run_id, inventory_id, url, canonical_url, hostname,
                source_role, allowed_jobs_json, provisional_family_id,
                duplicate_of_inventory_id, disposition, fetch_state,
                status_code, content_type, content_length, content_hash,
                raw_path, scraper_state, discovered_urls_json, error,
                resolved_url, mapped_source_keys_json, attempts_json,
                normalization_state, payload_profile_json, quality_issues_json,
                can_unlock_ready, audited_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["run_id"],
                    row["inventory_id"],
                    row["url"],
                    row["canonical_url"],
                    row["hostname"],
                    row["source_role"],
                    row["allowed_jobs_json"],
                    row["provisional_family_id"],
                    row.get("duplicate_of_inventory_id"),
                    row["disposition"],
                    row["fetch_state"],
                    row.get("status_code"),
                    row.get("content_type"),
                    row.get("content_length"),
                    row.get("content_hash"),
                    row.get("raw_path"),
                    row["scraper_state"],
                    row["discovered_urls_json"],
                    row.get("error"),
                    row.get("resolved_url"),
                    row.get("mapped_source_keys_json", "[]"),
                    row.get("attempts_json", "[]"),
                    row.get("normalization_state", "NOT_EVALUATED"),
                    row.get("payload_profile_json", "{}"),
                    row.get("quality_issues_json", "[]"),
                    1 if row.get("can_unlock_ready") else 0,
                    row["audited_at"],
                )
                for row in rows
            ],
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def complete_source_inventory_audit_run(
    *,
    run_id: str,
    status: str,
    completed_at: str,
    error: str | None = None,
    report_path: str | None = None,
) -> None:
    init_db()
    conn = connect()
    try:
        conn.execute(
            """
            UPDATE source_inventory_audit_runs
            SET status = ?, completed_at = ?, error = ?, report_path = ?
            WHERE run_id = ?
            """,
            (status, completed_at, error, report_path, run_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_source_inventory_audit_runs(limit: int = 100) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT * FROM source_inventory_audit_runs
            ORDER BY started_at DESC, run_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def list_source_inventory_audit_rows(
    *, run_id: str | None = None, limit: int = 1000
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if run_id:
            rows = conn.execute(
                """
                SELECT * FROM source_inventory_audit_rows
                WHERE run_id = ?
                ORDER BY inventory_id ASC
                LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM source_inventory_audit_rows
                ORDER BY audited_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def row_to_source_parse_result(row: sqlite3.Row) -> SourceParseResult:
    return SourceParseResult(
        id=row["id"],
        sourceKey=row["source_key"],
        snapshotId=row["snapshot_id"],
        parserState=row["parser_state"],
        dataDate=row["data_date"],
        recordCount=row["record_count"],
        summary=row["summary"],
        output=decode_json(row["output_json"]),
        error=row["error"],
        parsedAt=row["parsed_at"],
    )


def save_source_parse_result(result: SourceParseResult) -> SourceParseResult:
    init_db()
    conn = connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO source_parse_results (
                source_key, snapshot_id, parser_state, data_date, record_count,
                summary, output_json, error, parsed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.source_key,
                result.snapshot_id,
                result.parser_state,
                result.data_date,
                result.record_count,
                result.summary,
                encode_json(result.output),
                result.error,
                result.parsed_at,
            ),
        )
        row = conn.execute(
            "SELECT * FROM source_parse_results WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        conn.commit()
    finally:
        conn.close()
    saved = row_to_source_parse_result(row)
    save_source_parser_output_artifact(saved)
    save_structured_source_rows(saved)
    update_raw_archive_parse_state(saved)
    return saved


def get_latest_source_parse_result(source_key: str) -> SourceParseResult | None:
    init_db()
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT * FROM source_parse_results
            WHERE source_key = ?
            ORDER BY parsed_at DESC, id DESC
            LIMIT 1
            """,
            (source_key,),
        ).fetchone()
    finally:
        conn.close()
    return row_to_source_parse_result(row) if row else None


def list_source_parse_results(
    source_key: str | None = None, limit: int = 100
) -> list[SourceParseResult]:
    init_db()
    conn = connect()
    try:
        if source_key:
            rows = conn.execute(
                """
                SELECT * FROM source_parse_results
                WHERE source_key = ?
                ORDER BY parsed_at DESC, id DESC
                LIMIT ?
                """,
                (source_key, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM source_parse_results
                ORDER BY parsed_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [row_to_source_parse_result(row) for row in rows]


PARSER_VERSION_BY_SOURCE = {
    "nse_bhavcopy_eod": "1.1.0-pr-fallback",
    "nse_trade_to_trade": "1.0.0",
    "kite_derivatives_contract_master": "1.0.0",
    "nse_board_meetings": "1.0.0",
    "nse_most_active_futures": "1.0.0",
    "nse_most_active_options": "1.0.0",
    "nse_ipo_issue_calendar": "1.0.0",
    "nse_pr_market_snapshot": "1.0.0",
    "fred_real_yield_10y": "1.0.0",
    "fred_broad_dollar_index": "1.0.0",
    "eia_weekly_petroleum_stocks": "1.0.0",
    "world_gold_council_oi": "1.0.0",
    "wgc_gold_etf_holdings": "1.0.0",
    "wgc_gold_etf_flows": "1.0.0",
    "sge_daily_report": "1.0.0",
    "tradingeconomics_bdi": "1.1.0",
    "yahoo_bdry_shipping_proxy": "1.0.0",
    "google_trends_india_rss": "1.0.0",
    "crisil_ratings": "1.0.0",
    "icra_ratings": "1.0.0",
    "care_ratings": "1.0.0",
    "google_news_rss": "1.0.0",
    "usda_wasde_cornell": "2.0.0",
    "angelone_instrument_master": "1.0.0",
    "dhan_instrument_master": "1.0.0",
    "nse_index_close_eod": "1.0.0",
    "nse_trading_calendar": "1.0.0",
    "nse_equity_universe": "1.0.1",
    "nse_nifty500_constituents": "1.0.1",
    "nse_nifty50_constituents": "1.0.1",
    "cftc_cot": "1.1.0",
    "nse_fno_ban": "2.0.0-split",
    "nse_mwpl_ban": "1.0.0-compat",
    "nse_mwpl_percentages": "2.0.0-split",
    "nse_participant_oi": "1.0.0",
    "nse_large_deals": "1.0.0",
    "nse_fii_dii": "1.0.0",
    "bse_fii_dii": "1.0.0",
    "bse_participant_oi": "1.0.0",
    "amfi_nav": "1.0.0",
    "bse_bhavcopy_eod": "1.0.0",
    "nse_block_deal_live": "1.0.0",
    "nse_option_chain": "1.0.0",
    "nse_pit_current": "1.0.0",
    "nse_asm": "1.0.0",
    "nse_gsm": "1.0.0",
    "nse_pledge_data": "1.0.0",
    "nse_oi_spurts": "1.0.0",
    "nsdl_fpi_daily": "1.0.0",
    "amfi_monthly_portfolio": "1.0.0",
    "amfi_scheme_wise": "2.0.0",
    "mcx_bhavcopy": "1.0.0",
    "nse_fo_bhavcopy": "1.1.0-integrity",
    "nse_slb": "1.0.0",
    "nse_corporate_filings_actions": "1.0.0",
    "nse_daily_buyback": "1.0.0",
    "bse_buyback_tender": "1.1.0-index+xbrl",
    "bse_takeover_open_offer": "1.1.0-index+xbrl",
    "sebi_pit_sast": "1.0.0",
}


EXPECTED_FREQUENCY_BY_SOURCE = {
    "nse_trade_to_trade": "daily",
    "kite_derivatives_contract_master": "daily",
    "nse_board_meetings": "intraday",
    "nse_most_active_futures": "intraday",
    "nse_most_active_options": "intraday",
    "nse_ipo_issue_calendar": "intraday",
    "nse_pr_market_snapshot": "daily",
    "fred_real_yield_10y": "daily",
    "fred_broad_dollar_index": "daily",
    "eia_weekly_petroleum_stocks": "weekly",
    "world_gold_council_oi": "weekly",
    "wgc_gold_etf_holdings": "weekly",
    "wgc_gold_etf_flows": "weekly",
    "sge_daily_report": "daily",
    "tradingeconomics_bdi": "daily",
    "yahoo_bdry_shipping_proxy": "daily",
    "google_trends_india_rss": "intraday",
    "crisil_ratings": "event_based",
    "icra_ratings": "event_based",
    "care_ratings": "event_based",
    "google_news_rss": "intraday",
    "usda_wasde_cornell": "monthly",
    "angelone_instrument_master": "daily",
    "dhan_instrument_master": "daily",
    "nse_bhavcopy_eod": "daily",
    "nse_index_close_eod": "daily",
    "nse_trading_calendar": "monthly",
    "nse_equity_universe": "daily",
    "nse_nifty500_constituents": "event_based",
    "nse_nifty50_constituents": "event_based",
    "cftc_cot": "weekly",
    "nse_fno_ban": "daily",
    "nse_mwpl_ban": "daily",
    "nse_mwpl_percentages": "daily",
    "nse_participant_oi": "daily",
    "nse_large_deals": "daily",
    "nse_fii_dii": "daily",
    "bse_fii_dii": "daily",
    "bse_participant_oi": "daily",
    "amfi_nav": "daily",
    "bse_bhavcopy_eod": "daily",
    "nse_block_deal_live": "intraday",
    "nse_option_chain": "intraday",
    "nse_pit_current": "daily",
    "nse_asm": "daily",
    "nse_gsm": "daily",
    "nse_pledge_data": "quarterly",
    "nse_oi_spurts": "intraday",
    "nsdl_fpi_daily": "daily",
    "amfi_monthly_portfolio": "monthly",
    "amfi_scheme_wise": "quarterly",
    "mcx_bhavcopy": "daily",
    "nse_fo_bhavcopy": "daily",
    "nse_slb": "daily",
    "nse_corporate_filings_actions": "daily",
    "nse_daily_buyback": "daily",
    "bse_buyback_tender": "daily",
    "bse_takeover_open_offer": "daily",
    "sebi_pit_sast": "daily",
}


def schema_hash_for_output(output: dict[str, Any]) -> str:
    schema: dict[str, Any] = {}
    for key, value in sorted(output.items()):
        if isinstance(value, list):
            first = next((item for item in value if isinstance(item, dict)), None)
            schema[key] = sorted(first.keys()) if first else []
        elif isinstance(value, dict):
            schema[key] = sorted(value.keys())
        else:
            schema[key] = type(value).__name__
    return hashlib.sha256(encode_json(schema).encode("utf-8")).hexdigest()


def save_source_parser_output_artifact(result: SourceParseResult) -> int:
    init_db()
    is_fresh = is_data_date_fresh(result.source_key, result.data_date)
    parser_status = normalize_parser_status(
        source_key=result.source_key,
        parser_state=result.parser_state,
        data_date=result.data_date,
        record_count=result.record_count,
        is_fresh=is_fresh,
    )
    freshness_status = freshness_status_for(is_fresh, result.data_date, parser_status)
    now = datetime.now(timezone.utc).isoformat()
    conn = connect()
    try:
        snapshot = None
        if result.snapshot_id:
            snapshot = conn.execute(
                "SELECT * FROM source_snapshots WHERE id = ?",
                (result.snapshot_id,),
            ).fetchone()
        output_path = result.output.get("outputPath") or result.output.get("rawPath")
        content_hash = (
            snapshot["content_hash"] if snapshot else result.output.get("contentHash")
        )
        source_published_at = snapshot["last_modified"] if snapshot else None
        cursor = conn.execute(
            """
            INSERT INTO source_parser_outputs (
                source_key, parser_name, parser_version, raw_snapshot_id,
                data_date, source_published_at, parser_status, freshness_status,
                record_count, schema_hash, content_hash, output_path,
                error_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.source_key,
                f"{result.source_key}_parser",
                PARSER_VERSION_BY_SOURCE.get(result.source_key, "0.1.0"),
                result.snapshot_id,
                result.data_date,
                source_published_at,
                parser_status,
                freshness_status,
                result.record_count,
                schema_hash_for_output(result.output),
                content_hash,
                output_path,
                encode_json({"error": result.error, "summary": result.summary})
                if result.error
                else None,
                now,
            ),
        )
        output_id = _lastrowid(cursor)
        reason = (
            "fresh structured data"
            if is_fresh
            else stale_reason(result.source_key, result.data_date)
        )
        if parser_status != "STRUCTURED_OK":
            reason = f"{parser_status}: {result.summary}"
        conn.execute(
            """
            INSERT INTO source_freshness_status (
                source_key, expected_frequency, latest_data_date,
                latest_parser_output_id, is_fresh, reason, checked_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_key) DO UPDATE SET
                expected_frequency = excluded.expected_frequency,
                latest_data_date = excluded.latest_data_date,
                latest_parser_output_id = excluded.latest_parser_output_id,
                is_fresh = excluded.is_fresh,
                reason = excluded.reason,
                checked_at = excluded.checked_at
            """,
            (
                result.source_key,
                EXPECTED_FREQUENCY_BY_SOURCE.get(result.source_key, "unknown"),
                result.data_date,
                output_id,
                1 if is_fresh and parser_status == "STRUCTURED_OK" else 0,
                reason,
                now,
            ),
        )
        conn.commit()
        return output_id
    finally:
        conn.close()


def list_source_parser_outputs(
    source_key: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if source_key:
            rows = conn.execute(
                """
                SELECT * FROM source_parser_outputs
                WHERE source_key = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (source_key, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM source_parser_outputs
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def list_source_freshness_status() -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM source_freshness_status ORDER BY source_key ASC"
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def update_raw_archive_parse_state(result: SourceParseResult) -> None:
    if not result.snapshot_id:
        return
    init_db()
    conn = connect()
    try:
        row = conn.execute(
            "SELECT content_hash FROM source_snapshots WHERE id = ?",
            (result.snapshot_id,),
        ).fetchone()
        if row and row["content_hash"]:
            conn.execute(
                """
                UPDATE raw_source_archive
                SET parser_state_after_parse = ?,
                    data_date = ?
                WHERE source_key = ? AND content_hash = ?
                """,
                (
                    result.parser_state,
                    result.data_date,
                    result.source_key,
                    row["content_hash"],
                ),
            )
            conn.commit()
    finally:
        conn.close()


def _rebuild_cftc_features(conn: sqlite3.Connection) -> None:
    from .cftc_analytics import build_cftc_feature_history

    rows = [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM cftc_cot_positions ORDER BY market, report_date"
        ).fetchall()
    ]
    features = build_cftc_feature_history(rows)
    conn.execute("DELETE FROM cftc_cot_features")
    computed_at = datetime.now(timezone.utc).isoformat()
    for feature in features:
        conn.execute(
            """
            INSERT INTO cftc_cot_features (
                market, contract_market_code, report_date, feature_version,
                observation_count, position_state, crowding_state,
                position_price_divergence, payload_json, computed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feature["market"],
                feature.get("contractMarketCode"),
                feature["reportDate"],
                feature["featureVersion"],
                feature["observationCount"],
                feature["positionState"],
                feature["crowdingState"],
                feature["positionPriceDivergence"],
                json.dumps(feature, separators=(",", ":")),
                computed_at,
            ),
        )


def save_structured_source_rows(result: SourceParseResult) -> None:
    if result.parser_state != "PARSED_STRUCTURED":
        return
    source_key = result.source_key
    output = result.output or {}
    init_db()
    conn = connect()
    try:
        if source_key == "nse_bhavcopy_eod":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO nse_cash_eod (
                        source_parse_id, trade_date, symbol, series, isin,
                        open, high, low, close, previous_close, volume,
                        traded_value, trade_count, advance_state, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("tradeDate") or result.data_date,
                        item.get("symbol"),
                        item.get("series"),
                        item.get("isin"),
                        item.get("open"),
                        item.get("high"),
                        item.get("low"),
                        item.get("close"),
                        item.get("previousClose"),
                        item.get("volume", 0),
                        item.get("tradedValue", 0),
                        item.get("tradeCount", 0),
                        item.get("advanceState"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "nse_index_close_eod":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO nse_index_eod (
                        source_parse_id, index_name, index_date, open, high,
                        low, close, points_change, change_percent, volume,
                        turnover_crore, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("indexName"),
                        item.get("indexDate") or result.data_date,
                        item.get("open"),
                        item.get("high"),
                        item.get("low"),
                        item.get("close"),
                        item.get("pointsChange", 0),
                        item.get("changePercent", 0),
                        item.get("volume", 0),
                        item.get("turnoverCrore", 0),
                        result.parsed_at,
                    ),
                )
        elif source_key == "nse_trading_calendar":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO exchange_calendar_days (
                        source_parse_id, exchange, segment, trading_date, state,
                        description, weekday, morning_session, evening_session,
                        data_date, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("exchange", "NSE"),
                        item.get("segment"),
                        item.get("tradingDate"),
                        item.get("state"),
                        item.get("description"),
                        item.get("weekDay"),
                        item.get("morningSession"),
                        item.get("eveningSession"),
                        result.data_date,
                        result.parsed_at,
                    ),
                )
            for item in output.get("coverage", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO exchange_calendar_coverage (
                        source_parse_id, exchange, segment, calendar_year,
                        valid_from, valid_to, data_date, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("exchange", "NSE"),
                        item.get("segment"),
                        item.get("year"),
                        item.get("validFrom"),
                        item.get("validTo"),
                        result.data_date,
                        result.parsed_at,
                    ),
                )
        elif source_key == "nse_equity_universe":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO nse_instruments (
                        source_parse_id, data_date, symbol, company, series,
                        listing_date, paid_up_value, market_lot, isin,
                        face_value, active, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        result.data_date,
                        item.get("symbol"),
                        item.get("company"),
                        item.get("series"),
                        item.get("listingDate"),
                        item.get("paidUpValue"),
                        item.get("marketLot"),
                        item.get("isin"),
                        item.get("faceValue"),
                        1 if item.get("active", True) else 0,
                        result.parsed_at,
                    ),
                )
        elif source_key in {"nse_nifty50_constituents", "nse_nifty500_constituents"}:
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO nse_sector_membership (
                        source_parse_id, data_date, symbol, company, industry,
                        series, isin, index_membership, active, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        result.data_date,
                        item.get("symbol"),
                        item.get("company"),
                        item.get("industry"),
                        item.get("series"),
                        item.get("isin"),
                        item.get("indexMembership"),
                        1 if item.get("active", True) else 0,
                        result.parsed_at,
                    ),
                )
        elif source_key in {"nse_fno_ban", "nse_mwpl_ban", "nse_mwpl_percentages"}:
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO mwpl_snapshots (
                        source_parse_id, data_date, symbol, mwpl_percent,
                        total_oi, mwpl, ban_status, is_banned, oi_reliable, parsed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        result.data_date,
                        item.get("symbol"),
                        item.get("mwplPercent"),
                        item.get("totalOi"),
                        item.get("mwpl"),
                        item.get("banStatus"),
                        1 if item.get("isBanned") else 0,
                        1 if item.get("oiReliable") else 0,
                        result.parsed_at,
                    ),
                )
        elif source_key in {"fred_real_yield_10y", "fred_broad_dollar_index"}:
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO macro_series_observations (
                        source_parse_id, source_key, series_id, observation_date,
                        value, units, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        source_key,
                        item.get("seriesId"),
                        item.get("observationDate"),
                        item.get("value"),
                        item.get("units"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "amfi_nav":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO amfi_nav_observations (
                        source_parse_id, scheme_code, isin_growth,
                        isin_reinvestment, scheme_name, fund_house, category,
                        nav, nav_date, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("schemeCode"),
                        item.get("isinGrowth"),
                        item.get("isinReinvestment"),
                        item.get("schemeName"),
                        item.get("fundHouse"),
                        item.get("category"),
                        item.get("nav"),
                        item.get("navDate"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "nse_fii_dii":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO institutional_cash_flows (
                        source_parse_id, data_date, category, buy_value_crore,
                        sell_value_crore, net_value_crore, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("dataDate"),
                        item.get("category"),
                        item.get("buyValueCrore"),
                        item.get("sellValueCrore"),
                        item.get("netValueCrore"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "nse_option_chain":
            for index, item in enumerate(output.get("rows", [])):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO option_chain_observations (
                        source_parse_id, source_row_index, data_date, symbol,
                        expiry, strike, option_type, open_interest, oi_change,
                        volume, iv, last_price, underlying_value,
                        observed_timestamp, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        index,
                        result.data_date,
                        item.get("symbol"),
                        item.get("expiry"),
                        item.get("strike"),
                        item.get("optionType"),
                        item.get("openInterest"),
                        item.get("oiChange"),
                        item.get("volume"),
                        item.get("iv"),
                        item.get("lastPrice"),
                        item.get("underlyingValue"),
                        item.get("timestamp"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "nse_pit_current":
            for index, item in enumerate(output.get("rows", [])):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO nse_pit_current_events (
                        source_parse_id, source_row_index, symbol, company,
                        entity, transaction_type, security_type, quantity,
                        value, post_shares, post_holding_percent, event_date,
                        xbrl_link, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        index,
                        item.get("symbol"),
                        item.get("company"),
                        item.get("entity"),
                        item.get("transactionType"),
                        item.get("securityType"),
                        item.get("quantity"),
                        item.get("value"),
                        item.get("postShares"),
                        item.get("postHoldingPercent"),
                        item.get("eventDate"),
                        item.get("xbrlLink"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "bse_bhavcopy_eod":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO bse_cash_eod (
                        source_parse_id, data_date, scrip_code, name, open,
                        high, low, close, volume, turnover, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        result.data_date,
                        item.get("scripCode"),
                        item.get("name"),
                        item.get("open"),
                        item.get("high"),
                        item.get("low"),
                        item.get("close"),
                        item.get("volume"),
                        item.get("turnover"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "nse_block_deal_live":
            for index, item in enumerate(output.get("rows", [])):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO nse_block_deal_live_rows (
                        source_parse_id, source_row_index, data_date, symbol,
                        session, last_price, quantity, value, order_type,
                        observed_timestamp, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        index,
                        result.data_date,
                        item.get("symbol"),
                        item.get("session"),
                        item.get("lastPrice"),
                        item.get("quantity"),
                        item.get("value"),
                        item.get("orderType"),
                        item.get("timestamp"),
                        result.parsed_at,
                    ),
                )
        elif source_key in {"nse_asm", "nse_gsm"}:
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO surveillance_actions (
                        source_parse_id, source_key, data_date, symbol, company,
                        isin, measure, stage, surveillance_code, description,
                        effective_date, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        source_key,
                        result.data_date,
                        item.get("symbol"),
                        item.get("company"),
                        item.get("isin"),
                        item.get("measure"),
                        item.get("stage"),
                        item.get("code"),
                        item.get("description"),
                        item.get("effectiveDate"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "nse_pledge_data":
            for index, item in enumerate(output.get("rows", [])):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO promoter_pledge_source_rows (
                        source_parse_id, source_row_index, reporting_date,
                        company, broadcast_date,
                        pledged_shares, pledged_percent, promoter_holding_percent,
                        promoter_holding_shares, issued_shares,
                        symbol_mapping_status, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        index,
                        item.get("reportingDate"),
                        item.get("company"),
                        item.get("broadcastDate"),
                        item.get("pledgedShares"),
                        item.get("pledgedPercent"),
                        item.get("promoterHoldingPercent"),
                        item.get("promoterHoldingShares"),
                        item.get("issuedShares"),
                        "PENDING",
                        result.parsed_at,
                    ),
                )
        elif source_key == "nse_oi_spurts":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO oi_spurt_snapshots (
                        source_parse_id, data_date, symbol, latest_oi,
                        previous_oi, oi_change, oi_change_percent, volume,
                        underlying_value, previous_trading_date, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("currentTradingDate") or result.data_date,
                        item.get("symbol"),
                        item.get("latestOi"),
                        item.get("previousOi"),
                        item.get("oiChange"),
                        item.get("oiChangePercent"),
                        item.get("volume"),
                        item.get("underlyingValue"),
                        item.get("previousTradingDate"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "nsdl_fpi_daily":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO nsdl_fpi_daily_rows (
                        source_parse_id, data_date, table_index, row_index,
                        table_type, category, route_or_product,
                        gross_purchases_crore, gross_sales_crore,
                        net_investment_crore, net_investment_usd_million,
                        conversion_usd_inr, buy_contracts, buy_value_crore,
                        sell_contracts, sell_value_crore,
                        open_interest_contracts, open_interest_value_crore,
                        cells_json, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("reportingDate") or result.data_date,
                        item.get("tableIndex"),
                        item.get("rowIndex"),
                        item.get("tableType"),
                        item.get("category"),
                        item.get("routeOrProduct"),
                        item.get("grossPurchasesCrore"),
                        item.get("grossSalesCrore"),
                        item.get("netInvestmentCrore"),
                        item.get("netInvestmentUsdMillion"),
                        item.get("conversionUsdInr"),
                        item.get("buyContracts"),
                        item.get("buyValueCrore"),
                        item.get("sellContracts"),
                        item.get("sellValueCrore"),
                        item.get("openInterestContracts"),
                        item.get("openInterestValueCrore"),
                        encode_json(item.get("cells", [])),
                        result.parsed_at,
                    ),
                )
        elif source_key == "eia_weekly_petroleum_stocks":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO eia_petroleum_weekly (
                        source_parse_id, source_key, data_date, metric_key,
                        metric_name, previous_week_date, year_ago_date,
                        current_value, previous_week_value, weekly_change,
                        weekly_percent_change, year_ago_value, year_change,
                        year_percent_change, units, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        source_key,
                        result.data_date,
                        item.get("metricKey"),
                        item.get("metricName"),
                        item.get("previousWeekDate"),
                        item.get("yearAgoDate"),
                        item.get("currentValue"),
                        item.get("previousWeekValue"),
                        item.get("weeklyChange"),
                        item.get("weeklyPercentChange"),
                        item.get("yearAgoValue"),
                        item.get("yearChange"),
                        item.get("yearPercentChange"),
                        item.get("units"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "world_gold_council_oi":
            conn.execute("DELETE FROM wgc_gold_oi_observations")
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO wgc_gold_oi_observations (
                        source_parse_id, venue, observation_date,
                        open_interest_usd_bn, frequency, units, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("venue"),
                        item.get("observationDate"),
                        item.get("openInterestUsdBn"),
                        item.get("frequency"),
                        item.get("units"),
                        result.parsed_at,
                    ),
                )
        elif source_key in {"wgc_gold_etf_holdings", "wgc_gold_etf_flows"}:
            conn.execute(
                "DELETE FROM wgc_gold_etf_observations WHERE source_key = ?",
                (source_key,),
            )
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO wgc_gold_etf_observations (
                        source_parse_id, source_key, dataset, period,
                        observation_date, region, value, units,
                        gold_price_usd_oz, is_derived, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        source_key,
                        item.get("dataset"),
                        item.get("period"),
                        item.get("observationDate"),
                        item.get("region"),
                        item.get("value"),
                        item.get("units"),
                        item.get("goldPriceUsdOz"),
                        1 if item.get("isDerived") else 0,
                        result.parsed_at,
                    ),
                )
        elif source_key == "sge_daily_report":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO sge_daily_observations (
                        source_parse_id, trade_date, contract, open, high, low,
                        close, change, change_percent, weighted_average_price,
                        volume_kg, amount_cny, open_interest_lots, direction,
                        delivery_volume_lots, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("tradeDate"),
                        item.get("contract"),
                        item.get("open"),
                        item.get("high"),
                        item.get("low"),
                        item.get("close"),
                        item.get("change"),
                        item.get("changePercent"),
                        item.get("weightedAveragePrice"),
                        item.get("volumeKg"),
                        item.get("amountCny"),
                        item.get("openInterestLots"),
                        item.get("direction"),
                        item.get("deliveryVolumeLots"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "cftc_cot":
            for item in output.get("positionHistory") or output.get("positions", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cftc_cot_positions (
                        source_parse_id, market, contract_market_code, report_date, open_interest,
                        managed_money_long, managed_money_short, managed_money_net,
                        commercial_long, commercial_short, commercial_net,
                        non_reportable_long, non_reportable_short, non_reportable_net,
                        swap_dealer_long, swap_dealer_short, swap_dealer_net,
                        other_reportable_long, other_reportable_short, other_reportable_net,
                        parsed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("market"),
                        item.get("contractMarketCode"),
                        item.get("reportDate") or result.data_date,
                        item.get("openInterest"),
                        item.get("managedMoneyLong"),
                        item.get("managedMoneyShort"),
                        item.get("managedMoneyNet"),
                        item.get("commercialLong"),
                        item.get("commercialShort"),
                        item.get("commercialNet"),
                        item.get("nonReportableLong"),
                        item.get("nonReportableShort"),
                        item.get("nonReportableNet"),
                        item.get("swapDealerLong"),
                        item.get("swapDealerShort"),
                        item.get("swapDealerNet"),
                        item.get("otherReportableLong"),
                        item.get("otherReportableShort"),
                        item.get("otherReportableNet"),
                        result.parsed_at,
                    ),
                )
            _rebuild_cftc_features(conn)
        elif source_key == "nse_participant_oi":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO participant_oi_daily (
                        source_parse_id, data_date, participant, futures_long_oi,
                        futures_short_oi, futures_net_oi, options_long_oi,
                        options_short_oi, options_net_oi, total_net_oi, parsed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        result.data_date,
                        item.get("participant"),
                        item.get("futuresLongOi"),
                        item.get("futuresShortOi"),
                        item.get("futuresNetOi"),
                        item.get("optionsLongOi"),
                        item.get("optionsShortOi"),
                        item.get("optionsNetOi"),
                        item.get("totalNetOi"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "nse_large_deals":
            for item in output.get("deals", []):
                conn.execute(
                    """
                    INSERT INTO bulk_block_deals (
                        source_parse_id, data_date, symbol, deal_type, buyer,
                        seller, quantity, price, value, close_price, premium_pct,
                        deal_mode, parsed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("date") or result.data_date,
                        item.get("symbol"),
                        item.get("dealType"),
                        item.get("buyer"),
                        item.get("seller"),
                        item.get("quantity"),
                        item.get("price"),
                        item.get("value"),
                        item.get("closePrice"),
                        item.get("premiumPct"),
                        item.get("dealMode"),
                        result.parsed_at,
                    ),
                )
        elif (
            source_key == "amfi_scheme_wise"
            and output.get("datasetKind") == "AMFI_SCHEME_WISE_QUARTERLY_EXPOSURE"
        ):
            for item in output.get("exposures", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO amfi_scheme_exposure_rows (
                        source_parse_id, source_row_index, quarter_date, quarter_name, mf_id, amc,
                        scheme_id, scheme, isin, company_name, security_type,
                        market_value, market_value_percentage, parsed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("sourceRowIndex"),
                        item.get("quarterDate"),
                        item.get("quarterName"),
                        item.get("mfId"),
                        item.get("amc"),
                        item.get("schemeId"),
                        item.get("scheme"),
                        item.get("isin"),
                        item.get("companyName"),
                        item.get("securityType"),
                        item.get("marketValue"),
                        item.get("marketValuePercentage"),
                        result.parsed_at,
                    ),
                )
        elif source_key in {"amfi_monthly_portfolio", "amfi_scheme_wise"}:
            disclosure_month = output.get("month")
            previous_month_row = conn.execute(
                "SELECT MAX(disclosure_month) AS month FROM amfi_scheme_holdings WHERE disclosure_month < ?",
                (disclosure_month or "",),
            ).fetchone()
            previous_month = previous_month_row["month"] if previous_month_row else None
            previous_positions: dict[tuple[str, str, str, str], dict[str, Any]] = {}
            if previous_month:
                for previous in conn.execute(
                    """
                    SELECT amc, scheme, isin, stock, quantity
                    FROM amfi_scheme_holdings
                    WHERE disclosure_month = ?
                    """,
                    (previous_month,),
                ).fetchall():
                    key = (
                        str(previous["amc"] or "").strip().upper(),
                        str(previous["scheme"] or "").strip().upper(),
                        str(previous["isin"] or "").strip().upper(),
                        str(previous["stock"] or "").strip().upper(),
                    )
                    previous_positions[key] = {
                        "stock": key[3],
                        "isin": key[2],
                        "quantity": int(previous["quantity"] or 0),
                    }
            for item in output.get("holdings", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO amfi_scheme_holdings (
                        source_parse_id, disclosure_month, amc, scheme, isin,
                        stock, quantity, market_value, percent_aum, parsed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        item.get("month"),
                        item.get("amc"),
                        item.get("scheme"),
                        item.get("isin"),
                        item.get("stock"),
                        item.get("quantity"),
                        item.get("marketValue"),
                        item.get("percentAum"),
                        result.parsed_at,
                    ),
                )
            current_positions: dict[tuple[str, str, str, str], dict[str, Any]] = {}
            for item in output.get("holdings", []):
                stock = str(item.get("stock") or "").strip().upper()
                if not stock:
                    continue
                key = (
                    str(item.get("amc") or "").strip().upper(),
                    str(item.get("scheme") or "").strip().upper(),
                    str(item.get("isin") or "").strip().upper(),
                    stock,
                )
                position = current_positions.setdefault(
                    key,
                    {"stock": stock, "isin": key[2], "quantity": 0},
                )
                position["quantity"] += int(item.get("quantity") or 0)
            deltas_by_stock: dict[str, dict[str, Any]] = {}
            if previous_month:
                for key in set(previous_positions) | set(current_positions):
                    previous = previous_positions.get(key)
                    current = current_positions.get(key)
                    stock = (
                        str((current or previous or {}).get("stock") or "")
                        .strip()
                        .upper()
                    )
                    if not stock:
                        continue
                    previous_quantity = int((previous or {}).get("quantity") or 0)
                    current_quantity = int((current or {}).get("quantity") or 0)
                    delta = deltas_by_stock.setdefault(
                        stock,
                        {
                            "isin": (current or previous or {}).get("isin") or "",
                            "added": 0,
                            "reduced": 0,
                            "exited": 0,
                            "quantity": 0,
                        },
                    )
                    if previous_quantity <= 0 < current_quantity:
                        delta["added"] += 1
                    elif previous_quantity > 0 and current_quantity == 0:
                        delta["exited"] += 1
                    elif 0 < current_quantity < previous_quantity:
                        delta["reduced"] += 1
                    delta["quantity"] += current_quantity - previous_quantity
            for stock, delta in sorted(deltas_by_stock.items()):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO amfi_stock_deltas (
                        disclosure_month, stock, isin, schemes_added, schemes_reduced,
                        schemes_exited, net_quantity_change, parsed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        disclosure_month,
                        stock,
                        delta["isin"],
                        delta["added"],
                        delta["reduced"],
                        delta["exited"],
                        delta["quantity"],
                        result.parsed_at,
                    ),
                )
        elif source_key == "mcx_bhavcopy":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO mcx_bhavcopy_daily (
                        source_parse_id, data_date, symbol, expiry, close_price,
                        volume, open_interest, oi_change, parsed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        result.data_date,
                        item.get("symbol"),
                        item.get("expiry"),
                        item.get("close"),
                        item.get("volume"),
                        item.get("openInterest"),
                        item.get("oiChange"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "nse_fo_bhavcopy":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO fo_derivatives_daily (
                        source_parse_id, data_date, symbol, instrument, expiry,
                        strike, option_type, close_price, previous_close,
                        underlying_price, basis, basis_percent, open_interest,
                        oi_change, volume, oi_quadrant, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        result.data_date,
                        item.get("symbol"),
                        item.get("instrument"),
                        item.get("expiry"),
                        item.get("strike"),
                        item.get("optionType"),
                        item.get("close"),
                        item.get("previousClose"),
                        item.get("underlyingPrice"),
                        item.get("basis"),
                        item.get("basisPercent"),
                        item.get("openInterest"),
                        item.get("oiChange"),
                        item.get("volume"),
                        item.get("oiQuadrant"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "nse_slb":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO slb_snapshots (
                        source_parse_id, data_date, symbol, open_positions,
                        volume, borrow_rate, turnover, pressure, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        result.data_date,
                        item.get("symbol"),
                        item.get("openPositions"),
                        item.get("volume"),
                        item.get("borrowRate"),
                        item.get("turnover"),
                        item.get("pressure"),
                        result.parsed_at,
                    ),
                )
        elif source_key in {
            "nse_corporate_filings_actions",
            "nse_daily_buyback",
            "bse_buyback_tender",
            "bse_takeover_open_offer",
        }:
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT INTO corporate_events (
                        source_parse_id, source_key, data_date, symbol, company,
                        action_type, announcement_date, ex_date, record_date,
                        start_date, end_date, offer_price, quantity, action_class,
                        ratio_numerator, ratio_denominator, cash_amount,
                        adjustment_factor, predecessor_symbol, successor_symbol,
                        continuity_confirmed, revision_status, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        source_key,
                        result.data_date,
                        item.get("symbol"),
                        item.get("company"),
                        item.get("actionType"),
                        item.get("announcementDate"),
                        item.get("exDate"),
                        item.get("recordDate"),
                        item.get("startDate"),
                        item.get("endDate"),
                        item.get("offerPrice"),
                        item.get("quantity"),
                        item.get("actionClass"),
                        item.get("ratioNumerator"),
                        item.get("ratioDenominator"),
                        item.get("cashAmount"),
                        item.get("priceAdjustmentFactor"),
                        item.get("predecessorSymbol"),
                        item.get("successorSymbol"),
                        1
                        if item.get("continuityConfirmed") is True
                        else 0
                        if item.get("continuityConfirmed") is False
                        else None,
                        item.get("revisionStatus", "UNKNOWN"),
                        result.parsed_at,
                    ),
                )
        elif source_key == "sebi_pit_sast":
            for item in output.get("rows", []):
                conn.execute(
                    """
                    INSERT INTO sebi_disclosures (
                        source_parse_id, data_date, symbol, isin, entity,
                        relationship, transaction_type, event_date, disclosure_date,
                        quantity, price, pre_holding, post_holding, parsed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        result.data_date,
                        item.get("symbol"),
                        item.get("isin"),
                        item.get("entity"),
                        item.get("relationship"),
                        item.get("transactionType"),
                        item.get("eventDate"),
                        item.get("disclosureDate"),
                        item.get("quantity"),
                        item.get("price"),
                        item.get("preHolding"),
                        item.get("postHolding"),
                        result.parsed_at,
                    ),
                )
        conn.commit()
    finally:
        conn.close()


def list_raw_source_archive(
    source_key: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if source_key:
            rows = conn.execute(
                """
                SELECT * FROM raw_source_archive
                WHERE source_key = ?
                ORDER BY fetched_at DESC, id DESC
                LIMIT ?
                """,
                (source_key, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM raw_source_archive
                ORDER BY fetched_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


DOMAIN_TABLE_BY_SOURCE = {
    "nse_bhavcopy_eod": "nse_cash_eod",
    "nse_index_close_eod": "nse_index_eod",
    "nse_trading_calendar": "exchange_calendar_days",
    "nse_equity_universe": "nse_instruments",
    "nse_nifty500_constituents": "nse_sector_membership",
    "nse_nifty50_constituents": "nse_sector_membership",
    "nse_fno_ban": "mwpl_snapshots",
    "nse_mwpl_ban": "mwpl_snapshots",
    "nse_mwpl_percentages": "mwpl_snapshots",
    "cftc_cot": "cftc_cot_positions",
    "nse_participant_oi": "participant_oi_daily",
    "nse_large_deals": "bulk_block_deals",
    "nse_fii_dii": "institutional_cash_flows",
    "amfi_nav": "amfi_nav_observations",
    "bse_bhavcopy_eod": "bse_cash_eod",
    "nse_block_deal_live": "nse_block_deal_live_rows",
    "nse_option_chain": "option_chain_observations",
    "nse_pit_current": "nse_pit_current_events",
    "nse_asm": "surveillance_actions",
    "nse_gsm": "surveillance_actions",
    "nse_pledge_data": "promoter_pledge_source_rows",
    "nse_oi_spurts": "oi_spurt_snapshots",
    "nsdl_fpi_daily": "nsdl_fpi_daily_rows",
    "amfi_monthly_portfolio": "amfi_scheme_holdings",
    "amfi_scheme_wise": "amfi_scheme_exposure_rows",
    "mcx_bhavcopy": "mcx_bhavcopy_daily",
    "nse_fo_bhavcopy": "fo_derivatives_daily",
    "nse_slb": "slb_snapshots",
    "nse_corporate_filings_actions": "corporate_events",
    "nse_daily_buyback": "corporate_events",
    "bse_buyback_tender": "corporate_offer_events",
    "bse_takeover_open_offer": "corporate_offer_events",
    "sebi_pit_sast": "sebi_disclosures",
    "fred_real_yield_10y": "macro_series_observations",
    "fred_broad_dollar_index": "macro_series_observations",
    "eia_weekly_petroleum_stocks": "eia_petroleum_weekly",
    "world_gold_council_oi": "wgc_gold_oi_observations",
    "wgc_gold_etf_holdings": "wgc_gold_etf_observations",
    "wgc_gold_etf_flows": "wgc_gold_etf_observations",
    "sge_daily_report": "sge_daily_observations",
}

SYMBOL_COLUMN_BY_SOURCE = {
    "nse_bhavcopy_eod": ("nse_cash_eod", "symbol"),
    "nse_equity_universe": ("nse_instruments", "symbol"),
    "nse_nifty500_constituents": ("nse_sector_membership", "symbol"),
    "nse_nifty50_constituents": ("nse_sector_membership", "symbol"),
    "nse_fno_ban": ("mwpl_snapshots", "symbol"),
    "nse_mwpl_ban": ("mwpl_snapshots", "symbol"),
    "nse_mwpl_percentages": ("mwpl_snapshots", "symbol"),
    "nse_fo_bhavcopy": ("fo_derivatives_daily", "symbol"),
    "nse_slb": ("slb_snapshots", "symbol"),
    "nse_large_deals": ("bulk_block_deals", "symbol"),
    "nse_block_deal_live": ("nse_block_deal_live_rows", "symbol"),
    "nse_option_chain": ("option_chain_observations", "symbol"),
    "nse_pit_current": ("nse_pit_current_events", "symbol"),
    "nse_asm": ("surveillance_actions", "symbol"),
    "nse_gsm": ("surveillance_actions", "symbol"),
    "nse_oi_spurts": ("oi_spurt_snapshots", "symbol"),
    "amfi_monthly_portfolio": ("amfi_scheme_holdings", "stock"),
    "sebi_pit_sast": ("sebi_disclosures", "symbol"),
    "mcx_bhavcopy": ("mcx_bhavcopy_daily", "symbol"),
    "nse_corporate_filings_actions": ("corporate_events", "symbol"),
    "nse_daily_buyback": ("corporate_events", "symbol"),
    "bse_buyback_tender": ("corporate_offer_events", "symbol"),
    "bse_takeover_open_offer": ("corporate_offer_events", "symbol"),
}


def source_has_symbol_evidence(source_key: str, symbol: str) -> bool:
    mapping = SYMBOL_COLUMN_BY_SOURCE.get(source_key)
    if mapping is None:
        return False
    table, column = mapping
    normalized = symbol.strip().upper().replace("MCX ", "")
    init_db()
    conn = connect()
    try:
        if table == "surveillance_actions":
            row = conn.execute(
                f"SELECT 1 FROM {table} WHERE source_key = ? AND UPPER({column}) = ? LIMIT 1",
                (source_key, normalized),
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT 1 FROM {table} WHERE UPPER({column}) = ? LIMIT 1",
                (normalized,),
            ).fetchone()
    finally:
        conn.close()
    return row is not None


def list_current_surveillance_actions(symbol: str) -> list[dict[str, Any]]:
    """Return ASM/GSM rows only from each source's latest parsed snapshot."""
    normalized = symbol.strip().upper()
    init_db()
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT action.*
            FROM surveillance_actions AS action
            WHERE UPPER(action.symbol) = ?
              AND action.source_parse_id = (
                  SELECT result.id
                  FROM source_parse_results AS result
                  WHERE result.source_key = action.source_key
                  ORDER BY result.parsed_at DESC, result.id DESC
                  LIMIT 1
              )
            ORDER BY action.source_key, action.measure
            """,
            (normalized,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def list_source_domain_rows(source_key: str, limit: int = 100) -> list[dict[str, Any]]:
    table = DOMAIN_TABLE_BY_SOURCE.get(source_key)
    if table is None:
        return []
    init_db()
    conn = connect()
    try:
        if table == "surveillance_actions":
            rows = conn.execute(
                "SELECT * FROM surveillance_actions WHERE source_key = ? ORDER BY id DESC LIMIT ?",
                (source_key, limit),
            ).fetchall()
        elif table == "corporate_events":
            rows = conn.execute(
                "SELECT * FROM corporate_events WHERE source_key = ? ORDER BY id DESC LIMIT ?",
                (source_key, limit),
            ).fetchall()
        elif table == "macro_series_observations":
            rows = conn.execute(
                """
                SELECT * FROM macro_series_observations
                WHERE source_key = ?
                ORDER BY observation_date DESC
                LIMIT ?
                """,
                (source_key, limit),
            ).fetchall()
        elif table == "wgc_gold_etf_observations":
            rows = conn.execute(
                """
                SELECT * FROM wgc_gold_etf_observations
                WHERE source_key = ?
                ORDER BY observation_date DESC, is_derived DESC, region
                LIMIT ?
                """,
                (source_key, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def list_cftc_analytics(
    *,
    market: str | None = None,
    as_of: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    init_db()
    conditions: list[str] = []
    values: list[Any] = []
    if market:
        conditions.append("UPPER(market) LIKE ?")
        values.append(f"%{market.upper()}%")
    if as_of:
        conditions.append("report_date <= ?")
        values.append(as_of[:10])
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT payload_json FROM cftc_cot_features {where} ORDER BY report_date DESC, market LIMIT ?"
    values.append(limit)
    conn = connect()
    try:
        rows = conn.execute(query, values).fetchall()
    finally:
        conn.close()
    return [json.loads(row["payload_json"]) for row in rows]


def create_scanner_run(
    universe: str, trigger: str, gate_readiness_payload: dict, source_health: dict
) -> int:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    run_hash = hashlib.sha256(
        f"{universe}:{trigger}:{now}".encode("utf-8")
    ).hexdigest()[:16]
    conn = connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO scanner_runs (
                run_hash, universe, trigger, status, started_at,
                gate_readiness_json, source_health_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_hash,
                universe,
                trigger,
                "RUNNING",
                now,
                encode_json(gate_readiness_payload),
                encode_json(source_health),
            ),
        )
        conn.commit()
        return _lastrowid(cursor)
    finally:
        conn.close()


def finish_scanner_run(
    run_id: int,
    *,
    status: str,
    candidate_count: int = 0,
    paused_reason: str | None = None,
) -> None:
    init_db()
    conn = connect()
    try:
        conn.execute(
            """
            UPDATE scanner_runs
            SET status = ?, candidate_count = ?, paused_reason = ?, finished_at = ?
            WHERE id = ?
            """,
            (
                status,
                candidate_count,
                paused_reason,
                datetime.now(timezone.utc).isoformat(),
                run_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def save_scanner_candidate(run_id: int, payload: dict[str, Any]) -> None:
    init_db()
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO scanner_candidates (
                run_id, symbol, candidate_type, final_state, status_group,
                quality_score, gate_ratio, payload_json, outcome_label,
                false_screen_reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                payload.get("symbol", "UNKNOWN"),
                payload.get("type"),
                payload.get("state")
                or payload.get("finalState")
                or "WAIT_SOURCE_CONFIRMATION",
                payload.get("statusGroup") or payload.get("status_group") or "wait",
                payload.get("quality"),
                payload.get("gateRatio"),
                encode_json(payload),
                payload.get("outcomeLabel"),
                payload.get("falseScreenReason"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def save_gate_decision(
    *,
    run_id: str,
    symbol: str | None,
    gate_key: str,
    decision: str,
    state: str,
    required_sources: list[dict[str, Any]],
    reasons: list[str],
) -> int:
    init_db()
    conn = connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO gate_decisions (
                run_id, symbol, gate_key, decision, state,
                required_sources_json, reasons_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                symbol,
                gate_key,
                decision,
                state,
                encode_json(required_sources),
                encode_json(reasons),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return _lastrowid(cursor)
    finally:
        conn.close()


def list_gate_decisions(
    run_id: str | None = None, limit: int = 200
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if run_id:
            rows = conn.execute(
                """
                SELECT * FROM gate_decisions
                WHERE run_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM gate_decisions
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    results: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["required_sources"] = decode_json(item.pop("required_sources_json"))
        item["reasons"] = decode_json(item.pop("reasons_json"))
        results.append(item)
    return results


def list_scanner_runs(limit: int = 100) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM scanner_runs ORDER BY started_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def list_scanner_candidates(
    run_id: int | None = None, limit: int = 200
) -> list[dict[str, Any]]:
    init_db()
    conn = connect()
    try:
        if run_id is None:
            rows = conn.execute(
                "SELECT * FROM scanner_candidates ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM scanner_candidates
                WHERE run_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
    finally:
        conn.close()
    result = []
    for row in rows:
        item = dict(row)
        item["payload"] = decode_json(item.pop("payload_json"))
        result.append(item)
    return result


def row_to_harmonic_alert(row: sqlite3.Row) -> HarmonicAlertRecord:
    return HarmonicAlertRecord(
        id=row["id"],
        symbol=row["symbol"],
        timeframe=row["timeframe"],
        alertType=row["alert_type"],
        message=row["message"],
        state=row["state"],
        createdAt=row["created_at"],
    )


def save_harmonic_alerts(
    alerts: list[HarmonicAlertRecord],
) -> list[HarmonicAlertRecord]:
    init_db()
    if not alerts:
        return []
    created_ids: list[int] = []
    created_at = datetime.now(timezone.utc).isoformat()
    conn = connect()
    try:
        for alert in alerts:
            cursor = conn.execute(
                """
                INSERT INTO harmonic_alerts (
                    symbol, timeframe, alert_type, message, state, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.symbol,
                    alert.timeframe,
                    alert.alert_type,
                    alert.message,
                    alert.state,
                    created_at,
                ),
            )
            created_ids.append(_lastrowid(cursor))
        placeholders = ",".join("?" for _ in created_ids)
        rows = conn.execute(
            f"SELECT * FROM harmonic_alerts WHERE id IN ({placeholders}) ORDER BY id ASC",
            created_ids,
        ).fetchall()
        conn.commit()
    finally:
        conn.close()
    return [row_to_harmonic_alert(row) for row in rows]


def list_harmonic_alerts(
    symbol: str | None = None, limit: int = 100
) -> list[HarmonicAlertRecord]:
    init_db()
    conn = connect()
    try:
        if symbol:
            rows = conn.execute(
                """
                SELECT * FROM harmonic_alerts
                WHERE symbol = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (symbol.upper().strip(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM harmonic_alerts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [row_to_harmonic_alert(row) for row in rows]
