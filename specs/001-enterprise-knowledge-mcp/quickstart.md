# Quickstart & Validation Guide

End-to-end scenarios that prove the feature works. Details of the contracts live in
[contracts/](./contracts/) and the schema in [data-model.md](./data-model.md); this guide is how to
run and verify.

## Prerequisites

- Python 3.11, project installed in a virtualenv: `python -m pip install -e ".[dev]"`.
- First run downloads and caches model assets (Docling, BGE-M3, RapidOCR) — CPU-only, ARM64-safe.
- Sample DOCX/PDF/PPTX files for ingestion.

## Run locally

```text
# Native
python -m uvicorn app.main:app --reload            # http://localhost:8000

# Docker (built for linux/arm64)
docker compose up --build                          # http://localhost:8000
```

## Scenario A — Ingestion produces metadata-complete chunks (US2, FR-001–006, SC-001/002)

1. `POST /documents` with a PDF, a DOCX, and a PPTX (`curl -X POST .../documents -F file=@report.pdf`).
2. Expect `201 { document_id, status: "indexed", num_chunks }` for each.
3. **Verify**: every chunk carries all 8 metadata fields; PDF/DOCX chunks have `page_number`
   (slide null), PPTX chunks have `slide_number` (page null); `chunk_id` = `<document_id>-<seq>`;
   tables/figures are their own `chunk_type`; no chunk cuts a sentence or table row.

## Scenario B — Query with citations, hybrid retrieval (US1, FR-007–011, SC-003/007)

1. Connect an MCP client to `/mcp` (Claude Desktop/Code) **or** run the demo:
   `python tests/mcp_client_demo.py "yield improvement plan"`.
2. Try: `What is the yield improvement plan?`, `Show me the KPI table from Q4 report.`,
   `Summarize slide 5.`, plus a rare exact identifier, plus a mixed Chinese/English query.
3. **Verify**: results are relevant and each carries content + full metadata + score; exact-term and
   paraphrased queries both hit; server log shows
   `MCP tool invoked: search_documents | query=... top_k=...` and the retrieved chunk ids.

## Scenario C — Upload is instantly searchable (US2, FR-012, SC-004)

1. With the server running and an MCP session open, `POST /documents` a new file.
2. Immediately `search_documents` for its content — **no restart**.
3. **Verify**: new chunks appear; the reported `num_chunks` matches what the catalogue shows.

## Scenario D — Catalogue & drill-down (US3, FR-010, resources)

1. MCP `list_documents()` / resource `documents://all` → all indexed docs enumerated.
2. `get_document(document_id)` → summary with `num_chunks` and page/slide range.
3. `get_chunk(chunk_id)` → full content + metadata. Unknown ids → structured not-found.

## Scenario E — Reusable Skill, parity with index (US4, FR-015–018, SC-005/008)

```text
# Full pipeline → JSON + Markdown
python .claude/skills/document-preprocessing/scripts/preprocess.py "report.pdf" --stage all --out skill_output
# Single stage / format
python .claude/skills/document-preprocessing/scripts/preprocess.py "deck.pptx" --stage parse
python .claude/skills/document-preprocessing/scripts/preprocess.py "doc.docx" --stage chunk --format json --no-ocr
```

**Verify**:
- Chunks from `--stage chunk` equal (count + metadata) the knowledge base's chunks for the same
  file (parity — SC-005).
- Unsupported extension / missing file / oversized file → single-line `error: ...`, non-zero exit
  (2 or 1); input never modified; nothing written outside `--out` (SC-008).

## Scenario F — Deployment & persistence (FR-019–021, SC-006)

1. Public URL responds: `GET /health` → `{status: "ok"}`; `GET /` lists live MCP tools/resources;
   `GET /docs` shows Swagger; `/mcp` is reachable by an MCP client.
2. Index a document, restart/redeploy the service, search again → the document is still searchable
   (volume-persisted index).
3. **Verify**: runs CPU-only on the ARM64 node (no GPU calls).

## Run the test suite

```text
python -m pytest -q                                   # all layers
python -m pytest tests/test_skill_preprocess.py -v    # Skill CLI end-to-end
python -m pytest tests/test_mcp_integration.py -v     # real JSON-RPC MCP protocol
```

Expected: unit (cleaner/chunker/parser), index/retrieval (RRF + tokenizer), MCP direct + protocol,
REST (upload/health), and Skill layers all pass.
