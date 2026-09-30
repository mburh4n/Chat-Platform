"""Test helpers: tiny real PDFs and fake (but deterministic) embeddings."""

import hashlib
import math
import re

from app.models.document import EMBEDDING_DIMENSION


def make_pdf(pages: list[list[str]]) -> bytes:
    """Build a minimal valid PDF where each page shows the given text lines."""

    def escape(line: str) -> str:
        return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    page_count = len(pages)
    # Object numbers: 1 catalog, 2 page tree, 3 font, then (page, content) pairs
    page_ids = [4 + 2 * i for i in range(page_count)]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            f"<< /Type /Pages /Count {page_count} /Kids ["
            + " ".join(f"{pid} 0 R" for pid in page_ids)
            + "] >>"
        ).encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for page_id, lines in zip(page_ids, pages):
        text_ops = "BT /F1 11 Tf 14 TL 50 780 Td " + " ".join(f"({escape(l)}) Tj T*" for l in lines) + " ET"
        stream = text_ops.encode("latin-1")
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>"
        ).encode()
        objects[page_id + 1] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"

    output = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for number in sorted(objects):
        offsets[number] = len(output)
        output += b"%d 0 obj\n" % number + objects[number] + b"\nendobj\n"
    xref_start = len(output)
    size = max(objects) + 1
    output += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for number in range(1, size):
        output += b"%010d 00000 n \n" % offsets[number]
    output += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref_start)
    return bytes(output)


def fake_embedding(text: str) -> list[float]:
    """A deterministic unit vector built from the words in the text.

    Texts that share words get similar vectors, so similarity search behaves
    sensibly in tests without calling Gemini.
    """
    vector = [0.0] * EMBEDDING_DIMENSION
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        index = int(hashlib.sha256(word.encode()).hexdigest(), 16) % EMBEDDING_DIMENSION
        vector[index] += 1.0
    length = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / length for v in vector]


def fake_embed_documents(texts: list[str]) -> list[list[float]]:
    return [fake_embedding(text) for text in texts]
