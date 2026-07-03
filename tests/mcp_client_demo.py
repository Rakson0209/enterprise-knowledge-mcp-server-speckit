"""End-to-end MCP client demo (FR-022): drive a running server over the real MCP protocol.

Usage:
    # Terminal 1 - start the server
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

    # Terminal 2 - run a query through the deployed /mcp endpoint
    python tests/mcp_client_demo.py "yield improvement plan"

The server console will show inspectable tool-invocation logs, e.g.:
    INFO:app.mcp_server:MCP tool invoked: search_documents | query='...' top_k=3
    INFO:app.mcp_server:search_documents retrieved 3 chunk(s): [...]
"""

from __future__ import annotations

import asyncio
import sys

from fastmcp import Client

DEFAULT_URL = "http://127.0.0.1:8000/mcp"


async def run(query: str, url: str, top_k: int = 3) -> None:
    async with Client(url) as client:
        tools = [t.name for t in await client.list_tools()]
        print(f"Connected. Tools: {sorted(tools)}")

        result = await client.call_tool("search_documents", {"query": query, "top_k": top_k})
        for item in result.data:
            chunk = item["chunk"]
            loc = (
                f"page {chunk['page_number']}"
                if chunk.get("page_number") is not None
                else f"slide {chunk['slide_number']}"
            )
            print(f"\n[{item['rank']}] score={item['score']:.4f} "
                  f"{chunk['filename']} ({loc}) — {chunk['chunk_id']}")
            print(f"    {chunk['content'][:200]}")


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "yield improvement plan"
    url = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_URL
    asyncio.run(run(query, url))


if __name__ == "__main__":
    main()
