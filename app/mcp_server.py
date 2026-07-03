"""FastMCP Remote MCP server: 4 tools + 2 resources (constitution Principle IV).

The tool/resource surface is fixed and MUST NOT change without a governance amendment. Every tool
invocation is logged with operation name, query, and returned chunk identifiers (FR-011).
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from app.services.retriever import get_retriever
from app.services.vector_store import get_vector_store

logger = logging.getLogger("app.mcp_server")

mcp: FastMCP = FastMCP("Enterprise Knowledge Base")


@mcp.tool()
def search_documents(query: str, top_k: int = 5) -> list[dict]:
    """Hybrid-retrieve the most relevant chunks for a query (content + metadata + score)."""
    logger.info("MCP tool invoked: search_documents | query=%r top_k=%d", query, top_k)
    results = get_retriever().search(query, top_k=top_k)
    chunk_ids = [r.chunk.chunk_id for r in results]
    logger.info("search_documents retrieved %d chunk(s): %s", len(results), chunk_ids)
    return [r.model_dump() for r in results]


@mcp.tool()
def list_documents() -> list[dict]:
    """List the catalogue of indexed documents."""
    logger.info("MCP tool invoked: list_documents")
    docs = get_vector_store().documents()
    logger.info("list_documents returned %d document(s)", len(docs))
    return [d.model_dump() for d in docs]


@mcp.tool()
def get_document(document_id: str) -> dict:
    """Document-level metadata (chunk count, page/slide range) for one document."""
    logger.info("MCP tool invoked: get_document | document_id=%r", document_id)
    doc = get_vector_store().get_document(document_id)
    if doc is None:
        return {"error": "not_found", "document_id": document_id}
    return doc.model_dump()


@mcp.tool()
def get_chunk(chunk_id: str) -> dict:
    """Full content and metadata of a single chunk."""
    logger.info("MCP tool invoked: get_chunk | chunk_id=%r", chunk_id)
    chunk = get_vector_store().get_chunk(chunk_id)
    if chunk is None:
        return {"error": "not_found", "chunk_id": chunk_id}
    return chunk.model_dump()


@mcp.resource("documents://all")
def documents_all() -> list[dict]:
    """The full catalogue of indexed documents."""
    logger.info("MCP resource read: documents://all")
    return [d.model_dump() for d in get_vector_store().documents()]


@mcp.resource("documents://{document_id}")
def documents_one(document_id: str) -> dict:
    """A specific document and all its chunks."""
    logger.info("MCP resource read: documents://%s", document_id)
    store = get_vector_store()
    doc = store.get_document(document_id)
    if doc is None:
        return {"error": "not_found", "document_id": document_id}
    chunks = store.chunks_for_document(document_id)
    return {"document": doc.model_dump(), "chunks": [c.model_dump() for c in chunks]}


# Names of the registered tools/resources, for the landing page dynamic listing.
REGISTERED_TOOLS = ["search_documents", "list_documents", "get_document", "get_chunk"]
REGISTERED_RESOURCES = ["documents://all", "documents://{document_id}"]
