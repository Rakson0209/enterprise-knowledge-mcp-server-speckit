"""Cleaning pipeline: remove noise while preserving structure (FR-004).

Rules (constitution Principle I — structure-preserving):
- Normalize whitespace (tables keep their Markdown row structure untouched).
- Remove text repeated at/above ``header_footer_min_repeats`` across the document (boilerplate
  headers/footers).
- Remove page-number-only lines (e.g. ``12``, ``1 / 10``, ``Page 3``, ``第 5 頁``).
- Remove pure-symbol / no-substance paragraphs.
- Always preserve titles, tables, and figures; never apply a minimum-length rule to titles.
"""

from __future__ import annotations

import re
from collections import Counter

from app.config import get_settings
from app.models import ElementType, ParsedDocument, ParsedElement

_PAGE_NUMBER_PATTERNS = [
    re.compile(r"^\d+$"),
    re.compile(r"^\d+\s*/\s*\d+$"),
    re.compile(r"^[Pp]age\s+\d+$"),
    re.compile(r"^第\s*\d+\s*頁$"),
]

# A character carrying substance: latin letter, digit, or CJK ideograph.
_SUBSTANCE_RE = re.compile(r"[0-9A-Za-z一-鿿]")


def _normalize_ws(text: str) -> str:
    return re.sub(r"[ \t　]+", " ", text).strip()


def _is_page_number_line(text: str) -> bool:
    return any(p.match(text) for p in _PAGE_NUMBER_PATTERNS)


def _has_substance(text: str) -> bool:
    return bool(_SUBSTANCE_RE.search(text))


def clean_document(doc: ParsedDocument, min_repeats: int | None = None) -> ParsedDocument:
    if min_repeats is None:
        min_repeats = get_settings().header_footer_min_repeats

    # Count normalized text-element contents to detect repeated boilerplate.
    counts: Counter[str] = Counter()
    for el in doc.elements:
        if el.element_type == ElementType.text:
            counts[_normalize_ws(el.content)] += 1
    repeated = {key for key, c in counts.items() if key and c >= min_repeats}

    cleaned: list[ParsedElement] = []
    for el in doc.elements:
        # Titles / tables / figures are always preserved.
        if el.element_type in (ElementType.title, ElementType.figure):
            cleaned.append(el.model_copy(update={"content": _normalize_ws(el.content)}))
            continue
        if el.element_type == ElementType.table:
            cleaned.append(el)  # keep Markdown structure verbatim
            continue

        # Text elements are subject to noise removal.
        norm = _normalize_ws(el.content)
        if not norm:
            continue
        if _is_page_number_line(norm):
            continue
        if not _has_substance(norm):
            continue
        if norm in repeated:
            continue
        cleaned.append(el.model_copy(update={"content": norm}))

    return doc.model_copy(update={"elements": cleaned})
