import os

from llmtools import config, files


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
