---
description: "Task list for Enterprise Knowledge MCP Server & Preprocessing Skill"
---

# Tasks: Enterprise Knowledge MCP Server & Preprocessing Skill

**Input**: Design documents from `/specs/001-enterprise-knowledge-mcp/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md

**Tests**: INCLUDED — the Constitution (Principle VI: Test-First & Multi-Layer Verification) and
spec (FR-022, SC-007) mandate layered automated tests. Write each test before its implementation
and confirm it fails first (Red → Green).

**Organization**: Tasks are grouped by user story (US1–US4) for independent implementation and
testing. Each story maps to semantic commits per the constitution's commit discipline.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: US1–US4 for user-story phases; Setup/Foundational/Polish carry no story label
- All paths are repository-relative.

## Path Conventions

Single project: application code in `app/`, Skill in `.claude/skills/document-preprocessing/`,
tests in `tests/`. Layout per [plan.md](./plan.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, config, shared models. (PDF Step 1: `chore: initialize project`)

- [X] T001 Create project structure per plan.md (`app/`, `app/services/`, `app/api/`, `tests/`, `.claude/skills/document-preprocessing/`)
- [X] T002 Author `pyproject.toml` with dependencies (fastapi, uvicorn, fastmcp, docling, rapidocr-onnxruntime, sentence-transformers, rank-bm25, chromadb, pydantic, pydantic-settings) and `[dev]` extras (pytest); pin **CPU** torch wheels and document ARM64/aarch64 constraint (no CUDA)
- [X] T003 [P] Implement `app/config.py` (pydantic-settings): `embedding_model`, `chunk_max_chars=1200`, `header_footer_min_repeats=2`, `rrf_k=60`, `top_k_default`, `max_upload_mb=50`, `data_dir=/data`, `enable_ocr`, all env-overridable
- [X] T004 [P] Implement `app/models.py` Pydantic entities from data-model.md: `ParsedElement`, `ParsedDocument`, `Chunk` (8-field contract), `Document`, `SearchResult`
- [X] T005 [P] Configure pytest, linting/formatting, and `tests/conftest.py` with sample DOCX/PDF/PPTX fixtures

**Checkpoint**: Project installs (`pip install -e ".[dev]"`); config and models importable.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared parse→clean→chunk→index core plus the app skeleton that EVERY user story depends on.

**⚠️ CRITICAL**: No user story can be completed until this phase is done. (PDF Steps 3–6)

### Tests for Foundational (write first, ensure they fail) ⚠️

- [X] T006 [P] Unit tests `tests/test_parser.py` + `tests/test_parser_pptx.py`: structure preserved, page/slide provenance, RapidOCR figure text, ordered elements
- [X] T007 [P] Unit tests `tests/test_cleaner.py`: repeated header/footer removal (≥2), page-number-only lines, pure-symbol paragraphs removed; titles/tables/figures/page numbers preserved
- [X] T008 [P] Unit tests `tests/test_chunker.py`: semantic-boundary splits only, table/figure standalone chunks, full 8-field metadata, reproducible `<document_id>-<seq>` ids, no fixed-size splitting, page/slide change starts new chunk (SC-001, SC-002)
- [X] T009 [P] Index test `tests/test_index.py`: Chroma upsert + dense query + document aggregation

### Implementation for Foundational

- [X] T010 [P] Implement `app/services/parser.py`: Docling parse for DOCX/PDF/PPTX + RapidOCR image text → `ParsedDocument` with page/slide provenance
- [X] T011 [P] Implement `app/services/cleaner.py`: normalize whitespace; strip repeated header/footer, page-number lines, symbol-only paragraphs; preserve structure/titles/tables/figures
- [X] T012 Implement `app/services/chunker.py`: metadata-aware semantic-boundary chunking; each table/figure its own chunk; split only between whole elements when over `chunk_max_chars`; continuation chunks reuse `section_title` (depends on T004, T010, T011)
- [X] T013 [P] Implement `app/services/embedder.py`: BGE-M3 dense vectors, lazy-loaded, L2-normalized, CPU-only
- [X] T014 Implement `app/services/vector_store.py`: Chroma embedded/persistent (`data_dir`) — upsert, dense search, document aggregation; `get_vector_store()` singleton (depends on T013)
- [X] T015 Implement `app/services/pipeline.py`: orchestrate parse→clean→chunk→embed→upsert; reusable by upload endpoint and Skill (depends on T010–T014)
- [X] T016 Implement `app/main.py`: FastAPI app factory, shared lifespan, singletons; mount FastMCP ASGI app at `/mcp`; heavy sync work via thread pool
- [X] T017 Implement `app/mcp_server.py` skeleton: FastMCP instance, tool-invocation logging setup, registered with the app (tools added in later phases)
- [X] T018 Implement `GET /health` in `app/main.py` returning `{status:"ok"}` and a minimal landing page placeholder at `GET /`

**Checkpoint**: A document can be parsed→cleaned→chunked→indexed programmatically; foundational tests pass; server boots with `/health` and `/mcp` mounted.

---

## Phase 3: User Story 1 — Query enterprise knowledge with citations (Priority: P1) 🎯 MVP

**Goal**: Agents query the indexed corpus and receive relevant, cited passages via MCP hybrid search. (PDF Steps 7–8, 10)

**Independent Test**: With a seeded corpus, `search_documents` returns relevant chunks with full citation metadata + score for paraphrased, exact-term, and mixed CN/EN queries; invocation is logged.

### Tests for User Story 1 (write first) ⚠️

- [X] T019 [P] [US1] `tests/test_retriever.py`: dense+BM25 candidates, RRF fusion (k=60), CJK+Latin tokenizer, exact-term recall, BM25 refresh from Chroma
- [X] T020 [P] [US1] `tests/test_mcp_tools.py` (search portion): `search_documents` output shape (content+metadata+score), empty-query error, empty-index empty list
- [X] T021 [P] [US1] `tests/test_mcp_integration.py` (search): FastMCP in-memory JSON-RPC — discovery, input schema, structured output for `search_documents`

### Implementation for User Story 1

- [X] T022 [US1] Implement `app/services/retriever.py`: hybrid dense+BM25 with RRF fusion, CJK+Latin tokenizer, BM25 corpus rebuilt from Chroma, `refresh()`, `get_retriever()` singleton (depends on T014)
- [X] T023 [US1] Add `search_documents(query, top_k)` tool to `app/mcp_server.py`: returns `SearchResult` list, logs `MCP tool invoked: search_documents | query=... top_k=...` and retrieved chunk ids (FR-011)
- [X] T024 [P] [US1] Add `tests/mcp_client_demo.py`: runnable client against a live server producing inspectable tool-call logs (FR-022)

**Checkpoint**: US1 works independently — seeded corpus is searchable via MCP with citations and logs. **This is the MVP.**

---

## Phase 4: User Story 2 — Self-service document ingestion (Priority: P2)

**Goal**: Upload a document to the running service and have it searchable immediately, no restart. (PDF Step 2 + auto-index add-on)

**Independent Test**: `POST /documents` a DOCX/PDF/PPTX → `201` with `num_chunks`; a subsequent search finds its content without restart; unsupported/oversized files rejected.

### Tests for User Story 2 (write first) ⚠️

- [X] T025 [P] [US2] `tests/test_upload.py`: type validation (415), size limit (413), successful upload→index (201 + num_chunks), upload-then-search visibility with no restart, thread-pool non-blocking
- [X] T026 [P] [US2] `tests/test_health.py`: `/health` liveness

### Implementation for User Story 2

- [X] T027 [US2] Implement `app/api/documents.py` `POST /documents`: multipart upload, extension allowlist + size check, run `pipeline` in a thread pool, refresh retriever BM25, return `{document_id,status,num_chunks}` (depends on T015, T022)
- [X] T028 [US2] Wire the router into `app/main.py` and ensure shared singletons make new docs instantly visible to MCP search (FR-012)

**Checkpoint**: US1 + US2 both work — live upload feeds the same index MCP search reads.

---

## Phase 5: User Story 3 — Inspect catalogue and retrieve specific items (Priority: P3)

**Goal**: List indexed documents, inspect a document summary, and fetch a single chunk; browsable resources. (PDF Step 9)

**Independent Test**: `list_documents`/`documents://all` enumerate the corpus; `get_document` returns summary with page/slide range; `get_chunk` returns full content+metadata; unknown ids → structured not-found.

