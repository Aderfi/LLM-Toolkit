import pytest

from llmtools import config, documents


def test_read_docx(tmp_path, monkeypatch):
    docx = pytest.importorskip("docx")
    monkeypatch.setattr(config, "ALLOWED_ROOTS", [str(tmp_path)])
    d = docx.Document()
    d.add_paragraph("Hello world")
    p = str(tmp_path / "f.docx")
    d.save(p)
    assert "Hello world" in documents.read_docx(p)


def test_read_text_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ALLOWED_ROOTS", [str(tmp_path)])
    p = tmp_path / "f.txt"
    p.write_text("plain text")
    assert "plain text" in documents.read_text_file(str(p))
