import json as _json
import os
import shutil
import zipfile

from .core import backup_file, resolve_safe_path, tool

# All dataframe I/O goes through Polars. Tables are described as
#   'a,b;1,2;3,4'  ->  first row = column names, ';' separates rows.


def _parse_rows(content):
    """Turn 'header1,header2;v1,v2' text into a Polars DataFrame."""
    import polars as pl
    rows = [[c.strip() for c in r.split(",")] for r in content.split(";") if r.strip()]
    if not rows:
        return pl.DataFrame()
    header, *body = rows
    body = [r + [""] * (len(header) - len(r)) for r in body]
    return pl.DataFrame({h: [r[i] for r in body] for i, h in enumerate(header)})


def _read_any(abs_path):
    """Read csv/xlsx/json/ndjson/parquet into a Polars DataFrame by extension."""
    import polars as pl
    ext = os.path.splitext(abs_path)[1].lower()
    readers = {
        ".csv": pl.read_csv, ".xlsx": pl.read_excel, ".json": pl.read_json,
        ".ndjson": pl.read_ndjson, ".jsonl": pl.read_ndjson, ".parquet": pl.read_parquet,
    }
    if ext not in readers:
        raise ValueError(f"Unsupported table format: {ext}")
    return readers[ext](abs_path)


def _write_any(df, abs_path):
    ext = os.path.splitext(abs_path)[1].lower()
    writers = {
        ".csv": df.write_csv, ".xlsx": df.write_excel, ".json": df.write_json,
        ".ndjson": df.write_ndjson, ".jsonl": df.write_ndjson, ".parquet": df.write_parquet,
    }
    if ext not in writers:
        raise ValueError(f"Unsupported table format: {ext}")
    writers[ext](abs_path)


@tool
def read_csv(path: str, max_rows: int = 50) -> str:
    """Read a CSV file into a Polars DataFrame and show it.

    Args:
        path: CSV file path.
        max_rows: Maximum rows to display.
    """
    import polars as pl
    ap = resolve_safe_path(path)
    return str(pl.read_csv(ap, n_rows=max_rows))


@tool
def write_csv(path: str, content: str) -> str:
    """Write a CSV via Polars from rows given as 'header1,header2;v1,v2'.

    Args:
        path: Output CSV path.
        content: First row = column names, ';' separates rows.
    """
    ap = resolve_safe_path(path)
    backup_file(ap)
    _parse_rows(content).write_csv(ap)
    return f"Wrote {ap}"


@tool
def read_excel(path: str, sheet: str = "", max_rows: int = 50) -> str:
    """Read an Excel .xlsx sheet into a Polars DataFrame and show it.

    Args:
        path: .xlsx file path.
        sheet: Sheet name (empty = first sheet).
        max_rows: Maximum rows to display.
    """
    import polars as pl
    ap = resolve_safe_path(path)
    df = pl.read_excel(ap, sheet_name=sheet) if sheet else pl.read_excel(ap)
    return str(df.head(max_rows))


@tool
def write_excel(path: str, content: str, sheet: str = "Sheet1") -> str:
    """Write an Excel .xlsx via Polars from rows given as 'header1,header2;v1,v2'.

    Args:
        path: Output .xlsx path.
        content: First row = column names, ';' separates rows.
        sheet: Worksheet name.
    """
    ap = resolve_safe_path(path)
    backup_file(ap)
    _parse_rows(content).write_excel(ap, worksheet=sheet)
    return f"Wrote {ap}"


@tool
def convert_table(src: str, dst: str) -> str:
    """Convert a data table between formats by extension (csv/xlsx/json/ndjson/parquet).

    Args:
        src: Source table path.
        dst: Destination path; its extension decides the output format.
    """
    sp = resolve_safe_path(src)
    dp = resolve_safe_path(dst)
    backup_file(dp)
    _write_any(_read_any(sp), dp)
    return f"Converted {sp} -> {dp}"


@tool
def table_stats(path: str) -> str:
    """Summary statistics (Polars describe) of a table (csv/xlsx/json/parquet).

    Args:
        path: Table file path.
    """
    ap = resolve_safe_path(path)
    return str(_read_any(ap).describe())


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


@tool(confirm=True)
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
