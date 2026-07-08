from llmtools import markdown


def test_markdown_table():
    t = markdown.markdown_table("a,b", "1,2;3,4")
    assert "| a | b |" in t and "| 1 | 2 |" in t
