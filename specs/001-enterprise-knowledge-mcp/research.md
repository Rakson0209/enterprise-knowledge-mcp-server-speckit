# Phase 0 Research: Enterprise Knowledge MCP Server & Preprocessing Skill

All Technical Context items are resolved; there are no open `NEEDS CLARIFICATION` markers. The
decisions below record the technology choices and the key trade-offs, aligned with the source
requirements and constitution v1.1.0.

## D1. Document parsing: Docling (+ RapidOCR) vs. plain PDF OCR

- **Decision**: Use **Docling** as the primary parser for DOCX/PDF/PPTX, augmented with
  **RapidOCR** for text embedded in images.
- **Rationale**: Docling emits structured output — titles, tables (row/column), figures — with
  per-element page/slide provenance, which is what semantic-boundary chunking (Principle II)
  depends on. Docling's PPTX/DOCX pipelines do not OCR embedded images, so figure/slide-borne text
  would be lost; RapidOCR fills that gap. RapidOCR is ONNX-based and runs CPU-only on ARM64.
- **Alternatives considered**: Plain PDF OCR (e.g. Tesseract over rendered pages) — rejected: it
  produces a flat text stream that discards headings, table structure, and page/slide origin,
  violating Principles I & II and making citations impossible.

## D2. Retrieval: Hybrid (dense + BM25 + RRF) vs. single method / FTS

- **Decision**: **Hybrid** retrieval — BGE-M3 dense embeddings + rank-bm25 sparse — fused by
  **Reciprocal Rank Fusion (RRF, k=60)**.
- **Rationale**: Dense recall handles paraphrase/semantic similarity but misses exact rare terms
  and identifiers; BM25 catches exact/rare tokens (proper nouns, `CLAUDE.md`-style identifiers) that
  embeddings drop. RRF fuses by rank, avoiding the score-scale mismatch between cosine similarity
  and BM25 scores and eliminating manual weight tuning. Constitution Principle III forbids relying on
  a single method or plain FTS as the final strategy.
- **Alternatives considered**: (a) Dense-only — unstable recall for exact/rare terms; (b) SQLite
  FTS-only — no semantic generalization, explicitly disallowed; (c) weighted score fusion — requires
  per-corpus tuning and is brittle to scale differences.

## D3. Embedding model: BGE-M3

- **Decision**: **BGE-M3** via sentence-transformers, 1024-dim, **L2-normalized** so cosine ≡ inner
  product.
- **Rationale**: Strong multilingual model well-suited to mixed Chinese/English corpora (FR-008).
  Runs CPU-only on ARM64. Lazy-loaded to keep cold-start and memory within the node envelope.
- **Alternatives considered**: Smaller/English-only models — weaker on mixed CJK/Latin; proprietary
  embedding APIs — add network dependency and cost, conflict with self-contained deployment.

## D4. Vector store: embedded, persistent Chroma

- **Decision**: **Chroma** in embedded (in-process), persistent mode, data on the `/data` volume.
- **Rationale**: No separate database service to operate; persists across restart/redeploy
  (FR-020); fits single-service scale and the in-process singleton pattern that makes upload
  immediately visible to MCP search (FR-012). Chroma also acts as the single source of truth from
  which the BM25 corpus is rebuilt (Principle III).
- **Alternatives considered**: External vector DB (Qdrant/Weaviate/pgvector) — extra service to
  deploy and persist, over-scaled for this workload; FAISS raw — no built-in metadata store/
  persistence ergonomics.

## D5. Web + MCP hosting: single FastAPI ASGI app with FastMCP mounted at `/mcp`

- **Decision**: One **FastAPI** application factory that mounts the **FastMCP** ASGI app at `/mcp`
  and shares its lifespan; REST and MCP run in the same process and share singletons.
