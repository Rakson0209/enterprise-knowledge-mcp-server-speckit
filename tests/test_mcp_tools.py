"""MCP tool tests via the FastMCP in-memory client (US1 search + US3 catalogue)."""

from __future__ import annotations

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

import app.mcp_server as m
from tests._fakes import FakeRetriever, FakeStore, sample_chunks


@pytest.fixture
def patched(monkeypatch):
    chunks = sample_chunks()
    monkeypatch.setattr(m, "get_retriever", lambda: FakeRetriever(chunks))
    monkeypatch.setattr(m, "get_vector_store", lambda: FakeStore(chunks))
    return chunks


async def test_search_documents_returns_content_metadata_score(patched):
    async with Client(m.mcp) as c:
        res = await c.call_tool("search_documents", {"query": "yield", "top_k": 2})
    data = res.data
    assert len(data) == 2
    top = data[0]
    assert top["chunk"]["chunk_id"] == "report-0000"
    assert top["chunk"]["page_number"] == 1
    assert "score" in top and "rank" in top and top["rank"] == 1


async def test_search_documents_empty_query_errors(patched):
    async with Client(m.mcp) as c:
        with pytest.raises(ToolError):
            await c.call_tool("search_documents", {"query": "   ", "top_k": 3})


async def test_list_documents(patched):
    async with Client(m.mcp) as c:
        res = await c.call_tool("list_documents", {})
    data = res.data
    assert len(data) == 1
    assert data[0]["document_id"] == "report"
    assert data[0]["num_chunks"] == 2


async def test_get_document(patched):
    async with Client(m.mcp) as c:
        res = await c.call_tool("get_document", {"document_id": "report"})
    assert res.data["num_chunks"] == 2
    assert res.data["page_range"] == [1, 2]


async def test_get_document_not_found(patched):
    async with Client(m.mcp) as c:
        res = await c.call_tool("get_document", {"document_id": "nope"})
    assert res.data["error"] == "not_found"


async def test_get_chunk(patched):
    async with Client(m.mcp) as c:
        res = await c.call_tool("get_chunk", {"chunk_id": "report-0001"})
    assert res.data["chunk_type"] == "table"
    assert "| KPI | Value |" in res.data["content"]


async def test_get_chunk_not_found(patched):
    async with Client(m.mcp) as c:
        res = await c.call_tool("get_chunk", {"chunk_id": "missing"})
    assert res.data["error"] == "not_found"
