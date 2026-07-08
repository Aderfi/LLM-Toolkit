from llmtools import web


def test_web_search_formats(monkeypatch):
    class FakeDDGS:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def text(self, q, max_results):
            return [{"title": "T", "href": "http://x", "body": "B"}]

    monkeypatch.setattr(web, "DDGS", FakeDDGS)
    out = web.web_search("python")
    assert "T" in out and "http://x" in out


def test_fetch_url_strips_html(monkeypatch):
    class R:
        text = "<html><body><p>Hi</p><script>x</script></body></html>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(web.requests, "get", lambda *a, **k: R())
    out = web.fetch_url("http://x")
    assert "Hi" in out and "script" not in out
