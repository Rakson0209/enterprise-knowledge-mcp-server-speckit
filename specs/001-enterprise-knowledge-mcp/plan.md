# Implementation Plan: Enterprise Knowledge MCP Server & Preprocessing Skill

**Branch**: `001-enterprise-knowledge-mcp` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-enterprise-knowledge-mcp/spec.md`

## Summary

Build a production-ready enterprise document knowledge base that ingests DOCX/PDF/PPTX,
parses them with structure and provenance preserved, cleans boilerplate, chunks along semantic
boundaries with a complete metadata schema, indexes for hybrid (dense + sparse) retrieval, and
exposes the corpus to AI agents as a Remote MCP Server co-hosted with a REST upload API in a
single service. The same parse → clean → chunk core is repackaged as a standalone Claude Skill
(thin CLI wrapper) so a single document can be preprocessed locally without the server or index.
Technical approach: FastAPI + FastMCP in one ASGI app; Docling (+RapidOCR) parsing; BGE-M3 dense
vectors in embedded Chroma; rank-bm25 sparse; Reciprocal Rank Fusion; deployed via a single
`linux/arm64` Dockerfile to Zeabur (Arm Ampere A1, CPU-only) with a persistent volume.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI (ASGI web), FastMCP (Remote MCP over streamable HTTP),
Docling (structure-aware parsing), RapidOCR (image text recovery), sentence-transformers +
BGE-M3 (dense embeddings, 1024-dim, L2-normalized), rank-bm25 (sparse), Chroma (embedded,
persistent vector store), pydantic / pydantic-settings (models + config), uvicorn (server)

**Storage**: Embedded Chroma persisted to a mounted volume (`/data`) — holds dense vectors +
chunk documents + metadata; BM25 corpus rebuilt in-memory from the Chroma collection (single
source of truth). Uploaded files and model cache also persisted on the volume.

**Testing**: Pytest — unit, index/retrieval, MCP direct-call, MCP protocol (FastMCP in-memory
JSON-RPC client), REST, and Skill CLI end-to-end. Plus a runnable MCP client demo against a live
server.

**Target Platform**: Zeabur **Arm Ampere A1 Compute** — `linux/arm64` (aarch64), **no GPU**.
All inference CPU-only. Local dev may be any OS (Windows/macOS/Linux); container built for arm64.

**Project Type**: Single web service (REST + MCP co-hosted) with a bundled CLI Skill — single
project layout.

**Performance Goals**: Interactive agent search latency (target < ~2 s per query on a warm,
CPU-only node for a small/medium corpus); upload-to-searchable with no restart; server stays
responsive during ingestion (heavy sync work offloaded to a thread pool).

**Constraints**: CPU-only ARM64 (no CUDA); every dependency must ship an aarch64 wheel or build
cleanly on ARM; lazy model loading; default batch sizes/model choices within the node's CPU/RAM
envelope; input ≤ ~50 MB; soft chunk limit ~1200 chars; header/footer repetition threshold ≥ 2.

**Scale/Scope**: Single-service, single-tenant knowledge base; embedded (in-process) index, not a
distributed cluster. No agent auth in this version. Four MCP tools + two MCP resources; one REST
upload/catalogue surface; one Skill CLI.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution reference: `.specify/memory/constitution.md` v1.1.0.

| # | Principle | Plan compliance | Status |
|---|-----------|-----------------|--------|
| I | Structure-Preserving Ingestion | Docling parser recovers titles/tables/figures + page/slide provenance; RapidOCR recovers image text; no flat-OCR path | ✅ PASS |
| II | Metadata-Complete Semantic Chunking (NON-NEGOTIABLE) | Chunker splits on section/table/figure/page/slide only; each table/figure = own chunk; soft-limit split between whole elements; full 8-field schema incl. reproducible `<document_id>-<seq>` id | ✅ PASS |
| III | Hybrid Retrieval (Dense + Sparse + RRF) | BGE-M3 dense (Chroma) + rank-bm25 sparse fused by RRF (k=60); CJK+Latin tokenizer; BM25 rebuilt from Chroma; no FTS-only path | ✅ PASS |
| IV | MCP-First Interface Contract | FastMCP Remote MCP mounted at `/mcp` alongside REST in one ASGI app; exactly 4 tools + 2 resources; search returns content+metadata+score; upload indexes in-process (no restart) | ✅ PASS |
| V | Single Source of Truth (Thin-Wrapper Reuse / DRY) | parser/cleaner/chunker live only in `app/services/`; Skill CLI imports them; no reimplementation; Skill output == indexed output | ✅ PASS |
| VI | Test-First & Multi-Layer Verification | Pytest across unit / index-retrieval / MCP-direct / MCP-protocol / REST / Skill; regression tests on fixes; live MCP client demo | ✅ PASS |
| VII | Bounded, Least-Privilege Execution | Skill: read-only input, extension allowlist, size cap, output-dir confinement + path-escape refusal, no DB writes, no network; single-line error + exit codes 0/1/2 | ✅ PASS |
| — | ARM64 CPU-only deployment constraint | CPU-only inference, arm64 wheels, `linux/arm64` image, lazy load + thread-pool offload, volume persistence | ✅ PASS |
| — | Tech stack / deployment / observability | Python 3.11 + FastAPI + Docling + BGE-M3 + rank-bm25 + Chroma + FastMCP + Pytest; single Dockerfile → public HTTPS on Zeabur; volume persistence; tool-invocation logging; health check; pydantic-settings config | ✅ PASS |
| — | Development workflow | AI-only workflow; one semantic commit per step; layered tests as quality gate | ✅ PASS |

**Initial gate: PASS** — no violations; Complexity Tracking not required.

**Post-design re-check (after Phase 1): PASS** — data model, contracts, and quickstart introduce
no deviations from the principles above. See Complexity Tracking (empty).

## Project Structure

### Documentation (this feature)

```text
specs/001-enterprise-knowledge-mcp/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── mcp-tools.md         # 4 MCP tools + 2 MCP resources (JSON-RPC surface)
│   ├── rest-api.md          # REST upload/catalogue/health endpoints
│   └── skill-cli.md         # document-preprocessing CLI contract
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
app/
├── main.py                 # FastAPI app factory; mounts REST routes + /mcp ASGI app; shared lifespan
├── config.py               # pydantic-settings: models, chunk size, retrieval params, limits (env-overridable)
├── models.py               # Pydantic: Document, ParsedElement, Chunk, SearchResult, ...
├── landing.py              # Landing page: dynamically lists registered MCP tools/resources
├── mcp_server.py           # FastMCP: 4 tools + 2 resources; logs each tool invocation
├── services/
│   ├── parser.py           # Docling + RapidOCR → ParsedDocument (flat, ordered, page/slide provenance)
│   ├── cleaner.py          # Normalize whitespace; strip repeated header/footer, page-number lines, symbol noise
│   ├── chunker.py          # Metadata-aware, semantic-boundary chunking (no fixed-size splits)
│   ├── embedder.py         # BGE-M3 dense vectors (lazy load, L2-normalized)
│   ├── vector_store.py     # Chroma persistence: upsert / dense search / document aggregation
│   ├── retriever.py        # Hybrid dense + BM25, RRF fusion, CJK+Latin tokenizer
│   └── pipeline.py         # Orchestrates parse→clean→chunk→index; shared by upload endpoint & Skill
└── api/
    └── documents.py        # REST: upload (auto-index) + catalogue query

