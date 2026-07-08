from llmtools import markdown


def test_markdown_table():
    t = markdown.markdown_table("a,b", "1,2;3,4")
    assert "a" in t and "b" in t and "1" in t and "2" in t and "|" in t
