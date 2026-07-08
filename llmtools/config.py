import os

# --- User-editable placeholders ---
# Set your Obsidian vault path here, or via the OBSIDIAN_VAULT env var.
DEFAULT_VAULT = os.path.expanduser(os.environ.get("OBSIDIAN_VAULT", "DEFAULT_VAULT"))
MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "YOUR_NEWS_API_KEY")

# --- Audio: STT (faster-whisper) + TTS (Piper) ---
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")  # tiny/base/small/medium/large-v3
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")  # cpu or cuda
WHISPER_COMPUTE = os.environ.get("WHISPER_COMPUTE", "int8")  # int8 (cpu) / float16 (gpu)
PIPER_BIN = os.environ.get("PIPER_BIN", "piper")  # piper CLI binary name/path
PIPER_VOICE = os.environ.get("PIPER_VOICE", "")  # path to a .onnx voice model
PIPER_VOICES_DIR = os.path.expanduser(os.environ.get("PIPER_VOICES_DIR", "~/piper_voices"))

# --- Email (IMAP read / SMTP send) ---
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")  # app-password recommended
IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))

# --- Calendar / reminders (local files) ---
CALENDAR_FILE = os.environ.get("CALENDAR_FILE", os.path.join(os.getcwd(), "calendar.ics"))
REMINDERS_FILE = os.environ.get("REMINDERS_FILE", os.path.join(os.getcwd(), "reminders.md"))

# --- Knowledge / RAG (semantic search) ---
RAG_INDEX_DIR = os.path.expanduser(os.environ.get("RAG_INDEX_DIR", "~/.llmtools_rag"))
RAG_MODEL = os.environ.get("RAG_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# --- Safety switches ---
ALLOW_DELETE_FILES = False  # hardcode True to enable delete_file

# Roots that file/git tools may touch. cwd + vault by default.
ALLOWED_ROOTS = [os.getcwd(), DEFAULT_VAULT]
