import shutil
import subprocess

from llmtools.core import resolve_safe_path, tool


@tool
def mermaid_diagram(kind: str, definition: str) -> str:
    """Build a Mermaid diagram code block.

    Args:
        kind: Diagram type, e.g. 'flowchart', 'graph TD', 'sequenceDiagram'.
        definition: Diagram body, statements separated by ';'.
    """
    lines = [s.strip() for s in definition.split(";") if s.strip()]
    body = "\n    ".join(lines)
    return f"```mermaid\n{kind}\n    {body}\n```"


@tool
def graphviz_render(dot_source: str, output_path: str) -> str:
    """Render Graphviz DOT to an image; returns DOT source if 'dot' is unavailable.

    Args:
        dot_source: DOT graph source.
        output_path: Output image path (.png/.svg).
    """
    out = resolve_safe_path(output_path)
    if shutil.which("dot") is None:
        return f"Graphviz 'dot' binary not found. DOT source:\n{dot_source}"
    fmt = out.rsplit(".", 1)[-1]
    subprocess.run(["dot", f"-T{fmt}", "-o", out], input=dot_source.encode(), check=True)
    return f"Rendered graph to {out}"
