"""
Document Parser Service (TASK-P3-09).

Deep multi-format document parser for PDF, Word (DOCX), Excel (XLSX), and PowerPoint (PPTX).
Extracts structured text, metadata, and tabular data with sandboxed safety bounds
(max 25 MB file size and max 100 pages/slides) to prevent DoS and decompression attacks.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_PAGE_COUNT = 100                     # 100 pages / slides / sheets
DEFAULT_MAX_TEXT_CHARS = 100_000        # 100k characters text extraction ceiling


class DocumentParsingError(Exception):
    """Base error for document parsing failures."""


class FileSizeLimitExceededError(DocumentParsingError):
    """Raised when document exceeds 25 MB size limit."""


class PageCountLimitExceededError(DocumentParsingError):
    """Raised when document exceeds page limits."""


class UnsupportedDocumentFormatError(DocumentParsingError):
    """Raised when file extension or format is unsupported."""


class ParsedDocumentResult(BaseModel):
    """Structured extraction output for parsed documents."""
    model_config = ConfigDict(extra="forbid")

    file_name: str
    file_type: str
    file_size_bytes: int
    page_count: int
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tables: List[Dict[str, Any]] = Field(default_factory=list)


class DocumentParserService:
    """Service providing multi-format document extraction and parsing."""

    def __init__(self, max_file_size_bytes: int = MAX_FILE_SIZE_BYTES) -> None:
        self.max_file_size_bytes = max_file_size_bytes

    def _validate_path_and_size(self, path: Union[str, Path]) -> Path:
        resolved = Path(path).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Document file does not exist: {path}")
        if not resolved.is_file():
            raise ValueError(f"Path is not a regular file: {path}")

        size = resolved.stat().st_size
        if size > self.max_file_size_bytes:
            raise FileSizeLimitExceededError(
                f"File size ({size} bytes) exceeds maximum limit of {self.max_file_size_bytes} bytes (25 MB)"
            )
        return resolved

    def parse(self, path: Union[str, Path], max_chars: int = DEFAULT_MAX_TEXT_CHARS) -> ParsedDocumentResult:
        """Parse document based on its extension."""
        target = self._validate_path_and_size(path)
        ext = target.suffix.lower().lstrip(".")

        if ext == "pdf":
            result = self.parse_pdf(target, max_chars=max_chars)
        elif ext in ("docx", "doc"):
            result = self.parse_docx(target, max_chars=max_chars)
        elif ext in ("xlsx", "xls"):
            result = self.parse_xlsx(target, max_chars=max_chars)
        elif ext in ("pptx", "ppt"):
            result = self.parse_pptx(target, max_chars=max_chars)
        else:
            raise UnsupportedDocumentFormatError(
                f"Unsupported document format: '.{ext}'. Supported formats are: pdf, docx, xlsx, pptx."
            )

        from app.core.sanitizer import defang_data_tags
        result.text = defang_data_tags(result.text)
        return result

    def parse_pdf(self, path: Union[str, Path], max_chars: int = DEFAULT_MAX_TEXT_CHARS) -> ParsedDocumentResult:
        """Extract text and metadata from a PDF file using pypdf."""
        target = self._validate_path_and_size(path)
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(target))
        except Exception as exc:
            raise DocumentParsingError(f"Failed to read PDF file: {exc}") from exc

        num_pages = len(reader.pages)
        pages_to_read = min(num_pages, MAX_PAGE_COUNT)

        extracted_parts: List[str] = []
        for i in range(pages_to_read):
            try:
                page_text = reader.pages[i].extract_text() or ""
                if page_text.strip():
                    extracted_parts.append(f"--- Page {i + 1} ---\n{page_text.strip()}")
            except Exception as page_exc:
                logger.warning("Error reading PDF page %d: %s", i + 1, page_exc)

            if sum(len(p) for p in extracted_parts) >= max_chars:
                break

        metadata: Dict[str, Any] = {}
        if reader.metadata:
            for k, v in reader.metadata.items():
                if v:
                    clean_k = k.lstrip("/").lower()
                    metadata[clean_k] = str(v)

        full_text = "\n\n".join(extracted_parts)[:max_chars]
        return ParsedDocumentResult(
            file_name=target.name,
            file_type="pdf",
            file_size_bytes=target.stat().st_size,
            page_count=num_pages,
            text=full_text,
            metadata=metadata,
            tables=[],
        )

    def parse_docx(self, path: Union[str, Path], max_chars: int = DEFAULT_MAX_TEXT_CHARS) -> ParsedDocumentResult:
        """Extract paragraphs and tables from a Word (DOCX) document."""
        target = self._validate_path_and_size(path)
        try:
            import docx
            doc = docx.Document(str(target))
        except Exception as exc:
            raise DocumentParsingError(f"Failed to read DOCX file: {exc}") from exc

        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

        tables_data: List[Dict[str, Any]] = []
        table_lines: List[str] = []
        for t_idx, table in enumerate(doc.tables[:10]):
            rows: List[List[str]] = []
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells]
                if any(cells):
                    rows.append(cells)
                    table_lines.append(" | ".join(cells))
            if rows:
                tables_data.append({"table_index": t_idx, "rows": rows})

        text_sections = list(paragraphs)
        if table_lines:
            text_sections.append("--- Tables ---")
            text_sections.extend(table_lines)

        full_text = "\n\n".join(text_sections)[:max_chars]
        return ParsedDocumentResult(
            file_name=target.name,
            file_type="docx",
            file_size_bytes=target.stat().st_size,
            page_count=len(paragraphs),
            text=full_text,
            metadata={"paragraph_count": len(paragraphs), "table_count": len(tables_data)},
            tables=tables_data,
        )

    def parse_xlsx(self, path: Union[str, Path], max_chars: int = DEFAULT_MAX_TEXT_CHARS) -> ParsedDocumentResult:
        """Extract sheets and structured row/column tables from an Excel (XLSX) workbook."""
        target = self._validate_path_and_size(path)
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(target), data_only=True, read_only=True)
        except Exception as exc:
            raise DocumentParsingError(f"Failed to read XLSX file: {exc}") from exc

        sheet_names = wb.sheetnames
        sheets_data: List[Dict[str, Any]] = []
        text_sections: List[str] = []

        for name in sheet_names[:min(len(sheet_names), 10)]:
            ws = wb[name]
            sheet_rows: List[List[str]] = []
            text_sections.append(f"--- Sheet: {name} ---")

            for r_idx, row in enumerate(ws.iter_rows(values_only=True)):
                if r_idx >= 500:  # limit rows per sheet to 500 for safety
                    break
                row_vals = [str(v) if v is not None else "" for v in row]
                if any(row_vals):
                    sheet_rows.append(row_vals)
                    text_sections.append(" | ".join(row_vals))

            sheets_data.append({"sheet_name": name, "rows": sheet_rows})
            if sum(len(s) for s in text_sections) >= max_chars:
                break

        wb.close()
        full_text = "\n".join(text_sections)[:max_chars]
        return ParsedDocumentResult(
            file_name=target.name,
            file_type="xlsx",
            file_size_bytes=target.stat().st_size,
            page_count=len(sheet_names),
            text=full_text,
            metadata={"sheet_names": sheet_names},
            tables=sheets_data,
        )

    def parse_pptx(self, path: Union[str, Path], max_chars: int = DEFAULT_MAX_TEXT_CHARS) -> ParsedDocumentResult:
        """Extract slide text and presentation structure from a PowerPoint (PPTX) file."""
        target = self._validate_path_and_size(path)
        try:
            from pptx import Presentation
            prs = Presentation(str(target))
        except Exception as exc:
            raise DocumentParsingError(f"Failed to read PPTX file: {exc}") from exc

        num_slides = len(prs.slides)
        slide_sections: List[str] = []

        for i, slide in enumerate(prs.slides):
            if i >= MAX_PAGE_COUNT:
                break
            texts: List[str] = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        if paragraph.text.strip():
                            texts.append(paragraph.text.strip())
            if texts:
                slide_sections.append(f"--- Slide {i + 1} ---\n" + "\n".join(texts))
            if sum(len(s) for s in slide_sections) >= max_chars:
                break

        full_text = "\n\n".join(slide_sections)[:max_chars]
        return ParsedDocumentResult(
            file_name=target.name,
            file_type="pptx",
            file_size_bytes=target.stat().st_size,
            page_count=num_slides,
            text=full_text,
            metadata={"slide_count": num_slides},
            tables=[],
        )
