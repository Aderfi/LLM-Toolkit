import subprocess

from llmtools import git


def test_git_init_status_commit(tmp_path, monkeypatch):
    git.git_init(str(tmp_path))
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "a@b.c"])
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"])
    (tmp_path / "f.txt").write_text("hi")
    git.git_add(".", str(tmp_path))
    out = git.git_commit("init", str(tmp_path))
    assert "init" in out or "master" in out or "main" in out
    assert "nothing to commit" in git.git_status(str(tmp_path)).lower()


def test_git_tag_and_run_passthrough(tmp_path, monkeypatch):
    git.git_init(str(tmp_path))
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "a@b.c"])
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"])
    (tmp_path / "f.txt").write_text("hi")
    git.git_add(".", str(tmp_path))
    git.git_commit("init", str(tmp_path))
    git.git_tag_create("v1.0", message="first", repo=str(tmp_path))
    assert "v1.0" in git.git_tag_list(str(tmp_path))
    # escape hatch reaches arbitrary commands
    assert "v1.0" in git.git_run("tag --list", str(tmp_path))


def test_git_install_and_list_hook(tmp_path, monkeypatch):
    git.git_init(str(tmp_path))
    git.git_install_hook("pre-commit", "#!/bin/sh\nexit 0", repo=str(tmp_path))
    assert "pre-commit" in git.git_list_hooks(str(tmp_path))
    assert "exit 0" in git.git_show_hook("pre-commit", str(tmp_path))
