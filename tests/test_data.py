from llmtools import data


def test_csv_roundtrip(tmp_path, monkeypatch):
    p = str(tmp_path / "d.csv")
    data.write_csv(p, "a,b;1,2")
    out = data.read_csv(p)
    assert "a" in out and "b" in out and "1" in out and "2" in out


def test_excel_roundtrip(tmp_path, monkeypatch):
    p = str(tmp_path / "d.xlsx")
    data.write_excel(p, "name,age;bob,30")
    out = data.read_excel(p)
    assert "name" in out and "bob" in out and "30" in out


def test_convert_table_csv_to_parquet_and_back(tmp_path, monkeypatch):
    csv_p = str(tmp_path / "d.csv")
    data.write_csv(csv_p, "name,age;bob,30;ana,25")
    pq = str(tmp_path / "d.parquet")
    data.convert_table(csv_p, pq)
    assert (tmp_path / "d.parquet").exists()
    js = str(tmp_path / "d.json")
    data.convert_table(pq, js)
    assert "bob" in (tmp_path / "d.json").read_text()


def test_table_stats(tmp_path, monkeypatch):
    p = str(tmp_path / "d.csv")
    data.write_csv(p, "x,y;1,2;3,4")
    out = data.table_stats(p)
    assert "count" in out.lower() or "mean" in out.lower()


def test_zip_and_extract(tmp_path, monkeypatch):
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
