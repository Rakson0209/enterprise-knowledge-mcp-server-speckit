"""Parser tests. The Docling-backed parse path requires the ``docling`` runtime; those cases skip
when it is unavailable. Format detection and slug logic are always tested (pure logic)."""

from __future__ import annotations

import importlib.util

import pytest

from app.services.parser import _slugify, detect_format

_HAS_DOCLING = importlib.util.find_spec("docling") is not None


def test_detect_format():
    assert detect_format("a.docx") == "docx"
    assert detect_format("a.PDF") == "pdf"
    assert detect_format("deck.pptx") == "pptx"


def test_detect_format_rejects_unsupported():
    with pytest.raises(ValueError):
        detect_format("notes.txt")


def test_slugify():
    assert _slugify("Q4 Report 2026") == "q4-report-2026"
    assert _slugify("  ") == "document"


@pytest.mark.skipif(not _HAS_DOCLING, reason="docling runtime not installed")
def test_parse_pdf_preserves_provenance(tmp_path):
    # Integration test: requires docling + a real sample PDF. Placeholder for CI with the full stack.
    pytest.skip("provide a sample PDF fixture and assert page_number provenance under full stack")
