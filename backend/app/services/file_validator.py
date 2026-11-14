"""
File validation service for uploaded research papers.

Validates PDF files by checking:
- Extension (.pdf)
- Detected MIME type (application/pdf via python-magic)
- PDF header signature (%PDF-)
- File is non-empty and readable
- File is not password-protected (via pypdf)
- File size does not exceed the per-file limit
"""

import io
import logging
from dataclasses import dataclass
from pathlib import Path

import magic
from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)

# Per-file size limit: 20 MB
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

PDF_HEADER = b"%PDF-"
PDF_MIME_TYPE = "application/pdf"
PDF_EXTENSION = ".pdf"


@dataclass
class ValidationResult:
    """Outcome of validating a single uploaded file."""

    is_valid: bool
    rejection_reason: str | None = None


def validate_pdf(filename: str, file_bytes: bytes) -> ValidationResult:
    """
    Validate a single uploaded file as an acceptable PDF.

    Args:
        filename: The original filename reported by the client.
        file_bytes: The raw bytes of the uploaded file.

    Returns:
        ValidationResult with is_valid=True when all checks pass,
        or is_valid=False with a human-readable rejection_reason.
    """
    # 1. Extension check (case-insensitive)
    if Path(filename).suffix.lower() != PDF_EXTENSION:
        return ValidationResult(
            is_valid=False, rejection_reason="File does not have a .pdf extension."
        )

    # 2. Non-empty check
    if not file_bytes:
        return ValidationResult(is_valid=False, rejection_reason="File is empty.")

    # 3. Size check
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        size_mb = len(file_bytes) / (1024 * 1024)
        return ValidationResult(
            is_valid=False,
            rejection_reason=(
                f"File size {size_mb:.1f} MB exceeds the 20 MB per-file limit."
            ),
        )

    # 4. PDF header / magic-bytes check
    if not file_bytes.startswith(PDF_HEADER):
        return ValidationResult(
            is_valid=False,
            rejection_reason="File does not contain the PDF header signature (%PDF-).",
        )

    # 5. MIME type detection (server-side, not trusting the client value)
    try:
        detected_mime = magic.from_buffer(file_bytes, mime=True)
    except Exception:
        logger.exception("MIME detection failed for %s", filename)
        return ValidationResult(
            is_valid=False,
            rejection_reason="Could not determine the file type.",
        )

    if detected_mime != PDF_MIME_TYPE:
        return ValidationResult(
            is_valid=False,
            rejection_reason=(
                f"Detected MIME type '{detected_mime}' is not application/pdf."
            ),
        )

    # 6. Readability and password-protection check via pypdf
    try:
        reader = PdfReader(io.BytesIO(file_bytes), strict=False)
        if reader.is_encrypted:
            return ValidationResult(
                is_valid=False,
                rejection_reason="File is password-protected and cannot be processed.",
            )
        # Attempt to access at least the first page to confirm readability
        if len(reader.pages) == 0:
            return ValidationResult(
                is_valid=False,
                rejection_reason="PDF contains no pages and may be corrupted.",
            )
    except PdfReadError as exc:
        return ValidationResult(
            is_valid=False,
            rejection_reason=f"PDF is corrupted or unreadable: {exc}",
        )
    except Exception:
        logger.exception("Unexpected error reading PDF %s", filename)
        return ValidationResult(
            is_valid=False,
            rejection_reason="File could not be read; it may be corrupted.",
        )

    return ValidationResult(is_valid=True)

