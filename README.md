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

That's the whole contract. The decorator reads your type hints and docstring and builds
the Ollama JSON schema for you.

## Running it

```bash
uv pip install -r requirements.txt      # or plain pip
python agent.py "apunta en obsidian que tengo dentista el jueves"
```

You need Ollama running with a model pulled (`ollama run gemma4:e4b`). `agent.py` sends
your prompt, lets the model call whatever tools it needs, and prints the answer.

**Heads up on `ollama run`:** the bare Ollama REPL won't execute these tools for you —
the model can *ask* to call a tool, but something has to run it and hand back the result.
That "something" is `agent.py` (or the CLI below). Ollama by itself doesn't run your Python.

The tools also work standalone, outside the agent loop:

```bash
python -m llmtools list                                  # list every tool
python -m llmtools call get_library_docs '{"query":"polars group_by"}'
python -m llmtools chat "resúmeme este PDF: informe.pdf"  # interactive agent loop
```

## What's in the box

Around 120 tools, grouped by what they do:

- **Notes & docs** — Obsidian notes (python-frontmatter), Markdown (tabulate), reading PDF (PyMuPDF) / Word / text
- **Web** — DuckDuckGo search, fetch a page as clean markdown (trafilatura), generic HTTP requests
- **Git** — pretty much the whole CLI: commits, branches, tags, stash, rebase, hooks,
  GitHub releases, plus a `git_run` escape hatch for anything I forgot to wrap
- **Files** — read/write/move/copy, zip, download
- **Data** — CSV, Excel, JSON, Parquet via Polars (read, write, convert, stats), clipboard
- **Audio** — speech-to-text (faster-whisper) and text-to-speech (Piper)
- **Knowledge** — semantic search over your vault, OCR, YouTube transcripts, offline translate
- **Docs** — fetch up-to-date library docs (Context7), CLI program help (tldr/man), DevDocs lookup
- **Math** — evaluate & solve expressions symbolically (SymPy)
- **Everyday** — weather, news, time (offline via zoneinfo, defaults to your OS timezone),
  currency, calendar, reminders, system info, QR codes, passwords, unit conversion

Full list lives in the code — each module under `llmtools/` is one category.

## A couple of things to know

- **Nothing gets deleted by accident.** Before editing a file it saves a
  `name._backup.ext` copy, file tools stay inside allowed folders, and `delete_file` is
  off unless you flip `ALLOW_DELETE_FILES` in `config.py`.
- **Some tools need extra stuff.** The audio and knowledge tools pull in heavier
  dependencies, so they live in separate files you install only if you want them:

  ```bash
  uv pip install -r requirements-audio.txt   # STT + TTS
  uv pip install -r requirements-extra.txt   # RAG, OCR, YouTube, translate
  ```

  If a dependency is missing the tool just tells you instead of blowing up.
- **Config is in `llmtools/config.py`** (or env vars): your Obsidian vault path, the model
  name, email login, API keys. Set the vault before using the note tools — it ships as a
  placeholder.

## Adding your own

Drop a function in the matching module, decorate it with `@tool`, give it typed arguments
and a docstring with an `Args:` block. It registers itself on import. Done.

## Tests

```bash
pytest
```
