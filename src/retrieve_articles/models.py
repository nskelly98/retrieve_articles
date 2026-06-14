from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ArticleCandidate:
    title: str
    url: str
    source_name: str
    published_at: datetime | None
    snippet: str
    content_type: str = "blog"

    def normalized_url(self) -> str:
        return self.url.rstrip("/").lower()


@dataclass
class ArticleSelection:
    selected_url: str
    headline: str
    summary: str
    why_it_matters: list[str]
    read_time_minutes: int
    content_type: str
    title: str
    source_name: str
