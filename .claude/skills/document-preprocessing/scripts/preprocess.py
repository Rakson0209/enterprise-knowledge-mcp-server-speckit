#!/usr/bin/env python3
"""document-preprocessing — thin-wrapper CLI over the production parse/clean/chunk core.

Reuses ``app/services`` (constitution Principle V: single source of truth) so its output is
identical to what the knowledge base indexes. No HTTP/MCP server, no vector DB, no network.

I/O discipline: structured JSON -> stdout (with --stdout); progress logs -> stderr; UTF-8.
Exit codes: 0 success | 1 input/IO error | 2 usage/validation error.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from pathlib import Path

_ALLOWED_EXT = {".docx", ".pdf", ".pptx"}


def _log(msg: str, quiet: bool) -> None:
    if not quiet:
        print(msg, file=sys.stderr, flush=True)


def _die(msg: str, code: int) -> "None":
    print(f"error: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def _find_project_root(start: Path) -> Path:
    cur = start.resolve()
    while True:
        if (cur / "app" / "services" / "parser.py").exists():
            return cur
        if cur.parent == cur:
            _die("could not locate project root (app/services/parser.py)", 1)
        cur = cur.parent


def _slug(name: str) -> str:
    import re

    s = re.sub(r"[^\w\-]+", "-", name.strip().lower()).strip("-")
    return s or "document"


def _element_to_dict(el) -> dict:
    return el.model_dump(mode="json")


def _render_elements_md(doc) -> str:
    lines = [f"# {doc.filename}", ""]
    for el in doc.elements:
        loc = ""
        if el.page_number is not None:
            loc = f" (page {el.page_number})"
        elif el.slide_number is not None:
            loc = f" (slide {el.slide_number})"
        lines += [f"## {el.element_type.value}{loc}", "", el.content, ""]
    return "\n".join(lines)


def _render_chunks_md(chunks) -> str:
    lines = []
    for c in chunks:
        loc = f"page {c.page_number}" if c.page_number is not None else (
            f"slide {c.slide_number}" if c.slide_number is not None else "—"
        )
        section = c.section_title or "—"
        lines += [f"## {c.chunk_id} ({c.chunk_type.value}, {loc}, section: {section})", "",
                  c.content, ""]
    return "\n".join(lines)


def _write(out_dir: Path, stem: str, suffix: str, ext: str, payload: str) -> Path:
    filename = f"{stem}.{suffix}.{ext}"
    dest = (out_dir / filename).resolve()
    # Confine every write inside the output directory (refuse path escape).
    if os.path.commonpath([str(out_dir.resolve()), str(dest)]) != str(out_dir.resolve()):
        _die("refused: output path escapes --out directory", 2)
    dest.write_text(payload, encoding="utf-8")
    return dest


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="preprocess.py",
        description="Preprocess one DOCX/PDF/PPTX into index-ready JSON + Markdown.",
    )
    p.add_argument("input", help="path to a .docx/.pdf/.pptx file")
    p.add_argument("--stage", choices=["parse", "clean", "chunk", "all"], default="all")
    p.add_argument("--format", choices=["json", "md", "both"], default="both")
    p.add_argument("--out", default="./skill_output")
    p.add_argument("--doc-id", default=None)
    p.add_argument("--max-chars", type=int, default=1200)
    p.add_argument("--max-mb", type=int, default=50)
    p.add_argument("--no-ocr", action="store_true")
    p.add_argument("--stdout", action="store_true")
    p.add_argument("--quiet", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    input_path = Path(args.input)
    ext = input_path.suffix.lower()

    # --- validation (exit 2) / input errors (exit 1) ---
    if ext not in _ALLOWED_EXT:
        _die(f"unsupported file type: {ext} (allowed: .docx .pdf .pptx)", 2)
    if not input_path.exists():
        _die(f"input file not found: {input_path}", 1)
    if not input_path.is_file():
        _die(f"input path is not a file: {input_path}", 1)
    size_mb = input_path.stat().st_size / (1024 * 1024)
    if size_mb > args.max_mb:
        _die(f"input exceeds {args.max_mb} MB limit ({size_mb:.1f} MB)", 2)

    out_dir = Path(args.out)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _die(f"cannot create output directory: {exc}", 1)

    # --- wire in the production core (single source of truth) ---
    root = _find_project_root(Path(__file__).parent)
    sys.path.insert(0, str(root))
    from app.services.chunker import chunk_document
    from app.services.cleaner import clean_document
    from app.services.parser import parse_document

    stem = _slug(input_path.stem)
    doc_id = args.doc_id or stem
    want_json = args.format in ("json", "both")
    want_md = args.format in ("md", "both")
    do = {
        "parse": args.stage in ("parse", "all"),
        "clean": args.stage in ("clean", "all"),
        "chunk": args.stage in ("chunk", "all"),
    }

    written: list[str] = []
    final_json_payload = None
    try:
        _log(f"parsing {input_path.name} ...", args.quiet)
        parsed = parse_document(
            str(input_path), filename=input_path.name, document_id=doc_id,
            enable_ocr=not args.no_ocr,
        )

        if do["parse"]:
            data = parsed.model_dump(mode="json")
            if want_json:
                written.append(str(_write(out_dir, stem, "parsed", "json",
                                          json.dumps(data, ensure_ascii=False, indent=2))))
            if want_md:
                written.append(str(_write(out_dir, stem, "parsed", "md",
                                          _render_elements_md(parsed))))

        cleaned = clean_document(parsed)
        if do["clean"]:
            data = cleaned.model_dump(mode="json")
            if want_json:
                written.append(str(_write(out_dir, stem, "cleaned", "json",
                                          json.dumps(data, ensure_ascii=False, indent=2))))
            if want_md:
                written.append(str(_write(out_dir, stem, "cleaned", "md",
                                          _render_elements_md(cleaned))))

        if do["chunk"]:
            _log("chunking ...", args.quiet)
            chunks = chunk_document(cleaned, max_chars=args.max_chars)
            data = [c.model_dump(mode="json") for c in chunks]
            final_json_payload = data
            if want_json:
                written.append(str(_write(out_dir, stem, "chunks", "json",
                                          json.dumps(data, ensure_ascii=False, indent=2))))
            if want_md:
                written.append(str(_write(out_dir, stem, "chunks", "md",
                                          _render_chunks_md(chunks))))
            _log(f"produced {len(chunks)} chunk(s)", args.quiet)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - single-line error, no traceback
        _die(f"processing failed: {exc}", 1)

    for path in written:
        _log(f"wrote {path}", args.quiet)

    if args.stdout and final_json_payload is not None:
        # Ensure UTF-8 stdout on Windows (avoid cp950 crash on Chinese text).
        sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
        print(json.dumps(final_json_payload, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit as e:
        raise
