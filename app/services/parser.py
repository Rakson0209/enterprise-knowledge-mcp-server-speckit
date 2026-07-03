"""Structure-preserving parsing with Docling, plus RapidOCR for image text (Principle I).

Docling recovers titles, tables, and figures with per-element page/slide provenance (superior to
flat OCR). Docling's PPTX/DOCX pipelines do not OCR embedded images, so RapidOCR is applied to
picture items to recover figure/slide-borne text (FR-003).

Heavy imports (``docling``, ``rapidocr_onnxruntime``) are deferred so importing this module stays
cheap; the models are downloaded/cached once on the deployment node (CPU-only, ARM64-safe).
"""

from __future__ import annotations

import os
import threading
from functools import lru_cache

from app.config import get_settings
from app.models import ElementType, ParsedDocument, ParsedElement

_SUPPORTED = {".docx": "docx", ".pdf": "pdf", ".pptx": "pptx"}

# Docling labels → our element types.
_TITLE_LABELS = {"title", "section_header", "page_header"}
_TABLE_LABELS = {"table"}
_FIGURE_LABELS = {"picture", "figure"}


def detect_format(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _SUPPORTED:
        raise ValueError(f"unsupported file type: {ext}")
    return _SUPPORTED[ext]


class _OCR:
    """Lazy RapidOCR wrapper (CPU-only)."""

    def __init__(self) -> None:
        self._engine = None
        self._lock = threading.Lock()

    def text_of(self, image) -> str:
        if image is None:
            return ""
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    from rapidocr_onnxruntime import RapidOCR

                    self._engine = RapidOCR()
        import numpy as np

        result, _ = self._engine(np.array(image))
        if not result:
            return ""
        return " ".join(line[1] for line in result).strip()


@lru_cache
def _ocr() -> _OCR:
    return _OCR()


def _label_to_type(label: str) -> ElementType:
    label = (label or "").lower()
    if label in _TITLE_LABELS:
        return ElementType.title
    if label in _TABLE_LABELS:
        return ElementType.table
    if label in _FIGURE_LABELS:
        return ElementType.figure
    return ElementType.text


def parse_document(
    file_path: str,
    filename: str | None = None,
    document_id: str | None = None,
    enable_ocr: bool | None = None,
) -> ParsedDocument:
    """Parse a DOCX/PDF/PPTX file into an ordered ``ParsedDocument`` with provenance."""
    from docling.document_converter import DocumentConverter

    filename = filename or os.path.basename(file_path)
    fmt = detect_format(filename)
    document_id = document_id or _slugify(os.path.splitext(filename)[0])
    if enable_ocr is None:
        enable_ocr = get_settings().enable_ocr

    result = DocumentConverter().convert(file_path)
    doc = result.document

    elements: list[ParsedElement] = []
    order = 0
    for item, _level in doc.iterate_items():
        etype = _label_to_type(getattr(item, "label", "text"))
        page_no = _provenance_page(item)

        if etype == ElementType.table:
            content = _table_markdown(item, doc)
        elif etype == ElementType.figure:
            content = _figure_text(item, doc, enable_ocr)
        else:
            content = (getattr(item, "text", "") or "").strip()

        if not content:
            continue

        page_number = page_no if fmt in ("pdf", "docx") else None
        slide_number = page_no if fmt == "pptx" else None
        elements.append(
            ParsedElement(
                element_type=etype,
                content=content,
                page_number=page_number,
                slide_number=slide_number,
                order=order,
            )
        )
        order += 1

    return ParsedDocument(
        document_id=document_id, filename=filename, format=fmt, elements=elements
    )


def _provenance_page(item) -> int | None:
    prov = getattr(item, "prov", None)
    if prov:
        page = getattr(prov[0], "page_no", None)
        if page is not None:
            return int(page)
    return None


def _table_markdown(item, doc) -> str:
    for attr in ("export_to_markdown",):
        fn = getattr(item, attr, None)
        if callable(fn):
            try:
                return fn(doc).strip()
            except TypeError:
                return fn().strip()
    return (getattr(item, "text", "") or "").strip()


def _figure_text(item, doc, enable_ocr: bool) -> str:
    caption = ""
    cap_fn = getattr(item, "caption_text", None)
    if callable(cap_fn):
        try:
            caption = (cap_fn(doc) or "").strip()
        except TypeError:
            caption = (cap_fn() or "").strip()

    ocr_text = ""
    if enable_ocr:
        image = None
        get_image = getattr(item, "get_image", None)
        if callable(get_image):
            try:
                image = get_image(doc)
            except Exception:
                image = None
        ocr_text = _ocr().text_of(image)

    parts = [p for p in (caption, ocr_text) if p]
    return "\n".join(parts)


def _slugify(name: str) -> str:
    import re

    slug = re.sub(r"[^\w\-]+", "-", name.strip().lower()).strip("-")
    return slug or "document"
