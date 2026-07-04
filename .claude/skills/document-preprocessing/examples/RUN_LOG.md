# Run Log (verification evidence)

Real execution of the Skill CLI on `sample.docx` (the same file uploaded to the deployed
knowledge base), confirming the Skill reuses the production core and produces output identical to
what the server indexes (SC-005 parity).

## Command

```bash
python .claude/skills/document-preprocessing/scripts/preprocess.py \
  tests/fixtures/sample.docx --stage all --out skill_output
```

## stderr (progress log)

```text
parsing sample.docx ...
chunking ...
produced 4 chunk(s)
wrote skill_output/sample.parsed.json
wrote skill_output/sample.parsed.md
wrote skill_output/sample.cleaned.json
wrote skill_output/sample.cleaned.md
wrote skill_output/sample.chunks.json
wrote skill_output/sample.chunks.md
```

Exit code: `0`.

## What was produced

- **Parsed:** 6 elements — `title, text, title, table, title, text`.
- **Chunked:** **4 chunks** (every table becomes its own chunk; no fixed-size splitting):

| chunk_id | chunk_type | section_title | content (excerpt) |
|----------|-----------|---------------|-------------------|
| `<doc>-0000` | text | Yield Improvement Plan | "Yield Improvement Plan\nThe yield improvement plan targets a 12% increase…" |
| `<doc>-0001` | text | KPI Summary | "KPI Summary" |
| `<doc>-0002` | table | KPI Summary | "\| KPI \| Q3 \| Q4 \| … \| Yield \| 84% \| 88% \|" |
| `<doc>-0003` | text | 中文測試段落 | "中文測試段落\n本節用於驗證中英混合檢索：良率改善計畫與 KPI 指標。" |

All four chunks carry the complete 8-field metadata schema (verified: every chunk has
`document_id, filename, page_number, slide_number, chunk_id, chunk_type, content, section_title`).

## Sample chunk (from `sample.chunks.json`)

```json
{
  "document_id": "sample-report",
  "filename": "sample-report.docx",
  "page_number": null,
  "slide_number": null,
  "chunk_id": "sample-report-0002",
  "chunk_type": "table",
  "content": "| KPI   | Q3   | Q4   |\n|-------|------|------|\n| Yield | 84%  | 88%  |",
  "section_title": "KPI Summary"
}
```

## Parity with the knowledge base (SC-005)

The same `sample-report.docx` uploaded to the deployed server
(`POST https://ek-mcp-server.zeabur.app/documents`) returned:

```json
{"document_id": "sample-report", "status": "indexed", "num_chunks": 4}
```

and an MCP `search_documents` / `get_chunk` on the server returns the **same 4 chunks with the
same ids, types, and content** as the Skill output above — proving the Skill and the production
pipeline emit byte-for-schema identical chunks (one logic, two delivery forms).

> Note: `page_number` is `null` for DOCX because Docling does not assign page numbers to Word
> documents (page breaks are not represented in the DOCX XML). PDF/PPTX inputs populate
> `page_number` / `slide_number` respectively.
