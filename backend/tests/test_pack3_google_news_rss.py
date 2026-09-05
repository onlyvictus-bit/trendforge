from __future__ import annotations

import json

import pytest

from trendforge_api import phase3_multi_step_fetch
from trendforge_api.parsers.google_news_rss_parser import parse_google_news_rss
from trendforge_api.phase3_multi_step_fetch import MultiStepFetchResult
from trendforge_api.source_monitor import get_source_descriptor
from trendforge_api.source_parser import PARSER_MAP, STRUCTURED_PARSERS
from trendforge_api.source_resolver import resolve_and_fetch_source


def _xml(*items: str) -> str:
    return "<rss><channel>" + "".join(items) + "</channel></rss>"


def _item(
    title: str = "Indian shares rise - Example News",
    link: str = "https://news.google.com/rss/articles/one",
    published: str = "Mon, 10 Aug 2026 06:00:00 GMT",
) -> str:
    return (
        f"<item><title>{title}</title><link>{link}</link>"
        f"<pubDate>{published}</pubDate><description>Market update</description>"
        '<source url="https://example.com">Example News</source></item>'
    )


def _bundle(*feeds: dict[str, str]) -> bytes:
    return json.dumps({"feeds": list(feeds)}).encode()


def _feed(xml: str, query: str = "Indian stock market NSE BSE") -> dict[str, str]:
    return {"query": query, "url": "https://news.google.com/rss/search?q=test", "xml": xml}


def test_google_news_parser_applies_age_gate_and_preserves_context() -> None:
    content = _bundle(
        _feed(
            _xml(
                _item(),
                _item("Old", "https://news.google.com/old", "Sat, 01 Aug 2026 06:00:00 GMT"),
                _item("Future", "https://news.google.com/future", "Mon, 10 Aug 2026 06:10:00 GMT"),
            )
        )
    )
    parsed = parse_google_news_rss(content, last_modified="2026-08-10T06:05:00Z")
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 1
    assert parsed["data_date"] == "2026-08-10"
    assert parsed["output"]["staleItemCount"] == 1
    assert parsed["output"]["futureItemCount"] == 1
    row = parsed["output"]["rows"][0]
    assert row["publisher"] == "Example News"
    assert row["symbol"] is None
    assert row["scoreAuthority"] == "ZERO_SCORE_INFORMATIONAL"


@pytest.mark.parametrize(
    ("content", "state"),
    [
        (b"<html>blocked</html>", "WAIT_SCHEMA_MISMATCH"),
        (_bundle(), "WAIT_EMPTY_PARSE"),
        (json.dumps({"feeds": "bad"}).encode(), "WAIT_SCHEMA_MISMATCH"),
        (_bundle(_feed("not xml")), "WAIT_SCHEMA_MISMATCH"),
        (_bundle(_feed(_xml(_item(published="bad")))), "WAIT_EMPTY_PARSE"),
    ],
)
def test_google_news_parser_fails_closed(content: bytes, state: str) -> None:
    parsed = parse_google_news_rss(content, last_modified="2026-08-10T06:05:00Z")
    assert parsed["parser_state"] == state
    assert parsed["record_count"] == 0


def test_google_news_dedupes_deterministically() -> None:
    content = _bundle(_feed(_xml(_item(), _item())), _feed(_xml(_item())))
    first = parse_google_news_rss(content, last_modified="2026-08-10T06:05:00Z")
    second = parse_google_news_rss(content, last_modified="2026-08-10T06:05:00Z")
    assert first == second
    assert first["record_count"] == 1
    assert first["output"]["duplicateItemCount"] == 2


def test_google_news_is_registered_and_uses_existing_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert get_source_descriptor("google_news_rss") is not None
    assert "google_news_rss" in STRUCTURED_PARSERS
    assert "google_news_rss" in PARSER_MAP
    body = _bundle(_feed(_xml(_item())))
    monkeypatch.setattr(
        phase3_multi_step_fetch,
        "fetch_google_news_rss",
        lambda: MultiStepFetchResult(True, "https://news.google.com/rss/search", 200, body, "application/json", None),
    )
    resolved = resolve_and_fetch_source("google_news_rss", "https://news.google.com/rss/search")
    assert resolved.resolver_state == "GOOGLE_NEWS_RSS_BUNDLE"
    assert resolved.content == body
