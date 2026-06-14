from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Interests:
    topics: list[str]
    avoid: list[str]
    career_context: str
    rss_feeds: list[dict[str, str]]


def load_interests(path: Path) -> Interests:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return Interests(
        topics=data.get("topics", []),
        avoid=data.get("avoid", []),
        career_context=(data.get("career_context") or "").strip(),
        rss_feeds=data.get("rss_feeds", []),
    )
