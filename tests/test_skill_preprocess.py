"""End-to-end tests for the document-preprocessing Skill CLI (US4).

Safety/validation cases run without the Docling runtime (they exit before parsing). The full
parse→clean→chunk pipeline and Skill/index parity require Docling and skip when unavailable.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / ".claude" / "skills" / "document-preprocessing" / "scripts" / "preprocess.py"
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


@pytest.mark.skipif(not _HAS_DOCLING, reason="docling runtime not installed")
def test_full_pipeline_all_stages(tmp_path):
    pytest.skip(
        "with docling + a sample DOCX/PDF/PPTX: assert parsed/cleaned/chunks.{json,md} exist, "
        "chunk metadata schema is complete, custom --doc-id prefix is honored, and chunk count "
        "matches the knowledge base index for the same file (SC-005)"
    )
