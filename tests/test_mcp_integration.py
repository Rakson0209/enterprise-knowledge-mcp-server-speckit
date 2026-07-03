"""MCP protocol conformance (US1/US3) over the FastMCP in-memory JSON-RPC client.

Verifies discovery (exactly 4 tools + 2 resources), input schema, and structured output.
"""

from __future__ import annotations

import pytest
from fastmcp import Client

import app.mcp_server as m
from tests._fakes import FakeRetriever, FakeStore, sample_chunks


@pytest.fixture
def patched(monkeypatch):
    chunks = sample_chunks()
    monkeypatch.setattr(m, "get_retriever", lambda: FakeRetriever(chunks))
    monkeypatch.setattr(m, "get_vector_store", lambda: FakeStore(chunks))
    return chunks


async def test_discovery_exact_surface(patched):
    async with Client(m.mcp) as c:
        tools = {t.name for t in await c.list_tools()}
        resources = {str(r.uri) for r in await c.list_resources()}
        templates = {t.uriTemplate for t in await c.list_resource_templates()}

    assert tools == {"search_documents", "list_documents", "get_document", "get_chunk"}
    assert resources == {"documents://all"}
    assert templates == {"documents://{document_id}"}


async def test_search_input_schema(patched):
    async with Client(m.mcp) as c:
        tools = {t.name: t for t in await c.list_tools()}
    schema = tools["search_documents"].inputSchema
    props = schema["properties"]
    assert "query" in props and "top_k" in props
    assert "query" in schema.get("required", [])


async def test_structured_output_over_protocol(patched):
    async with Client(m.mcp) as c:
        res = await c.call_tool("search_documents", {"query": "yield", "top_k": 1})
    # structured, typed output (not an opaque string)
    assert isinstance(res.data, list)
    assert res.data[0]["chunk"]["document_id"] == "report"
