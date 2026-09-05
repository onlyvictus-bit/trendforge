from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


_RESULT_MARKER = "VYOM_RESULT="


@dataclass(frozen=True)
class BrowserDiscovery:
    state: str
    links: tuple[dict[str, str], ...]
    error: str | None
    can_unlock_ready: bool = False


def _safe_error(value: str, limit: int = 500) -> str:
    return " ".join(value.strip().split())[:limit]


def parse_vyom_output(output: str) -> BrowserDiscovery:
    marker_at = output.rfind(_RESULT_MARKER)
    if marker_at < 0:
        return BrowserDiscovery(
            state="INVALID_OUTPUT",
            links=(),
            error="VYOM did not emit its structured result marker.",
        )
    raw = output[marker_at + len(_RESULT_MARKER) :].strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return BrowserDiscovery(
            state="INVALID_OUTPUT",
            links=(),
            error=f"VYOM result was not valid JSON: {exc.msg}.",
        )

    if isinstance(payload, dict) and "payload" in payload:
        if not payload.get("ok"):
            return BrowserDiscovery(
                state="FAILED",
                links=(),
                error=_safe_error(str(payload.get("error") or "VYOM scrape failed.")),
            )
        payload = payload.get("payload")
    if not isinstance(payload, dict):
        return BrowserDiscovery(
            state="INVALID_OUTPUT",
            links=(),
            error="VYOM result payload was not an object.",
        )

    links: list[dict[str, str]] = []
    for item in payload.get("links") or []:
        if not isinstance(item, dict):
            continue
        href = str(item.get("href") or item.get("url") or "").strip()
        parsed = urlsplit(href)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        links.append({"url": href, "text": str(item.get("text") or "").strip()})
    return BrowserDiscovery(
        state="DISCOVERED" if links else "NO_LINKS",
        links=tuple(links),
        error=None,
    )


def discover_links_with_vyom(url: str, timeout_seconds: int = 30) -> BrowserDiscovery:
    if os.getenv("TRENDFORGE_ENABLE_VYOM_RESOLVER", "0").strip().lower() not in {
        "1",
        "true",
        "yes",
    }:
        return BrowserDiscovery(state="DISABLED", links=(), error=None)

    root_value = os.getenv("TRENDFORGE_VYOM_ROOT", "").strip()
    if not root_value:
        return BrowserDiscovery(
            state="UNAVAILABLE",
            links=(),
            error="TRENDFORGE_VYOM_ROOT is not configured.",
        )
    root = Path(root_value).expanduser().resolve()
    python = root / ".venv312" / "Scripts" / "python.exe"
    scraper = root / "tools" / "scraper.py"
    if not root.is_dir() or not python.is_file() or not scraper.is_file():
        return BrowserDiscovery(
            state="UNAVAILABLE",
            links=(),
            error="Configured VYOM root does not contain its Python runtime and scraper.",
        )

    wrapper = """
import asyncio
import json
import sys

from tools.scraper import ScraperTool

async def main():
    raw = await ScraperTool().execute(sys.argv[1], output_format="json")
    try:
        payload = json.loads(raw)
        result = {"ok": True, "payload": payload}
    except json.JSONDecodeError:
        result = {"ok": False, "error": raw[:500]}
    print("VYOM_RESULT=" + json.dumps(result, separators=(",", ":")))

asyncio.run(main())
""".strip()
    environment = os.environ.copy()
    environment["VYOM_MAX_OUTPUT"] = "200000"
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [str(python), "-c", wrapper, url],
            cwd=str(root),
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(5, timeout_seconds),
            check=False,
            creationflags=creation_flags,
        )
    except subprocess.TimeoutExpired:
        return BrowserDiscovery(
            state="TIMEOUT",
            links=(),
            error=f"VYOM exceeded the {max(5, timeout_seconds)} second timeout.",
        )
    except OSError as exc:
        return BrowserDiscovery(
            state="UNAVAILABLE",
            links=(),
            error=f"VYOM process could not start: {type(exc).__name__}.",
        )

    parsed = parse_vyom_output(completed.stdout)
    if completed.returncode != 0 and parsed.state == "INVALID_OUTPUT":
        return BrowserDiscovery(
            state="FAILED",
            links=(),
            error=_safe_error(
                completed.stderr or f"VYOM exited {completed.returncode}."
            ),
        )
    return parsed
