import csv
import json as _json
import os
import shutil
import zipfile

from llmtools.core import backup_file, resolve_safe_path, tool


@tool
def read_csv(path: str, max_rows: int = 50) -> str:
    """Read a CSV file and return its rows.

    Args:
        path: CSV file path.
        max_rows: Maximum rows to return.
    """
    ap = resolve_safe_path(path)
    with open(ap, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))[:max_rows]
    return "\n".join(", ".join(r) for r in rows) or "(empty)"


@tool
def write_csv(path: str, content: str) -> str:
    """Write a CSV file from rows given as 'a,b;c,d' (';' between rows).

    Args:
        path: Output CSV path.
        content: Rows, cells comma-separated, rows semicolon-separated.
    """
    ap = resolve_safe_path(path)
    backup_file(ap)
    with open(ap, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for row in content.split(";"):
            if row.strip():
                w.writerow([c.strip() for c in row.split(",")])
    return f"Wrote {ap}"


@tool
def read_excel(path: str, sheet: str = "", max_rows: int = 50) -> str:
    """Read an Excel .xlsx sheet.

    Args:
        path: .xlsx file path.
        sheet: Sheet name (empty = active sheet).
        max_rows: Maximum rows to return.
    """
    import openpyxl

    ap = resolve_safe_path(path)
    wb = openpyxl.load_workbook(ap, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.active
    out = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i >= max_rows:
            break
        out.append(", ".join("" if c is None else str(c) for c in row))
    return "\n".join(out) or "(empty)"


@tool
def write_excel(path: str, content: str, sheet: str = "Sheet1") -> str:
    """Write an Excel .xlsx from rows given as 'a,b;c,d'.

    Args:
        path: Output .xlsx path.
        content: Rows, cells comma-separated, rows semicolon-separated.
        sheet: Sheet name.
    """
    import openpyxl

    ap = resolve_safe_path(path)
    backup_file(ap)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    for row in content.split(";"):
        if row.strip():
            ws.append([c.strip() for c in row.split(",")])
    wb.save(ap)
    return f"Wrote {ap}"


@tool
def clipboard_get() -> str:
    """Get the current clipboard text."""
    import pyperclip

    return pyperclip.paste()


@tool
def clipboard_set(text: str) -> str:
    """Set the clipboard text.

    Args:
        text: Text to copy.
    """
    import pyperclip

    pyperclip.copy(text)
    return "Copied to clipboard."


@tool
def http_request(url: str, method: str = "GET", json_body: str = "", headers: str = "") -> str:
    """Make an HTTP request to a REST API and return status + body.

    Args:
        url: Target URL.
        method: HTTP method (GET/POST/PUT/DELETE...).
        json_body: JSON string body (empty = none).
        headers: JSON string of headers (empty = none).
    """
    import requests

    hdrs = _json.loads(headers) if headers else {}
    data = _json.loads(json_body) if json_body else None
    r = requests.request(method.upper(), url, json=data, headers=hdrs, timeout=30)
    return f"HTTP {r.status_code}\n{r.text[:4000]}"


@tool
def download_file(url: str, dest: str) -> str:
    """Download a URL to a local file.

    Args:
        url: Source URL.
        dest: Destination file path.
    """
    import requests

    dp = resolve_safe_path(dest)
    r = requests.get(url, timeout=60, stream=True)
    r.raise_for_status()
    with open(dp, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return f"Downloaded to {dp}"


@tool
def make_zip(source: str, dest: str) -> str:
    """Create a zip archive from a file or directory.

    Args:
        source: File or directory to compress.
        dest: Output .zip path.
    """
    sp = resolve_safe_path(source)
    dp = resolve_safe_path(dest)
    with zipfile.ZipFile(dp, "w", zipfile.ZIP_DEFLATED) as z:
        if os.path.isdir(sp):
            for root, _, files in os.walk(sp):
                for f in files:
                    fp = os.path.join(root, f)
                    z.write(fp, os.path.relpath(fp, sp))
        else:
            z.write(sp, os.path.basename(sp))
    return f"Created {dp}"


@tool
def extract_archive(path: str, dest: str) -> str:
    """Extract a zip or tar archive.

    Args:
        path: Archive file path.
        dest: Destination directory.
    """
    ap = resolve_safe_path(path)
    dp = resolve_safe_path(dest)
    shutil.unpack_archive(ap, dp)
    return f"Extracted to {dp}"
