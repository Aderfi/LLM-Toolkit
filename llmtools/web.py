import re

import requests

from .core import tool

try:
    from ddgs import DDGS
except ImportError:  # older package name
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web via DuckDuckGo.

    Args:
        query: Search query.
        max_results: Number of results.
    """
    if DDGS is None:
        return "Error: install 'ddgs' (pip install ddgs)."
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
    if not results:
        return "No results."
    return "\n\n".join(
        f"{i}. {r.get('title', '')}\n   {r.get('href', '')}\n   {r.get('body', '')}"
        for i, r in enumerate(results, 1)
    )


def _html_to_text(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    return re.sub(r"\s+\n", "\n", re.sub(r"[ \t]+", " ", text)).strip()


@tool
def fetch_url(url: str, max_chars: int = 4000) -> str:
    """Download a web page and return its main content as clean markdown.

    Args:
        url: The URL to fetch.
        max_chars: Truncate output to this many characters.
    """
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Gemma4Tools/1.0"})
    resp.raise_for_status()
    text = None
    try:
        import trafilatura
        text = trafilatura.extract(resp.text, url=url, output_format="markdown",
                                   include_links=True)
    except ImportError:
        pass
    if not text:  # trafilatura missing or found no main content
        text = _html_to_text(resp.text)
    return text[:max_chars] + ("…" if len(text) > max_chars else "")


@tool
def web_research(query: str, max_results: int = 3, max_chars_per_page: int = 3000) -> str:
    """Search the web and read the top results in one step (search + fetch each page).

    Args:
        query: Search query.
        max_results: How many result pages to read.
        max_chars_per_page: Truncate each page to this many characters.
    """
    if DDGS is None:
        return "Error: install 'ddgs' (pip install ddgs)."
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
    if not results:
        return "No results."
    parts = []
    for i, r in enumerate(results, 1):
        url = r.get("href", "")
        try:
            body = fetch_url(url, max_chars_per_page)
        except Exception as e:  # one unreachable page should not sink the others
            body = f"[could not fetch: {type(e).__name__}: {e}]\n{r.get('body', '')}"
        parts.append(f"## {i}. {r.get('title', '')}\nSource: {url}\n\n{body}")
    return "\n\n".join(parts)
