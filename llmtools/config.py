"""Centralised configuration (pydantic-settings).

Everything is read from environment variables or the ``.env`` file at the project root
(or the one given by ``LLMTOOLS_ENV_FILE``). Secrets are ``SecretStr``: they never show up
in logs or ``repr`` and are read explicitly with ``.get_secret_value()``.

Usage:
    from llmtools.config import get_settings
    s = get_settings()
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# llmtools/config.py -> project root (independent of the cwd)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = Path(os.environ.get("LLMTOOLS_ENV_FILE", PROJECT_ROOT / ".env")).expanduser()


def _expand(p: Path) -> Path:
    return p.expanduser().resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # empty `KEY=` -> default value (safe placeholders)
        extra="ignore",
    )

    # --- LLM (any OpenAI-compatible server: Ollama /v1, llama.cpp llama-server, vLLM...) ---
    llm_url: str = "http://localhost:11434/v1"
    llm_api_key: SecretStr = SecretStr("not-needed")
    llm_model: str = "gemma4:e4b"
    max_tool_rounds: int = Field(default=10, ge=1)
    # Tool groups (= module name in llmtools) offered to the model at start. "all" = every group.
    # A small model gets confused by 150 tools; the agent can enable more with enable_toolset.
    enabled_toolsets: Annotated[frozenset[str], NoDecode] = frozenset(
        {"shell", "files", "web", "browser", "memory", "utils"}
    )

    # --- Paths ---
    data_dir: Path = Path("~/.local/share/llmtools")  # state, memory, browser profile, tokens
    files_root: Path = Path("~/llm_files")  # default working folder; relative paths resolve here
    obsidian_vault: Path | None = None
    # Additional folders the tools may touch, comma separated: EXTRA_ROOTS=~/Projects,~/Documents
    extra_roots: Annotated[tuple[Path, ...], NoDecode] = ()

    # --- Shell / code execution ---
    command_timeout: int = Field(default=120, ge=1)  # seconds
    max_output_chars: int = Field(default=20000, ge=500)  # tool output truncation

    # --- Browser (Playwright) ---
    browser_headless: bool = True

    # --- Pharmacists' college (Playwright) ---
    college_user: str | None = None
    college_pass: SecretStr | None = None
    college_login_url: str | None = None
    college_circulars_url: str | None = None
    college_user_selector: str = "#user"
    college_pass_selector: str = "#pass"
    college_submit_selector: str = "button[type=submit]"
    college_content_selector: str = "main"
    college_rss_url: str | None = None  # if the college has RSS, prefer it over scraping

    # --- AEMPS ---
    aemps_rss_url: str = "https://www.aemps.gob.es/feed/"

    # --- Email (IMAP/SMTP; on Gmail use an app password) ---
    email_address: str | None = None
    email_password: SecretStr | None = None
    imap_host: str = "imap.gmail.com"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587

    # --- Google Drive (desktop OAuth) ---
    google_client_secret_file: Path | None = None  # credentials.json from Google Cloud

    # --- Audio ---
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute: str = "int8"
    piper_bin: str = "piper"
    piper_voice: str = (
        ""  # path to a Piper .onnx model, e.g. ~/piper_voices/es_ES-davefx-medium.onnx
    )
    piper_voices_dir: Path = Path("~/piper_voices")
    # Speech speed: 1.0 normal, >1 faster, <1 slower.
    piper_speed: float = Field(1.0, gt=0.25, le=4.0)
    # Speaker for multi-speaker voices (e.g. es_ES-sharvard); ignored on single-speaker voices.
    piper_speaker: int | None = None

    # --- Knowledge / RAG ---
    rag_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Safety ---
    allow_delete_files: bool = False

    @field_validator("enabled_toolsets", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return {x.strip() for x in v.split(",") if x.strip()}
        return v

    @field_validator("extra_roots", mode="before")
    @classmethod
    def _split_paths(cls, v):
        if isinstance(v, str):
            return tuple(_expand(Path(x.strip())) for x in v.split(",") if x.strip())
        return tuple(_expand(Path(x)) for x in v)

    @field_validator(
        "data_dir",
        "files_root",
        "obsidian_vault",
        "piper_voices_dir",
        "google_client_secret_file",
    )
    @classmethod
    def _expand_paths(cls, v: Path | None) -> Path | None:
        return _expand(v) if v is not None else None

    # --- Derived paths ---
    @property
    def allowed_roots(self) -> list[Path]:
        """Roots that file/shell tools may touch."""
        roots = [self.files_root]
        if self.obsidian_vault:
            roots.append(self.obsidian_vault)
        roots.extend(self.extra_roots)
        return roots

    @property
    def browser_profile_dir(self) -> Path:
        return self.data_dir / "browser_profile"

    @property
    def college_profile_dir(self) -> Path:
        return self.data_dir / "college_profile"

    @property
    def google_token_file(self) -> Path:
        return self.data_dir / "google_token.json"

    @property
    def rag_index_dir(self) -> Path:
        return self.data_dir / "rag_index"

    @property
    def memory_file(self) -> Path:
        return self.data_dir / "memory.json"

    @property
    def tasks_file(self) -> Path:
        return self.data_dir / "tasks.json"

    @property
    def calendar_file(self) -> Path:
        return self.files_root / "calendar.ics"

    @property
    def reminders_file(self) -> Path:
        return self.files_root / "reminders.md"


@lru_cache
def get_settings() -> Settings:
    """Cached settings. Lazy: importing modules does not fail if .env is missing."""
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.files_root.mkdir(parents=True, exist_ok=True)
    return s
