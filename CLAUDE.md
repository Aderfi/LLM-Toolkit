# llmtools

Tools for a local LLM agent (Ollama / llama.cpp via the OpenAI-compatible API).
Tool modules are kept in sync with `~/Projects/Muamar_Bot/src/muamar_bot/tools`: Muamar wins
on conflicts, but here everything is English and imports are `from .config` (flat package).

## Commands

- `uv sync --extra tools` (add `audio`, `extra`, `gpu` as needed); `uv run playwright install chromium` once
- `uv run pytest` · `uv run ruff check .`
- `uv run python -m llmtools list|call|chat|google-auth` · `uv run python agent.py` (REPL)

## Structure

- `llmtools/config.py` — pydantic-settings `Settings` from `.env` (`LLMTOOLS_ENV_FILE`); `get_settings()` is cached
- `llmtools/core.py` — `@tool` registry, Pydantic arg validation, `confirm` (bool or predicate),
  `resolve_safe_path` (relative to `FILES_ROOT`, inside `allowed_roots`), `run_argv`, `truncate`
- `llmtools/llm.py` — `Agent` loop; `ACTIVE_GROUPS` seeded from `ENABLED_TOOLSETS` + `meta`
- One module = one tool group (group name = module name). New module -> add it to `llmtools/__init__.py`.

## Conventions

- Side-effect tools use `@tool(confirm=True)`; `run_bash` confirms unless `shell.is_read_only`.
- `run_bash` is the only `bash -c` in the codebase (explicit, user-approved exception).
- Filesystem tools wrap CLI utilities (rg/grep, tree/find, du, mkdir) through `run_argv`.
- Tests: `tests/conftest.py` isolates settings (FILES_ROOT = tmp_path, no real `.env`);
  override with the `configure(KEY="value")` fixture.
