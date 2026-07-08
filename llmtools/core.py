import inspect
import os
import shutil
import typing

from llmtools import config

REGISTRY: dict = {}
_SCHEMAS: list = []

_PY_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _parse_docstring(doc: str):
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


def tool(fn):
    sig = inspect.signature(fn)
    summary, arg_docs = _parse_docstring(fn.__doc__ or "")
    props, required = {}, []
    for name, p in sig.parameters.items():
        ann = p.annotation
        origin = typing.get_origin(ann)
        base = typing.get_args(ann)[0] if origin is typing.Union else ann
        jtype = _PY_TO_JSON.get(base, "string")
        props[name] = {"type": jtype, "description": arg_docs.get(name, "")}
        if p.default is inspect.Parameter.empty:
            required.append(name)
    schema = {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": summary,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }
    REGISTRY[fn.__name__] = fn
    _SCHEMAS.append(schema)
    return fn


def get_schemas():
    return list(_SCHEMAS)


def call_tool(name, args):
    fn = REGISTRY.get(name)
    if not fn:
        return f"[ERROR] Unknown tool: {name}"
    try:
        return str(fn(**args))
    except Exception as e:
        return f"[ERROR] {name} failed: {e}"


def resolve_safe_path(path):
    ap = os.path.abspath(os.path.expanduser(path))
    roots = [os.path.abspath(os.path.expanduser(r)) for r in config.ALLOWED_ROOTS]
    if not any(ap == r or ap.startswith(r + os.sep) for r in roots):
        raise ValueError(f"Path '{path}' is outside allowed roots.")
    return ap


def backup_file(path):
    if os.path.isfile(path):
        root, ext = os.path.splitext(path)
        shutil.copy2(path, f"{root}._backup{ext}")
