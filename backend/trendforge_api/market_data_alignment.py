from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AlignmentState(StrEnum):
    VALID = "VALID"
    WAIT_MISSING_INPUT = "WAIT_MISSING_INPUT"
    WAIT_TRADING_DATE = "WAIT_TRADING_DATE"
    WAIT_FUTURE_INPUT = "WAIT_FUTURE_INPUT"
    WAIT_TIMESTAMP_SKEW = "WAIT_TIMESTAMP_SKEW"


class DerivedInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_key: str
    content_hash: str
    data_as_of: datetime
    fetched_at: datetime
    trading_date: date
    records: tuple[dict[str, Any], ...] = ()

    @field_validator("content_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        normalized = value.casefold()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("content_hash must be a SHA-256 digest")
        return normalized


class DerivedInputBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: AlignmentState
    trading_date: date
    evaluated_at: datetime
    required_keys: tuple[str, ...]
    inputs: tuple[DerivedInput, ...]
    maximum_skew_seconds: int | None = Field(default=None, ge=0)
    reason: str


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def build_derived_bundle(
    inputs: dict[str, DerivedInput],
    *,
    required_keys: tuple[str, ...],
    trading_date: date,
    evaluated_at: datetime,
    max_skew_seconds: int,
    future_tolerance_seconds: int = 120,
) -> DerivedInputBundle:
    if max_skew_seconds < 0 or future_tolerance_seconds < 0:
        raise ValueError("alignment tolerances cannot be negative")
    instant = _utc(evaluated_at)
    selected = tuple(inputs[key] for key in required_keys if key in inputs)
    missing = tuple(key for key in required_keys if key not in inputs)
    if missing:
        return DerivedInputBundle(
            state=AlignmentState.WAIT_MISSING_INPUT,
            trading_date=trading_date,
            evaluated_at=instant,
            required_keys=required_keys,
            inputs=selected,
            reason=f"missing required inputs: {', '.join(missing)}",
        )
    wrong_day = tuple(item.source_key for item in selected if item.trading_date != trading_date)
    if wrong_day:
        return DerivedInputBundle(
            state=AlignmentState.WAIT_TRADING_DATE,
            trading_date=trading_date,
            evaluated_at=instant,
            required_keys=required_keys,
            inputs=selected,
            reason=f"trading-date mismatch: {', '.join(wrong_day)}",
        )
    future = tuple(
        item.source_key
        for item in selected
        if (_utc(item.data_as_of) - instant).total_seconds() > future_tolerance_seconds
    )
    if future:
        return DerivedInputBundle(
            state=AlignmentState.WAIT_FUTURE_INPUT,
            trading_date=trading_date,
            evaluated_at=instant,
            required_keys=required_keys,
            inputs=selected,
            reason=f"future-dated inputs: {', '.join(future)}",
        )
    timestamps = [_utc(item.data_as_of) for item in selected]
    maximum_skew = int((max(timestamps) - min(timestamps)).total_seconds()) if timestamps else 0
    if maximum_skew > max_skew_seconds:
        return DerivedInputBundle(
            state=AlignmentState.WAIT_TIMESTAMP_SKEW,
            trading_date=trading_date,
            evaluated_at=instant,
            required_keys=required_keys,
            inputs=selected,
            maximum_skew_seconds=maximum_skew,
            reason=f"input skew {maximum_skew}s exceeds {max_skew_seconds}s",
        )
    return DerivedInputBundle(
        state=AlignmentState.VALID,
        trading_date=trading_date,
        evaluated_at=instant,
        required_keys=required_keys,
        inputs=selected,
        maximum_skew_seconds=maximum_skew,
        reason="all required hashes, dates and timestamps are compatible",
    )


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return _utc(parsed)


class CanonicalManifestSourceProvider:
    """Read-only projection from a committed MD69 manifest into panel sources."""

    def __init__(self, *, db_path: Path, data_root: Path) -> None:
        self.db_path = db_path.expanduser().resolve(strict=False)
        self.data_root = data_root.expanduser().resolve(strict=False)
        self.objects_root = self.data_root / "objects"

    @staticmethod
    def _safe_file(path_value: str, root: Path) -> Path | None:
        unresolved = Path(path_value).expanduser()
        if unresolved.is_symlink():
            return None
        path = unresolved.resolve(strict=False)
        try:
            path.relative_to(root.resolve(strict=False))
        except ValueError:
            return None
        if not path.is_file() or path.is_symlink():
            return None
        return path

    def _latest_manifest(self, trading_date: str) -> tuple[Path, str] | None:
        if not self.db_path.is_file():
            return None
        try:
            connection = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            try:
                rows = connection.execute(
                    """
                    SELECT manifest_path, manifest_hash FROM market_data_manifests
                    WHERE trading_date = ?
                    ORDER BY generated_at DESC
                    """,
                    (trading_date,),
                ).fetchall()
            finally:
                connection.close()
        except sqlite3.Error:
            return None
        accepted_statuses = {
            "SUCCESS_NEW",
            "SUCCESS_UNCHANGED",
            "CACHED_CURRENT",
            "STALE_LAST_GOOD",
        }
        for row in rows:
            path = self._safe_file(row["manifest_path"], self.data_root)
            if path is None:
                continue
            expected_hash = str(row["manifest_hash"]).casefold()
            try:
                content = path.read_bytes()
                if hashlib.sha256(content).hexdigest() != expected_hash:
                    continue
                manifest = json.loads(content)
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            if manifest.get("tradingDate") != trading_date:
                continue
            if not any(
                isinstance(entry, dict)
                and entry.get("status") in accepted_statuses
                for entry in manifest.get("entries", [])
            ):
                continue
            return path, expected_hash
        return None

    def __call__(
        self,
        *,
        now: datetime,
        market_trading_date: str,
        max_age_sec: int,
        source_keys: tuple[str, ...],
        research_source_keys: tuple[str, ...] = (),
        include_all_sources: bool = False,
        supporting_sample_limit: int = 10,
    ) -> dict[str, dict[str, Any]]:
        selected_manifest = self._latest_manifest(market_trading_date)
        if selected_manifest is None:
            return {}
        manifest_path, expected_manifest_hash = selected_manifest
        try:
            manifest_bytes = manifest_path.read_bytes()
            if hashlib.sha256(manifest_bytes).hexdigest() != expected_manifest_hash.casefold():
                return {}
            manifest = json.loads(manifest_bytes)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return {}
        if manifest.get("tradingDate") != market_trading_date:
            return {}
        instant = _utc(now)
        selected = set(source_keys) | set(research_source_keys)
        research_only = set(research_source_keys)
        output: dict[str, dict[str, Any]] = {}
        accepted_statuses = {
            "SUCCESS_NEW",
            "SUCCESS_UNCHANGED",
            "CACHED_CURRENT",
            "STALE_LAST_GOOD",
        }
        for entry in manifest.get("entries", []):
            if not isinstance(entry, dict):
                continue
            source_key = str(entry.get("sourceKey") or "")
            dynamic_support = include_all_sources and source_key not in selected
            if (
                (source_key not in selected and not dynamic_support)
                or entry.get("status") not in accepted_statuses
            ):
                continue
            object_path = self._safe_file(str(entry.get("objectPath") or ""), self.objects_root)
            if object_path is None:
                continue
            try:
                content = object_path.read_bytes()
            except OSError:
                continue
            content_hash = hashlib.sha256(content).hexdigest()
            if content_hash != str(entry.get("contentHash") or "").casefold():
                continue
            try:
                normalized = json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            records = normalized.get("records") if isinstance(normalized, dict) else None
            records = [row for row in records if isinstance(row, dict)] if isinstance(records, list) else []
            sampled_records = (
                records[: max(1, supporting_sample_limit)]
                if dynamic_support
                else records
            )
            data_date = str(entry.get("dataDate") or normalized.get("dataDate") or "")
            observed = _parse_datetime(entry.get("fetchedAt"))
            if observed is None:
                observed = _parse_datetime(manifest.get("generatedAt")) or instant
            age_sec = max(0, int((instant - observed).total_seconds()))
            future_sec = int((observed - instant).total_seconds())
            freshness_class = (
                "RESEARCH_EOD"
                if dynamic_support
                else "TRADING_DAY"
                if source_key == "nse_large_deals_snapshot"
                else "SESSION"
                if source_key == "nse_preopen_fo"
                else "RESEARCH_EOD"
                if source_key in research_only
                else "INTRADAY_300"
            )
            wrong_day = (
                bool(data_date) and data_date != market_trading_date
                if dynamic_support
                else data_date != market_trading_date
            )
            stale = freshness_class == "INTRADAY_300" and age_sec > max_age_sec
            future = future_sec > 120
            eligible = (
                bool(sampled_records)
                and not dynamic_support
                and source_key not in research_only
                and not wrong_day
                and not stale
                and not future
            )
            research_eligible = (
                bool(sampled_records)
                and (dynamic_support or bool(data_date))
                and not future
                and (not data_date or data_date <= market_trading_date)
            )
            output[source_key] = {
                "sourceKey": source_key,
                "sourceUrl": entry.get("sourceUrl"),
                "fetchState": "CANONICAL_MANIFEST",
                "state": (
                    "FRESH"
                    if eligible and freshness_class == "INTRADAY_300"
                    else "SESSION_CONTEXT"
                    if eligible and freshness_class == "SESSION"
                    else "TRADING_DAY_CONTEXT"
                    if eligible
                    else "RESEARCH_ONLY"
                    if research_eligible
                    else "QUARANTINED"
                    if wrong_day or future
                    else "STALE"
                    if stale
                    else "EMPTY"
                ),
                "eligible": eligible,
                "researchEligible": research_eligible,
                "freshnessClass": freshness_class,
                "tradingDate": data_date,
                "dataAsOf": observed.isoformat(),
                "fetchedAt": observed.isoformat(),
                "ageSec": age_sec,
                "parserState": normalized.get("parserState"),
                "sourceRowCount": len(records),
                "normalizedRowCount": len(records),
                "recordsSample": [dict(row) for row in sampled_records],
                "truncated": False,
                "contentHash": content_hash,
                "reason": (
                    "canonical MD69 manifest projection"
                    if eligible
                    else "canonical MD69 dynamic supporting projection"
                    if dynamic_support and research_eligible
                    else "canonical MD69 saved research projection"
                    if research_eligible
                    else "canonical input failed date/freshness/content eligibility"
                ),
            }
        return output
