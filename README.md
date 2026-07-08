# LLM Tools — Gemma4:e4b local toolset

Modular Python tool set exposed to a local Ollama model (`gemma4:e4b`) via
function-calling. Each tool is a plain function decorated with `@tool`; the
decorator introspects type hints + docstring to build the Ollama JSON schema
and auto-registers it. No manual schema lists.

## Install

```bash
uv pip install -p .venv/bin/python3 -r requirements.txt   # or: pip install -r requirements.txt
```

Audio tools (STT + TTS) and knowledge tools (RAG/OCR/YouTube/translate) are heavy and
optional — install separately:

```bash
uv pip install -p .venv/bin/python3 -r requirements-audio.txt   # STT + TTS
uv pip install -p .venv/bin/python3 -r requirements-extra.txt   # RAG, OCR, YouTube, translate
```

Email needs `EMAIL_ADDRESS` + `EMAIL_PASSWORD` (use an app-password) and, for non-Gmail,
`IMAP_HOST`/`SMTP_HOST`/`SMTP_PORT`. OCR needs the system `tesseract` binary.

For TTS, download a Piper voice (e.g. Spanish `es_ES-davefx-medium.onnx` + its `.json`)
into `~/piper_voices/` and set `PIPER_VOICE` (or the `voice` arg). STT model size is
`WHISPER_MODEL` (tiny/base/small/medium/large-v3).

## Configure

Edit `llmtools/config.py` (or use env vars):

| Setting | Meaning |
|---------|---------|
| `DEFAULT_VAULT` / `OBSIDIAN_VAULT` env | Obsidian vault path (placeholder — set it). |
| `MODEL` | Ollama model, default `gemma4:e4b`. |
| `NEWS_API_KEY` / env | NewsAPI key for `get_current_news`. |
| `ALLOW_DELETE_FILES` | `False` by default; set `True` to enable `delete_file`. |
| `ALLOWED_ROOTS` | Dirs file/git tools may touch (cwd + vault). |

## Run

```bash
python agent.py "crea una nota en obsidian sobre X"
```

Requires Ollama running with the model pulled (`ollama run gemma4:e4b`).

## Safety

- Every tool returns a string, never raises.
- File/git ops are confined to `ALLOWED_ROOTS`.
- Before mutating an existing file, a backup `name._backup.ext` is written.
- Deletion is off unless `ALLOW_DELETE_FILES = True`.
- `git_commit` never pushes.

## Tools (113)

- **obsidian**: create_note, read_note, append_to_note, list_notes, search_vault, add_tags_to_note
- **markdown**: create_markdown_doc, markdown_table, add_table_of_contents
- **documents**: read_pdf, read_docx, read_text_file, document_metadata
- **web**: web_search (DuckDuckGo), fetch_url
- **graphs**: mermaid_diagram, graphviz_render
- **files**: list_directory, find_files, read_file, write_file, move_file, copy_file, delete_file
- **git** (43): setup (init, clone), inspect (status, diff, log, show, blame, reflog),
  stage/commit/undo (add, commit, reset, restore, rm, clean, revert, stash),
  branch (branch, create_branch, checkout, delete_branch, rename_branch, merge, rebase, cherry_pick),
  tags (tag_list, tag_create, tag_delete, push_tags), remotes/network (remote_list, remote_add, fetch, pull, push),
  config (config_get, config_set), hooks (list_hooks, show_hook, install_hook, remove_hook),
  GitHub releases via `gh` (gh_release_create/list/view), and `git_run` (raw passthrough for any git command)
- **utils**: get_local_time, calculate, format_json, generate_uuid, hash_text, base64_encode, base64_decode
- **daily**: get_current_weather, get_current_news, get_current_time, convert_currency
- **audio** (STT faster-whisper / TTS Piper): transcribe_audio, record_and_transcribe, speak_text, list_tts_voices, play_audio
- **mail**: send_email (SMTP), read_emails (IMAP)
- **calendar**: add_event, list_events, add_reminder, list_reminders
- **data**: read_csv, write_csv, read_excel, write_excel, clipboard_get, clipboard_set, http_request, download_file, make_zip, extract_archive
- **knowledge**: index_documents, semantic_search (RAG), ocr_image, youtube_transcript, translate_text
- **system**: system_info, list_processes, desktop_notify
- **media**: resize_image, convert_image, screenshot, qr_generate
- **utils** (added): generate_password, convert_units

## Add a tool

Write a function in the relevant `llmtools/*.py` module, decorate with `@tool`,
give it typed params and a docstring with an `Args:` block. It auto-registers.

## Structure

```
agent.py            CLI runner (ollama loop)
llmtools/
  core.py           @tool decorator, registry, path/backup safety
  config.py         settings + safety switches
  obsidian.py markdown.py documents.py web.py
  graphs.py files.py git.py utils.py daily.py
tests/              pytest suite (45 tests)
```
