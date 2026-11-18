import os

# Never read the developer's real .env during tests (must run before llmtools is imported).
os.environ["LLMTOOLS_ENV_FILE"] = os.devnull

import pytest  # noqa: E402

from llmtools.config import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def settings(tmp_path, monkeypatch):
    """Isolated settings: FILES_ROOT = tmp_path, DATA_DIR inside it, nothing from the env."""
    for key in os.environ:
        if key.startswith(("OBSIDIAN_", "EXTRA_ROOTS", "ALLOW_DELETE", "PIPER_", "FILES_ROOT")):
            monkeypatch.delenv(key)
    monkeypatch.setenv("FILES_ROOT", str(tmp_path))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / ".data"))
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture
def configure(monkeypatch):
    """Override settings through env vars: ``configure(ALLOW_DELETE_FILES="true")``."""

    def _configure(**env: str):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()
        return get_settings()

    return _configure
