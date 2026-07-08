# Gemma4:e4b Local Toolset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular Python tool set exposed to a local Ollama `gemma4:e4b` model via function-calling, covering Obsidian notes, markdown, documents (PDF/Word), web search+fetch, graphs, files, git, and utilities.

**Architecture:** A `@tool` decorator in `llmtools/core.py` introspects each function's type hints + docstring to build the Ollama JSON schema and auto-registers `name → callable` in a central `REGISTRY`. Tool modules (obsidian, markdown, documents, web, graphs, files, git, utils, daily) just decorate plain functions. `agent.py` is the CLI runner: prompt → ollama → dispatch tool_calls → final answer.

**Tech Stack:** Python 3.13, Ollama HTTP API (`urllib`), `pypdf`, `python-docx`, `ddgs`, `requests`, system `git`/`graphviz` (optional).

## Global Constraints

- Every tool returns a `str`, never raises (exceptions caught → error string).
- `@tool` decorator is the ONLY registration mechanism; no manual schema lists.
- File-mutating ops call `backup_file()` first: `name.ext` → `name._backup.ext`.
- `ALLOW_DELETE_FILES = False` constant gates `delete_file`.
- File/git ops confined to `ALLOWED_ROOTS` via `resolve_safe_path()`.
- Vault path is the placeholder constant `DEFAULT_VAULT` in `config.py`.
- Model constant: `MODEL = "gemma4:e4b"`.
- Tests use `pytest`; network/binary-dependent tests marked or use local fixtures.

---

### Task 1: Package scaffold + config

**Files:**
- Create: `llmtools/__init__.py`, `llmtools/config.py`, `requirements.txt`, `tests/__init__.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `config.DEFAULT_VAULT: str`, `config.MODEL: str`, `config.ALLOW_DELETE_FILES: bool`, `config.ALLOWED_ROOTS: list[str]`, `config.NEWS_API_KEY: str`.

- [ ] **Step 1: Write `requirements.txt`**

```
pypdf>=4.0
python-docx>=1.1
ddgs>=6.0
requests>=2.31
pytest>=8.0
```

- [ ] **Step 2: Write `llmtools/config.py`**

```python
import os

# --- User-editable placeholders ---
DEFAULT_VAULT = os.path.expanduser(os.environ.get("OBSIDIAN_VAULT", "DEFAULT_VAULT"))
MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "YOUR_NEWS_API_KEY")

# --- Safety switches ---
ALLOW_DELETE_FILES = False  # hardcode True to enable delete_file

# Roots that file/git tools may touch. cwd + vault by default.
ALLOWED_ROOTS = [os.getcwd(), DEFAULT_VAULT]
```

- [ ] **Step 3: Write test `tests/test_config.py`**

```python
from llmtools import config

def test_delete_disabled_by_default():
    assert config.ALLOW_DELETE_FILES is False

def test_model_is_gemma4_e4b():
    assert config.MODEL == "gemma4:e4b"
```

- [ ] **Step 4: Run** `pytest tests/test_config.py -v` — Expected: PASS (empty `__init__.py` files created).

- [ ] **Step 5: Commit** `feat: package scaffold + config`

---

### Task 2: Core registry (`@tool` decorator + safety helpers)

**Files:**
- Create: `llmtools/core.py`, `tests/test_core.py`

**Interfaces:**
- Produces:
  - `@tool` decorator (registers fn, wraps exceptions → str).
  - `REGISTRY: dict[str, callable]`
  - `get_schemas() -> list[dict]` (Ollama function schemas)
  - `call_tool(name: str, args: dict) -> str`
  - `resolve_safe_path(path: str) -> str` (raises `ValueError` if outside roots)
  - `backup_file(path: str) -> None`

- [ ] **Step 1: Write failing test `tests/test_core.py`**

```python
import pytest
from llmtools import core

def test_tool_builds_schema_from_hints():
    @core.tool
    def sample(city: str, count: int = 3) -> str:
        """Do a thing.

        Args:
            city: The city name.
            count: How many.
        """
        return f"{city}-{count}"

    schemas = {s["function"]["name"]: s for s in core.get_schemas()}
    assert "sample" in schemas
    props = schemas["sample"]["function"]["parameters"]["properties"]
    assert props["city"]["type"] == "string"
    assert props["count"]["type"] == "integer"
    assert schemas["sample"]["function"]["parameters"]["required"] == ["city"]

