"""Vector store index tests. Require the ``chromadb`` runtime; skip when unavailable.

Uses precomputed fake embeddings (no embedding model needed) to exercise Chroma upsert, dense
query, and document aggregation.
"""

from __future__ import annotations

import importlib.util

import pytest

from app.models import Chunk, ChunkType

_HAS_CHROMA = importlib.util.find_spec("chromadb") is not None

pytestmark = pytest.mark.skipif(not _HAS_CHROMA, reason="chromadb runtime not installed")


def _chunk(cid, content, page=1, ctype=ChunkType.text):
    return Chunk(
        document_id="d", filename="d.pdf", page_number=page, chunk_id=cid,
        chunk_type=ctype, content=content, section_title="S",
    )


def test_upsert_query_and_aggregate(tmp_path):
    from app.services.vector_store import VectorStore

    store = VectorStore(str(tmp_path), "test_collection")
    chunks = [_chunk("d-0000", "alpha"), _chunk("d-0001", "beta", page=2, ctype=ChunkType.table)]
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    store.upsert(chunks, embeddings)

    assert store.count() == 2

    results = store.dense_search([1.0, 0.0], top_k=1)
    assert results and results[0].chunk.chunk_id == "d-0000"

    got = store.get_chunk("d-0001")
    assert got is not None and got.chunk_type == ChunkType.table

    docs = store.documents()
    assert docs[0].num_chunks == 2
    assert docs[0].page_range == (1, 2)
    assert set(docs[0].chunk_types) == {"text", "table"}
