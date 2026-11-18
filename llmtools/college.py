"""Circulars from the Pharmacists' College (website behind a login, via Playwright).

The session is kept in a persistent Chromium profile so it does not log in on every query.
URLs and the login form's CSS selectors are configurable in .env because they depend on
each college's website. If the college offers RSS (COLLEGE_RSS_URL) that is used instead,
which is much more stable than scraping.

One-off requirement: ``uv run playwright install chromium``
"""

import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from .config import Settings, get_settings
from .core import resolve_safe_path, tool

MAX_CHARS = 6000


def _require_config(s: Settings) -> None:
    missing = [
        n for n in ("college_user", "college_pass", "college_circulars_url") if not getattr(s, n)
    ]
    if missing:
        raise ValueError(f"Missing in .env: {', '.join(m.upper() for m in missing)}")


def _ensure_login(page, s: Settings) -> None:
    """If the page shows the login form, fill it in and go back to the circulars."""
    if page.locator(s.college_user_selector).count() == 0:
        return
    page.fill(s.college_user_selector, s.college_user)
    page.fill(s.college_pass_selector, s.college_pass.get_secret_value())
    page.click(s.college_submit_selector)
    page.wait_for_load_state("networkidle")
    page.goto(s.college_circulars_url, wait_until="networkidle")
    if page.locator(s.college_user_selector).count() > 0:
        raise RuntimeError("College login failed (wrong credentials or selectors?).")


def _open(p, s: Settings):
    s.college_profile_dir.mkdir(parents=True, exist_ok=True)
    return p.chromium.launch_persistent_context(str(s.college_profile_dir), headless=True)


def read_circulars() -> tuple[str, list[tuple[str, str]]]:
    """Return (text of the circulars page, [(title, url), ...] of its links)."""
    from playwright.sync_api import sync_playwright

    s = get_settings()
    _require_config(s)
    with sync_playwright() as p:
        ctx = _open(p, s)
        try:
            page = ctx.new_page()
            page.goto(s.college_login_url or s.college_circulars_url, wait_until="networkidle")
            _ensure_login(page, s)
            if page.url != s.college_circulars_url:
                page.goto(s.college_circulars_url, wait_until="networkidle")
            main = page.locator(s.college_content_selector).first
            text = main.inner_text()
            links = [
                (a.inner_text().strip(), urljoin(page.url, a.get_attribute("href") or ""))
                for a in main.locator("a[href]").all()
            ]
        finally:
            ctx.close()
    return text, [(t, u) for t, u in links if t]


def _from_rss(url: str) -> str:
    from .aemps import rss_entries

    items = rss_entries(url)
    return "\n".join(f"- {i['date'][:16]} {i['title']} ({i['link']})" for i in items[:20])


@tool
def college_circulars() -> str:
    """List the latest circulars from the Pharmacists' College (logs in if needed)."""
    s = get_settings()
    if s.college_rss_url:
        return _from_rss(s.college_rss_url)
    text, links = read_circulars()
    out = text[:MAX_CHARS]
    if links:
        out += "\n\nLinks:\n" + "\n".join(f"- {t[:120]}: {u}" for t, u in links[:40])
    return out


@tool
def college_download_circular(url: str) -> str:
    """Download a college circular (using the logged-in session) and return its text.

    Args:
        url: Circular URL (from the college_circulars list).
    """
    from playwright.sync_api import sync_playwright

    s = get_settings()
    _require_config(s)
    allowed_host = urlparse(s.college_circulars_url).netloc
    if urlparse(url).netloc != allowed_host:
        return f"[ERROR] Only URLs from {allowed_host} are allowed."
    with sync_playwright() as p:
        ctx = _open(p, s)
        try:
            page = ctx.new_page()
            page.goto(s.college_circulars_url, wait_until="networkidle")
            _ensure_login(page, s)
            resp = ctx.request.get(url)
            body, ctype = resp.body(), resp.headers.get("content-type", "")
            if "pdf" not in ctype:
                page.goto(url, wait_until="networkidle")
                return page.locator(s.college_content_selector).first.inner_text()[:MAX_CHARS]
        finally:
            ctx.close()

    name = re.sub(r"[^\w.-]", "_", Path(urlparse(url).path).name or "circular") or "circular"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    dest = Path(resolve_safe_path(f"circulars/{name}"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)

    from pypdf import PdfReader

    text = "\n".join(pg.extract_text() or "" for pg in PdfReader(dest).pages)
    return f"Saved to {dest}\n\n{text[:MAX_CHARS]}"
