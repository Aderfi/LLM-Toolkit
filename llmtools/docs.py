import os
import re
import shutil
import subprocess

from llmtools.core import tool


def _reject_flag(*values):
    """Block argv flag-smuggling: no argument may start with '-'."""
    for v in values:
        if v.strip().startswith("-"):
            return f"Error: invalid argument '{v}' (must not start with '-')."
    return None


@tool
def get_library_docs(query: str, library: str = "") -> str:
    """Get up-to-date docs for a programming library/framework/API via Context7.

    Args:
        query: What you want to know, e.g. 'polars groupby aggregation'.
        library: Optional library name or Context7 id like '/pola-rs/polars'
            (empty = resolve from the query).
    """
    if shutil.which("npx") is None:
        return "Error: Node.js/npx not installed (needed for Context7)."
    if library.startswith("/"):
        lib_id = library
    else:
        name = library or query
        err = _reject_flag(name, query)
        if err:
            return err
        r = subprocess.run(["npx", "ctx7@latest", "library", name, query],
                           capture_output=True, text=True, timeout=120)
        m = re.search(r"(/[\w.-]+/[\w.-]+)", r.stdout)
        if not m:
            return f"No Context7 library matched '{name}'.\n{r.stdout[:400]}"
        lib_id = m.group(1)
    err = _reject_flag(query)
    if err:
        return err
    r = subprocess.run(["npx", "ctx7@latest", "docs", lib_id, query],
                       capture_output=True, text=True, timeout=120)
    out = r.stdout.strip()
    return f"[{lib_id}]\n{out[:6000]}" if out else "(no docs returned)"


@tool
def get_command_help(program: str) -> str:
    """Get help for a CLI program: tldr examples first, else the man page.

    Args:
        program: Command/program name, e.g. 'ffmpeg' or 'git rebase'.
    """
    err = _reject_flag(program)
    if err:
        return err
    if shutil.which("tldr"):
        r = subprocess.run(["tldr", "--", program], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    if shutil.which("man"):
        env = {**os.environ, "MANPAGER": "cat", "PAGER": "cat", "MANWIDTH": "80"}
        r = subprocess.run(["man", "--", program.split()[0]], capture_output=True,
                           text=True, env=env)
        if r.returncode == 0 and r.stdout.strip():
            text = re.sub(r".\x08", "", r.stdout)  # strip man backspace formatting
            return text[:6000]
    return f"No tldr/man entry for '{program}'."


@tool
def devdocs_find(query: str) -> str:
    """Find matching DevDocs documentation sets and their URLs for a technology.

    Args:
        query: Technology name, e.g. 'python', 'react', 'postgresql'.
    """
    import requests
    try:
        docs = requests.get("https://devdocs.io/docs.json", timeout=20).json()
    except Exception as e:
        return f"Error: {e}"
    q = query.lower()
    hits = [d for d in docs
            if q in d.get("name", "").lower() or q in d.get("slug", "").lower()]
    if not hits:
        return f"No DevDocs match for '{query}'."
    return "\n".join(f"{d['name']} -> https://devdocs.io/{d['slug']}" for d in hits[:15])
