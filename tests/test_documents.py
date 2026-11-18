import pytest

from llmtools import documents


def test_read_docx(tmp_path):
    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.add_paragraph("Hello world")
    p = str(tmp_path / "f.docx")
    d.save(p)
    assert "Hello world" in documents.read_docx(p)


def test_read_text_file(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("plain text")
    assert "plain text" in documents.read_text_file(str(p))
