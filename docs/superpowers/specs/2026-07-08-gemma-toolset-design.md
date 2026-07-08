# Gemma4:e4b Local Toolset — Design

**Date:** 2026-07-08
**Status:** Approved (pending spec review)

## Purpose

Modular Python tool set (skills) for a local Ollama model (`gemma4:e4b`) covering
everyday tasks: Obsidian notes, markdown docs, graphs, reading PDF/Word documents,
web search + fetch, file operations, and general utilities. Tools are exposed to the
model through Ollama's function-calling (JSON schema) interface.

Extends the existing pure-stdlib prototype (`tools.py` + `day_day_tools.py`) into a
modular package with an auto-registry driven by a `@tool` decorator.

## Decisions

| Topic | Decision |
|-------|----------|
| External deps | pip allowed: `pypdf`, `python-docx`, `ddgs`, `requests`. Pinned in `requirements.txt`. |
| Tool → schema wiring | `@tool` decorator introspects type hints + docstring → Ollama JSON schema; central `REGISTRY` auto-collects. |
| Obsidian vault | Placeholder constant `DEFAULT_VAULT` in `config.py` (user sets later). |
| Web search | `ddgs` (DuckDuckGo), no API key. |
| File edits | Before any write/edit to an EXISTING file, auto-create backup copy `name.ext` → `name._backup.ext` (overwrites prior backup). |
| Deletion | Constant `ALLOW_DELETE_FILES = False`. `delete_file` refuses unless flipped to `True`. |
| Error handling | Every tool returns a `str`, never raises — model always gets usable feedback. |
| Path safety | file/move/copy/delete confined to allowed roots (vault + cwd + explicit args). |

## Architecture

```
LLM_tools/
  agent.py            # CLI runner — ollama chat loop + ASCII-tree UX
  llmtools/
    __init__.py       # exports REGISTRY, get_schemas(), call_tool()
    core.py           # @tool decorator, type-hint→schema introspection, registry, safety helpers
    config.py         # DEFAULT_VAULT, MODEL, ALLOW_DELETE_FILES, ALLOWED_ROOTS, API keys/env
    obsidian.py       # notes: create/read/append/list/search, tags
    markdown.py       # md docs, tables, TOC
    documents.py      # read_pdf, read_docx, read_text, metadata
    web.py            # web_search (ddgs), fetch_url → clean markdown
    graphs.py         # mermaid + graphviz generation/render
    files.py          # list/find/read/write/move/copy/delete (guarded)
    git.py            # status/diff/log/add/commit/branch/init (guarded to repo roots)
    utils.py          # local time, calc, json, uuid, hash, base64
    daily.py          # weather, news, currency, time (migrated from day_day_tools.py)
  requirements.txt
  docs/superpowers/specs/2026-07-08-gemma-toolset-design.md
```

### core.py — the registry engine

- `@tool` decorator:
  - Reads the function's type hints (`str`, `int`, `float`, `bool`, `list`, optional/defaults)
    and docstring (summary + `Args:` lines) to build the Ollama
    `{"type":"function","function":{...}}` schema.
  - Registers `name → callable` in a module-level `REGISTRY` dict.
  - Wraps the call so any exception is caught and returned as an error string.
- Public helpers:
  - `get_schemas()` → list of all tool schemas for the Ollama payload.
  - `call_tool(name, args)` → dispatch + string result.
- Safety helpers:
  - `resolve_safe_path(path)` → absolute path; raises/returns error if outside `ALLOWED_ROOTS`.
  - `backup_file(path)` → copies existing file to `name._backup.ext` before modification.

### agent.py — runner

Refactor of current `tools.py::main`. Reads prompt from argv, builds payload with
`get_schemas()`, calls Ollama (`gemma4:e4b`, `stream: False`), executes any `tool_calls`
via `call_tool`, feeds results back, prints final answer. Keeps the existing ASCII-tree
execution display.

## Tool inventory (~30)

- **obsidian**: `create_note`, `read_note`, `append_to_note`, `list_notes`, `search_vault`, `add_tags_to_note`
- **markdown**: `create_markdown_doc`, `markdown_table`, `add_table_of_contents`
- **documents**: `read_pdf`, `read_docx`, `read_text_file`, `document_metadata`
- **web**: `web_search`, `fetch_url`
- **graphs**: `mermaid_diagram`, `graphviz_render`
- **files**: `list_directory`, `find_files`, `read_file`, `write_file`, `move_file`, `copy_file`, `delete_file`
- **git**: `git_status`, `git_diff`, `git_log`, `git_add`, `git_commit`, `git_branch`, `git_init`
- **utils**: `get_local_time`, `calculate`, `format_json`, `generate_uuid`, `hash_text`, `base64_encode`, `base64_decode`
- **daily**: `get_current_weather`, `get_current_news`, `get_current_time`, `convert_currency`

## Behaviors of note

- **Backups**: `write_file`, `move_file`, `append_to_note`, `add_tags_to_note`, and any op
  that mutates an existing file call `backup_file()` first. New-file creation skips backup.
- **Delete guard**: `delete_file` checks `ALLOW_DELETE_FILES`; if `False`, returns a refusal
  string without touching the filesystem.
- **Path confinement**: destructive/file ops call `resolve_safe_path`; paths outside
  `ALLOWED_ROOTS` (default: `DEFAULT_VAULT`, cwd) return an error string.
- **Graphviz**: `graphviz_render` degrades to returning DOT source + a clear message if the
  `graphviz` system binary is absent (rendering optional).
- **Git**: tools shell out to the `git` binary via `subprocess`, run inside a repo root under
  `ALLOWED_ROOTS`, capture stdout/stderr, return as string. `git_commit` never pushes; push is
  out of scope. Missing `git` binary or non-repo dir returns a clear error string.

## Testing

- Unit tests per module with a `tests/` dir: schema generation from a sample decorated
  function, backup creation, delete guard on/off, path confinement rejection, and each
  tool's happy path (web/doc tests use small local fixtures or are marked network).
- Manual smoke: `python agent.py "crea una nota en obsidian sobre X"`.

## Out of scope

- No MCP server wrapper (Ollama-native tool calling only).
- No GUI.
- No streaming token output (keeps runner simple; can add later).
