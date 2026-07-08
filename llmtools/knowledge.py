import glob
import json
import os
import re

from llmtools import config
from llmtools.core import resolve_safe_path, tool

_EXTRA_MSG = "Error: install knowledge deps (pip install -r requirements-extra.txt)."

_model = None


def _embedder():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(config.RAG_MODEL)
    return _model


def _chunk(text, size=800):
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


@tool
def index_documents(path: str = "", glob_pattern: str = "*.md") -> str:
    """Build a semantic (embedding) index over text/markdown files.

    Args:
        path: Root directory (empty = DEFAULT_VAULT).
        glob_pattern: File glob, e.g. '*.md' or '*.txt'.
    """
    try:
        import numpy as np

        model = _embedder()
    except ImportError:
        return _EXTRA_MSG
    root = resolve_safe_path(path or config.DEFAULT_VAULT)
    files = glob.glob(os.path.join(root, "**", glob_pattern), recursive=True)
    texts, meta = [], []
    for fp in files:
        try:
            with open(fp, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            continue
        for j, ch in enumerate(_chunk(content)):
            texts.append(ch)
            meta.append({"file": fp, "chunk": j})
    if not texts:
        return "No documents found to index."
    emb = model.encode(texts, normalize_embeddings=True)
    os.makedirs(config.RAG_INDEX_DIR, exist_ok=True)
    np.save(os.path.join(config.RAG_INDEX_DIR, "emb.npy"), emb)
    with open(os.path.join(config.RAG_INDEX_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"texts": texts, "meta": meta}, f)
    return f"Indexed {len(texts)} chunks from {len(files)} files."


@tool
def semantic_search(query: str, k: int = 5) -> str:
    """Search the semantic index by meaning (run index_documents first).

    Args:
        query: Search query.
        k: Number of results.
    """
    ep = os.path.join(config.RAG_INDEX_DIR, "emb.npy")
    mp = os.path.join(config.RAG_INDEX_DIR, "meta.json")
    if not (os.path.exists(ep) and os.path.exists(mp)):
        return "No index found. Run index_documents first."
    try:
        import numpy as np

        model = _embedder()
    except ImportError:
        return _EXTRA_MSG
    emb = np.load(ep)
    with open(mp, encoding="utf-8") as f:
        store = json.load(f)
    q = model.encode([query], normalize_embeddings=True)[0]
    scores = emb @ q
    top = scores.argsort()[::-1][:k]
    out = []
    for i in top:
        m = store["meta"][int(i)]
        snippet = store["texts"][int(i)][:200].replace("\n", " ")
        out.append(f"[{scores[int(i)]:.2f}] {os.path.basename(m['file'])}: {snippet}")
    return "\n".join(out)


@tool
def ocr_image(path: str, language: str = "eng") -> str:
    """Extract text from an image using OCR (Tesseract).

    Args:
        path: Image file path.
        language: Tesseract language code, e.g. 'eng' or 'spa'.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "Error: install 'pytesseract' + 'Pillow' and the tesseract binary."
    ap = resolve_safe_path(path)
    return pytesseract.image_to_string(Image.open(ap), lang=language).strip() or "(no text)"


@tool
def youtube_transcript(url: str, language: str = "en") -> str:
    """Fetch the transcript of a YouTube video.

    Args:
        url: YouTube URL.
        language: Preferred transcript language code.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return "Error: install 'youtube-transcript-api'."
    m = re.search(r"(?:v=|youtu\.be/|/shorts/)([\w-]{11})", url)
    if not m:
        return "Could not parse a video id from the URL."
    try:
        tr = YouTubeTranscriptApi.get_transcript(m.group(1), languages=[language, "en"])
    except Exception as e:
        return f"Error: {e}"
    return " ".join(x["text"] for x in tr)


@tool
def translate_text(text: str, to_lang: str, from_lang: str = "en") -> str:
    """Translate text offline via Argos Translate.

    Args:
        text: Text to translate.
        to_lang: Target language code, e.g. 'es'.
        from_lang: Source language code.
    """
    try:
        import argostranslate.translate as at
    except ImportError:
        return "Error: install 'argostranslate' and the language package."
    try:
        return at.translate(text, from_lang, to_lang)
    except Exception as e:
        return f"Error: {e} (install the {from_lang}->{to_lang} language package)."
