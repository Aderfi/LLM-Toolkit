"""Shell and code execution for the agent.

``run_bash`` is a deliberate exception to the "argv lists, never ``bash -c``" rule: the agent
writes shell command lines. Read-only commands run directly; anything else needs human
confirmation (see ``is_read_only``). The working directory must be inside an allowed root.
"""

import re
import shlex
import sys

from .core import resolve_safe_path, run_argv, tool

# Commands that only read. A command line is read-only if every pipeline stage starts with one
# of these and uses none of its forbidden (writing / executing) flags.
_READ_ONLY: dict[str, tuple[str, ...]] = {
    "ls": (),
    "cat": (),
    "head": (),
    "tail": (),
    "wc": (),
    "grep": (),
    "egrep": (),
    "rg": ("--pre",),
    "find": ("-exec", "-ok", "-delete", "-fprint", "-fls"),
    "fd": ("-x", "-X", "--exec"),
    "fdfind": ("-x", "-X", "--exec"),
    "tree": ("-o",),
    "stat": (),
    "file": (),
    "du": (),
    "df": (),
    "pwd": (),
    "echo": (),
    "which": (),
    "whoami": (),
    "date": (),
    "basename": (),
    "dirname": (),
    "realpath": (),
    "readlink": (),
    "cut": (),
    "tr": (),
    "sort": ("-o", "--output"),
    "uniq": (),
    "diff": (),
    "cmp": (),
    "md5sum": (),
    "sha256sum": (),
    "git": ("--output",),
}
_READ_ONLY_GIT = {"status", "log", "diff", "show", "blame", "ls-files", "rev-parse"}
_HARMLESS_REDIRECTS = re.compile(r"\s2>/dev/null|\s2>&1")
_SHELL_META = re.compile(r"[<>`]|\$\(")  # redirection or command substitution


def is_read_only(command: str) -> bool:
    """True if ``command`` only reads (safe to run without asking)."""
    cmd = _HARMLESS_REDIRECTS.sub(" ", command)
    if _SHELL_META.search(cmd):
        return False
    for stage in re.split(r"\|\||&&|[|;&\n]", cmd):
        try:
            words = shlex.split(stage)
        except ValueError:
            return False
        if not words:
            continue
        name, args = words[0], words[1:]
        if name not in _READ_ONLY:
            return False
        if any(a.startswith(f) for a in args for f in _READ_ONLY[name]):
            return False
        if name == "git" and (not args or args[0] not in _READ_ONLY_GIT):
            return False
    return True


@tool(confirm=lambda a: not is_read_only(a["command"]))
def run_bash(command: str, cwd: str = ".", timeout: int = 0) -> str:
    """Run a bash command line and return its output. Preferred for any filesystem work:
    navigating, listing, searching, creating, moving or inspecting files.

    Args:
        command: Bash command line, e.g. 'ls -la' or 'rg -n TODO src | head'.
        cwd: Working directory (relative to FILES_ROOT, must be inside allowed roots).
        timeout: Seconds before the command is killed (0 = COMMAND_TIMEOUT setting).
    """
    return run_argv(["bash", "-c", command], cwd=resolve_safe_path(cwd), timeout=timeout or None)


@tool(confirm=True)
def run_python(code: str, cwd: str = ".", timeout: int = 0) -> str:
    """Run a Python snippet in a separate process and return what it prints.
    Use it for calculations or data processing, not for file navigation (use run_bash).

    Args:
        code: Python source code; print() the results you need.
        cwd: Working directory (relative to FILES_ROOT, must be inside allowed roots).
        timeout: Seconds before the process is killed (0 = COMMAND_TIMEOUT setting).
    """
    return run_argv(
        [sys.executable, "-c", code], cwd=resolve_safe_path(cwd), timeout=timeout or None
    )
