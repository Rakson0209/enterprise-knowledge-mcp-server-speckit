"""Metadata-aware, semantic-boundary chunking (constitution Principle II — NON-NEGOTIABLE).

Rules:
- Each table and each figure becomes its own chunk (chunk_type = table / figure).
- Continuous text joins the section opened by the nearest preceding title.
- A page/slide boundary change starts a new chunk.
- A section is split ONLY when it exceeds ``chunk_max_chars``, and ONLY between whole elements —
  never mid-sentence or mid-row. Continuation chunks reuse the same ``section_title``.
- ``chunk_id`` is unique and reproducible: ``<document_id>-<sequence>`` (zero-padded, monotonic).
"""

from __future__ import annotations

from app.config import get_settings
from app.models import Chunk, ChunkType, ElementType, ParsedDocument


def chunk_document(doc: ParsedDocument, max_chars: int | None = None) -> list[Chunk]:
    if max_chars is None:
        max_chars = get_settings().chunk_max_chars

    chunks: list[Chunk] = []
    seq = 0
    section_title: str | None = None

    # Accumulator for a run of text within one (section, page/slide) group.
    buf: list[str] = []
    buf_page: int | None = None
    buf_slide: int | None = None

    def new_chunk(content: str, page: int | None, slide: int | None, ctype: ChunkType) -> Chunk:
        nonlocal seq
        chunk = Chunk(
            document_id=doc.document_id,
            filename=doc.filename,
            page_number=page,
            slide_number=slide,
            chunk_id=f"{doc.document_id}-{seq:04d}",
            chunk_type=ctype,
            content=content,
            section_title=section_title,
        )
        seq += 1
        return chunk

    def flush() -> None:
        nonlocal buf, buf_page, buf_slide
        if not buf:
            return
        current: list[str] = []
        current_len = 0
        for piece in buf:
            piece_len = len(piece)
            if current and current_len + piece_len + 1 > max_chars:
                chunks.append(new_chunk("\n".join(current), buf_page, buf_slide, ChunkType.text))
                current, current_len = [], 0
            current.append(piece)
            current_len += piece_len + 1
        if current:
            chunks.append(new_chunk("\n".join(current), buf_page, buf_slide, ChunkType.text))
        buf, buf_page, buf_slide = [], None, None

    for el in sorted(doc.elements, key=lambda e: e.order):
        if el.element_type in (ElementType.table, ElementType.figure):
            flush()
            ctype = ChunkType.table if el.element_type == ElementType.table else ChunkType.figure
            chunks.append(new_chunk(el.content, el.page_number, el.slide_number, ctype))
            continue

        if el.element_type == ElementType.title:
            flush()
            section_title = el.content
            buf = [el.content]
            buf_page, buf_slide = el.page_number, el.slide_number
            continue

        # Text element: a page/slide change forces a new chunk.
        if buf and (el.page_number != buf_page or el.slide_number != buf_slide):
            flush()
        if not buf:
            buf_page, buf_slide = el.page_number, el.slide_number
        buf.append(el.content)

    flush()
    return chunks
