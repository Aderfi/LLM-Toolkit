from llmtools import config, data


def _roots(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ALLOWED_ROOTS", [str(tmp_path)])


def test_csv_roundtrip(tmp_path, monkeypatch):
    _roots(tmp_path, monkeypatch)
    p = str(tmp_path / "d.csv")
    data.write_csv(p, "a,b;1,2")
    out = data.read_csv(p)
    assert "a, b" in out and "1, 2" in out


def test_excel_roundtrip(tmp_path, monkeypatch):
    _roots(tmp_path, monkeypatch)
    p = str(tmp_path / "d.xlsx")
    data.write_excel(p, "name,age;bob,30")
    out = data.read_excel(p)
    assert "name" in out and "bob" in out and "30" in out


def test_zip_and_extract(tmp_path, monkeypatch):
    _roots(tmp_path, monkeypatch)
    (tmp_path / "f.txt").write_text("hi")
    z = str(tmp_path / "a.zip")
    data.make_zip(str(tmp_path / "f.txt"), z)
    dest = tmp_path / "out"
    dest.mkdir()
    data.extract_archive(z, str(dest))
    assert (dest / "f.txt").read_text() == "hi"


def test_http_request(monkeypatch):
    import requests

    class R:
        status_code = 200
        text = '{"ok": true}'

    monkeypatch.setattr(requests, "request", lambda *a, **k: R())
    out = data.http_request("http://x")
    assert "HTTP 200" in out and "ok" in out


def test_clipboard(monkeypatch):
    store = {}
    import pyperclip

    monkeypatch.setattr(pyperclip, "copy", lambda t: store.__setitem__("v", t))
    monkeypatch.setattr(pyperclip, "paste", lambda: store.get("v", ""))
    data.clipboard_set("hello")
    assert data.clipboard_get() == "hello"
