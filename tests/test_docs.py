import subprocess

from llmtools import docs


class _R:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def test_get_library_docs(monkeypatch):
    monkeypatch.setattr(docs.shutil, "which", lambda _: "/usr/bin/npx")
    seq = [_R("Context7-compatible library ID: /pola-rs/polars"),
           _R("### DataFrame.group_by\nGroups a DataFrame.")]
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: seq.pop(0))
    out = docs.get_library_docs("polars group_by")
    assert "/pola-rs/polars" in out and "group_by" in out.lower()


def test_get_command_help_tldr(monkeypatch):
    monkeypatch.setattr(docs.shutil, "which", lambda p: "/usr/bin/tldr" if p == "tldr" else None)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _R("git rebase examples...", 0))
    out = docs.get_command_help("git rebase")
    assert "examples" in out


def test_devdocs_find(monkeypatch):
    class Resp:
        def json(self):
            return [{"name": "Python", "slug": "python~3.12"},
                    {"name": "React", "slug": "react"}]
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: Resp())
    out = docs.devdocs_find("python")
    assert "Python" in out and "devdocs.io/python" in out


def test_cli_list_and_call(capsys):
    from llmtools import __main__ as cli
    cli._cmd_list([])
    listed = capsys.readouterr().out
    assert "calculate" in listed and "get_library_docs" in listed

    cli._cmd_call(["calculate", '{"expression": "6*7"}'])
    assert "42" in capsys.readouterr().out
