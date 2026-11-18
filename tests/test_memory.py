from llmtools import memory, meta
from llmtools.core import ACTIVE_GROUPS


def test_remember_recall_forget(settings):
    assert "#1" in memory.remember("User prefers Spanish answers", tags="Preference, language")
    memory.remember("Project llmtools uses uv")
    assert "Spanish" in memory.recall("spanish")
    assert "uv" in memory.recall("llmtools uv") and "Spanish" not in memory.recall("llmtools uv")
    assert "preference" in memory.recall("preference")
    assert settings.memory_file.exists()
    assert memory.forget(1) == "Forgot #1."
    assert "No memory #1" in memory.forget(1)
    assert "Spanish" not in memory.recall()


def test_tasks():
    assert memory.task_list() == "No tasks."
    memory.task_add("Read the data")
    memory.task_add("Write the report")
    assert memory.task_done(1) == "Task #1 done."
    assert memory.task_list() == "#2 [ ] Write the report"
    assert "#1 [x] Read the data" in memory.task_list(include_done=True)
    assert "Removed 1" in memory.task_clear_done()
    assert "No task #9" in memory.task_done(9)


def test_toolsets():
    ACTIVE_GROUPS.clear()
    ACTIVE_GROUPS.add("meta")
    assert "[off] git" in meta.list_toolsets()
    assert "git_status" in meta.enable_toolset("git")
    assert "git" in ACTIVE_GROUPS
    assert "Unknown group" in meta.enable_toolset("nope")
    ACTIVE_GROUPS.clear()