- **Rationale**: A single service exposes both the REST upload/catalogue API and the Remote MCP
  endpoint over streamable HTTP, so uploaded documents are instantly searchable via MCP without a
  restart (FR-012, Principle IV). FastMCP registers tools/resources via decorators and provides an
  in-memory client for hermetic protocol tests (Principle VI). Async/ASGI lets heavy sync work be
  offloaded to a thread pool so the event loop stays responsive (FR-014).
- **Alternatives considered**: Separate MCP and REST services — duplicated state, cross-process
  cache-coherency problems, harder "instant visibility"; stdio-only MCP — not remotely reachable.

## D6. Reusable preprocessing: thin-wrapper Claude Skill (DRY)

- **Decision**: Package parse/clean/chunk as a **Claude Skill** — `SKILL.md` + a `preprocess.py`
  argparse CLI that imports `app/services` parser/cleaner/chunker directly.
- **Rationale**: Principle V mandates one implementation reused by all delivery forms. The CLI walks
  up to find the project root (anchored on `app/services/parser.py`), adds it to `sys.path`, and
  calls production code, so Skill output is byte-for-schema identical to indexed output (FR-015,
  FR-018, SC-005). `SKILL.md` frontmatter (name/description) lets agents auto-discover and trigger it.
- **Alternatives considered**: Reimplementing a lightweight parser in the Skill — violates DRY,
  drifts from the knowledge base; shipping as a separate package — breaks single-source-of-truth and
  complicates version sync.

## D7. Skill I/O and safety boundaries

- **Decision**: stdout carries structured JSON, stderr carries progress logs; UTF-8 everywhere;
  read-only input; extension allowlist (`.docx/.pdf/.pptx`); size cap (default 50 MB); all writes
  confined to `--out`; no DB writes; no network; single-line `error: ...` + exit codes (0/1/2); no
  raw traceback.
- **Rationale**: Principle VII (bounded, least-privilege). Separating stdout/stderr keeps machine
  output clean for agents/CI; UTF-8 avoids Windows cp950 corruption of Chinese text; path-escape
  refusal and read-only input make it safe to run against untrusted files/dirs (FR-017, SC-008).
- **Alternatives considered**: Mixed stdout logging — corrupts JSON consumers; writing anywhere —
  unsafe; dumping tracebacks — noisy and leaks internals.

## D8. Deployment: single `linux/arm64` Dockerfile → Zeabur, persistent volume

- **Decision**: One multi-stage **Dockerfile** targeting **`linux/arm64`**, deployed to **Zeabur**
  (auto-detects Dockerfile), with a **volume mounted at `/data`** for index, uploads, and model
  cache. Provide `/`, `/health`, `/mcp`, `/docs` endpoints.
- **Rationale**: Target node is Zeabur Arm Ampere A1 (aarch64, no GPU) — FR-021 and the constitution
  ARM64 constraint. All dependencies must ship aarch64 wheels or build on ARM; inference is CPU-only;
  torch CPU wheels pinned. Volume persistence satisfies FR-020/SC-006. Health check enables liveness
  probing (FR-019).
- **Alternatives considered**: x86 build — wrong architecture for the node; GPU images — no GPU
  available; ephemeral storage — index lost on redeploy.
- **ARM64 risk watch**: Confirm aarch64 wheels/build for torch (CPU), onnxruntime (RapidOCR),
  chromadb, tokenizers, and Docling's native deps during setup; pin CPU torch; keep default batch
  sizes small to stay within node RAM.

## D9. Testing strategy

- **Decision**: Pytest across six layers — unit (cleaner/chunker/parser + PPTX), index/retrieval,
  MCP direct-call, MCP protocol (FastMCP in-memory JSON-RPC client), REST, and Skill CLI end-to-end —
  plus a runnable `mcp_client_demo.py` against a live server producing inspectable tool-invocation
  logs.
- **Rationale**: The metadata schema, retrieval behavior, and MCP protocol are machine contracts;
  only layered tests (including real-protocol tests) prove they hold (Principle VI, FR-022, SC-007).
- **Alternatives considered**: Unit-only — misses protocol/contract regressions; manual testing —
  not repeatable, no regression safety net.
