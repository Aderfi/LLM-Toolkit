"""Persistent agent memory (facts to remember across sessions) and a task list for planning.

Both live as JSON in DATA_DIR (memory.json, tasks.json).
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from .config import get_settings
from .core import tool


class MemoryItem(BaseModel):
    id: int
    text: str
    tags: list[str] = []
    created: datetime


class Task(BaseModel):
    id: int
    title: str
    done: bool = False
    created: datetime


_MEMORIES = TypeAdapter(list[MemoryItem])
_TASKS = TypeAdapter(list[Task])


def _load[T](path: Path, adapter: TypeAdapter[list[T]]) -> list[T]:
    return adapter.validate_json(path.read_bytes()) if path.exists() else []


def _save[T](path: Path, adapter: TypeAdapter[list[T]], items: list[T]) -> None:
    path.write_bytes(adapter.dump_json(items, indent=2))


def _next_id(items: list) -> int:
    return max((i.id for i in items), default=0) + 1


@tool
def remember(text: str, tags: str = "") -> str:
    """Store a fact in long-term memory (persists across sessions).

    Args:
        text: The fact to remember, self-contained, e.g. 'User prefers answers in Spanish'.
        tags: Optional comma-separated tags, e.g. 'preference,language'.
    """
    path = get_settings().memory_file
    items = _load(path, _MEMORIES)
    item = MemoryItem(
        id=_next_id(items),
        text=text.strip(),
        tags=[t.strip().lower() for t in tags.split(",") if t.strip()],
        created=datetime.now(),
    )
    items.append(item)
    _save(path, _MEMORIES, items)
    return f"Remembered #{item.id}."


@tool
def recall(query: str = "", max_results: int = 20) -> str:
    """Search long-term memory (case-insensitive words in text or tags; empty = latest).

    Args:
        query: Words to look for; every word must match.
        max_results: Maximum number of memories returned.
    """
    items = _load(get_settings().memory_file, _MEMORIES)
    words = query.lower().split()
    hits = [m for m in items if all(w in (m.text + " " + " ".join(m.tags)).lower() for w in words)]
    if not hits:
        return "No memories found."
    return "\n".join(
        f"#{m.id} [{m.created:%Y-%m-%d}] {m.text}"
        + (f" (tags: {', '.join(m.tags)})" if m.tags else "")
        for m in hits[-max_results:]
    )


@tool
def forget(memory_id: int) -> str:
    """Delete one memory by its id (see recall).

    Args:
        memory_id: Memory id, e.g. 3.
    """
    path = get_settings().memory_file
    items = _load(path, _MEMORIES)
    kept = [m for m in items if m.id != memory_id]
    if len(kept) == len(items):
        return f"No memory #{memory_id}."
    _save(path, _MEMORIES, kept)
    return f"Forgot #{memory_id}."


@tool
def task_add(title: str) -> str:
    """Add a step to the task list (use it to plan multi-step work).

    Args:
        title: Short description of the step.
    """
    path = get_settings().tasks_file
    tasks = _load(path, _TASKS)
    task = Task(id=_next_id(tasks), title=title.strip(), created=datetime.now())
    tasks.append(task)
    _save(path, _TASKS, tasks)
    return f"Added task #{task.id}."


@tool
def task_list(include_done: bool = False) -> str:
    """Show the task list.

    Args:
        include_done: Also show completed tasks.
    """
    tasks = [t for t in _load(get_settings().tasks_file, _TASKS) if include_done or not t.done]
    if not tasks:
        return "No tasks."
    return "\n".join(f"#{t.id} [{'x' if t.done else ' '}] {t.title}" for t in tasks)


@tool
def task_done(task_id: int) -> str:
    """Mark a task as completed.

    Args:
        task_id: Task id, e.g. 2.
    """
    path = get_settings().tasks_file
    tasks = _load(path, _TASKS)
    for t in tasks:
        if t.id == task_id:
            t.done = True
            _save(path, _TASKS, tasks)
            return f"Task #{task_id} done."
    return f"No task #{task_id}."


@tool
def task_clear_done() -> str:
    """Remove all completed tasks from the list."""
    path = get_settings().tasks_file
    tasks = _load(path, _TASKS)
    pending = [t for t in tasks if not t.done]
    _save(path, _TASKS, pending)
    return f"Removed {len(tasks) - len(pending)} completed task(s)."
