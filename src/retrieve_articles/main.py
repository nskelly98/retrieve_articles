from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Optional

from retrieve_articles.agent import select_and_summarize, select_keyword_only
from retrieve_articles.config import load_settings
from retrieve_articles.discover.arxiv_source import fetch_arxiv_candidates
from retrieve_articles.discover.hackernews_source import fetch_hackernews_candidates
from retrieve_articles.discover.rss_source import fetch_rss_candidates
from retrieve_articles.emailer import (
    send_article_email,
    send_no_candidates_email,
    send_test_email,
)
from retrieve_articles.history import append_to_history, load_history, seen_urls
from retrieve_articles.interests import load_interests
from retrieve_articles.models import ArticleCandidate


def discover_candidates(
    interests,
    *,
    lookback_days: int,
    max_candidates: int,
) -> list[ArticleCandidate]:
    tasks = {
        "arxiv": lambda: fetch_arxiv_candidates(lookback_days),
        "hackernews": lambda: fetch_hackernews_candidates(lookback_days),
        "rss": lambda: fetch_rss_candidates(interests.rss_feeds, lookback_days),
    }

    candidates: list[ArticleCandidate] = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            source = futures[future]
            try:
                result = future.result()
                candidates.extend(result)
                print(f"Fetched {len(result)} candidates from {source}")
            except Exception as exc:
                print(f"Warning: {source} discovery failed: {exc}", file=sys.stderr)

    candidates.sort(
        key=lambda c: c.published_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return candidates[:max_candidates]


def filter_unseen(
    candidates: list[ArticleCandidate],
    history_urls: set[str],
) -> list[ArticleCandidate]:
    return [c for c in candidates if c.normalized_url() not in history_urls]


def run_daily(*, dry_run: bool = False, no_llm: bool = False) -> int:
    settings = load_settings()
    interests = load_interests(settings.interests_path)
    history = load_history(settings.history_path)
    known_urls = seen_urls(history)

    print("Discovering candidates...")
    candidates = discover_candidates(
        interests,
        lookback_days=settings.lookback_days,
        max_candidates=settings.max_candidates,
    )
    unseen = filter_unseen(candidates, known_urls)
    print(f"Found {len(candidates)} total, {len(unseen)} unseen candidates")

    if not unseen:
        print("No unseen candidates found.")
        if dry_run:
            print("Dry run: would send no-candidates email.")
            return 0
        send_no_candidates_email(
            gmail_address=settings.gmail_address,
            gmail_app_password=settings.gmail_app_password,
            recipient=settings.effective_recipient,
        )
        print("Sent no-candidates notification.")
        return 0

    if no_llm:
        print("Selecting with keyword fallback (--no-llm)...")
        selection = select_keyword_only(interests, unseen)
    else:
        print("Selecting and summarizing with OpenAI...")
        selection = select_and_summarize(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            interests=interests,
            candidates=unseen,
        )

    print(f"Selected: {selection.title}")
    print(f"URL: {selection.selected_url}")
    print(f"Subject: Today's read: {selection.headline}")

    if dry_run:
        print("\n--- Summary ---")
        print(selection.summary)
        print("\n--- Why it matters ---")
        for item in selection.why_it_matters:
            print(f"- {item}")
        return 0

    send_article_email(
        gmail_address=settings.gmail_address,
        gmail_app_password=settings.gmail_app_password,
        recipient=settings.effective_recipient,
        selection=selection,
    )
    append_to_history(
        settings.history_path,
        selection.selected_url,
        selection.title,
    )
    print(f"Email sent to {settings.effective_recipient}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Daily Article Agent")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover and curate without sending email or updating history",
    )
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Send a test email to verify Gmail SMTP configuration",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip OpenAI and pick by keyword match (useful when API quota is unavailable)",
    )
    args = parser.parse_args(argv)

    if args.test_email:
        settings = load_settings()
        send_test_email(
            gmail_address=settings.gmail_address,
            gmail_app_password=settings.gmail_app_password,
            recipient=settings.effective_recipient,
        )
        print(f"Test email sent to {settings.effective_recipient}")
        return 0

    return run_daily(dry_run=args.dry_run, no_llm=args.no_llm)


if __name__ == "__main__":
    raise SystemExit(main())
