"""Chroma persistence: the single source of truth for chunks + dense vectors.

Embedded, persistent Chroma stored under ``<data_dir>/chroma`` so the index survives
restart/redeploy (FR-020). ``chromadb`` is imported lazily inside ``__init__`` to keep module
import light.
"""

from __future__ import annotations

import os
from functools import lru_cache

from app.config import get_settings
from app.models import Chunk, ChunkType, Document, SearchResult


def _chunk_to_metadata(chunk: Chunk) -> dict:
    # Chroma metadata values must be scalar and non-null: omit None-valued keys.
    meta: dict = {
        "document_id": chunk.document_id,
        "filename": chunk.filename,
        "chunk_type": chunk.chunk_type.value,
    }
    if chunk.page_number is not None:
        meta["page_number"] = chunk.page_number
    if chunk.slide_number is not None:
        meta["slide_number"] = chunk.slide_number
    if chunk.section_title is not None:
        meta["section_title"] = chunk.section_title
    return meta


def _metadata_to_chunk(chunk_id: str, content: str, meta: dict) -> Chunk:
    return Chunk(
        document_id=meta["document_id"],
        filename=meta["filename"],
        page_number=meta.get("page_number"),
        slide_number=meta.get("slide_number"),
        chunk_id=chunk_id,
        chunk_type=ChunkType(meta["chunk_type"]),
        content=content,
        section_title=meta.get("section_title"),
    )


class VectorStore:
    def __init__(self, data_dir: str, collection_name: str) -> None:
        import chromadb

        path = os.path.join(data_dir, "chroma")
        os.makedirs(path, exist_ok=True)
        self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        self._collection.upsert(
            ids=[c.chunk_id for c in chunks],
            documents=[c.content for c in chunks],
            metadatas=[_chunk_to_metadata(c) for c in chunks],
            embeddings=embeddings,
        )

    def count(self) -> int:
        return self._collection.count()

    def dense_search(self, query_embedding: list[float], top_k: int) -> list[SearchResult]:
        if self._collection.count() == 0:
            return []
        res = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        ids = res["ids"][0]
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        dists = res["distances"][0]
        results: list[SearchResult] = []
        for rank, (cid, doc, meta, dist) in enumerate(zip(ids, docs, metas, dists), start=1):
            chunk = _metadata_to_chunk(cid, doc, meta)
            results.append(SearchResult(chunk=chunk, score=1.0 - float(dist), rank=rank))
        return results

    def all_chunks(self) -> list[Chunk]:
        res = self._collection.get(include=["documents", "metadatas"])
        return [
            _metadata_to_chunk(cid, doc, meta)
            for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"])
        ]

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        res = self._collection.get(ids=[chunk_id], include=["documents", "metadatas"])
        if not res["ids"]:
            return None
        return _metadata_to_chunk(res["ids"][0], res["documents"][0], res["metadatas"][0])

    def documents(self) -> list[Document]:
        return _aggregate_documents(self.all_chunks())

    def get_document(self, document_id: str) -> Document | None:
        chunks = [c for c in self.all_chunks() if c.document_id == document_id]
        if not chunks:
            return None
        return _aggregate_documents(chunks)[0]

    def chunks_for_document(self, document_id: str) -> list[Chunk]:
        chunks = [c for c in self.all_chunks() if c.document_id == document_id]
        return sorted(chunks, key=lambda c: c.chunk_id)


def _aggregate_documents(chunks: list[Chunk]) -> list[Document]:
    by_doc: dict[str, list[Chunk]] = {}
    for c in chunks:
        by_doc.setdefault(c.document_id, []).append(c)

    docs: list[Document] = []
    for document_id, group in by_doc.items():
        pages = [c.page_number for c in group if c.page_number is not None]
        slides = [c.slide_number for c in group if c.slide_number is not None]
        docs.append(
            Document(
                document_id=document_id,
                filename=group[0].filename,
                num_chunks=len(group),
                page_range=(min(pages), max(pages)) if pages else None,
                slide_range=(min(slides), max(slides)) if slides else None,
                chunk_types=sorted({c.chunk_type.value for c in group}),
            )
        )
    return docs


@lru_cache
def get_vector_store() -> VectorStore:
    settings = get_settings()
    return VectorStore(settings.data_dir, settings.chroma_collection)
