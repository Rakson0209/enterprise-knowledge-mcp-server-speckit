"""Unit tests for metadata-aware, semantic-boundary chunking (constitution Principle II)."""

from __future__ import annotations

from app.models import ChunkType
from app.services.chunker import chunk_document
from app.services.cleaner import clean_document


def test_full_metadata_schema(pdf_like_document):
    chunks = chunk_document(clean_document(pdf_like_document))
    assert chunks
    for c in chunks:
        assert c.document_id == "report"
        assert c.filename == "report.pdf"
        assert c.chunk_id.startswith("report-")
        assert c.chunk_type in ChunkType
        assert c.content
        # exactly one of page/slide populated for a PDF-style doc
        assert c.page_number is not None and c.slide_number is None


def test_reproducible_chunk_ids(pdf_like_document):
    cleaned = clean_document(pdf_like_document)
    ids1 = [c.chunk_id for c in chunk_document(cleaned)]
    ids2 = [c.chunk_id for c in chunk_document(cleaned)]
    assert ids1 == ids2
    assert len(set(ids1)) == len(ids1)  # unique
    assert ids1[0] == "report-0000"


def test_table_and_figure_are_standalone_chunks(pdf_like_document):
    chunks = chunk_document(clean_document(pdf_like_document))
    assert any(c.chunk_type == ChunkType.table for c in chunks)
    assert any(c.chunk_type == ChunkType.figure for c in chunks)
    for c in chunks:
        if c.chunk_type == ChunkType.table:
            assert c.content.startswith("| KPI")
        if c.chunk_type == ChunkType.figure:
            assert "throughput" in c.content


def test_pptx_uses_slide_numbers(pptx_like_document):
    chunks = chunk_document(clean_document(pptx_like_document))
    assert chunks
    for c in chunks:
        assert c.slide_number is not None and c.page_number is None


def test_page_change_starts_new_chunk(pdf_like_document):
    chunks = chunk_document(clean_document(pdf_like_document))
    text_chunks = [c for c in chunks if c.chunk_type == ChunkType.text]
    pages = {c.page_number for c in text_chunks}
    assert pages == {1, 2}  # text from page 1 and page 2 never merged into one chunk


def test_section_title_propagates_to_continuation(long_section_document):
    # small limit forces element-boundary splits within one section
    chunks = chunk_document(long_section_document, max_chars=80)
    text_chunks = [c for c in chunks if c.chunk_type == ChunkType.text]
    assert len(text_chunks) > 1  # section was split
    assert all(c.section_title == "Big Section" for c in text_chunks)


def test_no_fixed_size_splitting_keeps_whole_elements(long_section_document):
    # Every produced chunk's text is a join of whole element sentences (no mid-sentence cut).
    chunks = chunk_document(long_section_document, max_chars=80)
    for c in chunks:
        for line in c.content.split("\n"):
            # each line is either the title or a complete "Sentence number N ..." element
            assert line == "Big Section" or line.startswith("Sentence number")
