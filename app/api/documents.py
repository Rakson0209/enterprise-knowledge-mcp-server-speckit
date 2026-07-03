"""REST endpoints: upload (auto-index) + catalogue query."""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import get_settings
from app.services.parser import _slugify, detect_format
from app.services.pipeline import index_document
from app.services.vector_store import get_vector_store

router = APIRouter()

_ALLOWED_EXT = {".docx", ".pdf", ".pptx"}


@router.post("/documents", status_code=201)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document; it is parsed, cleaned, chunked, and indexed in-process (no restart)."""
    settings = get_settings()
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(status_code=415, detail=f"unsupported file type: {ext}")

    contents = await file.read()
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413, detail=f"file exceeds {settings.max_upload_mb} MB limit"
        )

    uploads_dir = os.path.join(settings.data_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    dest = os.path.join(uploads_dir, os.path.basename(filename))
    with open(dest, "wb") as fh:
        fh.write(contents)

    try:
        # Offload heavy sync work (Docling/OCR/embedding) so the event loop stays responsive.
        chunks = await asyncio.to_thread(index_document, dest, filename=filename)
    except Exception as exc:  # noqa: BLE001 - surface a clean 400 to the client
        raise HTTPException(status_code=400, detail=f"failed to process document: {exc}") from exc

    document_id = chunks[0].document_id if chunks else _slugify(os.path.splitext(filename)[0])
    return {"document_id": document_id, "status": "indexed", "num_chunks": len(chunks)}


@router.get("/documents")
def list_documents_rest():
    """Catalogue of indexed documents."""
    return [d.model_dump() for d in get_vector_store().documents()]
