"""Tests for the file validation service (app/services/file_validator.py)."""

import io
import struct

import pytest

from app.services.file_validator import (
    MAX_FILE_SIZE_BYTES,
    validate_pdf,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_pdf_bytes() -> bytes:
    """Return the smallest syntactically valid PDF that pypdf can open."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n190\n%%EOF"
    )


# ---------------------------------------------------------------------------
# Extension tests
# ---------------------------------------------------------------------------

class TestExtensionCheck:
    def test_rejects_txt_extension(self):
        result = validate_pdf("paper.txt", _minimal_pdf_bytes())
        assert not result.is_valid
        assert "extension" in result.rejection_reason.lower()

    def test_rejects_no_extension(self):
        result = validate_pdf("paper", _minimal_pdf_bytes())
        assert not result.is_valid

    def test_accepts_pdf_extension(self):
        # Full valid path tested in integration; here we just verify the check
        # does not block a .pdf filename — remaining checks may still fail.
        result = validate_pdf("paper.PDF", _minimal_pdf_bytes())
        # Extension check is case-insensitive (.PDF should be accepted)
        # The result may still fail on MIME detection in CI without libmagic,
        # but it must not fail specifically on the extension.
        if not result.is_valid:
            assert "extension" not in result.rejection_reason.lower()


# ---------------------------------------------------------------------------
# Empty and size tests
# ---------------------------------------------------------------------------

class TestSizeChecks:
    def test_rejects_empty_file(self):
        result = validate_pdf("paper.pdf", b"")
        assert not result.is_valid
        assert "empty" in result.rejection_reason.lower()

    def test_rejects_oversized_file(self):
        oversized = b"%PDF-" + b"x" * MAX_FILE_SIZE_BYTES
        result = validate_pdf("big.pdf", oversized)
        assert not result.is_valid
        assert "20 mb" in result.rejection_reason.lower()

    def test_accepts_exactly_at_limit(self):
        # A file exactly at the limit should not be rejected for size;
        # it may be rejected for content, but not for size.
        at_limit = b"%PDF-" + b"x" * (MAX_FILE_SIZE_BYTES - 5)
        result = validate_pdf("limit.pdf", at_limit)
        if not result.is_valid:
            assert "20 mb" not in result.rejection_reason.lower()


# ---------------------------------------------------------------------------
# PDF header / magic-bytes tests
# ---------------------------------------------------------------------------

class TestPdfHeaderCheck:
    def test_rejects_missing_pdf_header(self):
        result = validate_pdf("fake.pdf", b"Not a PDF at all")
        assert not result.is_valid
        assert "%PDF-" in result.rejection_reason


# ---------------------------------------------------------------------------
# Corruption / password tests (require pypdf)
# ---------------------------------------------------------------------------

class TestPdfReadabilityCheck:
    def test_rejects_truncated_pdf(self):
        truncated = b"%PDF-1.4\n1 0 obj\n<< /Type /Cata"
        result = validate_pdf("truncated.pdf", truncated)
        # May fail on MIME or on pypdf; either way it must be rejected.
        assert not result.is_valid

