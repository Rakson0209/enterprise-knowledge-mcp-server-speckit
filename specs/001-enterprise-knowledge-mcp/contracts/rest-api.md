# Contract: REST API

FastAPI routes co-hosted with the MCP server in one ASGI app. Shares the same singletons as MCP,
so an uploaded document is immediately searchable via `search_documents` with no restart (FR-012).

## `POST /documents` — upload & auto-index

Multipart form upload of one document.

- **Input**: `file` (multipart) — a `.docx`, `.pdf`, or `.pptx` file.
- **Behavior**: runs the full pipeline in-process (parse → clean → chunk → embed → Chroma upsert),
  then refreshes the BM25 corpus. Heavy sync work runs in a thread pool so the event loop stays
  responsive (FR-014).
- **Success**: `201` `{ "document_id": "...", "status": "indexed", "num_chunks": N }`.
- **Errors**:
  - `415` unsupported file type (extension not in allowlist) (FR-013).
  - `413` file exceeds `max_upload_mb` (FR-013).
  - `400` unreadable/corrupt document → structured error.

## `GET /documents` — catalogue

- **Output**: `200` list of document summaries (same shape as MCP `list_documents`).

## `GET /health` — liveness

- **Output**: `200` `{ "status": "ok" }` (FR-019). No heavy work; safe as a liveness probe.

## `GET /` — landing page

- **Output**: `200` HTML page introducing the project and **dynamically** listing the currently
  registered MCP tools and resources (FR-019).

## `GET /docs` — API documentation

- **Output**: Swagger UI for the REST surface (provided by FastAPI).

## `GET /mcp` — Remote MCP endpoint

- The mounted MCP ASGI app (see [mcp-tools.md](./mcp-tools.md)); target for Claude Desktop /
  Claude Code clients.