def test_call_tool_returns_string_and_catches_errors():
    @core.tool
    def boom() -> str:
        """Explode."""
        raise RuntimeError("kaboom")
    out = core.call_tool("boom", {})
    assert isinstance(out, str) and "kaboom" in out

def test_resolve_safe_path_rejects_outside(tmp_path, monkeypatch):
    monkeypatch.setattr(core.config, "ALLOWED_ROOTS", [str(tmp_path)])
    with pytest.raises(ValueError):
        core.resolve_safe_path("/etc/passwd")

def test_backup_file_creates_backup(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("hi")
    core.backup_file(str(f))
    assert (tmp_path / "note._backup.md").read_text() == "hi"
```

- [ ] **Step 2: Run** `pytest tests/test_core.py -v` — Expected: FAIL (module attrs missing).

- [ ] **Step 3: Implement `llmtools/core.py`**

```python
import inspect
import os
import shutil
import typing
from llmtools import config

REGISTRY: dict = {}
_SCHEMAS: list = []

_PY_TO_JSON = {str: "string", int: "integer", float: "number", bool: "boolean",
               list: "array", dict: "object"}

def _parse_docstring(doc: str):
    """Return (summary, {arg_name: description})."""
    summary, args = "", {}
    if not doc:
        return summary, args
    lines = [l.strip() for l in doc.strip().splitlines()]
    summary = lines[0]
    in_args = False
    for l in lines:
        if l.lower().startswith("args:"):
            in_args = True
            continue
        if in_args and ":" in l:
            name, _, desc = l.partition(":")
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
    schema = {"type": "function", "function": {
        "name": fn.__name__, "description": summary,
        "parameters": {"type": "object", "properties": props, "required": required}}}
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
```

- [ ] **Step 4: Run** `pytest tests/test_core.py -v` — Expected: PASS.

- [ ] **Step 5: Commit** `feat: core @tool registry + safety helpers`

---

### Task 3: Files module

**Files:**
- Create: `llmtools/files.py`, `tests/test_files.py`

**Interfaces:**
- Consumes: `core.tool`, `resolve_safe_path`, `backup_file`, `config.ALLOW_DELETE_FILES`.
- Produces tools: `list_directory`, `find_files`, `read_file`, `write_file`, `move_file`, `copy_file`, `delete_file`.

- [ ] **Step 1: Write failing test `tests/test_files.py`**

```python
import os
from llmtools import files, core, config

def _roots(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ALLOWED_ROOTS", [str(tmp_path)])

def test_write_then_read(tmp_path, monkeypatch):
    _roots(tmp_path, monkeypatch)
    p = str(tmp_path / "a.txt")
    files.write_file(p, "hello")
    assert "hello" in files.read_file(p)

def test_write_backs_up_existing(tmp_path, monkeypatch):
    _roots(tmp_path, monkeypatch)
    p = str(tmp_path / "a.txt")
    files.write_file(p, "v1")
    files.write_file(p, "v2")
    assert (tmp_path / "a._backup.txt").read_text() == "v1"

def test_delete_blocked_when_disabled(tmp_path, monkeypatch):
    _roots(tmp_path, monkeypatch)
    monkeypatch.setattr(config, "ALLOW_DELETE_FILES", False)
    p = str(tmp_path / "a.txt")
    files.write_file(p, "x")
    out = files.delete_file(p)
    assert "disabled" in out.lower() and os.path.exists(p)

def test_delete_allowed_when_enabled(tmp_path, monkeypatch):
    _roots(tmp_path, monkeypatch)
    monkeypatch.setattr(config, "ALLOW_DELETE_FILES", True)
    p = str(tmp_path / "a.txt")
    files.write_file(p, "x")
    files.delete_file(p)
    assert not os.path.exists(p)
```

- [ ] **Step 2: Run** `pytest tests/test_files.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `llmtools/files.py`**

```python
import os
import shutil
import glob
from llmtools import config
from llmtools.core import tool, resolve_safe_path, backup_file

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
```

- [ ] **Step 4: Run** `pytest tests/test_files.py -v` — Expected: PASS.

- [ ] **Step 5: Commit** `feat: files module (guarded, backups, delete switch)`

---

### Task 4: Utils module

**Files:**
- Create: `llmtools/utils.py`, `tests/test_utils.py`

**Interfaces:**
- Produces tools: `get_local_time`, `calculate`, `format_json`, `generate_uuid`, `hash_text`, `base64_encode`, `base64_decode`.

- [ ] **Step 1: Write failing test `tests/test_utils.py`**

```python
from llmtools import utils

def test_calculate():
    assert "7" in utils.calculate("3 + 4")

def test_calculate_rejects_names():
    assert "error" in utils.calculate("__import__('os')").lower()

def test_base64_roundtrip():
    enc = utils.base64_encode("hola")
    assert "hola" == utils.base64_decode(enc.strip())

def test_hash_text():
    assert len(utils.hash_text("x").split(":")[-1].strip()) == 64
```

- [ ] **Step 2: Run** `pytest tests/test_utils.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `llmtools/utils.py`**

```python
import ast
import base64 as _b64
import hashlib
import json
import operator
import uuid
from datetime import datetime
from llmtools.core import tool

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
        ast.USub: operator.neg}

def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")

@tool
def calculate(expression: str) -> str:
    """Evaluate a safe arithmetic expression (+ - * / ** %).

    Args:
        expression: Math expression, e.g. '3 * (4 + 1)'.
    """
    try:
        return str(_eval(ast.parse(expression, mode="eval").body))
    except Exception as e:
        return f"Error: {e}"

@tool
def get_local_time() -> str:
    """Get the current local date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool
def format_json(text: str) -> str:
    """Pretty-print a JSON string.

    Args:
        text: Raw JSON text.
    """
    return json.dumps(json.loads(text), indent=2, ensure_ascii=False)

@tool
def generate_uuid() -> str:
    """Generate a random UUID4."""
    return str(uuid.uuid4())

@tool
def hash_text(text: str) -> str:
    """SHA-256 hash of a string.

    Args:
        text: Input text.
    """
    return "sha256: " + hashlib.sha256(text.encode()).hexdigest()

@tool
def base64_encode(text: str) -> str:
    """Base64-encode a string.

    Args:
        text: Input text.
    """
    return _b64.b64encode(text.encode()).decode()

@tool
def base64_decode(data: str) -> str:
    """Base64-decode a string.

    Args:
        data: Base64 text.
    """
    return _b64.b64decode(data.encode()).decode()
```

- [ ] **Step 4: Run** `pytest tests/test_utils.py -v` — Expected: PASS.

- [ ] **Step 5: Commit** `feat: utils module`

---

### Task 5: Obsidian + Markdown modules

**Files:**
- Create: `llmtools/obsidian.py`, `llmtools/markdown.py`, `tests/test_obsidian.py`, `tests/test_markdown.py`

**Interfaces:**
- Consumes: `core.tool`, `resolve_safe_path`, `backup_file`, `config.DEFAULT_VAULT`.
- Produces (obsidian): `create_note`, `read_note`, `append_to_note`, `list_notes`, `search_vault`, `add_tags_to_note`.
- Produces (markdown): `create_markdown_doc`, `markdown_table`, `add_table_of_contents`.
- Note helper: `_note_path(name, vault)` resolves `<vault>/<name>.md`.

- [ ] **Step 1: Write failing tests**

`tests/test_obsidian.py`:
```python
from llmtools import obsidian, config

def test_create_and_read_note(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ALLOWED_ROOTS", [str(tmp_path)])
    monkeypatch.setattr(config, "DEFAULT_VAULT", str(tmp_path))
    obsidian.create_note("Idea", "Body text", tags="a,b")
    out = obsidian.read_note("Idea")
    assert "Body text" in out and "tags:" in out

def test_append_backs_up(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ALLOWED_ROOTS", [str(tmp_path)])
    monkeypatch.setattr(config, "DEFAULT_VAULT", str(tmp_path))
    obsidian.create_note("N", "v1")
    obsidian.append_to_note("N", "more")
    assert (tmp_path / "N._backup.md").exists()
    assert "more" in obsidian.read_note("N")
```

`tests/test_markdown.py`:
```python
from llmtools import markdown

def test_markdown_table():
    t = markdown.markdown_table("a,b", "1,2;3,4")
    assert "| a | b |" in t and "| 1 | 2 |" in t
```

- [ ] **Step 2: Run** `pytest tests/test_obsidian.py tests/test_markdown.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `llmtools/obsidian.py`**

```python
import os
import glob
from datetime import datetime
from llmtools import config
from llmtools.core import tool, resolve_safe_path, backup_file

def _vault():
    return config.DEFAULT_VAULT

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
    p = _note_path(title)
    backup_file(p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    fm = ["---", f"title: {title}", f"created: {datetime.now():%Y-%m-%d}",
          "tags: [" + ", ".join(tag_list) + "]", "---", ""]
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(fm) + content + "\n")
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
```

- [ ] **Step 4: Implement `llmtools/markdown.py`**

```python
import os
from llmtools.core import tool, resolve_safe_path, backup_file

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
    h = [c.strip() for c in headers.split(",")]
    out = ["| " + " | ".join(h) + " |", "| " + " | ".join("---" for _ in h) + " |"]
    for r in rows.split(";"):
        if r.strip():
            out.append("| " + " | ".join(c.strip() for c in r.split(",")) + " |")
    return "\n".join(out)

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
```

- [ ] **Step 5: Run** `pytest tests/test_obsidian.py tests/test_markdown.py -v` — Expected: PASS.

- [ ] **Step 6: Commit** `feat: obsidian + markdown modules`

---

### Task 6: Documents module (PDF/Word/text)

**Files:**
- Create: `llmtools/documents.py`, `tests/test_documents.py`

**Interfaces:**
- Consumes: `core.tool`, `resolve_safe_path`, `pypdf`, `docx`.
- Produces tools: `read_pdf`, `read_docx`, `read_text_file`, `document_metadata`.

- [ ] **Step 1: Write test `tests/test_documents.py`** (generates a docx fixture)

```python
import pytest
from llmtools import documents, config

def test_read_docx(tmp_path, monkeypatch):
    docx = pytest.importorskip("docx")
    monkeypatch.setattr(config, "ALLOWED_ROOTS", [str(tmp_path)])
    d = docx.Document()
    d.add_paragraph("Hello world")
    p = str(tmp_path / "f.docx")
    d.save(p)
    assert "Hello world" in documents.read_docx(p)

def test_read_text_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ALLOWED_ROOTS", [str(tmp_path)])
    p = tmp_path / "f.txt"
    p.write_text("plain text")
    assert "plain text" in documents.read_text_file(str(p))
```

- [ ] **Step 2: Run** `pytest tests/test_documents.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `llmtools/documents.py`**

```python
import os
from llmtools.core import tool, resolve_safe_path

@tool
def read_pdf(path: str, max_pages: int = 0) -> str:
    """Extract text from a PDF.

    Args:
        path: PDF file path.
        max_pages: Max pages to read (0 = all).
    """
    from pypdf import PdfReader
    ap = resolve_safe_path(path)
    reader = PdfReader(ap)
    pages = reader.pages if max_pages == 0 else reader.pages[:max_pages]
    return "\n\n".join((pg.extract_text() or "") for pg in pages).strip() or "(no extractable text)"

@tool
def read_docx(path: str) -> str:
    """Extract text from a Word .docx file.

    Args:
        path: .docx file path.
    """
    import docx
    ap = resolve_safe_path(path)
    doc = docx.Document(ap)
    return "\n".join(p.text for p in doc.paragraphs)

@tool
def read_text_file(path: str) -> str:
    """Read a plain-text file.

    Args:
        path: Text file path.
    """
    ap = resolve_safe_path(path)
    with open(ap, encoding="utf-8", errors="replace") as f:
        return f.read()

@tool
def document_metadata(path: str) -> str:
    """Return size and basic metadata for a document.

    Args:
        path: File path.
    """
    ap = resolve_safe_path(path)
    st = os.stat(ap)
    return f"path: {ap}\nsize: {st.st_size} bytes\next: {os.path.splitext(ap)[1]}"
```

- [ ] **Step 4: Run** `pytest tests/test_documents.py -v` — Expected: PASS (docx test skips if lib missing).

- [ ] **Step 5: Commit** `feat: documents module (pdf/docx/text)`

---

### Task 7: Web module (search + fetch)

**Files:**
- Create: `llmtools/web.py`, `tests/test_web.py`

**Interfaces:**
- Consumes: `core.tool`, `ddgs`, `requests`.
- Produces tools: `web_search`, `fetch_url`.

- [ ] **Step 1: Write test `tests/test_web.py`** (unit, no network — monkeypatched)

```python
from llmtools import web

def test_web_search_formats(monkeypatch):
    class FakeDDGS:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def text(self, q, max_results):
            return [{"title": "T", "href": "http://x", "body": "B"}]
    monkeypatch.setattr(web, "DDGS", FakeDDGS)
    out = web.web_search("python")
    assert "T" in out and "http://x" in out

def test_fetch_url_strips_html(monkeypatch):
    class R:
        text = "<html><body><p>Hi</p><script>x</script></body></html>"
        def raise_for_status(self): pass
    monkeypatch.setattr(web.requests, "get", lambda *a, **k: R())
    out = web.fetch_url("http://x")
    assert "Hi" in out and "script" not in out
```

- [ ] **Step 2: Run** `pytest tests/test_web.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `llmtools/web.py`**

```python
import re
import requests
from llmtools.core import tool

try:
    from ddgs import DDGS
except ImportError:  # older package name
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web via DuckDuckGo.

    Args:
        query: Search query.
        max_results: Number of results.
    """
    if DDGS is None:
        return "Error: install 'ddgs' (pip install ddgs)."
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
    if not results:
        return "No results."
    return "\n\n".join(
        f"{i}. {r.get('title','')}\n   {r.get('href','')}\n   {r.get('body','')}"
        for i, r in enumerate(results, 1))

def _html_to_text(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    return re.sub(r"\s+\n", "\n", re.sub(r"[ \t]+", " ", text)).strip()

@tool
def fetch_url(url: str, max_chars: int = 4000) -> str:
    """Download a web page and return cleaned text.

    Args:
        url: The URL to fetch.
        max_chars: Truncate output to this many characters.
    """
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Gemma4Tools/1.0"})
    resp.raise_for_status()
    text = _html_to_text(resp.text)
    return text[:max_chars] + ("…" if len(text) > max_chars else "")
```

- [ ] **Step 4: Run** `pytest tests/test_web.py -v` — Expected: PASS.

- [ ] **Step 5: Commit** `feat: web module (ddgs search + url fetch)`

---

### Task 8: Graphs module

**Files:**
- Create: `llmtools/graphs.py`, `tests/test_graphs.py`

**Interfaces:**
- Consumes: `core.tool`, `resolve_safe_path`, optional system `dot` binary.
- Produces tools: `mermaid_diagram`, `graphviz_render`.

- [ ] **Step 1: Write test `tests/test_graphs.py`**

```python
from llmtools import graphs

def test_mermaid_diagram():
    out = graphs.mermaid_diagram("flowchart", "A-->B;B-->C")
    assert out.startswith("```mermaid") and "A-->B" in out

def test_graphviz_without_binary(monkeypatch, tmp_path):
    from llmtools import config
    monkeypatch.setattr(config, "ALLOWED_ROOTS", [str(tmp_path)])
    monkeypatch.setattr(graphs.shutil, "which", lambda _: None)
    out = graphs.graphviz_render("digraph{a->b}", str(tmp_path / "g.png"))
    assert "dot" in out.lower() and "a->b" in out
```

- [ ] **Step 2: Run** `pytest tests/test_graphs.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `llmtools/graphs.py`**

```python
import shutil
import subprocess
from llmtools.core import tool, resolve_safe_path

@tool
def mermaid_diagram(kind: str, definition: str) -> str:
    """Build a Mermaid diagram code block.

    Args:
        kind: Diagram type, e.g. 'flowchart', 'graph TD', 'sequenceDiagram'.
        definition: Diagram body, statements separated by ';'.
    """
    lines = [s.strip() for s in definition.split(";") if s.strip()]
    body = "\n    ".join(lines)
    return f"```mermaid\n{kind}\n    {body}\n```"

@tool
def graphviz_render(dot_source: str, output_path: str) -> str:
    """Render Graphviz DOT to an image; returns DOT source if 'dot' is unavailable.

    Args:
        dot_source: DOT graph source.
        output_path: Output image path (.png/.svg).
    """
    out = resolve_safe_path(output_path)
    if shutil.which("dot") is None:
        return f"Graphviz 'dot' binary not found. DOT source:\n{dot_source}"
    fmt = out.rsplit(".", 1)[-1]
    subprocess.run(["dot", f"-T{fmt}", "-o", out],
                   input=dot_source.encode(), check=True)
    return f"Rendered graph to {out}"
```

- [ ] **Step 4: Run** `pytest tests/test_graphs.py -v` — Expected: PASS.

- [ ] **Step 5: Commit** `feat: graphs module (mermaid + graphviz)`

---

### Task 9: Git module

**Files:**
- Create: `llmtools/git.py`, `tests/test_git.py`

**Interfaces:**
- Consumes: `core.tool`, `resolve_safe_path`, system `git`.
- Produces tools: `git_status`, `git_diff`, `git_log`, `git_add`, `git_commit`, `git_branch`, `git_init`.
- Helper: `_run_git(args, repo)` → captured stdout/stderr string.

- [ ] **Step 1: Write test `tests/test_git.py`**

```python
import subprocess
from llmtools import git, config

def test_git_init_status_commit(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ALLOWED_ROOTS", [str(tmp_path)])
    git.git_init(str(tmp_path))
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "a@b.c"])
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"])
    (tmp_path / "f.txt").write_text("hi")
    git.git_add(".", str(tmp_path))
    out = git.git_commit("init", str(tmp_path))
    assert "init" in out or "master" in out or "main" in out
    assert "nothing to commit" in git.git_status(str(tmp_path)).lower()
```

- [ ] **Step 2: Run** `pytest tests/test_git.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `llmtools/git.py`**

```python
import shutil
import subprocess
from llmtools.core import tool, resolve_safe_path

def _run_git(args, repo):
    if shutil.which("git") is None:
        return "Error: 'git' binary not found."
    rp = resolve_safe_path(repo)
    r = subprocess.run(["git", "-C", rp, *args], capture_output=True, text=True)
    return (r.stdout + r.stderr).strip() or "(no output)"

@tool
def git_status(repo: str = ".") -> str:
    """Show git working-tree status.

    Args:
        repo: Repository path.
    """
    return _run_git(["status"], repo)

@tool
def git_diff(repo: str = ".") -> str:
    """Show unstaged git diff.

    Args:
        repo: Repository path.
    """
    return _run_git(["diff"], repo)

@tool
def git_log(repo: str = ".", count: int = 10) -> str:
    """Show recent commit log (oneline).

    Args:
        repo: Repository path.
        count: Number of commits.
    """
    return _run_git(["log", f"-{count}", "--oneline"], repo)

@tool
def git_add(pathspec: str = ".", repo: str = ".") -> str:
    """Stage files.

    Args:
        pathspec: Files/globs to stage.
        repo: Repository path.
    """
    return _run_git(["add", pathspec], repo) or "Staged."

@tool
def git_commit(message: str, repo: str = ".") -> str:
    """Create a commit (never pushes).

    Args:
        message: Commit message.
        repo: Repository path.
    """
    return _run_git(["commit", "-m", message], repo)

@tool
def git_branch(repo: str = ".") -> str:
    """List branches.

    Args:
        repo: Repository path.
    """
    return _run_git(["branch", "-a"], repo)

@tool
def git_init(repo: str = ".") -> str:
    """Initialize a git repository.

    Args:
        repo: Directory to init.
    """
    return _run_git(["init"], repo)
```

- [ ] **Step 4: Run** `pytest tests/test_git.py -v` — Expected: PASS.

- [ ] **Step 5: Commit** `feat: git module`

---

### Task 10: Daily module (migrate existing tools to decorator)

**Files:**
- Create: `llmtools/daily.py`, `tests/test_daily.py`
- Reference: existing `day_day_tools.py` (source logic to migrate).

**Interfaces:**
- Consumes: `core.tool`, `config.NEWS_API_KEY`, `urllib`.
- Produces tools: `get_current_weather`, `get_current_news`, `get_current_time`, `convert_currency`.

- [ ] **Step 1: Write test `tests/test_daily.py`** (monkeypatched, no network)

```python
import json
from llmtools import daily

def test_weather_formats(monkeypatch):
    seq = [
        {"results": [{"latitude": 1, "longitude": 2, "country": "X"}]},
        {"current": {"temperature_2m": 20, "wind_speed_10m": 5},
         "current_units": {"temperature_2m": "°C", "wind_speed_10m": "km/h"}},
    ]
    monkeypatch.setattr(daily, "_get_json", lambda url: seq.pop(0))
    out = daily.get_current_weather("Madrid")
    assert "20" in out and "Madrid" in out
```

- [ ] **Step 2: Run** `pytest tests/test_daily.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `llmtools/daily.py`** (migrate logic, add `_get_json` helper for testability)

```python
import json
import urllib.parse
import urllib.request
from llmtools import config
from llmtools.core import tool

def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Gemma4Tools/1.0",
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))

@tool
def get_current_weather(city: str, unit: str = "celsius") -> str:
    """Get current weather for a city.

    Args:
        city: City name.
        unit: 'celsius' or 'fahrenheit'.
    """
    geo = _get_json(f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1")
    if not geo.get("results"):
        return f"Could not find city: {city}."
    loc = geo["results"][0]
    tu = "fahrenheit" if unit.lower() == "fahrenheit" else "celsius"
    w = _get_json(f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&current=temperature_2m,wind_speed_10m&temperature_unit={tu}")
    c = w["current"]
    return (f"Weather in {city.title()} ({loc.get('country','')}): "
            f"{c['temperature_2m']}{w['current_units']['temperature_2m']}, "
            f"wind {c['wind_speed_10m']}{w['current_units']['wind_speed_10m']}.")

@tool
def get_current_news(topic: str = "") -> str:
    """Fetch latest news headlines, optionally by topic.

    Args:
        topic: Optional search topic.
    """
    key = config.NEWS_API_KEY
    if key in ("YOUR_NEWS_API_KEY", "YOUR_API_KEY", ""):
        return "Error: set NEWS_API_KEY env var or config value."
    if topic.strip():
        url = f"https://newsapi.org/v2/everything?q={urllib.parse.quote(topic)}&sortBy=publishedAt&pageSize=5&apiKey={key}"
    else:
        url = f"https://newsapi.org/v2/top-headlines?language=en&pageSize=5&apiKey={key}"
    data = _get_json(url)
    if data.get("status") != "ok":
        return f"Error: {data.get('message','unknown')}"
    arts = data.get("articles", [])
    if not arts:
        return "No articles found."
    return "\n".join(f"{i}. {a.get('title','')} ({a.get('source',{}).get('name','')})"
                     for i, a in enumerate(arts, 1))

@tool
def get_current_time(timezone: str) -> str:
    """Get current time for a timezone.

    Args:
        timezone: e.g. 'Europe/Madrid'.
    """
    d = _get_json(f"https://timeapi.io/api/Time/current/zone?timeZone={urllib.parse.quote(timezone)}")
    if d.get("time") and d.get("date"):
        return f"Time in {timezone}: {d['time']} on {d['date']}."
    return f"Could not fetch time for {timezone}."

@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount between currencies.

    Args:
        amount: Amount to convert.
        from_currency: 3-letter source code.
        to_currency: 3-letter target code.
    """
    fc, tc = from_currency.upper(), to_currency.upper()
    data = _get_json(f"https://api.exchangerate-api.com/v4/latest/{fc}")
    rates = data.get("rates", {})
    if tc not in rates:
        return f"Error: unsupported currency '{tc}'."
    return f"{amount} {fc} = {float(amount)*rates[tc]:.2f} {tc} (rate {rates[tc]})."
```

- [ ] **Step 4: Run** `pytest tests/test_daily.py -v` — Expected: PASS.

- [ ] **Step 5: Commit** `feat: daily module (migrated to decorator)`

---

### Task 11: Package aggregation (`__init__.py`) + wire all modules

**Files:**
- Modify: `llmtools/__init__.py`
- Create: `tests/test_registry.py`

**Interfaces:**
- Produces: importing `llmtools` imports every tool module (populating REGISTRY) and re-exports `REGISTRY`, `get_schemas`, `call_tool`.

- [ ] **Step 1: Write test `tests/test_registry.py`**

```python
import llmtools

def test_all_tools_registered():
    names = set(llmtools.REGISTRY)
    expected = {"create_note", "read_pdf", "web_search", "git_status",
                "list_directory", "calculate", "mermaid_diagram",
                "get_current_weather", "markdown_table"}
    assert expected <= names

def test_schemas_match_registry():
    schema_names = {s["function"]["name"] for s in llmtools.get_schemas()}
    assert schema_names == set(llmtools.REGISTRY)
```

- [ ] **Step 2: Run** `pytest tests/test_registry.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `llmtools/__init__.py`**

```python
from llmtools.core import REGISTRY, get_schemas, call_tool  # noqa: F401
from llmtools import (  # noqa: F401  (import populates REGISTRY)
    obsidian, markdown, documents, web, graphs, files, git, utils, daily,
)
```

- [ ] **Step 4: Run** `pytest tests/test_registry.py -v` — Expected: PASS.

- [ ] **Step 5: Commit** `feat: aggregate all tool modules in package init`

---

### Task 12: agent.py runner

**Files:**
- Create: `agent.py`
- Reference: existing `tools.py` (ASCII-tree UX to preserve).

**Interfaces:**
- Consumes: `llmtools.get_schemas`, `llmtools.call_tool`, `config.MODEL`, `config.OLLAMA_URL`.

- [ ] **Step 1: Implement `agent.py`**

```python
import json
import sys
import urllib.request
from llmtools import get_schemas, call_tool, REGISTRY
from llmtools import config

def call_ollama(payload):
    req = urllib.request.Request(config.OLLAMA_URL,
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())

def main():
    if len(sys.argv) < 2:
        print("Usage: python agent.py \"your prompt\"")
        sys.exit(1)
    query = " ".join(sys.argv[1:])
    print(f"\n[SYSTEM] {len(REGISTRY)} tools loaded.\n[PROMPT] {query}\n")

    messages = [{"role": "user", "content": query}]
    payload = {"model": config.MODEL, "messages": messages,
               "tools": get_schemas(), "stream": False}
    try:
        resp = call_ollama(payload)
    except Exception as e:
        print(f"[ERROR] Ollama call failed: {e}\nIs Ollama running with {config.MODEL} pulled?")
        return

    msg = resp.get("message", {})
    if msg.get("tool_calls"):
        messages.append(msg)
        print("[TOOL EXECUTION]")
        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            args = tc["function"]["arguments"]
            print(f"  └── {name}({args})")
            result = call_tool(name, args)
            print(f"      → {str(result)[:200]}")
            messages.append({"role": "tool", "name": name, "content": str(result)})
        payload["messages"] = messages
        resp = call_ollama(payload)
        print("\n[RESPONSE]\n" + resp.get("message", {}).get("content", ""))
    else:
        print("[RESPONSE]\n" + msg.get("content", ""))

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test** `python agent.py "what time is it in Madrid"` — Expected: tool call + answer (needs Ollama running). If Ollama down, prints clear error.

- [ ] **Step 3: Full test run** `pytest -q` — Expected: all PASS.

- [ ] **Step 4: Commit** `feat: agent.py runner wired to registry`

---

### Task 13: README + cleanup

**Files:**
- Create: `README.md`
- Delete/keep: leave old `tools.py`/`day_day_tools.py` in place (superseded; note in README).

- [ ] **Step 1: Write `README.md`** documenting install (`pip install -r requirements.txt`), setting `DEFAULT_VAULT`/`OBSIDIAN_VAULT`, `ALLOW_DELETE_FILES`, running `python agent.py "..."`, and the tool inventory.

- [ ] **Step 2: Commit** `docs: README with setup + tool inventory`

---

## Self-Review

**Spec coverage:** every module in the spec (obsidian, markdown, documents, web, graphs, files, git, utils, daily, core, config, agent) maps to a task. Backups, delete guard, path confinement, decorator registry, DEFAULT_VAULT placeholder, gemma4:e4b model, string-returns — all covered.

**Placeholder scan:** no TBD/TODO; every code step has full code. `DEFAULT_VAULT`/`YOUR_NEWS_API_KEY` are intentional user-set placeholders, not plan gaps.

**Type consistency:** `resolve_safe_path`, `backup_file`, `tool`, `get_schemas`, `call_tool`, `REGISTRY`, `_get_json`, `_run_git`, `_note_path` names used consistently across tasks.
