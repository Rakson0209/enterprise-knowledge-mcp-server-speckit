"""PPTX parsing maps provenance to slide numbers. Full parse requires the docling runtime."""

from __future__ import annotations

import importlib.util

import pytest

from app.services.parser import detect_format

_HAS_DOCLING = importlib.util.find_spec("docling") is not None


def test_pptx_format_detected():
    assert detect_format("deck.pptx") == "pptx"


@pytest.mark.skipif(not _HAS_DOCLING, reason="docling runtime not installed")
def test_parse_pptx_sets_slide_numbers():
    pytest.skip("provide a sample PPTX fixture and assert slide_number is populated (page_number null)")
