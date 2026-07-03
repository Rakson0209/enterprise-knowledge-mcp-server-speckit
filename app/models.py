"""Shared Pydantic models used across services, REST, MCP, and the Skill.

The ``Chunk`` metadata schema is fixed by the source requirements and the constitution
(Principle II) and MUST NOT change without a governance amendment.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ElementType(str, Enum):
    title = "title"
    text = "text"
    table = "table"
    figure = "figure"


class ChunkType(str, Enum):
    text = "text"
    table = "table"
    figure = "figure"


class ParsedElement(BaseModel):
    """An ordered, flat unit emitted by the parser (before cleaning/chunking)."""

    element_type: ElementType
    content: str
    page_number: int | None = None
    slide_number: int | None = None
    order: int


class ParsedDocument(BaseModel):
    """Result of parsing one file."""

    document_id: str
    filename: str
    format: str  # docx / pdf / pptx
    elements: list[ParsedElement] = Field(default_factory=list)


class Chunk(BaseModel):
    """The atomic unit of retrieval — the persisted metadata contract (FR-006)."""

    document_id: str
    filename: str
    page_number: int | None = None
    slide_number: int | None = None
    chunk_id: str  # unique & reproducible: <document_id>-<sequence>
    chunk_type: ChunkType
    content: str
    section_title: str | None = None


class Document(BaseModel):
    """Document-level catalogue view, aggregated from persisted chunks."""

    document_id: str
    filename: str
    num_chunks: int
    page_range: tuple[int, int] | None = None
    slide_range: tuple[int, int] | None = None
    chunk_types: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    """A chunk returned for a query, augmented with ranking."""

    chunk: Chunk
    score: float
    rank: int
