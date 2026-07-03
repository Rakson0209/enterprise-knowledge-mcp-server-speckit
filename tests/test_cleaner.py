"""Unit tests for the cleaning pipeline (FR-004)."""

from __future__ import annotations

from app.models import ChunkType, ElementType
from app.services.chunker import chunk_document
from app.services.cleaner import clean_document


def _contents(doc, etype=None):
    return [e.content for e in doc.elements if etype is None or e.element_type == etype]


def test_removes_repeated_header_footer(pdf_like_document):
    cleaned = clean_document(pdf_like_document, min_repeats=2)
    assert "ACME Confidential" not in _contents(cleaned)


def test_removes_page_number_only_lines(pdf_like_document):
    cleaned = clean_document(pdf_like_document)
    texts = _contents(cleaned, ElementType.text)
    assert "1" not in texts and "2" not in texts


def test_removes_symbol_only_paragraphs(pdf_like_document):
    cleaned = clean_document(pdf_like_document)
    assert "----" not in _contents(cleaned)


def test_preserves_titles_tables_figures(pdf_like_document):
    cleaned = clean_document(pdf_like_document)
    types = {e.element_type for e in cleaned.elements}
    assert ElementType.title in types
    assert ElementType.table in types
    assert ElementType.figure in types
    assert "Yield Improvement Plan" in _contents(cleaned, ElementType.title)


def test_short_title_not_dropped():
    from app.models import ParsedDocument, ParsedElement

    doc = ParsedDocument(
        document_id="d",
        filename="d.pdf",
        format="pdf",
        elements=[ParsedElement(element_type=ElementType.title, content="KPI", page_number=1, order=0)],
    )
    cleaned = clean_document(doc)
    assert "KPI" in _contents(cleaned, ElementType.title)


def test_table_markdown_preserved_through_clean_and_chunk(pdf_like_document):
    cleaned = clean_document(pdf_like_document)
    chunks = chunk_document(cleaned, max_chars=1200)
    table_chunks = [c for c in chunks if c.chunk_type == ChunkType.table]
    assert table_chunks
    assert "| KPI | Value |" in table_chunks[0].content
