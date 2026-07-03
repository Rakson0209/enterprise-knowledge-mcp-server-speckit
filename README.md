# Enterprise Knowledge MCP Server

A production-ready enterprise document knowledge base. It ingests unstructured documents
(**DOCX / PDF / PPTX**), parses them with structure and provenance preserved, cleans boilerplate,
chunks along semantic boundaries with a complete metadata schema, indexes them for **hybrid
retrieval** (dense + sparse), and exposes the corpus to AI agents as a **Remote MCP Server**
co-hosted with a REST API. The same parse → clean → chunk core is also packaged as a reusable
**Claude Skill** for single-file preprocessing.

> Built end-to-end with an **AI-only workflow** (Claude Code) using Spec Kit
> (constitution → spec → plan → tasks → implement), with a semantic commit history.

## Architecture

```text
DOCX / PDF / PPTX
      │  Docling parse (+ RapidOCR for image text) → structure + page/slide provenance
      ▼
   Clean (remove repeated headers/footers, page-number lines, symbol noise; keep structure)
      ▼
   Metadata-aware chunk (semantic boundaries; each table/figure standalone; no fixed-size splits)
      ▼
   Hybrid index — BGE-M3 dense vectors (Chroma) + BM25 sparse, fused by Reciprocal Rank Fusion
      ▼
   Remote MCP Server (FastMCP) + REST API  →  Claude Desktop / Claude Code / any agent
```

Module layout: [`app/`](app/) — `services/` (parser, cleaner, chunker, embedder, vector_store,
retriever, pipeline), `mcp_server.py` (tools/resources), `api/documents.py` (REST), `main.py`
(FastAPI factory co-hosting `/mcp`).

## Tech stack & why

| Concern | Choice | Why |
|---------|--------|-----|
| Parsing | Docling (+RapidOCR) | Structure + page/slide provenance; recovers image text (not flat OCR) |
| Dense | BGE-M3 (sentence-transformers) | Multilingual (CN/EN), 1024-dim, L2-normalized |
| Sparse | BM25 (rank-bm25) | Exact/rare terms & identifiers embeddings miss |
| Fusion | Reciprocal Rank Fusion (k=60) | Rank-based; no score-scale tuning |
| Vector store | Chroma (embedded, persistent) | No separate service; survives restart |
| Web + MCP | FastAPI + FastMCP (one ASGI app) | REST + Remote MCP in one process; upload instantly searchable |
| Deploy | Docker → Zeabur (Arm Ampere A1, CPU-only) | Public HTTPS + persistent volume |
| Tests | Pytest (+ FastMCP in-memory client) | Layered incl. real MCP protocol |

## MCP interface

Connect an MCP client to the `/mcp` endpoint. Four tools + two resources:

| Type | Name | Purpose |
|------|------|---------|
| Tool | `search_documents(query, top_k)` | Hybrid-retrieve relevant chunks (content + metadata + score) |
| Tool | `list_documents()` | Catalogue of indexed documents |
| Tool | `get_document(document_id)` | Document summary (chunk count, page/slide range) |
| Tool | `get_chunk(chunk_id)` | Full content + metadata of one chunk |
| Resource | `documents://all` | The full catalogue |
| Resource | `documents://{document_id}` | A document and all its chunks |

Example queries: `What is the yield improvement plan?` · `Show me the KPI table from the Q4
report.` · `Summarize slide 5.`

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Landing page (dynamic MCP tool/resource listing) |
| `/health` | Liveness check |
| `/mcp` | Remote MCP endpoint (Claude Desktop / Claude Code) |
| `/docs` | REST API docs (Swagger UI) |
| `POST /documents` | Upload a document (auto-indexed, no restart) |
| `GET /documents` | Catalogue of indexed documents |

## Run

```bash
# Native (Python 3.11+)
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload            # http://localhost:8000

# Docker (CPU-only; container listens on $PORT, default 8080)
docker compose up --build                          # http://localhost:8080
```

Add a document (upload = auto-index, no restart):

```bash
curl -X POST http://localhost:8000/documents -F "file=@/path/to/report.pdf"
# -> 201 {"document_id":"report","status":"indexed","num_chunks":42}
```

## Reusable preprocessing Skill

The parse → clean → chunk core is packaged as the
[`document-preprocessing`](.claude/skills/document-preprocessing/) Claude Skill — a thin wrapper
that reuses the same `app/services` logic (single source of truth), so its output equals what the
knowledge base indexes. No server, no vector DB, no network.

```bash
python .claude/skills/document-preprocessing/scripts/preprocess.py "report.pdf" --stage all --out skill_output
```

See the Skill's [SKILL.md](.claude/skills/document-preprocessing/SKILL.md) and
[OUTPUT_SCHEMA.md](.claude/skills/document-preprocessing/reference/OUTPUT_SCHEMA.md).

## Tests & MCP verification

```bash
python -m pytest -q                                # all layers
python -m pytest tests/test_mcp_integration.py -v  # real JSON-RPC MCP protocol
python -m pytest tests/test_skill_preprocess.py -v # Skill CLI end-to-end
```

Layers: unit (cleaner/chunker/parser), index/retrieval (Chroma + RRF + CJK tokenizer), MCP direct
+ protocol (FastMCP in-memory client), REST (upload/health), and Skill CLI.

End-to-end MCP demo against a running server (produces inspectable tool-call logs):

```bash
# Terminal 1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# Terminal 2
python tests/mcp_client_demo.py "yield improvement plan"
```

The server logs each invocation, e.g.:

```text
INFO:app.mcp_server:MCP tool invoked: search_documents | query='...' top_k=3
INFO:app.mcp_server:search_documents retrieved 3 chunk(s): [...]
```

## Deployment (Zeabur)

Zeabur auto-detects the [`Dockerfile`](Dockerfile) and builds for `linux/arm64` (Arm Ampere A1,
no GPU — all inference CPU-only). Mount a **volume at `/data`** so the Chroma index, uploads, and
model cache persist across restart/redeploy. Configuration is via `KB_`-prefixed environment
variables (see [`app/config.py`](app/config.py)).

## Configuration

| Env var | Default | Meaning |
|---------|---------|---------|
| `KB_EMBEDDING_MODEL` | `BAAI/bge-m3` | Dense embedding model |
| `KB_CHUNK_MAX_CHARS` | `1200` | Soft chunk limit (split only at element boundaries) |
| `KB_HEADER_FOOTER_MIN_REPEATS` | `2` | Repetition threshold for boilerplate removal |
| `KB_RRF_K` | `60` | Reciprocal Rank Fusion constant |
| `KB_TOP_K_DEFAULT` | `5` | Default search result count |
| `KB_MAX_UPLOAD_MB` | `50` | Upload size limit |
| `KB_DATA_DIR` | `./data` (`/data` in Docker) | Persistence root |
| `KB_ENABLE_OCR` | `true` | Image text recovery (RapidOCR) |

## AI-only workflow

Developed entirely through Claude Code following a fixed cadence per step: **plan → implement →
code review → test**, one step per semantic commit (no single "final version" commit). The
project constitution ([`.specify/memory/constitution.md`](.specify/memory/constitution.md))
encodes the non-negotiable principles (structure-preserving ingestion; metadata-complete semantic
chunking; hybrid retrieval; MCP-first contract; single-source-of-truth reuse; test-first
verification; bounded execution; ARM64 CPU-only deployment). Spec, plan, and tasks live under
[`specs/001-enterprise-knowledge-mcp/`](specs/001-enterprise-knowledge-mcp/).
