import os

from llmtools.core import backup_file, resolve_safe_path, tool


@tool
def create_markdown_doc(path: str, title: str, body: str) -> str:
    """Create a markdown document with an H1 title (backs up existing).

    Args:
        path: Output file path.
        title: Document title (H1).
        body: Markdown body.
    """
    ap = resolve_safe_path(path)
    backup_file(ap)
    os.makedirs(os.path.dirname(ap) or ".", exist_ok=True)
    with open(ap, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n{body}\n")
    return f"Wrote {ap}"


@tool
def markdown_table(headers: str, rows: str) -> str:
    """Build a markdown table.

    Args:
        headers: Comma-separated header cells.
        rows: Rows as 'a,b;c,d' (cells comma-separated, rows semicolon-separated).
    """
    from tabulate import tabulate
    h = [c.strip() for c in headers.split(",")]
    body = [[c.strip() for c in r.split(",")] for r in rows.split(";") if r.strip()]
    return tabulate(body, headers=h, tablefmt="github")


@tool
def add_table_of_contents(markdown_text: str) -> str:
    """Generate a table of contents from markdown headings.

    Args:
        markdown_text: Markdown source with # headings.
    """
    toc = []
    for line in markdown_text.splitlines():
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            text = line.lstrip("#").strip()
            anchor = text.lower().replace(" ", "-")
            toc.append("  " * (level - 1) + f"- [{text}](#{anchor})")
    return "\n".join(toc) if toc else "(no headings)"
