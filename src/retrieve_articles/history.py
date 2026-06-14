from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

HISTORY_CAP = 400


@dataclass
class SeenArticle:
    url: str
    title: str
    sent_at: str

    @classmethod
    def from_dict(cls, data: dict) -> SeenArticle:
        return cls(url=data["url"], title=data["title"], sent_at=data["sent_at"])


def _normalize_url(url: str) -> str:
    return url.rstrip("/").lower()


def load_history(path: Path) -> list[SeenArticle]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return [SeenArticle.from_dict(entry) for entry in data]


def save_history(path: Path, history: list[SeenArticle]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    trimmed = history[-HISTORY_CAP:]
    with path.open("w", encoding="utf-8") as f:
        json.dump([asdict(entry) for entry in trimmed], f, indent=2)
        f.write("\n")


def seen_urls(history: list[SeenArticle]) -> set[str]:
    return {_normalize_url(entry.url) for entry in history}


def append_to_history(
    path: Path,
    url: str,
    title: str,
    *,
    now: datetime | None = None,
) -> None:
    history = load_history(path)
    timestamp = (now or datetime.now(timezone.utc)).isoformat()
    history.append(SeenArticle(url=url, title=title, sent_at=timestamp))
    save_history(path, history)
