"""Interactive web browser (Playwright, Chromium) whose session persists between tool calls.

Use it for pages that need JavaScript, clicks, forms or a login; for plain articles
``fetch_url`` / ``web_research`` are faster. The profile (cookies, logins) is kept in
DATA_DIR/browser_profile.

One-off requirement: ``uv run playwright install chromium``
"""

from .config import get_settings
from .core import resolve_safe_path, tool, truncate

_session: dict = {}  # playwright, context, page
_MAX_LINKS = 60


def _page():
    page = _session.get("page")
    if page is not None and not page.is_closed():
        return page
    from playwright.sync_api import sync_playwright

    s = get_settings()
    if "pw" not in _session:
        _session["pw"] = sync_playwright().start()
    s.browser_profile_dir.mkdir(parents=True, exist_ok=True)
    ctx = _session["pw"].chromium.launch_persistent_context(
        str(s.browser_profile_dir), headless=s.browser_headless
    )
    _session["ctx"] = ctx
    _session["page"] = ctx.pages[0] if ctx.pages else ctx.new_page()
    return _session["page"]


def _snapshot(page, max_chars: int) -> str:
    """URL, title, visible text and the first links of the current page."""
    text = page.inner_text("body")
    links = page.eval_on_selector_all(
        "a[href]", "els => els.map(e => [e.innerText.trim(), e.href]).filter(l => l[0])"
    )
    link_lines = "\n".join(f"- {t[:80]}: {u}" for t, u in links[:_MAX_LINKS])
    return (
        f"URL: {page.url}\nTitle: {page.title()}\n\n{truncate(text, max_chars)}"
        f"\n\nLinks:\n{link_lines or '(none)'}"
    )


def _locate(page, target: str):
    """CSS/Playwright selector if it looks like one, otherwise the first element with that text."""
    if target[:1] in "#.[/" or "=" in target:
        return page.locator(target).first
    return page.get_by_text(target).first


@tool
def browser_open(url: str, max_chars: int = 6000) -> str:
    """Open a URL in the browser (renders JavaScript) and return the page text and links.

    Args:
        url: Address to open.
        max_chars: Truncate the page text to this many characters.
    """
    page = _page()
    page.goto(url, wait_until="domcontentloaded")
    return _snapshot(page, max_chars)


@tool
def browser_click(target: str, max_chars: int = 6000) -> str:
    """Click an element on the current page and return the resulting page.

    Args:
        target: Visible text of a link/button, or a CSS selector like '#submit'.
        max_chars: Truncate the page text to this many characters.
    """
    page = _page()
    _locate(page, target).click()
    page.wait_for_load_state("domcontentloaded")
    return _snapshot(page, max_chars)


@tool(confirm=lambda a: a["submit"])
def browser_type(selector: str, text: str, submit: bool = False) -> str:
    """Type text into a field of the current page (optionally pressing Enter to submit).

    Args:
        selector: CSS selector of the input, e.g. 'input[name=q]'.
        text: Text to type.
        submit: Press Enter afterwards (asks for confirmation).
    """
    page = _page()
    field = page.locator(selector).first
    field.fill(text)
    if submit:
        field.press("Enter")
        page.wait_for_load_state("domcontentloaded")
        return _snapshot(page, 4000)
    return f"Typed into {selector}."


@tool
def browser_read(max_chars: int = 6000) -> str:
    """Return the text and links of the page currently open in the browser.

    Args:
        max_chars: Truncate the page text to this many characters.
    """
    return _snapshot(_page(), max_chars)


@tool
def browser_back(max_chars: int = 6000) -> str:
    """Go back to the previous page and return it.

    Args:
        max_chars: Truncate the page text to this many characters.
    """
    page = _page()
    page.go_back(wait_until="domcontentloaded")
    return _snapshot(page, max_chars)


@tool
def browser_screenshot(out_path: str = "browser.png", full_page: bool = False) -> str:
    """Save a screenshot of the current browser page.

    Args:
        out_path: Output PNG path.
        full_page: Capture the whole scrollable page, not just the viewport.
    """
    out = resolve_safe_path(out_path)
    _page().screenshot(path=out, full_page=full_page)
    return f"Screenshot saved to {out}"


@tool
def browser_close() -> str:
    """Close the browser session."""
    if "ctx" in _session:
        _session.pop("ctx").close()
    _session.pop("page", None)
    if "pw" in _session:
        _session.pop("pw").stop()
    return "Browser closed."
