<!--
Sync Impact Report
==================
Version change: 1.0.0 → 1.1.0
Change type: MINOR (new deployment/runtime constraint added)

Modified principles: none
Added principles: none
Amended sections:
  - Additional Constraints & Standards → Deployment: added ARM64 / CPU-only
    (Zeabur Arm Ampere A1, no GPU) runtime target requirement.

Prior baseline (v1.0.0, initial ratification) added:
  - I. Structure-Preserving Ingestion
  - II. Metadata-Complete Semantic Chunking (NON-NEGOTIABLE)
  - III. Hybrid Retrieval (Dense + Sparse + RRF)
  - IV. MCP-First Interface Contract
  - V. Single Source of Truth (Thin-Wrapper Reuse / DRY)
  - VI. Test-First & Multi-Layer Verification
  - VII. Bounded, Least-Privilege Execution
  - Sections: Additional Constraints & Standards, Development Workflow, Governance

Templates requiring updates:
  - .specify/templates/plan-template.md ✅ compatible (dynamic Constitution Check gate; no edit required)
  - .specify/templates/spec-template.md ✅ compatible (no principle-specific sections needed)
  - .specify/templates/tasks-template.md ✅ compatible (test tasks + observability tasks supported)

Follow-up TODOs: none
-->

# Enterprise Knowledge MCP Server Constitution

## Core Principles

### I. Structure-Preserving Ingestion

Document ingestion MUST preserve source structure and provenance. Parsing MUST use a
structure-aware parser (Docling) that recovers titles, tables, figures, and per-element
page numbers (PDF/DOCX) or slide numbers (PPTX). Embedded images in PPTX/DOCX MUST be
OCR-recovered (RapidOCR) so figure-borne text is not lost. Reducing a document to a flat
OCR text stream that discards headings, tables, or page/slide origin is PROHIBITED.

Rationale: Downstream chunking and retrieval quality depend entirely on retaining semantic
boundaries and provenance; structure lost at parse time cannot be reconstructed later.

### II. Metadata-Complete Semantic Chunking (NON-NEGOTIABLE)

Chunking MUST split along semantic boundaries (section / table / figure / page / slide),
NEVER by fixed character or token count that cuts across sentences, table rows, or
elements. Every table and every figure MUST become its own chunk. A chunk MAY be split only
when a section exceeds the configured soft limit (`chunk_max_chars`, default 1200), and only
between whole elements. Every chunk MUST carry the complete metadata schema:
`document_id`, `filename`, `page_number` (int|null), `slide_number` (int|null),
`chunk_id` (unique, reproducible: `<document_id>-<sequence>`), `chunk_type`
(text|table|figure), `content` (tables as Markdown), and `section_title` (str|null).
Any chunk missing a required field or produced by fixed-size splitting is a defect.

Rationale: Precise citations (page/slide/section) and reproducible chunk IDs are the
contract every consumer relies on; fixed-size splitting destroys retrievability and
traceability.

### III. Hybrid Retrieval (Dense + Sparse + RRF)

Retrieval MUST be hybrid: dense embeddings (BGE-M3, L2-normalized) combined with sparse
BM25, fused by Reciprocal Rank Fusion (RRF, k=60). Relying on SQLite FTS — or any single
retrieval method — as the final retrieval strategy is PROHIBITED. The tokenizer MUST retain
both Latin words and individual CJK characters so mixed Chinese/English content is reachable
by both methods. BM25 corpus MUST derive from the vector store as the single source of truth
and refresh immediately after new documents are indexed.

Rationale: Dense recall misses exact terms and rare identifiers; sparse lacks semantic
generalization. RRF fuses by rank, avoiding score-scale mismatch and manual weight tuning.

### IV. MCP-First Interface Contract

The knowledge base MUST be exposed as a Remote MCP Server via FastMCP (streamable HTTP
transport), mounted alongside the REST API in a single service. The MCP surface MUST provide
exactly these four tools — `search_documents(query, top_k)`, `list_documents()`,
`get_document(document_id)`, `get_chunk(chunk_id)` — and these two resources —
`documents://all` and `documents://{document_id}`. Search results MUST return chunk content
together with full metadata and scores. Uploading a document MUST index it in-process
(no restart) so it is immediately queryable via MCP.

Rationale: A stable, minimal tool/resource contract is what lets Claude Desktop and other
agents integrate reliably; the in-process index keeps the service simple and consistent.

### V. Single Source of Truth (Thin-Wrapper Reuse / DRY)

Parsing, cleaning, and chunking logic MUST live in one place (`app/services/`) and be reused
by every delivery form. The `document-preprocessing` Claude Skill MUST be a thin wrapper that
imports and calls the production `parser` / `cleaner` / `chunker` — it MUST NOT reimplement or
copy that logic. Any Skill or alternate entry point MUST produce chunks identical to those the
knowledge base indexes.

Rationale: One logic, multiple delivery forms. Duplicated preprocessing would silently drift
and break the guarantee that Skill output equals indexed output.

### VI. Test-First & Multi-Layer Verification

