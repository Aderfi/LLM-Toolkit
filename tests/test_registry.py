import llmtools


def test_all_tools_registered():
    names = set(llmtools.REGISTRY)
    expected = {
        "create_note",
        "read_pdf",
        "web_search",
        "git_status",
        "list_directory",
        "calculate",
        "mermaid_diagram",
        "get_current_weather",
        "markdown_table",
    }
    assert expected <= names


def test_schemas_match_registry():
    schema_names = {s["function"]["name"] for s in llmtools.get_schemas()}
    assert schema_names == set(llmtools.REGISTRY)
