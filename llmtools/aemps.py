"""AEMPS alerts and information notes (aemps.gob.es RSS; they are not in CIMA)."""

import feedparser

from ._http import client
from .config import get_settings
from .core import tool


def rss_entries(url: str | None = None) -> list[dict]:
    r = client().get(url or get_settings().aemps_rss_url, headers={"Accept": "application/rss+xml"})
    r.raise_for_status()
    feed = feedparser.parse(r.content)
    return [
        {
            "title": e.get("title", ""),
            "link": e.get("link", ""),
            "date": e.get("published", ""),
            "summary": e.get("summary", ""),
        }
        for e in feed.entries
    ]


@tool
def aemps_alerts(text: str = "", max_results: int = 10) -> str:
    """Latest alerts, recalls and information notes published by the Spanish AEMPS.

    Args:
        text: Text to filter titles by, e.g. 'retira' or 'seguridad' (empty = all).
        max_results: Maximum number of results.
    """
    items = rss_entries()
    if text:
        items = [i for i in items if text.lower() in i["title"].lower()]
    if not items:
        return "No matching publications."
    return "\n".join(f"- {i['date'][:16]} {i['title']} ({i['link']})" for i in items[:max_results])
