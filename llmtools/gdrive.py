"""Google Drive through the official API with desktop OAuth.

One-off setup:
  1. In Google Cloud Console create an "OAuth client ID" of type *Desktop* and download the JSON.
  2. Put its path in GOOGLE_CLIENT_SECRET_FILE in .env.
  3. Run ``uv run python -m llmtools google-auth`` and authorise in the browser.
The token is stored in DATA_DIR/google_token.json and refreshes itself.
"""

from pathlib import Path

from .config import get_settings
from .core import resolve_safe_path, tool

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


def authorize() -> Path:
    """Interactive OAuth flow (run from the CLI, not by the agent)."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    s = get_settings()
    if not s.google_client_secret_file:
        raise ValueError("Set GOOGLE_CLIENT_SECRET_FILE in .env.")
    flow = InstalledAppFlow.from_client_secrets_file(str(s.google_client_secret_file), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=False)
    s.google_token_file.write_text(creds.to_json())
    return s.google_token_file


def _service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token = get_settings().google_token_file
    if not token.exists():
        raise RuntimeError("Drive not authorised: run `uv run python -m llmtools google-auth`.")
    creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        token.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds, cache_discovery=False)


@tool
def drive_list(name: str = "", max_results: int = 10) -> str:
    """List recent Google Drive files, optionally filtered by name.

    Args:
        name: Text the file name must contain (empty = all).
        max_results: Maximum number of results.
    """
    q = "trashed = false"
    if name:
        q += " and name contains '{}'".format(name.replace("\\", "\\\\").replace("'", "\\'"))
    res = (
        _service()
        .files()
        .list(
            q=q,
            pageSize=max_results,
            orderBy="modifiedTime desc",
            fields="files(id, name, mimeType, modifiedTime, webViewLink)",
        )
        .execute()
    )
    files = res.get("files", [])
    if not files:
        return "No files."
    return "\n".join(
        f"- {f['name']} ({f['modifiedTime'][:10]}) {f.get('webViewLink', '')}" for f in files
    )


@tool(confirm=True)
def drive_upload(path: str, folder_id: str = "") -> str:
    """Upload a local file (inside the allowed folders) to Google Drive.

    Args:
        path: File path, relative to FILES_ROOT.
        folder_id: Destination Drive folder ID (empty = root).
    """
    from googleapiclient.http import MediaFileUpload

    p = Path(resolve_safe_path(path))
    meta = {"name": p.name, **({"parents": [folder_id]} if folder_id else {})}
    f = (
        _service()
        .files()
        .create(
            body=meta, media_body=MediaFileUpload(str(p), resumable=True), fields="id, webViewLink"
        )
        .execute()
    )
    return f"Uploaded {p.name}: {f.get('webViewLink')}"
