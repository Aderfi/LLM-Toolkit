"""Shared HTTP client (httpx) for public APIs."""

from functools import lru_cache

import httpx

USER_AGENT = "llmtools/0.1 (+personal use)"


@lru_cache
def client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )


def get_json(url: str, **params) -> dict | list | None:
    """GET and decode JSON. Returns ``None`` if the API answers without a body (204)."""
    r = client().get(url, params={k: v for k, v in params.items() if v not in (None, "")})
    r.raise_for_status()
    if r.status_code == 204 or not r.content:
        return None
    return r.json()