### Tests for User Story 3 (write first) ⚠️

- [X] T029 [P] [US3] `tests/test_mcp_tools.py` (catalogue portion): `list_documents`, `get_document`, `get_chunk` output shapes + not-found handling
- [X] T030 [P] [US3] `tests/test_mcp_resources.py`: `documents://all` and `documents://{document_id}` resource contents + unknown-id handling
- [X] T031 [P] [US3] `tests/test_mcp_integration.py` (resources): resource URI resolution incl. templated form over JSON-RPC

### Implementation for User Story 3

- [X] T032 [US3] Add `list_documents()`, `get_document(document_id)`, `get_chunk(chunk_id)` tools to `app/mcp_server.py` (depends on T014, T017)
- [X] T033 [US3] Add resources `documents://all` and `documents://{document_id}` (with all chunks) to `app/mcp_server.py`
- [X] T034 [P] [US3] Add `GET /documents` catalogue endpoint in `app/api/documents.py`
- [X] T035 [US3] Implement dynamic landing page in `app/landing.py` listing currently registered MCP tools/resources; wire into `GET /` (FR-019)

**Checkpoint**: US1 + US2 + US3 work — full agent navigation surface complete.

---

## Phase 6: User Story 4 — Reusable single-file preprocessing Skill (Priority: P4)

**Goal**: Standalone CLI turns one document into index-ready output, reusing the same core, no server/index/network. (PDF Task 2: `feat: package preprocessing pipeline as document-preprocessing claude skill`)

