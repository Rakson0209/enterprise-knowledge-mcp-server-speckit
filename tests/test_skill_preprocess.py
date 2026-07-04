"""End-to-end tests for the document-preprocessing Skill CLI (US4).

Safety/validation cases run without the Docling runtime (they exit before parsing). The full
parse→clean→chunk pipeline and Skill/index parity require Docling and skip when unavailable.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / ".claude" / "skills" / "document-preprocessing" / "scripts" / "preprocess.py"
_FIXTURE = _REPO / "tests" / "fixtures" / "sample.docx"
_HAS_DOCLING = importlib.util.find_spec("docling") is not None


def _run(args: list[str]):
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args], capture_output=True, text=True, cwd=str(_REPO)
    )


def test_script_exists():
    assert _SCRIPT.exists()


def test_reject_unsupported_extension():
    r = _run(["notes.txt"])
    assert r.returncode == 2
    assert r.stderr.strip().startswith("error:")
    assert "traceback" not in r.stderr.lower()


def test_missing_file():
    r = _run(["does-not-exist.pdf"])
    assert r.returncode == 1
    assert r.stderr.strip().startswith("error:")


def test_oversized_input(tmp_path):
    f = tmp_path / "big.pdf"
    f.write_bytes(b"x" * 2048)
    r = _run([str(f), "--max-mb", "0"])
    assert r.returncode == 2
    assert "exceeds" in r.stderr.lower()


def test_usage_error_without_input():
    r = _run([])
    assert r.returncode == 2  # argparse usage error


def test_no_traceback_on_error():
    r = _run(["bad.xlsx"])
    assert r.returncode == 2
    assert "Traceback (most recent call last)" not in r.stderr


_REQUIRED_CHUNK_FIELDS = {
    "document_id", "filename", "page_number", "slide_number",
    "chunk_id", "chunk_type", "content", "section_title",
}


@pytest.mark.skipif(not _HAS_DOCLING, reason="docling runtime not installed")
def test_full_pipeline_all_stages(tmp_path):
    """Run parse->clean->chunk end-to-end and assert artifacts, schema, and chunk parity."""
    out = tmp_path / "out"
    r = _run([str(_FIXTURE), "--stage", "all", "--out", str(out), "--doc-id", "sample-report"])
    assert r.returncode == 0, r.stderr

    # All six artifacts are written.
    for suffix in ("parsed", "cleaned", "chunks"):
        for ext in ("json", "md"):
            assert (out / f"sample.{suffix}.{ext}").exists(), f"missing sample.{suffix}.{ext}"

    chunks = json.loads((out / "sample.chunks.json").read_text(encoding="utf-8"))

    # Known-good count for this fixture (matches what the knowledge base indexes — SC-005).
    assert len(chunks) == 4

    for i, c in enumerate(chunks):
        # Complete 8-field metadata schema on every chunk.
        assert set(c.keys()) == _REQUIRED_CHUNK_FIELDS
        # Reproducible, sequential chunk_id: <document_id>-<zero-padded seq>.
        assert c["chunk_id"] == f"sample-report-{i:04d}"
        assert c["document_id"] == "sample-report"
        assert c["chunk_type"] in {"text", "table", "figure"}
        assert c["content"]

    # The table became its own chunk (no fixed-size splitting merged it).
    assert any(c["chunk_type"] == "table" for c in chunks)


@pytest.mark.skipif(not _HAS_DOCLING, reason="docling runtime not installed")
def test_json_only_skips_markdown(tmp_path):
    out = tmp_path / "out"
    r = _run([str(_FIXTURE), "--stage", "chunk", "--format", "json", "--out", str(out)])
    assert r.returncode == 0, r.stderr
    assert (out / "sample.chunks.json").exists()
    assert not (out / "sample.chunks.md").exists()
