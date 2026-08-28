"""
Headline fetching for qualitative context (Fed commentary, geopolitical
events, central bank buying) that pure price/macro data won't capture.

Uses NewsAPI.org (free tier: 100 requests/day, key required but instant
signup at https://newsapi.org/register). Optional -- if NEWSAPI_KEY is not
set, this section is skipped in the report rather than failing.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass

import requests

from config import NEWSAPI_KEY, NEWS_QUERY, NEWS_PAGE_SIZE, REQUEST_TIMEOUT, USER_AGENT

log = logging.getLogger("xau_fundamentals.news")

BASE_URL = "https://newsapi.org/v2/everything"


@dataclass
class Headline:
    title: str
    source: str
    url: str
    published_at: str


def fetch_headlines() -> tuple[list[Headline], str | None]:
    """Returns (headlines, error). headlines is [] if skipped or failed."""
    if not NEWSAPI_KEY:
        return [], "NEWSAPI_KEY not set -- skipped (optional)."

    params = {
        "q": NEWS_QUERY,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": NEWS_PAGE_SIZE,
        "apiKey": NEWSAPI_KEY,
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "ok":
            return [], f"NewsAPI error: {data.get('message', 'unknown error')}"
        articles = data.get("articles", [])
        headlines = [
            Headline(
                title=a.get("title", "(no title)"),
                source=(a.get("source") or {}).get("name", "unknown"),
                url=a.get("url", ""),
                published_at=a.get("publishedAt", ""),
            )
            for a in articles
        ]
        return headlines, None
    except Exception as exc:
        log.debug("NewsAPI fetch failed: %s", exc)
        return [], f"NewsAPI request failed: {exc}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    heads, err = fetch_headlines()
    if err:
        print("SKIPPED:", err)
    for h in heads:
        print(f"- [{h.source}] {h.title}")
