from __future__ import annotations

from datetime import datetime, timedelta, timezone

import feedparser
import httpx

from retrieve_articles.models import ArticleCandidate

ENTRIES_PER_FEED = 10


def _parse_published(entry: dict) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
    return None


def fetch_rss_candidates(
    feeds: list[dict[str, str]],
    lookback_days: int = 3,
) -> list[ArticleCandidate]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    candidates: list[ArticleCandidate] = []
    seen_urls: set[str] = set()

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for feed_info in feeds:
            name = feed_info.get("name", "RSS")
            url = feed_info.get("url", "")
            if not url:
                continue

            try:
                response = client.get(url)
                response.raise_for_status()
                parsed = feedparser.parse(response.text)
            except (httpx.HTTPError, ValueError):
                continue

            for entry in parsed.entries[:ENTRIES_PER_FEED]:
                link = entry.get("link") or ""
                if not link or link in seen_urls:
                    continue

                published_at = _parse_published(entry)
                if published_at and published_at < cutoff:
                    continue

                seen_urls.add(link)
                title = (entry.get("title") or "Untitled").strip()
                snippet = entry.get("summary") or entry.get("description") or ""
                snippet = _strip_html(snippet)
                if len(snippet) > 500:
                    snippet = snippet[:497] + "..."

                candidates.append(
                    ArticleCandidate(
                        title=title,
                        url=link,
                        source_name=name,
                        published_at=published_at,
                        snippet=snippet or f"Recent post from {name}.",
                        content_type="blog",
                    )
                )

    return candidates


def _strip_html(text: str) -> str:
    import re

    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()
