"""Isolated, hash-pinned R2 shadow execution for the frozen inventory screener."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .inventory_source_bundle import InventorySourceBundleV1

SCHEMA_VERSION = "trendforge.inventory-shadow.v1"
PINNED_SCREENER_SHA256 = "D3A6860F20DC81BF228F84C73B6352FEC496CEA64376B7560BCF0EE5E5C3F356"
DEFAULT_SCRIPT = Path(__file__).resolve().parents[3] / "frontend" / "inventory-workbench" / "screener.js"
MAX_ROWS = 500
MAX_INPUT_BYTES = 1_000_000
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

NODE_RUNNER = r"""
const fs = require('fs');
const vm = require('vm');
const scriptPath = process.argv[1];
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  const payload = JSON.parse(input);
  const sandbox = {
    window: {},
    console: { log() {}, info() {}, warn() {}, error() {} },
    performance: { now: () => 0 },
  };
  vm.createContext(sandbox, { name: 'trendforge-r2-shadow', codeGeneration: { strings: false, wasm: false } });
  const source = fs.readFileSync(scriptPath, 'utf8');
  vm.runInContext(source, sandbox, { timeout: 750, displayErrors: true });
  const engine = sandbox.window.ScreenerEngine;
  if (!engine) throw new Error('frozen ScreenerEngine export missing');
  engine.buildSymbolTable(payload.inventory, { force: true, silentHooks: true });
  const snapshot = engine.getSnapshot({
    limit: 500,
    state: { universe: 'all', preset: 'all', sortKey: 'score', sortDir: 'desc', search: '' }
  });
  const rows = (snapshot && snapshot.rows || []).map(row => ({
    symbol: row.symbol,
    score: row.score,
    scoreParts: row.scoreParts,
    sources: row.sources
  }));
  process.stdout.write(JSON.stringify({
    contract: snapshot && snapshot.contract,
    version: snapshot && snapshot.version,
    scorePolicy: snapshot && snapshot.scorePolicy,
    rows
  }));
});
"""


class ShadowScreenerResult(BaseModel):
    model_config = MODEL_CONFIG

    schema_version: str = SCHEMA_VERSION
    mode: Literal["SHADOW"] = "SHADOW"
    status: str
    script_sha256: str | None = None
    source_row_count: int = Field(default=0, ge=0)
    input_row_count: int = Field(default=0, ge=0)
    truncated: bool = False
    output_row_count: int = Field(default=0, ge=0)
    output_hash: str | None = None
    rows: tuple[dict[str, Any], ...] = ()
    error: str | None = None
    can_vote: bool = False
    can_change_baseline: bool = False


def _sanitized_inventory(bundle: InventorySourceBundleV1) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in bundle.stock_records[:MAX_ROWS]:
        session_return = row.cheap_features.get("sessionReturn")
        records.append(
            {
                "symbol": row.symbol,
                "pChange": round(float(session_return) * 100.0, 8)
                if isinstance(session_return, (int, float))
                else None,
            }
        )
    return [
        {
            "row_no": 1,
            "source_key": "r1_shadow_cash",
            "active_source_keys": "nse_bhavcopy_eod",
            "status": "STRONG",
            "records_sample": records,
        }
    ]


def run_shadow_screener(
    bundle: InventorySourceBundleV1,
    *,
    script_path: Path = DEFAULT_SCRIPT,
    timeout_seconds: float = 2.0,
) -> ShadowScreenerResult:

    source_count = len(bundle.stock_records)
    input_count = min(source_count, MAX_ROWS)
    truncated = source_count > MAX_ROWS
    try:

        script_bytes = script_path.read_bytes()
    except OSError as exc:
        return ShadowScreenerResult(status="SCRIPT_UNAVAILABLE", error=str(exc))
    script_hash = hashlib.sha256(script_bytes).hexdigest().upper()
    if script_hash != PINNED_SCREENER_SHA256:
        return ShadowScreenerResult(
            status="HASH_MISMATCH",
            script_sha256=script_hash,
            source_row_count=source_count,
            input_row_count=input_count,
            truncated=truncated,
            error="frozen screener hash does not match the pinned R2 contract",
        )
    node = shutil.which("node")
    if node is None:
        return ShadowScreenerResult(
            status="RUNTIME_UNAVAILABLE",
            script_sha256=script_hash,
            source_row_count=source_count,
            input_row_count=input_count,
            truncated=truncated,
            error="Node.js runtime is unavailable",
        )
    payload = json.dumps(
        {"inventory": _sanitized_inventory(bundle)},
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(payload) > MAX_INPUT_BYTES:
        return ShadowScreenerResult(
            status="INPUT_LIMIT_EXCEEDED",
            script_sha256=script_hash,
            source_row_count=source_count,
            input_row_count=input_count,
            truncated=truncated,
            error="sanitized shadow input exceeds the byte limit",
        )
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
        "WINDIR": os.environ.get("WINDIR", "C:\\Windows"),
    }
    try:
        completed = subprocess.run(
            [node, "--max-old-space-size=64", "-e", NODE_RUNNER, str(script_path)],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ShadowScreenerResult(
            status="TIMEOUT" if isinstance(exc, subprocess.TimeoutExpired) else "RUNTIME_FAILED",
            script_sha256=script_hash,
            source_row_count=source_count,
            input_row_count=input_count,
            truncated=truncated,
            error=str(exc),
        )
    if completed.returncode != 0:
        return ShadowScreenerResult(
            status="RUNTIME_FAILED",
            script_sha256=script_hash,
            source_row_count=source_count,
            input_row_count=input_count,
            truncated=truncated,
            error=completed.stderr.decode("utf-8", errors="replace")[:1000],
        )
    try:
        raw = json.loads(completed.stdout.decode("utf-8"))
        rows = tuple(
            sorted(
                (
                    {
                        "symbol": str(row.get("symbol") or "").upper(),
                        "score": row.get("score"),
                        "scoreParts": row.get("scoreParts") or [],
                        "sources": row.get("sources") or [],
                    }
                    for row in raw.get("rows", [])
                    if isinstance(row, dict) and row.get("symbol")
                ),
                key=lambda row: row["symbol"],
            )
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        return ShadowScreenerResult(
            status="OUTPUT_INVALID",
            script_sha256=script_hash,
            source_row_count=source_count,
            input_row_count=input_count,
            truncated=truncated,
            error=str(exc),
        )
    normalized = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return ShadowScreenerResult(
        status="COMPLETED",
        script_sha256=script_hash,
        source_row_count=source_count,
            input_row_count=input_count,
            truncated=truncated,
        output_row_count=len(rows),
        output_hash=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        rows=rows,
    )