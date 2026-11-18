from .core import backup_file, resolve_safe_path, tool


@tool
def resize_image(path: str, width: int, height: int, out_path: str = "") -> str:
    """Resize an image to the given dimensions.

    Args:
        path: Input image path.
        width: Target width in pixels.
        height: Target height in pixels.
        out_path: Output path (empty = overwrite input, backed up first).
    """
    try:
        from PIL import Image
    except ImportError:
        return "Error: install 'Pillow'."
    ap = resolve_safe_path(path)
    out = resolve_safe_path(out_path) if out_path else ap
    if not out_path:
        backup_file(ap)
    Image.open(ap).resize((width, height)).save(out)
    return f"Saved {out}"


@tool
def convert_image(path: str, out_path: str) -> str:
    """Convert an image to another format (determined by the output extension).

    Args:
        path: Input image path.
        out_path: Output path with the target extension, e.g. 'img.png'.
    """
    try:
        from PIL import Image
    except ImportError:
        return "Error: install 'Pillow'."
    ap = resolve_safe_path(path)
    out = resolve_safe_path(out_path)
    Image.open(ap).convert("RGB").save(out)
    return f"Saved {out}"


@tool
def screenshot(out_path: str = "screenshot.png") -> str:
    """Capture a screenshot of the primary monitor.

    Args:
        out_path: Output image path.
    """
    try:
        import mss
    except ImportError:
        return "Error: install 'mss'."
    out = resolve_safe_path(out_path)
    with mss.mss() as sct:
        sct.shot(output=out)
    return f"Saved {out}"


@tool
def qr_generate(data: str, out_path: str = "qr.png") -> str:
    """Generate a QR code image from text/URL.

    Args:
        data: Text or URL to encode.
        out_path: Output image path.
    """
    try:
        import qrcode
    except ImportError:
        return "Error: install 'qrcode'."
    out = resolve_safe_path(out_path)
    qrcode.make(data).save(out)
    return f"Saved QR to {out}"
