from __future__ import annotations

from datetime import datetime, timedelta, timezone

import arxiv

from retrieve_articles.models import ArticleCandidate

ARXIV_CATEGORIES = ["cs.LG", "cs.AI", "stat.ML"]
RESULTS_PER_CATEGORY = 10


def fetch_arxiv_candidates(lookback_days: int = 3) -> list[ArticleCandidate]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    candidates: list[ArticleCandidate] = []
    seen_urls: set[str] = set()

    for category in ARXIV_CATEGORIES:
        search = arxiv.Search(
            query=f"cat:{category}",
            max_results=RESULTS_PER_CATEGORY,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        for result in search.results():
            published = result.published
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            if published < cutoff:
                continue

            url = result.entry_id
            if url in seen_urls:
                continue
            seen_urls.add(url)

            snippet = (result.summary or "").strip()
            if len(snippet) > 500:
                snippet = snippet[:497] + "..."

            candidates.append(
                ArticleCandidate(
                    title=result.title.replace("\n", " ").strip(),
                    url=url,
                    source_name=f"arXiv ({category})",
                    published_at=published,
                    snippet=snippet,
                    content_type="paper",
                )
            )

    return candidates
