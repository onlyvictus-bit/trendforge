"""Pure parser for bounded Google News RSS search bundles."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree

from .common import source_result


MAX_ARTICLE_AGE = timedelta(days=7)
MAX_FUTURE_SKEW = timedelta(minutes=2)


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _plain(value: Any) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", str(value or ""))
    return _text(html.unescape(without_tags))


def _reference(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _published(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_google_news_rss(
    content: bytes,
    *,
    url: str | None = None,
    last_modified: str | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Normalize fresh articles while rejecting old, future, empty, or malformed data."""
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Google News RSS bundle is not valid JSON.",
            output={"rows": [], "scope": "CONTEXT_INFORMATIONAL"},
            error=str(exc),
        )
    feeds = payload.get("feeds") if isinstance(payload, dict) else None
    if not isinstance(feeds, list):
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Google News RSS bundle is missing its feeds list.",
            output={"rows": [], "scope": "CONTEXT_INFORMATIONAL"},
            error="missing feeds list",
        )
    if not feeds:
        return source_result(
            parser_state="WAIT_EMPTY_PARSE",
            data_date=None,
            record_count=0,
            summary="Google News RSS returned no populated feeds; retain last-good.",
            output={"rows": [], "sourceFeedCount": 0, "scope": "CONTEXT_INFORMATIONAL"},
            error="empty feeds list",
        )
    reference = _reference(last_modified)
    if reference is None:
        return source_result(
            parser_state="WAIT_SCHEMA_MISMATCH",
            data_date=None,
            record_count=0,
            summary="Google News RSS requires a valid fetch timestamp for its age gate.",
            output={"rows": [], "scope": "CONTEXT_INFORMATIONAL"},
            error="missing or invalid last_modified",
        )

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    source_items = invalid = stale = future = duplicates = 0
    valid_feeds = 0
    for feed in feeds:
        if not isinstance(feed, dict):
            invalid += 1
            continue
        query = _text(feed.get("query"))
        feed_url = _text(feed.get("url"))
        xml = feed.get("xml")
        if not query or not isinstance(xml, str) or not xml.strip():
            invalid += 1
            continue
        try:
            root = ElementTree.fromstring(xml)
        except ElementTree.ParseError:
            invalid += 1
            continue
        items = root.findall(".//item")
        if items:
            valid_feeds += 1
        for item in items:
            source_items += 1
            title = _text(item.findtext("title"))
            link = _text(item.findtext("link"))
            published_raw = _text(item.findtext("pubDate"))
            published = _published(published_raw)
            if not title or not link or published is None:
                invalid += 1
                continue
            if published > reference + MAX_FUTURE_SKEW:
                future += 1
                continue
            if reference - published > MAX_ARTICLE_AGE:
                stale += 1
                continue
            identity = (title.casefold(), link)
            if identity in seen:
                duplicates += 1
                continue
            seen.add(identity)
            source_node = item.find("source")
            publisher = _text(source_node.text if source_node is not None else "")
            publisher_url = _text(source_node.get("url") if source_node is not None else "")
            if not publisher and " - " in title:
                publisher = title.rsplit(" - ", 1)[1]
            rows.append(
                {
                    "symbol": None,
                    "mappingState": "UNMAPPED_NO_FUZZY_TICKER_MATCH",
                    "searchQuery": query,
                    "title": title,
                    "description": _plain(item.findtext("description")) or None,
                    "articleUrl": link,
                    "publisher": publisher or None,
                    "publisherUrl": publisher_url or None,
                    "publishedAt": published.isoformat().replace("+00:00", "Z"),
                    "publicationDate": published.date().isoformat(),
                    "feedUrl": feed_url or None,
                    "sourceUrl": url,
                    "sourceTrust": "OPEN_SOURCE_UNOFFICIAL",
                    "scope": "CONTEXT_INFORMATIONAL",
                    "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
                }
            )
    if not rows:
        state = "WAIT_EMPTY_PARSE" if valid_feeds else "WAIT_SCHEMA_MISMATCH"
        return source_result(
            parser_state=state,
            data_date=None,
            record_count=0,
            summary="Google News RSS produced no fresh valid articles; retain last-good.",
            output={
                "rows": [],
                "sourceFeedCount": len(feeds),
                "sourceItemCount": source_items,
                "invalidItemCount": invalid,
                "staleItemCount": stale,
                "futureItemCount": future,
                "scope": "CONTEXT_INFORMATIONAL",
            },
            error="no fresh valid rows",
        )
    rows.sort(key=lambda row: (row["publishedAt"], row["title"]), reverse=True)
    return source_result(
        parser_state="PARSED_STRUCTURED",
        data_date=max(row["publicationDate"] for row in rows),
        record_count=len(rows),
        summary=f"Parsed {len(rows)} fresh Google News RSS articles from {valid_feeds} feeds.",
        output={
            "rows": rows,
            "records": rows,
            "sourceFeedCount": len(feeds),
            "validFeedCount": valid_feeds,
            "sourceItemCount": source_items,
            "normalizedRowCount": len(rows),
            "invalidItemCount": invalid,
            "staleItemCount": stale,
            "futureItemCount": future,
            "duplicateItemCount": duplicates,
            "unmappedArticleCount": len(rows),
            "maxArticleAgeDays": MAX_ARTICLE_AGE.days,
            "parserVersion": "1.0.0",
            "sourceTrust": "OPEN_SOURCE_UNOFFICIAL",
            "scope": "CONTEXT_INFORMATIONAL",
            "scoreAuthority": "ZERO_SCORE_INFORMATIONAL",
            "symbolMappingPolicy": "NO_FUZZY_TICKER_MATCH",
        },
    )
