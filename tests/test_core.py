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


def test_resolve_safe_path_rejects_outside(tmp_path, monkeypatch):
    monkeypatch.setattr(core.config, "ALLOWED_ROOTS", [str(tmp_path)])
    with pytest.raises(ValueError):
        core.resolve_safe_path("/etc/passwd")


def test_backup_file_creates_backup(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("hi")
    core.backup_file(str(f))
    assert (tmp_path / "note._backup.md").read_text() == "hi"
