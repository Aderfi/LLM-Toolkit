from llmtools import config, graphs


def test_mermaid_diagram():
    out = graphs.mermaid_diagram("flowchart", "A-->B;B-->C")
    assert out.startswith("```mermaid") and "A-->B" in out


def test_graphviz_without_binary(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ALLOWED_ROOTS", [str(tmp_path)])
    monkeypatch.setattr(graphs.shutil, "which", lambda _: None)
    out = graphs.graphviz_render("digraph{a->b}", str(tmp_path / "g.png"))
    assert "dot" in out.lower() and "a->b" in out
