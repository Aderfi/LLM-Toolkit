import pytest

import llmtools
from llmtools import shell


@pytest.mark.parametrize(
    "cmd",
    [
        "ls -la",
        "cat a.txt | head -5",
        "rg -n TODO src 2>/dev/null | wc -l",
        "find . -name '*.py'",
        "git status && git log --oneline -3",
        "du -h -d 1 . | sort -h",
    ],
)
def test_read_only_commands(cmd):
    assert shell.is_read_only(cmd)


@pytest.mark.parametrize(
    "cmd",
    [
        "rm -rf build",
        "echo hi > out.txt",
        "cat $(which python)",
        "find . -name '*.tmp' -delete",
        "find . -exec rm {} ;",
        "ls; rm x",
        "git commit -m x",
        "git diff --output=patch.txt",
        "sort -o sorted.txt a.txt",
        "FOO=1 ls",
        "mkdir new",
        "python3 -c 'print(1)'",
        "cat 'unterminated",
    ],
)
def test_mutating_commands_need_confirmation(cmd):
    assert not shell.is_read_only(cmd)
    assert llmtools.needs_confirmation("run_bash", {"command": cmd})


def test_run_bash_in_files_root(tmp_path):
    (tmp_path / "hello.txt").write_text("hi there")
    assert "hello.txt" in shell.run_bash("ls")
    assert "hi there" in shell.run_bash("cat hello.txt")
    assert shell.run_bash("exit 3").startswith("[exit 3]")


def test_run_bash_rejects_cwd_outside_roots():
    out = llmtools.call_tool("run_bash", {"command": "ls", "cwd": "/"})
    assert "outside allowed roots" in out


def test_run_bash_timeout():
    assert "timeout" in shell.run_bash("sleep 5", timeout=1)


def test_run_python():
    assert llmtools.needs_confirmation("run_python", {"code": "print(1)"})
    assert shell.run_python("print(6 * 7)").strip() == "42"
