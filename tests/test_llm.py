"""Agent loop with a fake OpenAI client (no LLM server needed)."""

from types import SimpleNamespace

from llmtools import llm
from llmtools.core import ACTIVE_GROUPS


def _tool_call(name, arguments, call_id="c1"):
    tc = SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))
    tc.model_dump = lambda: {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }
    return tc


def _reply(content=None, tool_calls=None):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class _FakeCompletions:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.replies.pop(0)


def _agent(monkeypatch, replies):
    completions = _FakeCompletions(replies)
    monkeypatch.setattr(
        llm, "OpenAI", lambda **_: SimpleNamespace(chat=SimpleNamespace(completions=completions))
    )
    return llm.Agent(), completions


def test_agent_runs_tool_then_answers(monkeypatch, tmp_path):
    (tmp_path / "f.txt").write_text("secret-ish")
    agent, completions = _agent(
        monkeypatch,
        [_reply(tool_calls=[_tool_call("run_bash", '{"command": "cat f.txt"}')]), _reply("done")],
    )
    messages = [{"role": "user", "content": "read f.txt"}]
    assert agent.run(messages) == "done"
    tool_msg = next(m for m in messages if m["role"] == "tool")
    assert "secret-ish" in tool_msg["content"] and "<tool_result" in tool_msg["content"]
    offered = {t["function"]["name"] for t in completions.calls[0]["tools"]}
    assert {"run_bash", "enable_toolset"} <= offered and "git_status" not in offered


def test_agent_asks_before_mutating(monkeypatch, tmp_path):
    asked = []
    agent, _ = _agent(
        monkeypatch,
        [_reply(tool_calls=[_tool_call("run_bash", '{"command": "touch x"}')]), _reply("ok")],
    )
    messages = [{"role": "user", "content": "create x"}]
    agent.run(messages, confirm=lambda n, a: asked.append(n) or False)
    assert asked == ["run_bash"] and not (tmp_path / "x").exists()
    assert any("cancelled" in m.get("content", "") for m in messages if m["role"] == "tool")


def test_enable_toolset_extends_offered_tools(monkeypatch):
    agent, completions = _agent(
        monkeypatch,
        [_reply(tool_calls=[_tool_call("enable_toolset", '{"group": "git"}')]), _reply("ok")],
    )
    agent.run([{"role": "user", "content": "use git"}])
    offered = {t["function"]["name"] for t in completions.calls[1]["tools"]}
    assert "git_status" in offered
    ACTIVE_GROUPS.clear()


def test_agent_stops_at_round_limit(monkeypatch, configure):
    configure(MAX_TOOL_ROUNDS="2")
    loop = [_reply(tool_calls=[_tool_call("task_list", "{}")]) for _ in range(2)]
    agent, _ = _agent(monkeypatch, loop)
    assert "limit" in agent.run([{"role": "user", "content": "x"}])
