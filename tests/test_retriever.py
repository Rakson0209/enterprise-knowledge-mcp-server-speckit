"""Unit tests for hybrid retrieval: RRF fusion, CJK+Latin tokenizer, exact-term recall.

Uses a fake in-memory store + a deterministic bag-of-words embedder so the retrieval logic is
exercised without downloading BGE-M3 or running Chroma.
"""

from __future__ import annotations

from app.models import Chunk, ChunkType, SearchResult
from app.services.retriever import Retriever, rrf_fuse, tokenize


# --- Fakes -----------------------------------------------------------------

class FakeEmbedder:
    """Bag-of-words vectors over a fixed vocabulary (deterministic, no model)."""

    def __init__(self, vocab: list[str]) -> None:
        self.vocab = vocab

    def _vec(self, text: str) -> list[float]:
        toks = tokenize(text)
        return [float(toks.count(term)) for term in self.vocab]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


class FakeStore:
    def __init__(self, chunks: list[Chunk], embedder: FakeEmbedder) -> None:
        self._chunks = chunks
        self._embedder = embedder
        self._vectors = {c.chunk_id: embedder.embed([c.content])[0] for c in chunks}

    def all_chunks(self) -> list[Chunk]:
        return list(self._chunks)

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        return next((c for c in self._chunks if c.chunk_id == chunk_id), None)

    def dense_search(self, query_embedding, top_k) -> list[SearchResult]:
        def dot(a, b):
            return sum(x * y for x, y in zip(a, b))

        scored = [
            (c, dot(query_embedding, self._vectors[c.chunk_id])) for c in self._chunks
        ]
        scored.sort(key=lambda t: t[1], reverse=True)
        return [
            SearchResult(chunk=c, score=s, rank=i)
            for i, (c, s) in enumerate(scored[:top_k], start=1)
            if s > 0
        ]


def _chunk(cid: str, content: str) -> Chunk:
    return Chunk(
        document_id="d", filename="d.pdf", page_number=1, chunk_id=cid,
        chunk_type=ChunkType.text, content=content,
    )


def _build_retriever():
    chunks = [
        _chunk("d-0000", "the yield improvement plan raises output"),
        _chunk("d-0001", "quarterly revenue and profit summary"),
        _chunk("d-0002", "identifier CLAUDE.md rare token appears here"),
        _chunk("d-0003", "中文 文件 檢索 測試 yield"),
    ]
    vocab = ["yield", "improvement", "plan", "revenue", "profit", "claude", "md",
             "中", "文", "檢", "索", "測", "試"]
    embedder = FakeEmbedder(vocab)
    retriever = Retriever(FakeStore(chunks, embedder), embedder, rrf_k=60)
    retriever.refresh()
    return retriever


# --- Tests -----------------------------------------------------------------

def test_tokenize_keeps_latin_words_and_individual_cjk():
    assert tokenize("Yield 中文 CLAUDE.md") == ["yield", "中", "文", "claude", "md"]


def test_rrf_fuse_rewards_agreement():
    fused = rrf_fuse([["a", "b", "c"], ["b", "a", "d"]], k=60)
    top = [cid for cid, _ in fused]
    # 'a' and 'b' appear in both lists near the top → outrank singletons c/d
    assert set(top[:2]) == {"a", "b"}


def test_semantic_query_hits_relevant_chunk():
    retriever = _build_retriever()
    results = retriever.search("yield improvement", top_k=3)
    assert results[0].chunk.chunk_id == "d-0000"
    assert results[0].rank == 1


def test_exact_rare_token_recalled_via_bm25():
    retriever = _build_retriever()
    results = retriever.search("CLAUDE.md", top_k=3)
    assert any(r.chunk.chunk_id == "d-0002" for r in results)


def test_mixed_language_query():
    retriever = _build_retriever()
    results = retriever.search("中文 檢索", top_k=3)
    assert any(r.chunk.chunk_id == "d-0003" for r in results)


def test_empty_query_raises():
    retriever = _build_retriever()
    try:
        retriever.search("   ", top_k=3)
        assert False, "expected ValueError"
    except ValueError:
        pass
