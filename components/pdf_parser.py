"""
PDF Parser Component
Extracts and preprocesses text from PDF files using pdfplumber (primary) and PyPDF2 (fallback).
"""

import re
import io
from dataclasses import dataclass, field
from typing import BinaryIO, List

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import pypdf as PyPDF2  # modern package name
    PYPDF2_AVAILABLE = True
except ImportError:
    try:
        import PyPDF2  # legacy fallback
        PYPDF2_AVAILABLE = True
    except ImportError:
        PYPDF2_AVAILABLE = False


@dataclass
class TextExtractionResult:
    text: str
    page_count: int
    extraction_method: str
    confidence: float
    errors: List[str] = field(default_factory=list)
    success: bool = True


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class PDFParser:
    """Extracts and preprocesses text content from PDF files."""

    MAX_FILE_SIZE_MB = 10
    MIN_TEXT_LENGTH = 50

    def _read_bytes(self, pdf_file) -> bytes:
        """Safely read all bytes from a file-like object (handles Streamlit UploadedFile)."""
        try:
            # Streamlit UploadedFile: use .getvalue() if available (most reliable)
            if hasattr(pdf_file, 'getvalue'):
                return pdf_file.getvalue()
            # Regular file-like: seek to start then read
            if hasattr(pdf_file, 'seek'):
                pdf_file.seek(0)
            return pdf_file.read()
        except Exception as e:
            raise IOError(f"Could not read file bytes: {e}")

    def validate_pdf(self, pdf_file) -> ValidationResult:
        """Validate PDF file before processing."""
        errors = []
        warnings = []

        try:
            content = self._read_bytes(pdf_file)

            if len(content) == 0:
                errors.append("File is empty.")
                return ValidationResult(is_valid=False, errors=errors)

            size_mb = len(content) / (1024 * 1024)
            if size_mb > self.MAX_FILE_SIZE_MB:
                errors.append(f"File too large ({size_mb:.1f}MB). Maximum allowed: {self.MAX_FILE_SIZE_MB}MB.")
                return ValidationResult(is_valid=False, errors=errors)

            if content[:4] != b'%PDF':
                errors.append("File does not appear to be a valid PDF.")
                return ValidationResult(is_valid=False, errors=errors)

            if size_mb > 5:
                warnings.append(f"Large file ({size_mb:.1f}MB) may take longer to process.")

        except Exception as e:
            errors.append(f"Could not read file: {str(e)}")
            return ValidationResult(is_valid=False, errors=errors)

        return ValidationResult(is_valid=True, warnings=warnings)

    def extract_text(self, pdf_file) -> TextExtractionResult:
        """Extract text from PDF using pdfplumber with PyPDF2 fallback."""
        errors = []

        # Read bytes once — works with Streamlit UploadedFile and regular files
        try:
            pdf_bytes = self._read_bytes(pdf_file)
        except Exception as e:
            return TextExtractionResult(
                text="", page_count=0, extraction_method="none",
                confidence=0.0, errors=[str(e)], success=False
            )

        # Try pdfplumber first
        if PDFPLUMBER_AVAILABLE:
            try:
                result = self._extract_with_pdfplumber(io.BytesIO(pdf_bytes))
                if result.success and len(result.text) >= self.MIN_TEXT_LENGTH:
                    return result
                else:
                    errors.append("pdfplumber extracted insufficient text, trying fallback.")
            except Exception as e:
                errors.append(f"pdfplumber failed: {str(e)}")

        # Fallback to PyPDF2
        if PYPDF2_AVAILABLE:
            try:
                result = self._extract_with_pypdf2(io.BytesIO(pdf_bytes))
                result.errors = errors + result.errors
                return result
            except Exception as e:
                errors.append(f"PyPDF2 fallback failed: {str(e)}")

        return TextExtractionResult(
            text="",
            page_count=0,
            extraction_method="none",
            confidence=0.0,
            errors=errors + ["All PDF extraction methods failed. Please ensure the PDF contains selectable text."],
            success=False
        )

    def _extract_with_pdfplumber(self, pdf_file) -> TextExtractionResult:
        """Extract text using pdfplumber with layout-aware settings."""
        pages_text = []
        page_count = 0

        with pdfplumber.open(pdf_file) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                # Try layout-aware extraction first (fixes squished text in columnar PDFs)
                try:
                    text = page.extract_text(layout=True, x_tolerance=3, y_tolerance=3)
                except TypeError:
                    text = page.extract_text(x_tolerance=3, y_tolerance=3)

                if not text:
                    text = page.extract_text()

                if text:
                    pages_text.append(text)

        raw_text = "\n".join(pages_text)
        processed = self.preprocess_text(raw_text)

        return TextExtractionResult(
            text=processed,
            page_count=page_count,
            extraction_method="pdfplumber",
            confidence=0.95 if len(processed) > self.MIN_TEXT_LENGTH else 0.3,
            success=len(processed) >= self.MIN_TEXT_LENGTH
        )

    def _extract_with_pypdf2(self, pdf_file) -> TextExtractionResult:
        """Extract text using pypdf/PyPDF2."""
        try:
            reader = PyPDF2.PdfReader(pdf_file)
        except AttributeError:
            reader = PyPDF2.PdfFileReader(pdf_file)
        page_count = len(reader.pages)
        pages_text = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)

        raw_text = "\n".join(pages_text)
        processed = self.preprocess_text(raw_text)

        return TextExtractionResult(
            text=processed,
            page_count=page_count,
            extraction_method="PyPDF2",
            confidence=0.80 if len(processed) > self.MIN_TEXT_LENGTH else 0.2,
            success=len(processed) >= self.MIN_TEXT_LENGTH
        )

    def preprocess_text(self, raw_text: str) -> str:
        """Clean and normalize extracted text."""
        if not raw_text:
            return ""

        # Normalize whitespace and line endings
        text = raw_text.replace('\r\n', '\n').replace('\r', '\n')

        # Fix squished words — insert space before capital letters in long runs
        import re as _re
        def fix_squished(line):
            stripped = line.strip()
            if not stripped:
                return line
            words = stripped.split()
            avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
            if avg_word_len > 12:
                # Split on camelCase boundaries
                line = _re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', line)
                line = _re.sub(r'(?<=[A-Z]{2})(?=[A-Z][a-z])', ' ', line)
                # Split on letter→digit and digit→letter
                line = _re.sub(r'(?<=[a-zA-Z])(?=[0-9])', ' ', line)
                line = _re.sub(r'(?<=[0-9])(?=[a-zA-Z])', ' ', line)
                # Split known word boundaries using common prefixes/suffixes
                line = _re.sub(r'(?<=[a-z])(at|in|on|is|are|was|for|and|the|of|to|with|by|from|as)(?=[A-Z])', r' \1 ', line)
            return line

        lines = text.split('\n')
        lines = [fix_squished(line) for line in lines]
        text = '\n'.join(lines)

        # Remove excessive whitespace while preserving structure
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]{2,}', ' ', text)

        # Remove common PDF artifacts
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # non-ASCII (icons/symbols)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)  # control chars

        # Clean up lines
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        text = '\n'.join(lines)

        return text.strip()
