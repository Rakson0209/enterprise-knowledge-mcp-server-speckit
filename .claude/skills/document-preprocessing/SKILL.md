---
name: document-preprocessing
description: >
  Preprocess a single enterprise document (DOCX/PDF/PPTX) into index-ready structured JSON and
  human-readable Markdown, using the same production parse → clean → chunk pipeline as the
  Enterprise Knowledge MCP Server. Use when you need to parse a document, strip boilerplate
  (headers/footers/page numbers), or produce metadata-complete semantic chunks for one file —
  without starting the HTTP/MCP server or touching the vector database.
---

# document-preprocessing

A thin CLI wrapper over the knowledge base's production services (`app/services/parser`,
`cleaner`, `chunker`). It reuses the exact same logic, so the chunks it emits are **identical**
(count + metadata) to what the knowledge base indexes for the same file.

## When to use

- Parse one DOCX/PDF/PPTX and inspect its structure (titles, tables, figures, page/slide numbers).
- Clean a document (remove repeated headers/footers, page-number-only lines, symbol noise).
- Produce metadata-complete, semantic-boundary chunks (index-ready JSON) for a single file.
- Ad-hoc or CI preprocessing where running the server is unnecessary.

## Usage

```bash
python .claude/skills/document-preprocessing/scripts/preprocess.py <input> [options]
```

| Option | Default | Meaning |
|--------|---------|---------|
| `--stage {parse,clean,chunk,all}` | `all` | Pipeline stage(s) to run |
| `--format {json,md,both}` | `both` | Output artifact(s) |
| `--out DIR` | `./skill_output` | Output directory (created if absent) |
| `--doc-id ID` | filename slug | document id / chunk-id prefix |
| `--max-chars N` | `1200` | Soft chunk limit (split only at element boundaries) |
| `--max-mb N` | `50` | Reject inputs larger than this |
| `--no-ocr` | off | Disable image OCR (faster) |
| `--stdout` | off | Also print final JSON to stdout |
| `--quiet` | off | Suppress progress logs |

## Examples

```bash
# Full pipeline → JSON + Markdown into ./skill_output
python .claude/skills/document-preprocessing/scripts/preprocess.py "report.pdf" --stage all --out skill_output

# Parse a deck to inspect slide structure
python .claude/skills/document-preprocessing/scripts/preprocess.py "deck.pptx" --stage parse

# Chunk for indexing, JSON only, OCR off
python .claude/skills/document-preprocessing/scripts/preprocess.py "doc.docx" --stage chunk --format json --no-ocr
```

## Contract

- Output files (by input stem): `<stem>.parsed.*`, `<stem>.cleaned.*`, `<stem>.chunks.*`.
- Exit codes: `0` success · `1` input/IO error · `2` usage/validation error.
- See [reference/OUTPUT_SCHEMA.md](reference/OUTPUT_SCHEMA.md) for the JSON/metadata schema and
  [examples/RUN_LOG.md](examples/RUN_LOG.md) for a real run.

## Safety boundaries

Read-only input (never modified); only `.docx/.pdf/.pptx` accepted; oversized inputs rejected;
all writes confined to `--out` (path escape refused); no database writes; no outbound network
(model files are cached locally by Docling/RapidOCR once). On error: a single `error: ...` line
and a non-zero exit — never a raw traceback.
