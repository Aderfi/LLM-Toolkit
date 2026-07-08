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
def render_mermaid(definition: str, out_path: str = "diagram.svg") -> str:
    """Render a Mermaid diagram to an image file via mermaid-py (needs internet).

    Args:
        definition: Full Mermaid definition, e.g. 'graph TD; A-->B; B-->C'.
        out_path: Output image path (.svg or .png).
    """
    out = resolve_safe_path(out_path)
    try:
        from mermaid import Mermaid
    except ImportError:
        return "Error: install 'mermaid-py'."
    try:
        diagram = Mermaid(definition)
        if out.lower().endswith(".png"):
            diagram.to_png(out)
        else:
            diagram.to_svg(out)
        return f"Rendered Mermaid diagram to {out}"
    except Exception as e:
        return f"Error rendering Mermaid (needs internet via mermaid.ink): {e}"


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
    import graphviz
    base, fmt = out.rsplit(".", 1)
    graphviz.Source(dot_source).render(outfile=out, format=fmt, cleanup=True)
    return f"Rendered graph to {out}"
