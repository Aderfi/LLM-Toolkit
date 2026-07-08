from llmtools import config, obsidian


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
