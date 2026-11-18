"""Tool registry: ``@tool`` decorator, JSON schemas and validated execution.

Each tool is a plain function with type hints and a Google-style docstring.
A Pydantic model is built from the signature that:
  * generates the JSON Schema sent to the LLM, and
  * validates/coerces the arguments the LLM returns before running ("5" -> 5).
"""

import inspect
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from .config import get_settings

# Static flag, or a predicate over the call arguments (e.g. "only if the command writes").
ConfirmPolicy = bool | Callable[[dict], bool]


@dataclass(frozen=True)
class Tool:
    name: str
    fn: Callable[..., Any]
    args_model: type[BaseModel]
    description: str
    group: str  # module name, e.g. "cima"
    confirm: ConfirmPolicy  # needs human confirmation before running

    def schema(self) -> dict:
        params = self.args_model.model_json_schema()
        params.pop("title", None)
        for prop in params.get("properties", {}).values():
            prop.pop("title", None)
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": params},
        }


REGISTRY: dict[str, Tool] = {}
# Groups currently offered to the model; the agent seeds it and enable_toolset extends it.
ACTIVE_GROUPS: set[str] = set()


def _parse_docstring(doc: str) -> tuple[str, dict[str, str]]:
    """Return (summary, {arg_name: description})."""
    summary, args = "", {}
    if not doc:
        return summary, args
    lines = [n.strip() for n in doc.strip().splitlines()]
    summary = lines[0]
    in_args = False
    for n in lines:
        if n.lower().startswith("args:"):
            in_args = True
            continue
        if in_args and ":" in n:
            name, _, desc = n.partition(":")
            args[name.strip()] = desc.strip()
    return summary, args


def _register(fn: Callable, confirm: ConfirmPolicy) -> Callable:
    summary, arg_docs = _parse_docstring(fn.__doc__ or "")
    fields = {}
    for name, p in inspect.signature(fn).parameters.items():
        ann = str if p.annotation is inspect.Parameter.empty else p.annotation
        default = ... if p.default is inspect.Parameter.empty else p.default
        fields[name] = (ann, Field(default, description=arg_docs.get(name, "")))
    model = create_model(f"{fn.__name__}_args", __config__=ConfigDict(extra="ignore"), **fields)
    REGISTRY[fn.__name__] = Tool(
        name=fn.__name__,
        fn=fn,
        args_model=model,
        description=summary,
        group=fn.__module__.rsplit(".", 1)[-1],
        confirm=confirm,
    )
    return fn


def tool(fn: Callable | None = None, *, confirm: ConfirmPolicy = False):
    """Register a tool: ``@tool``, ``@tool(confirm=True)`` or ``@tool(confirm=predicate)``."""
    if fn is None:
        return lambda f: _register(f, confirm)
    return _register(fn, confirm)


def get_schemas(groups: frozenset[str] | set[str] | None = None) -> list[dict]:
    """Tool schemas (all of them, or only those in ``groups``)."""
    return [t.schema() for t in REGISTRY.values() if groups is None or t.group in groups]


def needs_confirmation(name: str, args: dict | None = None) -> bool:
    t = REGISTRY.get(name)
    if not t:
        return False
    if callable(t.confirm):
        try:
            return bool(t.confirm(t.args_model.model_validate(args or {}).model_dump()))
        except ValidationError:
            return False  # call_tool reports the invalid arguments
    return t.confirm


def call_tool(name: str, args: dict | None) -> str:
    t = REGISTRY.get(name)
    if not t:
        return f"[ERROR] Unknown tool: {name}"
    try:
        validated = t.args_model.model_validate(args or {})
    except ValidationError as e:
        return f"[ERROR] Invalid arguments for {name}: {e}"
    try:
        return str(t.fn(**dict(validated)))
    except Exception as e:
        return f"[ERROR] {name} failed: {type(e).__name__}: {e}"


def resolve_safe_path(path: str | Path) -> str:
    """Resolve ``path`` (relative to FILES_ROOT) and require it to be inside an allowed root."""
    s = get_settings()
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = s.files_root / p
    p = p.resolve()
    if not any(p.is_relative_to(r) for r in s.allowed_roots):
        raise ValueError(f"Path '{path}' is outside allowed roots.")
    return str(p)


def backup_file(path: str) -> None:
    p = Path(path)
    if p.is_file():
        shutil.copy2(p, p.with_name(f"{p.stem}._backup{p.suffix}"))


def truncate(text: str, limit: int | None = None) -> str:
    """Cut ``text`` to MAX_OUTPUT_CHARS (or ``limit``), keeping head and tail."""
    limit = limit or get_settings().max_output_chars
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n... [{len(text) - limit} chars truncated] ...\n{text[-half:]}"


def run_argv(argv: list[str], cwd: str | None = None, timeout: int | None = None) -> str:
    """Run a command (argv list, no shell) and return stdout+stderr, truncated.

    A non-zero exit code is reported in the output instead of raising, so the model sees it.
    """
    if shutil.which(argv[0]) is None:
        raise FileNotFoundError(f"'{argv[0]}' is not installed.")
    try:
        r = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout or get_settings().command_timeout,
        )
    except subprocess.TimeoutExpired as e:
        return f"[timeout after {e.timeout}s]"
    out = (r.stdout + (f"\n[stderr]\n{r.stderr}" if r.stderr.strip() else "")).strip()
    if r.returncode != 0:
        out = f"[exit {r.returncode}]\n{out}"
    return truncate(out) or "(no output)"
