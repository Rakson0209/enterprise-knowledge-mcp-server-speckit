"""Shared pipeline: parse → clean → chunk (→ index).

This is the single source of truth (constitution Principle V) reused by the REST upload endpoint
and the document-preprocessing Skill. ``process_document`` performs parse→clean→chunk only (no
index, no network); ``index_document`` additionally embeds and upserts into the vector store and
refreshes hybrid retrieval.
"""

from __future__ import annotations

from app.models import Chunk
from app.services.chunker import chunk_document
from app.services.cleaner import clean_document
from app.services.parser import parse_document


def process_document(
    file_path: str,
    filename: str | None = None,
    document_id: str | None = None,
    enable_ocr: bool | None = None,
    max_chars: int | None = None,
) -> list[Chunk]:
    """parse → clean → chunk. No indexing, no network."""
    parsed = parse_document(
        file_path, filename=filename, document_id=document_id, enable_ocr=enable_ocr
    )
    cleaned = clean_document(parsed)
    return chunk_document(cleaned, max_chars=max_chars)


def index_document(
    file_path: str,
    filename: str | None = None,
    document_id: str | None = None,
    enable_ocr: bool | None = None,
    max_chars: int | None = None,
) -> list[Chunk]:
    """Full ingestion: process → embed → upsert → refresh hybrid retrieval."""
    from app.services.embedder import get_embedder
    from app.services.retriever import get_retriever
    from app.services.vector_store import get_vector_store

    chunks = process_document(
        file_path,
        filename=filename,
        document_id=document_id,
        enable_ocr=enable_ocr,
        max_chars=max_chars,
    )
    if chunks:
        embeddings = get_embedder().embed([c.content for c in chunks])
        get_vector_store().upsert(chunks, embeddings)
        get_retriever().refresh()
    return chunks
