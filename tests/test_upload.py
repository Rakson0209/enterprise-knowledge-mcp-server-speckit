"""REST upload tests (US2): type/size validation and auto-index (with a faked pipeline)."""

from __future__ import annotations

import app.api.documents as documents
from app.config import Settings
from app.main import app
from app.models import Chunk, ChunkType
from fastapi.testclient import TestClient


def test_reject_unsupported_type():
    with TestClient(app) as client:
        r = client.post("/documents", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_reject_oversized(monkeypatch):
    tiny = Settings(max_upload_mb=0)
    monkeypatch.setattr(documents, "get_settings", lambda: tiny)
    with TestClient(app) as client:
        r = client.post("/documents", files={"file": ("a.pdf", b"%PDF-1.4 data", "application/pdf")})
    assert r.status_code == 413


def test_upload_indexes_and_reports_num_chunks(monkeypatch, tmp_path):
    monkeypatch.setattr(documents, "get_settings", lambda: Settings(data_dir=str(tmp_path)))

    def fake_index(path, filename=None):
        return [
            Chunk(document_id="a", filename=filename, page_number=1, chunk_id="a-0000",
                  chunk_type=ChunkType.text, content="x"),
            Chunk(document_id="a", filename=filename, page_number=1, chunk_id="a-0001",
                  chunk_type=ChunkType.text, content="y"),
        ]

    monkeypatch.setattr(documents, "index_document", fake_index)

    with TestClient(app) as client:
        r = client.post("/documents", files={"file": ("a.pdf", b"%PDF-1.4 data", "application/pdf")})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "indexed"
    assert body["num_chunks"] == 2
    assert body["document_id"] == "a"
