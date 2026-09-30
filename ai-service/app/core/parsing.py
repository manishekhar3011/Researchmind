"""
Parses raw uploaded files into a list of (text, page_number) tuples.
page_number is None for formats without a native page concept (TXT, DOCX sections).
"""
from io import BytesIO
from typing import List, Tuple

from pypdf import PdfReader
from docx import Document as DocxDocument


def parse_pdf(file_bytes: bytes) -> List[Tuple[str, int]]:
    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((text, i))
    return pages


def parse_docx(file_bytes: bytes) -> List[Tuple[str, int]]:
    doc = DocxDocument(BytesIO(file_bytes))
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    # DOCX has no native page numbers pre-render; treat whole doc as one "page" unit.
    return [(full_text, 1)] if full_text.strip() else []


def parse_txt(file_bytes: bytes) -> List[Tuple[str, int]]:
    text = file_bytes.decode("utf-8", errors="ignore")
    return [(text, 1)] if text.strip() else []


def parse_document(file_bytes: bytes, file_type: str) -> List[Tuple[str, int]]:
    file_type = file_type.lower()
    if file_type == "pdf":
        return parse_pdf(file_bytes)
    if file_type == "docx":
        return parse_docx(file_bytes)
    if file_type == "txt":
        return parse_txt(file_bytes)
    raise ValueError(f"Unsupported file type: {file_type}")