**Independent Test**: CLI runs full pipeline and stages; chunks match the knowledge base's chunks for the same file (SC-005); rejects bad input with single-line error + exit codes; writes only inside `--out`.

### Tests for User Story 4 (write first) ⚠️

- [X] T036 [P] [US4] `tests/test_skill_preprocess.py`: all-stage artifacts, cleaning removes boilerplate/page numbers, chunk metadata complete, custom `--doc-id` prefix, reject unsupported ext / missing / oversized, `--format json` skips markdown, output-dir confinement (SC-005, SC-008)

### Implementation for User Story 4

- [X] T037 [US4] Implement `.claude/skills/document-preprocessing/scripts/preprocess.py`: argparse CLI (`--stage/--format/--out/--doc-id/--max-chars/--max-mb/--no-ocr/--stdout/--quiet`), project-root discovery (anchor `app/services/parser.py`), thin-wrap parser/cleaner/chunker, stdout(JSON)/stderr(logs) split, UTF-8, safety boundaries, single-line `error:` + exit codes 0/1/2 (depends on T010–T012)
- [X] T038 [P] [US4] Write `.claude/skills/document-preprocessing/SKILL.md` with name/description frontmatter for agent auto-discovery
- [X] T039 [P] [US4] Write `.claude/skills/document-preprocessing/reference/OUTPUT_SCHEMA.md` documenting the JSON/metadata schema
- [X] T040 [US4] Generate `.claude/skills/document-preprocessing/examples/RUN_LOG.md` from a real document run proving Skill/index chunk-count parity

**Checkpoint**: All four stories independently functional; Skill output equals indexed output.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Deployment, docs, and final verification across all stories.

- [X] T041 [P] Author `Dockerfile` targeting `linux/arm64` (CPU-only base, pinned CPU torch), `.dockerignore`, and `docker-compose.yml` for local run
- [ ] T042 Verify all dependencies provide aarch64 wheels or build on ARM (torch CPU, onnxruntime, chromadb, tokenizers, Docling native deps); adjust pins as needed (research.md D8 risk watch)
- [ ] T043 Configure Zeabur deployment with a volume mounted at `/data` (index, uploads, model cache); confirm public HTTPS URL, `/health`, `/`, `/docs`, `/mcp` reachable (FR-019, FR-020, SC-006)
- [X] T044 [P] Write `README.md`: AI-only workflow (plan/dev/review/test), example queries, MCP client connection, upload usage, local/Docker run, deploy URL
- [ ] T045 Run `quickstart.md` scenarios A–F end-to-end against local + deployed service; confirm restart persistence and CPU-only operation
- [X] T046 Run full `pytest -q`; ensure all layers green and add regression tests for any defects found

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately
- **Foundational (Phase 2)**: depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3–6)**: all depend on Foundational
  - US1 (P1) → US2 (P2) → US3 (P3) → US4 (P4) in priority order; US2/US3 share `app/mcp_server.py` and `app/api/documents.py` so coordinate edits
  - US4 depends only on the `app/services` core (T010–T012), so it can start right after Foundational if desired
- **Polish (Phase 7)**: depends on all targeted stories

### Story Independence

- **US1**: testable with a seeded corpus — the MVP slice
- **US2**: adds live ingestion on top of the same index US1 reads
- **US3**: adds catalogue/drill-down tools + resources; independent of US2
- **US4**: reuses the core independently of the running server

### Within Each Story

- Tests written first and failing → implementation → integration
- Services before endpoints/tools; models (Phase 1) before services

---

## Parallel Execution Examples

```text
# Phase 1 setup (after T001/T002):
T003 config.py | T004 models.py | T005 pytest+fixtures

# Phase 2 foundational tests together:
T006 test_parser | T007 test_cleaner | T008 test_chunker | T009 test_index
# Phase 2 independent implementations:
T010 parser | T011 cleaner | T013 embedder   (T012 chunker after T010/T011; T014 after T013)

# Phase 3 (US1) tests together:
T019 test_retriever | T020 test_mcp_tools(search) | T021 test_mcp_integration(search)
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup → 2. Phase 2 Foundational (CRITICAL) → 3. Phase 3 US1 → **STOP & VALIDATE**:
   seed a corpus and confirm MCP search returns cited results with logs. Deploy/demo if ready.

### Incremental Delivery

1. Setup + Foundational → core ready
2. US1 → MVP (query with citations)
3. US2 → live upload/auto-index
4. US3 → catalogue + resources
5. US4 → reusable Skill
6. Polish → deploy to Zeabur (ARM64) + README + full verification

Each story is a semantic commit increment per the constitution's commit discipline.

---

## Notes

- [P] = different files, no incomplete dependencies
- Tests are mandated by the constitution — write them first and confirm they fail
- Commit after each task or logical group with a semantic message (no "final version" squash)
- Constitution NON-NEGOTIABLES enforced by T008 (semantic chunking + metadata), T019/T022 (hybrid+RRF), T023/T032/T033 (exact 4 tools + 2 resources), T037 (thin-wrapper reuse + safety), T041–T043 (ARM64 CPU-only deploy)
