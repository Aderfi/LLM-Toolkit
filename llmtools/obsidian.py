import glob
import os
from datetime import datetime

from .config import get_settings
from .core import backup_file, resolve_safe_path, tool


def _vault():
    vault = get_settings().obsidian_vault
    if vault is None:
        raise ValueError("OBSIDIAN_VAULT is not configured.")
    return str(vault)


def _note_path(name):
    name = name if name.endswith(".md") else name + ".md"
    return resolve_safe_path(os.path.join(_vault(), name))


@tool
def create_note(title: str, content: str, tags: str = "") -> str:
    """Create an Obsidian note with YAML frontmatter.

    Args:
        title: Note title (also the filename).
        content: Markdown body.
        tags: Comma-separated tags.
    """
    import frontmatter
    p = _note_path(title)
    backup_file(p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    post = frontmatter.Post(content, title=title,
                            created=f"{datetime.now():%Y-%m-%d}", tags=tag_list)
    with open(p, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))
    return f"Created note: {p}"


@tool
def read_note(title: str) -> str:
    """Read an Obsidian note by title.

    Args:
        title: Note title.
    """
    with open(_note_path(title), encoding="utf-8") as f:
        return f.read()


@tool
def append_to_note(title: str, content: str) -> str:
    """Append text to an existing note (backs up first).

    Args:
        title: Note title.
        content: Text to append.
    """
    p = _note_path(title)
    backup_file(p)
    with open(p, "a", encoding="utf-8") as f:
        f.write("\n" + content + "\n")
    return f"Appended to {p}"


@tool
def list_notes() -> str:
    """List all notes in the vault."""
    hits = glob.glob(os.path.join(_vault(), "**", "*.md"), recursive=True)
    return "\n".join(os.path.relpath(h, _vault()) for h in hits) or "(no notes)"


@tool
def search_vault(query: str) -> str:
    """Search note contents for a query string.

    Args:
        query: Text to search for.
    """
    hits = []
    for h in glob.glob(os.path.join(_vault(), "**", "*.md"), recursive=True):
        try:
            with open(h, encoding="utf-8", errors="replace") as f:
                if query.lower() in f.read().lower():
                    hits.append(os.path.relpath(h, _vault()))
        except OSError:
            pass
    return "\n".join(hits) if hits else "No matches."


@tool
def add_tags_to_note(title: str, tags: str) -> str:
    """Append tags as an inline line to a note (backs up first).

    Args:
        title: Note title.
        tags: Comma-separated tags.
    """
    p = _note_path(title)
    backup_file(p)
    inline = " ".join("#" + t.strip() for t in tags.split(",") if t.strip())
    with open(p, "a", encoding="utf-8") as f:
        f.write("\n" + inline + "\n")
    return f"Added tags to {p}"
