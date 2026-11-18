import os

import pytest

from llmtools import files


def test_write_then_read(tmp_path):
    p = str(tmp_path / "a.txt")
    files.write_file(p, "hello")
    assert "hello" in files.read_file(p)


def test_relative_path_resolves_in_files_root(tmp_path):
    files.write_file("sub/rel.txt", "x")
    assert (tmp_path / "sub" / "rel.txt").read_text() == "x"


def test_write_backs_up_existing(tmp_path):
    p = str(tmp_path / "a.txt")
    files.write_file(p, "v1")
    files.write_file(p, "v2")
    assert (tmp_path / "a._backup.txt").read_text() == "v1"


def test_delete_blocked_when_disabled(tmp_path):
    p = str(tmp_path / "a.txt")
    files.write_file(p, "x")
    out = files.delete_file(p)
    assert "disabled" in out.lower() and os.path.exists(p)


def test_delete_allowed_when_enabled(tmp_path, configure):
    configure(ALLOW_DELETE_FILES="true")
    p = str(tmp_path / "a.txt")
    files.write_file(p, "x")
    files.delete_file(p)
    assert not os.path.exists(p)


def test_edit_file_replaces_unique_text(tmp_path):
    p = tmp_path / "e.txt"
    p.write_text("alpha beta gamma")
    out = files.edit_file(str(p), "beta", "BETA")
    assert "1 occurrence" in out and p.read_text() == "alpha BETA gamma"
    assert (tmp_path / "e._backup.txt").read_text() == "alpha beta gamma"


def test_edit_file_rejects_missing_and_ambiguous(tmp_path):
    p = tmp_path / "e.txt"
    p.write_text("x x")
    assert "not found" in files.edit_file(str(p), "y", "z")
    assert "2 times" in files.edit_file(str(p), "x", "z")
    assert "2 occurrence" in files.edit_file(str(p), "x", "z", replace_all=True)
    assert p.read_text() == "z z"


def test_grep_files(tmp_path):
    (tmp_path / "a.py").write_text("def foo():\n    return 1\n")
    (tmp_path / "b.txt").write_text("foo in text\n")
    out = files.grep_files("foo", ".", glob_pattern="*.py")
    assert "a.py:1:def foo" in out and "b.txt" not in out
    assert files.grep_files("nothing_here") == "No matches."


def test_make_directory_and_tree(tmp_path):
    assert "Created" in files.make_directory("x/y/z")
    (tmp_path / "x" / "y" / "z" / "f.txt").write_text("1")
    tree = files.file_tree("x", depth=5)
    assert "z" in tree and "f.txt" in tree


def test_disk_usage(tmp_path):
    (tmp_path / "d").mkdir()
    assert str(tmp_path / "d") in files.disk_usage(".")


def test_extra_roots_allowed(tmp_path_factory, configure):
    other = tmp_path_factory.mktemp("other")
    (other / "o.txt").write_text("outside")
    with pytest.raises(ValueError, match="outside allowed roots"):
        files.read_file(str(other / "o.txt"))
    configure(EXTRA_ROOTS=str(other))
    assert files.read_file(str(other / "o.txt")) == "outside"
