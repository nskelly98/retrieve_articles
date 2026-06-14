from __future__ import annotations

import json
import re
import sys
from typing import List, Literal

from openai import APIError, AuthenticationError, OpenAI, RateLimitError
from pydantic import BaseModel, Field

from retrieve_articles.interests import Interests
from retrieve_articles.models import ArticleCandidate, ArticleSelection

SYSTEM_PROMPT = """You are a curator for a data scientist / AI solutions engineer.
Pick exactly one article from the provided candidate list that best matches the
user's interests and career goals. You must choose a URL that appears in the list.
Write a clear, engaging summary suitable for a lunch-break read."""


class AgentResponse(BaseModel):
    selected_url: str
    headline: str = Field(max_length=120)
    summary: str
    why_it_matters: List[str] = Field(min_length=1, max_length=5)
    read_time_minutes: int = Field(ge=1, le=120)
    content_type: Literal["blog", "news", "paper"]


def _build_user_prompt(interests: Interests, candidates: list[ArticleCandidate]) -> str:
    topics = "\n".join(f"- {t}" for t in interests.topics)
    avoid = "\n".join(f"- {a}" for a in interests.avoid)
    candidate_lines = []
    for i, c in enumerate(candidates, start=1):
        published = c.published_at.isoformat() if c.published_at else "unknown"
        candidate_lines.append(
            f"{i}. [{c.content_type}] {c.title}\n"
            f"   URL: {c.url}\n"
            f"   Source: {c.source_name}\n"
            f"   Published: {published}\n"
            f"   Snippet: {c.snippet}"
        )

    return f"""User interests:
{topics}

Topics to avoid:
{avoid}

Career context:
{interests.career_context}

Candidates (pick exactly one by URL):
{chr(10).join(candidate_lines)}

Return JSON with: selected_url, headline, summary (2-3 paragraphs),
why_it_matters (2-3 bullets), read_time_minutes, content_type."""


def _keyword_fallback(
    interests: Interests,
    candidates: list[ArticleCandidate],
) -> ArticleCandidate:
    keywords = [t.lower() for t in interests.topics]
    keywords.extend(re.findall(r"\b\w{4,}\b", interests.career_context.lower()))

    def score(candidate: ArticleCandidate) -> int:
        text = f"{candidate.title} {candidate.snippet}".lower()
        return sum(1 for kw in keywords if kw in text)

    return max(candidates, key=score)


def _fallback_selection(
    interests: Interests,
    candidate: ArticleCandidate,
) -> ArticleSelection:
    return ArticleSelection(
        selected_url=candidate.url,
        headline=candidate.title[:120],
        summary=(
            f"{candidate.snippet}\n\n"
            "This piece was selected as a fallback when the AI curator could not "
            "produce a valid choice. Read the full article for details."
        ),
        why_it_matters=[
            f"Relevant to your interest in {interests.topics[0]}.",
            f"From {candidate.source_name}, a trusted source in your field.",
        ],
        read_time_minutes=10,
        content_type=candidate.content_type,
        title=candidate.title,
        source_name=candidate.source_name,
    )


def select_keyword_only(
    interests: Interests,
    candidates: list[ArticleCandidate],
) -> ArticleSelection:
    fallback_candidate = _keyword_fallback(interests, candidates)
    return _fallback_selection(interests, fallback_candidate)


def select_and_summarize(
    *,
    api_key: str,
    model: str,
    interests: Interests,
    candidates: list[ArticleCandidate],
) -> ArticleSelection:
    if not candidates:
        raise ValueError("No candidates available for selection.")

    client = OpenAI(api_key=api_key)
    url_map = {c.normalized_url(): c for c in candidates}
    prompt = _build_user_prompt(interests, candidates)

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
            )
        except (RateLimitError, AuthenticationError, APIError) as exc:
            print(
                f"Warning: OpenAI unavailable ({exc}). Using keyword fallback.",
                file=sys.stderr,
            )
            return select_keyword_only(interests, candidates)

        content = response.choices[0].message.content or "{}"
        parsed = AgentResponse.model_validate(json.loads(content))
        normalized = parsed.selected_url.rstrip("/").lower()
        candidate = url_map.get(normalized)
        if candidate:
            return ArticleSelection(
                selected_url=candidate.url,
                headline=parsed.headline,
                summary=parsed.summary,
                why_it_matters=parsed.why_it_matters,
                read_time_minutes=parsed.read_time_minutes,
                content_type=parsed.content_type,
                title=candidate.title,
                source_name=candidate.source_name,
            )

    fallback_candidate = _keyword_fallback(interests, candidates)
    return _fallback_selection(interests, fallback_candidate)
