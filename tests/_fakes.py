"""Fake store/retriever for testing the MCP + REST layers without ML models or Chroma."""

from __future__ import annotations

from app.models import Chunk, ChunkType, SearchResult
from app.services.vector_store import _aggregate_documents


def sample_chunks() -> list[Chunk]:
    return [
        Chunk(
            document_id="report", filename="report.pdf", page_number=1,
            chunk_id="report-0000", chunk_type=ChunkType.text,
            content="the yield improvement plan raises output", section_title="Plan",
        ),
        Chunk(
            document_id="report", filename="report.pdf", page_number=2,
            chunk_id="report-0001", chunk_type=ChunkType.table,
            content="| KPI | Value |\n| --- | --- |\n| Yield | 88% |", section_title="KPI",
        ),
    ]


class FakeStore:
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    def documents(self):
        return _aggregate_documents(self._chunks)

    def get_document(self, document_id: str):
        docs = [d for d in self.documents() if d.document_id == document_id]
        return docs[0] if docs else None

    def get_chunk(self, chunk_id: str):
        return next((c for c in self._chunks if c.chunk_id == chunk_id), None)

    def chunks_for_document(self, document_id: str):
        return [c for c in self._chunks if c.document_id == document_id]


class FakeRetriever:
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    def search(self, query: str, top_k: int = 5):
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")
        return [
            SearchResult(chunk=c, score=1.0 / i, rank=i)
            for i, c in enumerate(self._chunks[:top_k], start=1)
        ]
