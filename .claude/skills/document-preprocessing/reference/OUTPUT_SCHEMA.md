# Output Schema

The Skill emits the same schema the Enterprise Knowledge MCP Server indexes.

## `<stem>.parsed.json` / `<stem>.cleaned.json`

A `ParsedDocument`:

```json
{
  "document_id": "q4-report",
  "filename": "q4-report.pdf",
  "format": "pdf",
  "elements": [
    {
      "element_type": "title | text | table | figure",
      "content": "…(tables rendered as Markdown)…",
      "page_number": 1,
      "slide_number": null,
      "order": 0
    }
  ]
}
```

`cleaned.json` has the same shape after boilerplate/noise removal (titles, tables, figures, and
page/slide numbers preserved).

## `<stem>.chunks.json`

A list of `Chunk` objects — the metadata contract (fixed by the constitution):

```json
[
  {
    "document_id": "q4-report",
    "filename": "q4-report.pdf",
    "page_number": 1,
    "slide_number": null,
    "chunk_id": "q4-report-0000",
    "chunk_type": "text | table | figure",
    "content": "…",
    "section_title": "Yield Improvement Plan"
  }
]
```

| Field | Type | Notes |
|-------|------|-------|
| `document_id` | str | groups a document's chunks |
| `filename` | str | original filename |
| `page_number` | int \| null | 1-based (PDF/DOCX) |
| `slide_number` | int \| null | 1-based (PPTX) |
| `chunk_id` | str | unique & reproducible: `<document_id>-<sequence>` |
| `chunk_type` | str | `text` / `table` / `figure` |
| `content` | str | chunk body (tables as Markdown) |
| `section_title` | str \| null | nearest preceding title |

## Markdown artifacts

`<stem>.parsed.md` / `.cleaned.md` render elements with type + page/slide headings;
`<stem>.chunks.md` renders each chunk with its id, type, location, and section.
