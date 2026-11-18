import pytest

from llmtools import core


def test_tool_builds_schema_from_hints():
    @core.tool
    def sample(city: str, count: int = 3) -> str:
        """Do a thing.

        Args:
            city: The city name.
            count: How many.
        """
        return f"{city}-{count}"

    schemas = {s["function"]["name"]: s for s in core.get_schemas()}
    assert "sample" in schemas
    props = schemas["sample"]["function"]["parameters"]["properties"]
    assert props["city"]["type"] == "string"
    assert props["count"]["type"] == "integer"
    assert schemas["sample"]["function"]["parameters"]["required"] == ["city"]


def test_call_tool_returns_string_and_catches_errors():
    @core.tool
    def boom() -> str:
        """Explode."""
        raise RuntimeError("kaboom")

    out = core.call_tool("boom", {})
    assert isinstance(out, str) and "kaboom" in out


def test_resolve_safe_path_rejects_outside():
    with pytest.raises(ValueError):
        core.resolve_safe_path("/etc/passwd")
    with pytest.raises(ValueError):
        core.resolve_safe_path("../escape.txt")


def test_call_tool_coerces_and_validates_args():
    @core.tool
    def add(a: int, b: int = 1) -> str:
        """Add.

        Args:
            a: First.
            b: Second.
        """
        return str(a + b)

    assert core.call_tool("add", {"a": "5", "b": 2}) == "7"
    assert "Invalid arguments" in core.call_tool("add", {"a": "five"})
    assert "Invalid arguments" in core.call_tool("add", {})


def test_needs_confirmation_static_and_conditional():
    @core.tool(confirm=True)
    def risky() -> str:
        """Risky."""
        return "done"

    @core.tool(confirm=lambda a: a["loud"])
    def maybe(loud: bool = False) -> str:
        """Maybe."""
        return "ok"

    assert core.needs_confirmation("risky")
    assert not core.needs_confirmation("maybe", {"loud": False})
    assert core.needs_confirmation("maybe", {"loud": "true"})
    assert not core.needs_confirmation("unknown_tool")


def test_run_argv_reports_exit_code_and_truncates(configure):
    configure(MAX_OUTPUT_CHARS="500")
    assert core.run_argv(["false"]).startswith("[exit 1]")
    out = core.run_argv(["python3", "-c", "print('x' * 5000)"])
    assert "truncated" in out and len(out) < 700


def test_backup_file_creates_backup(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("hi")
    core.backup_file(str(f))
    assert (tmp_path / "note._backup.md").read_text() == "hi"
