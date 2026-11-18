"""Tool groups the agent can discover and switch on at runtime (always offered)."""

from collections import Counter

from .core import ACTIVE_GROUPS, REGISTRY, tool


@tool
def list_toolsets() -> str:
    """List all tool groups, how many tools each has and whether it is enabled."""
    counts = Counter(t.group for t in REGISTRY.values())
    return "\n".join(
        f"{'[on] ' if g in ACTIVE_GROUPS else '[off]'} {g} ({n} tools)"
        for g, n in sorted(counts.items())
    )


@tool
def enable_toolset(group: str) -> str:
    """Enable a tool group so its tools become available from the next step on.

    Args:
        group: Group name from list_toolsets, e.g. 'git' or 'cima'.
    """
    tools = sorted(t.name for t in REGISTRY.values() if t.group == group)
    if not tools:
        return f"Unknown group '{group}'. Call list_toolsets."
    ACTIVE_GROUPS.add(group)
    return f"Enabled '{group}': {', '.join(tools)}"
