# Contract: MCP Interface (Tools & Resources)

Transport: Remote MCP over streamable HTTP, mounted at `/mcp` (FastMCP). Exactly **4 tools** and
**2 resources** — this surface is fixed by Constitution Principle IV and MUST NOT change without a
governance amendment. Every tool invocation is logged server-side with operation name, query, and
returned chunk identifiers (FR-011).

## Tools

### `search_documents(query: str, top_k: int = 5) -> list[SearchResult]`

Hybrid-retrieve the most relevant chunks for a query.

- **Input**: `query` (non-empty string), `top_k` (positive int; bounded to a sane max).
- **Behavior**: dense (BGE-M3) + sparse (BM25) candidates fused by RRF (k=60); mixed CJK/Latin
  tokenizer; ordered by descending fused score.
- **Output**: list of `{ chunk: {8-field metadata + content}, score: float, rank: int }`.
- **Errors**: empty query → structured error; empty index → empty list (not an error).
- **Log**: `MCP tool invoked: search_documents | query='...' top_k=N` then
  `search_documents retrieved N chunk(s): [chunk_id, ...]`.

### `list_documents() -> list[Document]`

List the catalogue of indexed documents.

- **Input**: none.
- **Output**: list of document summaries `{ document_id, filename, num_chunks, page_range|null,
  slide_range|null, chunk_types }`.
- **Errors**: none; empty index → empty list.

### `get_document(document_id: str) -> Document`

Document-level metadata for one document.

- **Input**: `document_id`.
- **Output**: `{ document_id, filename, num_chunks, page_range|null, slide_range|null,
  chunk_types }`.
- **Errors**: unknown `document_id` → structured not-found result.

### `get_chunk(chunk_id: str) -> Chunk`

Full content and metadata of a single chunk.

- **Input**: `chunk_id` (`<document_id>-<sequence>`).
- **Output**: the full 8-field `Chunk`.
- **Errors**: unknown `chunk_id` → structured not-found result.

## Resources

### `documents://all`

The full catalogue — same content as `list_documents()`, exposed as a browsable resource.

### `documents://{document_id}`

A specific document and **all** its chunks (each with full metadata).

- **Errors**: unknown `document_id` → structured not-found result.

## Protocol conformance (verified by `test_mcp_integration.py`)

- Tool/resource **discovery** returns exactly these 4 tools + 2 resources.
- Each tool exposes a correct **input schema** (types, required fields, defaults).
- Tool results are **structured** (typed output, not opaque strings).
- Resource **URIs** resolve, including the templated `documents://{document_id}` form.
- Exercised over real **JSON-RPC** via the FastMCP in-memory client.
