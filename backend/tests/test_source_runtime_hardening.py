from __future__ import annotations

import asyncio
from datetime import date, datetime
from pathlib import Path

import httpx

from trendforge_api.institutional_sources import AsyncEndpointClient, FetchState
from trendforge_api.parsers.common import parse_date_value


def test_parse_date_value_handles_exchange_and_excel_formats() -> None:
    assert parse_date_value("14-Jul-2026 15:32:10+05:30") == "2026-07-14"
    assert parse_date_value("/Date(1784024699000)/") == "2026-07-14"
    assert parse_date_value(46217) == "2026-07-14"
    assert parse_date_value(datetime(2026, 7, 14, 15, 30)) == "2026-07-14"
    assert parse_date_value(date(2026, 7, 14)) == "2026-07-14"
    assert parse_date_value("not-a-date") is None


def test_retry_after_is_bounded_and_success_reports_attempts(
    tmp_path: Path, monkeypatch
) -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json={"Sensex": 80_000})

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    async def run():
        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        client = AsyncEndpointClient(
            archive_root=tmp_path / "raw",
            cache_db=tmp_path / "cache.sqlite3",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await client.fetch("bse_sensex")
        finally:
            await client.aclose()

    result = asyncio.run(run())

    assert result.state == FetchState.RAW_ARCHIVED
    assert result.attempts == 2
    assert result.status_code == 200
    assert calls == 2
    assert sleeps and sleeps[0] == 1


def test_html_access_denied_is_wrong_content_not_valid_empty(tmp_path: Path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><title>Access Denied</title><p>captcha</p></html>",
            headers={"Content-Type": "text/html"},
        )

    async def run():
        client = AsyncEndpointClient(
            archive_root=tmp_path / "raw",
            cache_db=tmp_path / "cache.sqlite3",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await client.fetch("bse_sensex")
        finally:
            await client.aclose()

    result = asyncio.run(run())

    assert result.state == FetchState.WRONG_CONTENT
    assert result.error_type == "BLOCK_PAGE"
    assert result.status_code == 200
    assert result.record_count == 0
    assert result.can_score is False