.claude/skills/document-preprocessing/
├── SKILL.md                # Skill description + trigger frontmatter (name/description)
├── scripts/preprocess.py   # Thin-wrapper CLI over app/services parser/cleaner/chunker
├── reference/OUTPUT_SCHEMA.md
└── examples/RUN_LOG.md     # Real execution record (verification evidence)

tests/
├── test_parser.py / test_parser_pptx.py
├── test_cleaner.py
├── test_chunker.py
├── test_index.py
├── test_retriever.py
├── test_mcp_tools.py
├── test_mcp_resources.py
├── test_mcp_integration.py     # FastMCP in-memory client, real JSON-RPC
├── test_upload.py
├── test_health.py
├── test_skill_preprocess.py
└── mcp_client_demo.py          # Runnable demo against a live server

Dockerfile                  # linux/arm64 build
docker-compose.yml          # Local run
pyproject.toml              # Deps + optional [dev]; project install
README.md                   # AI workflow, usage, example queries, deploy URL
```

**Structure Decision**: Single project (web service + bundled CLI Skill). One FastAPI ASGI app
co-hosts REST and the MCP server, sharing a single lifespan and singletons
(`get_vector_store()` / `get_retriever()`) so uploads are instantly visible to MCP search. The
Skill lives under `.claude/skills/` and imports the same `app/services` core — no duplication.

## Complexity Tracking

> No Constitution Check violations. No entries required.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
