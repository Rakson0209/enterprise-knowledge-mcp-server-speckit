"""FastAPI application factory.

Co-hosts the REST API and the FastMCP Remote MCP server in one ASGI app, sharing a single
lifespan and the same service singletons — so an uploaded document is immediately visible to MCP
search with no restart (constitution Principle IV).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.documents import router as documents_router
from app.landing import render_landing_page
from app.mcp_server import mcp

logging.basicConfig(
    level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s"
)


def create_app() -> FastAPI:
    # FastMCP streamable-HTTP ASGI app; its lifespan starts the MCP session manager and must be
    # propagated to the parent FastAPI app.
    mcp_app = mcp.http_app(path="/")

    app = FastAPI(
        title="Enterprise Knowledge MCP Server",
        version="0.1.0",
        lifespan=mcp_app.lifespan,
    )

    app.include_router(documents_router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def landing() -> str:
        return render_landing_page()

    # Mount the Remote MCP endpoint at /mcp.
    app.mount("/mcp", mcp_app)

    return app


app = create_app()
