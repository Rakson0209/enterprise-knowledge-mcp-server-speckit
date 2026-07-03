"""Hybrid retrieval: dense (BGE-M3) + sparse (BM25) fused by Reciprocal Rank Fusion.

Constitution Principle III: never rely on a single method / plain FTS. The BM25 corpus is rebuilt
from the vector store (single source of truth) on ``refresh()``. The tokenizer keeps both Latin
words and individual CJK characters so mixed Chinese/English content is reachable by both methods.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.config import get_settings
from app.models import SearchResult

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[一-鿿]")


def tokenize(text: str) -> list[str]:
    """Latin words/numbers as whole tokens; each CJK character as its own token."""
    return _TOKEN_RE.findall(text.lower())


def rrf_fuse(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion. rank is 1-based: score += 1 / (k + rank)."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for position, chunk_id in enumerate(ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + position)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


class Retriever:
    def __init__(self, store, embedder, rrf_k: int | None = None) -> None:
        self._store = store
        self._embedder = embedder
        self.rrf_k = rrf_k if rrf_k is not None else get_settings().rrf_k
        self._bm25 = None
        self._bm25_ids: list[str] = []
        self._chunks_by_id: dict = {}

    def refresh(self) -> None:
        """Rebuild the BM25 corpus from the vector store. Call after new documents are indexed."""
        from rank_bm25 import BM25Okapi

        chunks = self._store.all_chunks()
        self._chunks_by_id = {c.chunk_id: c for c in chunks}
        self._bm25_ids = [c.chunk_id for c in chunks]
        corpus = [tokenize(c.content) for c in chunks]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def _sparse_ids(self, query: str, top_k: int) -> list[str]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self._bm25_ids[i] for i in order[:top_k] if scores[i] > 0]

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")
        if top_k is None:
            top_k = get_settings().top_k_default

        # Over-fetch each arm so fusion has candidates beyond the final cut.
        fetch = max(top_k * 4, top_k)

        query_embedding = self._embedder.embed([query])[0]
        dense = self._store.dense_search(query_embedding, fetch)
        dense_ids = [r.chunk.chunk_id for r in dense]
        for r in dense:
            self._chunks_by_id.setdefault(r.chunk.chunk_id, r.chunk)

        sparse_ids = self._sparse_ids(query, fetch)

        fused = rrf_fuse([dense_ids, sparse_ids], k=self.rrf_k)

        results: list[SearchResult] = []
        for rank, (chunk_id, score) in enumerate(fused[:top_k], start=1):
            chunk = self._chunks_by_id.get(chunk_id) or self._store.get_chunk(chunk_id)
            if chunk is None:
                continue
            results.append(SearchResult(chunk=chunk, score=score, rank=rank))
        return results


@lru_cache
def get_retriever() -> Retriever:
    from app.services.embedder import get_embedder
    from app.services.vector_store import get_vector_store

    retriever = Retriever(get_vector_store(), get_embedder())
    retriever.refresh()
    return retriever
