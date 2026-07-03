"""Shared test fixtures.

Fixtures build ``ParsedDocument`` objects directly so the cleaning/chunking/retrieval layers
can be tested hermetically without invoking Docling or downloading embedding models.
"""

from __future__ import annotations

import pytest

from app.models import ElementType, ParsedDocument, ParsedElement


def _el(order: int, etype: ElementType, content: str, page=None, slide=None) -> ParsedElement:
    return ParsedElement(
        element_type=etype, content=content, page_number=page, slide_number=slide, order=order
    )


@pytest.fixture
def pdf_like_document() -> ParsedDocument:
    """A PDF/DOCX-style parsed document (page numbers), with repeated header/footer noise."""
    els = [
        _el(0, ElementType.text, "ACME Confidential", page=1),          # repeated header
        _el(1, ElementType.title, "Yield Improvement Plan", page=1),
        _el(2, ElementType.text, "The plan targets a 12% yield increase in Q4.", page=1),
        _el(3, ElementType.text, "1", page=1),                          # page-number-only line
        _el(4, ElementType.text, "ACME Confidential", page=2),          # repeated header
        _el(5, ElementType.title, "KPI Summary", page=2),
        _el(6, ElementType.table, "| KPI | Value |\n| --- | --- |\n| Yield | 88% |", page=2),
        _el(7, ElementType.text, "----", page=2),                       # symbol-only noise
        _el(8, ElementType.figure, "Figure 1: throughput trend rising", page=2),
        _el(9, ElementType.text, "2", page=2),                          # page-number-only line
    ]
    return ParsedDocument(document_id="report", filename="report.pdf", format="pdf", elements=els)


@pytest.fixture
def pptx_like_document() -> ParsedDocument:
    """A PPTX-style parsed document (slide numbers)."""
    els = [
        _el(0, ElementType.title, "Roadmap", slide=1),
        _el(1, ElementType.text, "Phase 1 delivers the MVP.", slide=1),
        _el(2, ElementType.title, "Metrics", slide=5),
        _el(3, ElementType.text, "Slide 5 covers throughput and yield.", slide=5),
        _el(4, ElementType.figure, "chart: yield over time", slide=5),
    ]
    return ParsedDocument(document_id="deck", filename="deck.pptx", format="pptx", elements=els)


@pytest.fixture
def long_section_document() -> ParsedDocument:
    """A single section whose text exceeds a small soft limit, to exercise element-boundary splits."""
    els = [_el(0, ElementType.title, "Big Section", page=1)]
    for i in range(1, 9):
        els.append(_el(i, ElementType.text, f"Sentence number {i} with enough words to add length.", page=1))
    return ParsedDocument(document_id="big", filename="big.pdf", format="pdf", elements=els)