Every principle-bearing behavior MUST be covered by automated Pytest tests across the layers
it touches: unit (cleaning rules, semantic-boundary chunking, metadata completeness,
page/slide provenance), index/retrieval (Chroma upsert/query, RRF fusion, mixed-language
tokenizer), MCP direct-call and MCP protocol (FastMCP in-memory client over real JSON-RPC:
discovery, input schema, structured output, resource URIs), and REST. Bug fixes MUST add a
regression test. A verifiable end-to-end MCP client demo MUST exist and exercise a running
server through the real protocol.

Rationale: The metadata schema, retrieval contract, and MCP protocol are all machine
contracts; only layered tests — including real-protocol tests — prove they hold.

### VII. Bounded, Least-Privilege Execution

Local/Skill execution MUST enforce explicit safety boundaries: input files opened read-only
and never modified; only `.docx` / `.pdf` / `.pptx` accepted; inputs over the size limit
(default 50 MB) rejected; all writes confined to the declared output directory with path
escape refused; no database writes and no outbound network calls (model files cached locally
once by Docling/RapidOCR). On error, emit a single `error: ...` line and a non-zero exit code
(1 = input/IO, 2 = usage/validation) — never a raw traceback.

Rationale: A reusable preprocessing tool runs against untrusted files in untrusted
directories; predictable, least-privilege behavior is what makes it safe for agents and CI.

## Additional Constraints & Standards

- **Technology stack**: Python 3.11; FastAPI (async/ASGI) hosting both REST and the MCP ASGI
  app in one service; Docling + RapidOCR for parsing; BGE-M3 (sentence-transformers) for dense
  vectors; rank-bm25 for sparse; Chroma (embedded, persistent) as the vector store; FastMCP
  for the MCP server; Pytest for tests. Substituting a component that violates a Core Principle
  (e.g. FTS-only retrieval) is a governance change, not a routine choice.
- **Deployment**: The service MUST be deployable via a single Dockerfile and MUST be published
  at a reachable public `https://` URL (Zeabur/Railway/Render). Persistent state (index,
  uploads, model cache) MUST live on a mounted volume so it survives restart/redeploy.
- **Runtime target (ARM64, CPU-only)**: The production node is Zeabur **Arm Ampere A1 Compute**
  — `linux/arm64` (aarch64) with **no GPU**. Therefore: (a) all ML inference (BGE-M3 embeddings,
  RapidOCR, Docling) MUST run CPU-only — code MUST NOT assume CUDA/GPU and SHOULD pin
  CPU/`torch` CPU wheels; (b) every dependency MUST provide an ARM64/aarch64 wheel (or build
  cleanly on ARM) — dependencies that are x86-only or require a GPU are PROHIBITED; (c) the
  Docker image MUST build for `linux/arm64` (base image and multi-arch build reflect this);
  (d) because inference is CPU-bound and slower, models MUST be lazy-loaded, embeddings/OCR run
  in a thread pool off the async event loop, and default resource settings (batch sizes, model
  choice) MUST stay within the node's CPU/RAM envelope.
- **Observability**: MCP tool invocations MUST be logged with enough detail to verify behavior
  (tool name, query, retrieved chunk identifiers). A health-check endpoint MUST be provided.
- **Configuration**: Runtime settings (models, chunk size, retrieval parameters) MUST be
  centralized (pydantic-settings) and overridable via environment variables.

## Development Workflow

- **AI-only workflow**: Development is conducted through an AI agent (Claude Code) following a
  fixed cadence per step — plan (state goal, rationale, affected files, test approach, commit
  message) → implement → code review → test. The README MUST document the tools and agent
  workflow used (planning / development / code review / testing).
- **Semantic commit discipline**: One step maps to one semantic commit. Producing an entire
  system in a single commit, or collapsing history into a single "final version" commit, is
  PROHIBITED. Commit history MUST remain complete and semantically meaningful.
- **Quality gates**: A change MUST NOT merge unless its layer-appropriate tests pass, the
  metadata schema and MCP contract remain intact, and any deviation from a Core Principle is
  recorded in the plan's Complexity Tracking with justification and the rejected simpler
  alternative.

## Governance

This constitution supersedes other development practices for this project. All plans, reviews,
and merges MUST verify compliance with the Core Principles; unavoidable deviations MUST be
justified in the plan's Complexity Tracking table.

Amendments MUST be proposed with rationale, applied to this file, and version-bumped per
semantic versioning: MAJOR for backward-incompatible governance/principle removal or
redefinition; MINOR for a new principle or materially expanded guidance; PATCH for
clarifications and non-semantic refinements. On amendment, dependent templates
(`plan-template.md`, `spec-template.md`, `tasks-template.md`) and runtime guidance (README)
MUST be reviewed for consistency in the same change.

Compliance is reviewed at every plan approval and code review. The `/speckit-analyze` and
`/speckit-plan` Constitution Check gates are the enforcement points; a failing gate blocks
progression until resolved or explicitly justified.

**Version**: 1.1.0 | **Ratified**: 2026-07-03 | **Last Amended**: 2026-07-03
