# Phase 1 Data Model: Enterprise Knowledge MCP Server & Preprocessing Skill

Entities are Pydantic models in `app/models.py` (shared across services, REST, MCP, and the Skill).
Field names for the persisted **Chunk metadata** are fixed by the source requirements and the
constitution and MUST NOT change without a governance amendment.

## Entity: ParsedElement

An ordered, flat unit emitted by the parser before cleaning/chunking. Internal (not persisted).

| Field | Type | Notes |
|-------|------|-------|
| `element_type` | enum(`title`, `text`, `table`, `figure`) | Structural role from Docling |
| `content` | str | Text, or table rendered as Markdown, or OCR-recovered figure text |
| `page_number` | int \| null | 1-based (PDF/DOCX) |
| `slide_number` | int \| null | 1-based (PPTX) |
| `order` | int | Document order, monotonic |

**Rules**: order preserved from source; tables retain row/column structure as Markdown; figure text
comes from RapidOCR when images are present.

## Entity: ParsedDocument

Result of parsing one file. Internal.

| Field | Type | Notes |
|-------|------|-------|
| `document_id` | str | Slug of filename (or `--doc-id` override in Skill) |
| `filename` | str | Original filename |
| `format` | enum(`docx`, `pdf`, `pptx`) | Detected from extension |
| `elements` | list[ParsedElement] | Ordered |

## Entity: Chunk (persisted — the metadata contract)

The atomic unit of retrieval. **Every field below is required by FR-006 and Principle II.**

| Field | Type | Constraints |
|-------|------|-------------|
| `document_id` | str | Non-empty; groups chunks of one document |
| `filename` | str | Original filename |
| `page_number` | int \| null | 1-based; null for PPTX |
| `slide_number` | int \| null | 1-based; null for PDF/DOCX |
| `chunk_id` | str | **Unique & reproducible**: `<document_id>-<sequence>` (zero-padded monotonic) |
| `chunk_type` | enum(`text`, `table`, `figure`) | table/figure chunks are standalone |
| `content` | str | Chunk body; tables rendered as Markdown |
| `section_title` | str \| null | Nearest preceding title; retained across continuation chunks |

**Validation & invariants**:
- `chunk_id` MUST be deterministic for the same input (re-running produces identical ids).
- Exactly one of `page_number` / `slide_number` is populated per document format (the other null).
- Each table and each figure element becomes its own chunk (`chunk_type` = table/figure).
- No chunk is produced by fixed-size splitting; splits occur only between whole elements when a
  section exceeds `chunk_max_chars`, and continuation chunks reuse `section_title`.
- A page/slide boundary change within a continuous section forces a new chunk.

**State/derivation**: `ParsedDocument → clean() → chunk()` produces the chunk list; embedding +
upsert into Chroma persists it; the BM25 corpus is rebuilt from persisted chunk `content`.

## Entity: Document (catalogue view)

Document-level aggregate derived from persisted chunks (not stored separately).

| Field | Type | Notes |
|-------|------|-------|
| `document_id` | str | Key |
| `filename` | str | |
| `num_chunks` | int | Count of chunks for this document |
| `page_range` | [int, int] \| null | Min/max page across chunks (PDF/DOCX) |
| `slide_range` | [int, int] \| null | Min/max slide across chunks (PPTX) |
| `chunk_types` | list[str] | Distinct chunk types present |

## Entity: SearchResult

A chunk returned for a query, augmented with ranking. Returned by MCP `search_documents`.

| Field | Type | Notes |
|-------|------|-------|
| `chunk` | Chunk | Full chunk with all metadata |
| `score` | float | RRF fusion score (higher = more relevant) |
| `rank` | int | 1-based position in the fused result list |

**Rules**: results ordered by descending score; `top_k` bounds the count; both dense and sparse
candidates are eligible before fusion.

## Entity: PreprocessOutput (Skill)

Per-document artifacts produced by the standalone tool. Not persisted to any DB.

| Field | Type | Notes |
|-------|------|-------|
| `stage` | enum(`parse`, `clean`, `chunk`, `all`) | Which stage produced this |
| `json_artifact` | file | `<stem>.parsed.json` / `.cleaned.json` / `.chunks.json` |
| `md_artifact` | file | Human-readable rendering (when format includes `md`) |
| `chunks` | list[Chunk] | For `chunk`/`all`: identical schema & values to indexed chunks |

**Invariant (SC-005)**: for a given input file and default parameters, `chunks` here equal (same
count and metadata) the chunks the knowledge base indexes for that file.

## Configuration (app/config.py — pydantic-settings, env-overridable)

| Setting | Default | Meaning |
|---------|---------|---------|
| `embedding_model` | BGE-M3 | Dense model id |
| `chunk_max_chars` | 1200 | Soft split limit (split only between whole elements) |
| `header_footer_min_repeats` | 2 | Repetition threshold for boilerplate removal |
| `rrf_k` | 60 | RRF constant |
| `top_k_default` | e.g. 5 | Default search result count |
| `max_upload_mb` / `max_mb` | 50 | Input size limit (REST + Skill) |
| `data_dir` | `/data` | Persistence root (Chroma, uploads, model cache) |
| `enable_ocr` | true | Image text recovery on/off |

## Relationships

```text
ParsedDocument 1─┐
                 ├─ elements ──> ParsedElement (ordered)
                 └─ clean+chunk ──> Chunk (1 document : N chunks)

Chunk ──persist──> Chroma (dense vectors + metadata)  ──rebuild──> BM25 corpus
Chunk ──aggregate──> Document (catalogue)
Query + Chunks ──RRF──> SearchResult (N)
Single file ──Skill pipeline──> PreprocessOutput (chunks ≡ indexed chunks)
```
