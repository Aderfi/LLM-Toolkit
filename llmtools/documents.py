import os

from llmtools.core import resolve_safe_path, tool


@tool
def read_pdf(path: str, max_pages: int = 0) -> str:
    """Extract text from a PDF.

    Args:
        path: PDF file path.
        max_pages: Max pages to read (0 = all).
    """
    from pypdf import PdfReader

    ap = resolve_safe_path(path)
    reader = PdfReader(ap)
    pages = reader.pages if max_pages == 0 else reader.pages[:max_pages]
    text = "\n\n".join((pg.extract_text() or "") for pg in pages).strip()
    return text or "(no extractable text)"


@tool
def read_docx(path: str) -> str:
    """Extract text from a Word .docx file.

    Args:
        path: .docx file path.
    """
    import docx

    ap = resolve_safe_path(path)
    doc = docx.Document(ap)
    return "\n".join(p.text for p in doc.paragraphs)


@tool
def read_text_file(path: str) -> str:
    """Read a plain-text file.

    Args:
        path: Text file path.
    """
    ap = resolve_safe_path(path)
    with open(ap, encoding="utf-8", errors="replace") as f:
        return f.read()


@tool
def document_metadata(path: str) -> str:
    """Return size and basic metadata for a document.

    Args:
        path: File path.
    """
    ap = resolve_safe_path(path)
    st = os.stat(ap)
    return f"path: {ap}\nsize: {st.st_size} bytes\next: {os.path.splitext(ap)[1]}"
