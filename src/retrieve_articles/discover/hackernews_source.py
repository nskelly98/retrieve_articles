from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from retrieve_articles.models import ArticleCandidate

HN_API_URL = "https://hn.algolia.com/api/v1/search"
HN_QUERIES = [
    "machine learning",
    "artificial intelligence",
    "data science",
    "LLM",
    "MLOps",
    "RAG",
]
HITS_PER_QUERY = 8


def fetch_hackernews_candidates(lookback_days: int = 3) -> list[ArticleCandidate]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    cutoff_ts = int(cutoff.timestamp())
    candidates: list[ArticleCandidate] = []
    seen_urls: set[str] = set()

    with httpx.Client(timeout=30.0) as client:
        for query in HN_QUERIES:
            response = client.get(
                HN_API_URL,
                params={
                    "query": query,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{cutoff_ts}",
                    "hitsPerPage": HITS_PER_QUERY,
                },
            )
            response.raise_for_status()
            hits = response.json().get("hits", [])

            for hit in hits:
                url = hit.get("url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                created_at = hit.get("created_at_i")
                published_at = None
                if created_at:
                    published_at = datetime.fromtimestamp(created_at, tz=timezone.utc)

                title = (hit.get("title") or "Untitled").strip()
                snippet = f"Hacker News discussion with {hit.get('points', 0)} points."

                candidates.append(
                    ArticleCandidate(
                        title=title,
                        url=url,
                        source_name="Hacker News",
                        published_at=published_at,
                        snippet=snippet,
                        content_type="news",
                    )
                )

    return candidates
