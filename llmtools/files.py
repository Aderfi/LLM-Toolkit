import glob
import os
import shutil

from .config import get_settings
from .core import backup_file, resolve_safe_path, run_argv, tool

# Folders skipped by tree/search listings.
_NOISE_DIRS = [".git", "node_modules", "__pycache__", ".venv", ".mypy_cache", ".ruff_cache"]


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


@tool(confirm=True)
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


@tool(confirm=True)
def delete_file(path: str) -> str:
    """Delete a file (disabled unless ALLOW_DELETE_FILES is True).

    Args:
        path: File path.
    """
    if not get_settings().allow_delete_files:
        return "Deletion is disabled (ALLOW_DELETE_FILES=False)."
    ap = resolve_safe_path(path)
    os.remove(ap)
    return f"Deleted {ap}."


@tool
def edit_file(path: str, old_text: str, new_text: str, replace_all: bool = False) -> str:
    """Replace an exact text fragment in a file (backs up the file first).

    Args:
        path: File path.
        old_text: Exact text to replace (include enough context to be unique).
        new_text: Replacement text.
        replace_all: Replace every occurrence instead of requiring exactly one.
    """
    ap = resolve_safe_path(path)
    with open(ap, encoding="utf-8") as f:
        content = f.read()
    n = content.count(old_text)
    if n == 0:
        return "[ERROR] old_text not found; read the file and copy the fragment exactly."
    if n > 1 and not replace_all:
        return f"[ERROR] old_text found {n} times; add context or set replace_all=True."
    backup_file(ap)
    with open(ap, "w", encoding="utf-8") as f:
        f.write(content.replace(old_text, new_text))
    return f"Replaced {n if replace_all else 1} occurrence(s) in {ap}."


@tool
def make_directory(path: str) -> str:
    """Create a directory, including missing parents (mkdir -p).

    Args:
        path: Directory path.
    """
    ap = resolve_safe_path(path)
    out = run_argv(["mkdir", "-p", "--", ap])
    return f"Created {ap}." if out == "(no output)" else out


@tool
def grep_files(
    pattern: str,
    path: str = ".",
    glob_pattern: str = "",
    ignore_case: bool = False,
    max_results: int = 100,
) -> str:
    """Search file contents with a regex (ripgrep, or grep -r) and return file:line:match.

    Args:
        pattern: Regular expression to search for.
        path: File or directory to search.
        glob_pattern: Only files matching this glob, e.g. '*.py'.
        ignore_case: Case-insensitive search.
        max_results: Maximum number of matching lines returned.
    """
    ap = resolve_safe_path(path)
    if shutil.which("rg"):
        argv = ["rg", "-n", "--no-heading", "--color", "never"]
        argv += ["-i"] if ignore_case else []
        argv += ["-g", glob_pattern] if glob_pattern else []
    else:
        argv = ["grep", "-rnI", *(f"--exclude-dir={d}" for d in _NOISE_DIRS)]
        argv += ["-i"] if ignore_case else []
        argv += [f"--include={glob_pattern}"] if glob_pattern else []
    out = run_argv([*argv, "-e", pattern, "--", ap])
    if out.startswith("[exit 1]"):  # rg/grep: exit 1 = no matches
        return "No matches."
    lines = out.splitlines()
    more = f"\n... ({len(lines) - max_results} more lines)" if len(lines) > max_results else ""
    return "\n".join(lines[:max_results]) + more


@tool
def file_tree(path: str = ".", depth: int = 2) -> str:
    """Show the directory tree (tree, or find) skipping .git, node_modules, caches and venvs.

    Args:
        path: Root directory.
        depth: Maximum depth to show.
    """
    ap = resolve_safe_path(path)
    if shutil.which("tree"):
        return run_argv(
            ["tree", "-a", "--noreport", "-L", str(depth), "-I", "|".join(_NOISE_DIRS), ap]
        )
    prune = []
    for d in _NOISE_DIRS:
        prune += ["-name", d, "-o"]
    return run_argv(
        ["find", ap, "-maxdepth", str(depth), "(", *prune[:-1], ")", "-prune", "-o", "-print"]
    )


@tool
def disk_usage(path: str = ".") -> str:
    """Size of a directory and of its direct children (du -h -d 1).

    Args:
        path: Directory path.
    """
    return run_argv(["du", "-h", "-d", "1", "--", resolve_safe_path(path)])
