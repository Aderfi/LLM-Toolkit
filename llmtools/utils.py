import ast
import base64 as _b64
import hashlib
import json
import operator
import uuid
from datetime import datetime

from llmtools.core import tool

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")


@tool
def calculate(expression: str) -> str:
    """Evaluate a safe arithmetic expression (+ - * / ** %).

    Args:
        expression: Math expression, e.g. '3 * (4 + 1)'.
    """
    try:
        return str(_eval(ast.parse(expression, mode="eval").body))
    except Exception as e:
        return f"Error: {e}"


@tool
def get_local_time() -> str:
    """Get the current local date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def format_json(text: str) -> str:
    """Pretty-print a JSON string.

    Args:
        text: Raw JSON text.
    """
    return json.dumps(json.loads(text), indent=2, ensure_ascii=False)


@tool
def generate_uuid() -> str:
    """Generate a random UUID4."""
    return str(uuid.uuid4())


@tool
def hash_text(text: str) -> str:
    """SHA-256 hash of a string.

    Args:
        text: Input text.
    """
    return "sha256: " + hashlib.sha256(text.encode()).hexdigest()


@tool
def base64_encode(text: str) -> str:
    """Base64-encode a string.

    Args:
        text: Input text.
    """
    return _b64.b64encode(text.encode()).decode()


@tool
def base64_decode(data: str) -> str:
    """Base64-decode a string.

    Args:
        data: Base64 text.
    """
    return _b64.b64decode(data.encode()).decode()


@tool
def generate_password(length: int = 16, symbols: bool = True) -> str:
    """Generate a strong random password.

    Args:
        length: Password length (minimum 4).
        symbols: Include punctuation symbols.
    """
    import secrets
    import string

    alpha = string.ascii_letters + string.digits + ("!@#$%^&*()-_=+" if symbols else "")
    return "".join(secrets.choice(alpha) for _ in range(max(4, length)))


@tool
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert a value between physical units (length, mass, temperature, etc.).

    Args:
        value: The numeric value.
        from_unit: Source unit, e.g. 'meter', 'kg', 'celsius'.
        to_unit: Target unit, e.g. 'foot', 'lb', 'fahrenheit'.
    """
    try:
        import pint
    except ImportError:
        return "Error: install 'pint'."
    ureg = pint.UnitRegistry()
    try:
        q = ureg.Quantity(value, from_unit).to(to_unit)
        return f"{value} {from_unit} = {q.magnitude:.4g} {to_unit}"
    except Exception as e:
        return f"Error: {e}"
