# llmtools

A little toolbox I put together so a local model running on Ollama (I use Gemma, but
anything with tool-calling works) can actually *do* things instead of just talking about
them — take notes in my Obsidian vault, read PDFs, search the web, run git, transcribe a
voice memo, that sort of thing.

The idea is simple: you write a normal Python function, slap a `@tool` decorator on it,
and it shows up for the model automatically. No schema files to keep in sync.

```python
from llmtools.core import tool

@tool
def greet(name: str) -> str:
    """Say hello to someone.

    Args:
        name: Who to greet.
    """
    return f"Hola, {name}!"
```

That's the whole contract. The decorator reads your type hints and docstring, builds the
JSON schema from them (via Pydantic) and validates/coerces whatever arguments the model
sends back before running the function. Tools with side effects are declared with
`@tool(confirm=True)` (or a predicate over the arguments) and the agent asks you `y/N`
before running them.

## Running it

```bash
uv sync --extra tools                   # core + everyday tools (add audio/extra/gpu as needed)
uv run playwright install chromium      # once, for the browser and college tools
uv run python agent.py                  # interactive agent (REPL)
uv run python agent.py "apunta en obsidian que tengo dentista el jueves"   # one-shot
```

You need an OpenAI-compatible server with a tool-calling model: Ollama
(`ollama run gemma4:e4b`, served at `http://localhost:11434/v1`) or llama.cpp's
`llama-server`. The agent sends your prompt, lets the model call tools for several rounds,
asks before anything with side effects, and prints the answer.

**Heads up on `ollama run`:** the bare Ollama REPL won't execute these tools for you —
the model can *ask* to call a tool, but something has to run it and hand back the result.
That "something" is `agent.py` (or the CLI below). Ollama by itself doesn't run your Python.

The tools also work standalone, outside the agent loop:

```bash
uv run python -m llmtools list                                  # list every tool by group
uv run python -m llmtools call get_library_docs '{"query":"polars group_by"}'
uv run python -m llmtools chat "resúmeme este PDF: informe.pdf"  # agent (REPL without a prompt)
uv run python -m llmtools google-auth                           # one-off Google Drive login
```

### Tool groups

A small model gets lost with 150+ tool schemas, so the agent starts with a few groups
(`ENABLED_TOOLSETS`, default `shell,files,web,browser,memory,utils`) and can switch on
others itself with `list_toolsets` / `enable_toolset`. Set `ENABLED_TOOLSETS=all` to offer
everything from the start.

## What's in the box

Around 160 tools, grouped by what they do:

- **Shell** — `run_bash` (read-only commands like `ls`, `cat`, `rg`, `find`, `git status`
  run directly; anything that writes asks first) and `run_python`. The agent is told to
  prefer bash for filesystem work.
- **Files** — read/write/move/copy, exact-text `edit_file`, `grep_files` (ripgrep),
  `file_tree`, `make_directory`, `disk_usage`
- **Browser** — a persistent Playwright session: open, click, type, read, back, screenshot
- **Memory & planning** — long-term `remember` / `recall` / `forget`, and a task list
  (`task_add`, `task_list`, `task_done`) for multi-step work
- **Pharmacy (Spain)** — CIMA (search, drug record, supply problems, new/withdrawn
  medicines, safety notes), AEMPS alerts, international equivalents via ATC + RxNorm +
  openFDA, pharmacists' college circulars (login via Playwright)
- **Google Drive** — list and upload (desktop OAuth)
- **Notes & docs** — Obsidian notes (python-frontmatter), Markdown (tabulate), reading PDF (PyMuPDF) / Word / text
- **Web** — DuckDuckGo search, `web_research` (search + read top pages in one call), fetch a
  page as clean markdown (trafilatura), generic HTTP requests
- **Git** — pretty much the whole CLI: commits, branches, tags, stash, rebase, hooks,
  GitHub releases, plus a `git_run` escape hatch for anything I forgot to wrap
- **Files** — read/write/move/copy, zip, download
- **Data** — CSV, Excel, JSON, Parquet via Polars (read, write, convert, stats), clipboard
- **Audio** — speech-to-text (faster-whisper) and text-to-speech (Piper)
- **Knowledge** — semantic search over your vault, OCR, YouTube transcripts, offline translate
- **Docs** — fetch up-to-date library docs (Context7), CLI program help (tldr/man), DevDocs lookup
- **Math** — evaluate & solve expressions symbolically (SymPy)
- **Everyday** — weather, news (Google News), time (offline via zoneinfo, defaults to your
  OS timezone), currency, calendar, reminders, system info, processes, QR codes, passwords,
  unit conversion

Full list lives in the code — each module under `llmtools/` is one category.

## A couple of things to know

- **Nothing gets deleted by accident.** Before editing a file it saves a
  `name._backup.ext` copy, file and shell tools stay inside allowed folders
  (`FILES_ROOT`, the Obsidian vault and `EXTRA_ROOTS`), and `delete_file` is off unless you
  set `ALLOW_DELETE_FILES=true`.
- **Tool output is untrusted.** The agent wraps every result as data and is told never to
  follow instructions found inside web pages, files or emails.
- **Some tools need extra stuff.** Heavier dependencies are optional extras:

  ```bash
  uv sync --extra tools    # everyday tools (Polars, PDF, Office, calendar, mail, Drive...)
  uv sync --extra audio    # STT + TTS (faster-whisper, Piper)
  uv sync --extra extra    # RAG, OCR, YouTube, translate
  uv sync --extra gpu      # CUDA libs for faster-whisper
  ```

  If a dependency is missing the tool just tells you instead of blowing up.
- **Config lives in `.env`** at the project root (or the file in `LLMTOOLS_ENV_FILE`),
  read by `llmtools/config.py`. Main keys: `LLM_URL`, `LLM_MODEL`, `ENABLED_TOOLSETS`,
  `FILES_ROOT` (default `~/llm_files`, where relative paths resolve), `EXTRA_ROOTS`
  (comma-separated), `OBSIDIAN_VAULT`, `DATA_DIR` (memory, browser profile, tokens),
  `EMAIL_ADDRESS` / `EMAIL_PASSWORD`, `GOOGLE_CLIENT_SECRET_FILE`, `COLLEGE_*`,
  `WHISPER_*`, `PIPER_*`. See `Settings` in `config.py` for the full list and defaults.

## Adding your own

Drop a function in the matching module, decorate it with `@tool`, give it typed arguments
and a docstring with an `Args:` block. It registers itself on import. Done.

## Tests

```bash
uv run pytest
```
