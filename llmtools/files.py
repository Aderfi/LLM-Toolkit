import glob
import os
import shutil

from llmtools import config
from llmtools.core import backup_file, resolve_safe_path, tool


@tool
def list_directory(path: str = ".") -> str:
    """List files and folders in a directory.

    Args:
        path: Directory path.
    """
    ap = resolve_safe_path(path)
    entries = sorted(os.listdir(ap))
    return "\n".join(entries) if entries else "(empty)"


@tool
def find_files(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern, recursively.

    Args:
        pattern: Glob pattern, e.g. '*.md'.
        path: Root directory to search.
    """
    ap = resolve_safe_path(path)
    hits = glob.glob(os.path.join(ap, "**", pattern), recursive=True)
    return "\n".join(hits) if hits else "No matches."


@tool
def read_file(path: str) -> str:
    """Read a UTF-8 text file.

    Args:
        path: File path.
    """
    ap = resolve_safe_path(path)
    with open(ap, encoding="utf-8", errors="replace") as f:
        return f.read()


@tool
def write_file(path: str, content: str) -> str:
    """Write text to a file (backs up existing file first).

    Args:
        path: File path.
        content: Text content to write.
    """
    ap = resolve_safe_path(path)
    backup_file(ap)
    os.makedirs(os.path.dirname(ap) or ".", exist_ok=True)
    with open(ap, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Wrote {len(content)} chars to {ap}."


@tool
def move_file(src: str, dst: str) -> str:
    """Move/rename a file (backs up destination if it exists).

    Args:
        src: Source path.
        dst: Destination path.
    """
    a, b = resolve_safe_path(src), resolve_safe_path(dst)
    backup_file(b)
    shutil.move(a, b)
    return f"Moved {a} -> {b}."


@tool
def copy_file(src: str, dst: str) -> str:
    """Copy a file (backs up destination if it exists).

    Args:
        src: Source path.
        dst: Destination path.
    """
    a, b = resolve_safe_path(src), resolve_safe_path(dst)
    backup_file(b)
    shutil.copy2(a, b)
    return f"Copied {a} -> {b}."


@tool
def delete_file(path: str) -> str:
    """Delete a file (disabled unless ALLOW_DELETE_FILES is True).

    Args:
        path: File path.
    """
    if not config.ALLOW_DELETE_FILES:
        return "Deletion is disabled (ALLOW_DELETE_FILES=False)."
    ap = resolve_safe_path(path)
    os.remove(ap)
    return f"Deleted {ap}."
