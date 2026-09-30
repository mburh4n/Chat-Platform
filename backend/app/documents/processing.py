"""PDF text extraction and chunking. Pure functions: no database, no HTTP."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)

NO_TEXT_MESSAGE = (
    "No text could be extracted from this PDF. It is probably a scanned image; "
    "only text-based PDFs are supported (OCR is not available)."
)


class PDFProcessingError(Exception):
    """The PDF can't be used. The message is safe to show to the user."""


@dataclass(frozen=True)
class TextChunk:
    page_number: int  # 1-based
    content: str


def clean_text(text: str) -> str:
    """Tidy extracted text while keeping paragraph breaks."""
    text = text.replace("\x00", "")  # PostgreSQL can't store NUL characters
    text = re.sub(r"[ \t\r\f\v]+", " ", text)  # runs of spaces -> one space
    text = re.sub(r" *\n *", "\n", text)  # no spaces around line breaks
    text = re.sub(r"\n{3,}", "\n\n", text)  # at most one blank line
    return text.strip()


def extract_pages(path: Path) -> list[str]:
    """Return the cleaned text of every page, in order (empty string if a page has none)."""
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            # Many PDFs are "encrypted" with an empty password just to set permissions
            try:
                reader.decrypt("")
                _ = reader.pages[0] if reader.pages else None
            except Exception as exc:
                raise PDFProcessingError("This PDF is password-protected and can't be read.") from exc

        pages: list[str] = []
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                pages.append(clean_text(page.extract_text() or ""))
            except Exception:
                # One broken page shouldn't fail the whole document
                logger.warning("Could not extract text from page %s of %s", page_number, path.name)
                pages.append("")
        return pages
    except PDFProcessingError:
        raise
    except (PdfReadError, ValueError, OSError) as exc:
        raise PDFProcessingError("This file could not be read as a PDF. It may be damaged.") from exc


# Where a chunk may end, best first: paragraph, line, sentence, word
_BREAKPOINTS = ("\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ")


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into chunks of about chunk_size characters.

    Each chunk ends at the most natural break found in its last 30%
    (paragraph > line > sentence > word), and the next chunk starts
    chunk_overlap characters earlier, so a sentence cut at a boundary
    still appears whole in one of the two chunks.
    """
    if chunk_overlap >= chunk_size * 0.7:
        raise ValueError("chunk_overlap must be well below chunk_size")

    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            search_from = start + int(chunk_size * 0.7)
            for breakpoint in _BREAKPOINTS:
                position = text.rfind(breakpoint, search_from, end)
                if position != -1:
                    end = position + len(breakpoint)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break

        # Step back for the overlap, then forward to the start of a word
        next_start = end - chunk_overlap
        space = text.find(" ", next_start, end)
        start = space + 1 if space != -1 else next_start

    return chunks


def build_chunks(pages: list[str], chunk_size: int, chunk_overlap: int) -> list[TextChunk]:
    """Chunk every page separately, so each chunk has an exact page number."""
    chunks: list[TextChunk] = []
    for page_number, page_text in enumerate(pages, start=1):
        for content in split_text(page_text, chunk_size, chunk_overlap):
            chunks.append(TextChunk(page_number=page_number, content=content))
    return chunks
