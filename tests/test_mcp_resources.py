"""MCP resource tests (US3): documents://all and documents://{document_id}."""

from __future__ import annotations

import json

import pytest
from fastmcp import Client

import app.mcp_server as m
from tests._fakes import FakeStore, sample_chunks


@pytest.fixture
def patched(monkeypatch):
    chunks = sample_chunks()
    monkeypatch.setattr(m, "get_vector_store", lambda: FakeStore(chunks))
    return chunks


def _payload(result):
    # read_resource returns a list of contents; take the first text block and parse JSON.
    block = result[0]
    text = getattr(block, "text", None)
    return json.loads(text) if text is not None else block


async def test_documents_all(patched):
    async with Client(m.mcp) as c:
        result = await c.read_resource("documents://all")
    data = _payload(result)
    assert isinstance(data, list) and data[0]["document_id"] == "report"


async def test_documents_one_includes_chunks(patched):
    async with Client(m.mcp) as c:
        result = await c.read_resource("documents://report")
    data = _payload(result)
    assert data["document"]["document_id"] == "report"
    assert len(data["chunks"]) == 2
    assert {ch["chunk_id"] for ch in data["chunks"]} == {"report-0000", "report-0001"}


async def test_documents_one_not_found(patched):
    async with Client(m.mcp) as c:
        result = await c.read_resource("documents://nope")
    data = _payload(result)
    assert data["error"] == "not_found"
