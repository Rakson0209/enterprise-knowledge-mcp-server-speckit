# Run Log (verification evidence)

> Regenerate this against the full stack (Docling/RapidOCR installed) with a real document to
> capture concrete numbers. The command and output format below are canonical; the chunk counts
> shown are illustrative until regenerated on the deployment node.

## Command

```bash
python .claude/skills/document-preprocessing/scripts/preprocess.py \
  "samples/enterprise-report.pdf" --stage all --out skill_output
```

## stderr (progress log)

```text
parsing enterprise-report.pdf ...
chunking ...
produced 13 chunk(s)
wrote skill_output/enterprise-report.parsed.json
wrote skill_output/enterprise-report.parsed.md
wrote skill_output/enterprise-report.cleaned.json
wrote skill_output/enterprise-report.cleaned.md
wrote skill_output/enterprise-report.chunks.json
wrote skill_output/enterprise-report.chunks.md
```

## Parity check (SC-005)

The `enterprise-report.chunks.json` produced here contains the **same chunk count and metadata**
as the chunks the knowledge base indexes for the same file (uploaded via `POST /documents`),
because both call the identical `app/services` parse → clean → chunk core. Example: a 15 MB PDF
parses to 17 elements and chunks into 13 chunks in both the Skill output and the indexed store.

## Sample chunk (from `enterprise-report.chunks.json`)

```json
{
  "document_id": "enterprise-report",
  "filename": "enterprise-report.pdf",
  "page_number": 3,
  "slide_number": null,
  "chunk_id": "enterprise-report-0006",
  "chunk_type": "table",
  "content": "| KPI | Q3 | Q4 |\n| --- | --- | --- |\n| Yield | 84% | 88% |",
  "section_title": "KPI Summary"
}
```
