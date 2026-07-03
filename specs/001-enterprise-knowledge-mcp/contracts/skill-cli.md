# Contract: document-preprocessing Skill CLI

A standalone argparse CLI (`.claude/skills/document-preprocessing/scripts/preprocess.py`) that
thin-wraps the production `app/services` parser/cleaner/chunker. No server, no index, no network.
Output chunks are identical (count + metadata) to what the knowledge base indexes for the same file
(FR-015, FR-018, SC-005).

## Invocation

```text
preprocess.py <input_file> [options]
```

## Options

| Option | Default | Meaning |
|--------|---------|---------|
| `--stage {parse,clean,chunk,all}` | `all` | Pipeline stage(s) to run |
| `--format {json,md,both}` | `both` | Which artifact(s) to emit |
| `--out DIR` | `./skill_output` | Output directory (created if absent) |
| `--doc-id ID` | filename slug | document id / chunk-id prefix |
| `--max-chars N` | `1200` | Soft chunk limit (split only at element boundaries) |
| `--max-mb N` | `50` | Reject inputs larger than this |
| `--no-ocr` | off | Disable image OCR (faster) |
| `--stdout` | off | Also print final JSON to stdout |
| `--quiet` | off | Suppress progress logs |

## Output files (named by input stem)

- `--stage parse` → `<stem>.parsed.{json,md}`
- `--stage clean` → `<stem>.cleaned.{json,md}`
- `--stage chunk` → `<stem>.chunks.{json,md}`
- `--stage all` → all intermediate artifacts

## I/O discipline

- Structured JSON → **stdout** (only with `--stdout`); progress logs → **stderr**; never mixed.
- **UTF-8** everywhere (avoids Windows cp950 corruption of Chinese text).

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Input or I/O error (missing/unreadable file, write failure) |
| `2` | Usage or validation error (bad args, unsupported extension, oversized file) |

## Safety boundaries (Principle VII, FR-017, SC-008)

- Input opened **read-only**; never modified.
- Only `.docx` / `.pdf` / `.pptx` accepted; oversized inputs rejected.
- All writes confined to `--out`; any path escape refused.
- No database writes; no outbound network (model assets cached locally by Docling/RapidOCR once).
- On error: a single line `error: ...` and a non-zero exit code — **no raw traceback**.

## Root discovery

The CLI walks upward to find the project root (anchored on `app/services/parser.py`), adds it to
`sys.path`, and imports the production modules — so it runs regardless of where it is invoked from
and stays byte-for-schema identical to the knowledge base.
