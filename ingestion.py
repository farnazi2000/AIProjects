"""Input adapters for text, email bodies, and PDF submissions."""

from __future__ import annotations

from pathlib import Path
from pypdf import PdfReader


def read_submission(text: str | None, file_path: Path | None, source_type: str) -> tuple[str, str]:
    if text is not None:
        return text, source_type
    if file_path is None:
        raise ValueError("A submission is required")
    if not file_path.is_file():
        raise FileNotFoundError(f"Submission not found: {file_path}")
    if file_path.suffix.lower() == ".pdf":
    
        content = "\n".join(page.extract_text() or "" for page in PdfReader(file_path).pages).strip()
        if not content:
            raise ValueError("The PDF contains no extractable text (it may be a scanned image).")
        return content, "pdf"
    return file_path.read_text(encoding="utf-8"), source_type
