from llmtools.config import Settings


def test_defaults(settings, tmp_path):
    assert settings.allow_delete_files is False
    assert settings.llm_model == "gemma4:e4b"
    assert settings.llm_url == "http://localhost:11434/v1"
    assert settings.allowed_roots == [tmp_path.resolve()]
    assert settings.calendar_file == tmp_path / "calendar.ics"


def test_allowed_roots_include_vault_and_extra_roots(tmp_path, configure):
    (tmp_path / "v").mkdir()
    s = configure(OBSIDIAN_VAULT=str(tmp_path / "v"), EXTRA_ROOTS=f"{tmp_path}/a, {tmp_path}/b")
    assert s.allowed_roots == [tmp_path, tmp_path / "v", tmp_path / "a", tmp_path / "b"]


def test_enabled_toolsets_csv(configure):
    s = configure(ENABLED_TOOLSETS="git, cima")
    assert s.enabled_toolsets == frozenset({"git", "cima"})


def test_secrets_not_in_repr(configure):
    s = configure(EMAIL_PASSWORD="hunter2")
    assert "hunter2" not in repr(s)
    assert isinstance(s, Settings) and s.email_password.get_secret_value() == "hunter2"
