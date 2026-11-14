"""
ALEX Resume Studio Document Exporter.
Generates professional DOCX and standards-compliant PDF documents
from tailored resume and cover letter markdown.
Integrates with ALEX FileWorkspaceService storage.
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
import pypdf

logger = logging.getLogger(__name__)


class DocumentExporter:
    """Renders structured Markdown into professional DOCX and PDF documents."""

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = workspace_root

    # -----------------------------------------------------------------------
    # DOCX Generation
    # -----------------------------------------------------------------------

    def export_docx(
        self,
        title: str,
        subtitle: str,
        content_markdown: str,
        contact_info: str = "",
    ) -> bytes:
        """Generates a professionally styled DOCX document from markdown."""
        doc = docx.Document()

        # Set 0.75-inch standard margins
        for section in doc.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)

        # Document Header: Candidate Name / Title
        if title:
            h_p = doc.add_paragraph()
            h_p.paragraph_format.space_before = Pt(0)
            h_p.paragraph_format.space_after = Pt(2)
            run = h_p.add_run(title)
            run.font.size = Pt(20)
            run.font.bold = True
            run.font.color.rgb = RGBColor(15, 23, 42)  # Slate 900

        # Subtitle / Professional Role
        if subtitle:
            sub_p = doc.add_paragraph()
            sub_p.paragraph_format.space_before = Pt(0)
            sub_p.paragraph_format.space_after = Pt(2)
            s_run = sub_p.add_run(subtitle)
            s_run.font.size = Pt(11)
            s_run.font.bold = True
            s_run.font.color.rgb = RGBColor(30, 41, 59)  # Slate 800

        # Contact Info Line
        if contact_info:
            c_p = doc.add_paragraph()
            c_p.paragraph_format.space_before = Pt(0)
            c_p.paragraph_format.space_after = Pt(12)
            c_run = c_p.add_run(contact_info)
            c_run.font.size = Pt(9.5)
            c_run.font.color.rgb = RGBColor(100, 116, 139)  # Slate 500

        # Parse Markdown Body
        lines = content_markdown.splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            # Heading 1 (# ...)
            if line.startswith("# ") and not (title and line[2:].strip() == title):
                heading_text = line[2:].strip()
                h = doc.add_heading(level=1)
                h.paragraph_format.space_before = Pt(12)
                h.paragraph_format.space_after = Pt(4)
                r = h.add_run(heading_text)
                r.font.size = Pt(14)
                r.font.bold = True
                r.font.color.rgb = RGBColor(15, 23, 42)

            # Heading 2 (## ...)
            elif line.startswith("## "):
                heading_text = line[3:].strip()
                h = doc.add_heading(level=2)
                h.paragraph_format.space_before = Pt(10)
                h.paragraph_format.space_after = Pt(3)
                r = h.add_run(heading_text.upper())
                r.font.size = Pt(11.5)
                r.font.bold = True
                r.font.color.rgb = RGBColor(30, 41, 59)

            # Heading 3 (### ...)
            elif line.startswith("### "):
                heading_text = line[4:].strip()
                h = doc.add_heading(level=3)
                h.paragraph_format.space_before = Pt(8)
                h.paragraph_format.space_after = Pt(2)
                r = h.add_run(heading_text)
                r.font.size = Pt(10.5)
                r.font.bold = True
                r.font.color.rgb = RGBColor(51, 65, 85)

            # Bullet items (* ..., - ..., + ...)
            elif line.startswith(("* ", "- ", "+ ", "• ")) or re.match(r"^\s*[\*\-\+]\s+", line):
                clean_bullet = re.sub(r"^\s*[\*\-\+•]\s+", "", line)
                bp = doc.add_paragraph(style="List Bullet")
                bp.paragraph_format.space_before = Pt(0)
                bp.paragraph_format.space_after = Pt(2)
                self._append_formatted_runs(bp, clean_bullet)

            # Regular paragraph
            else:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(6)
                self._append_formatted_runs(p, line)

        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()

    def _append_formatted_runs(self, paragraph: docx.text.paragraph.Paragraph, text: str) -> None:
        """Handles basic inline markdown (e.g. **bold**, *italic*)."""
        # Simple regex tokenizer for bold **text**
        parts = re.split(r"(\*\*.*?\*\*)", text)
        for part in parts:
            if part.startswith("**") and part.endswith("**") and len(part) >= 4:
                bold_text = part[2:-2]
                r = paragraph.add_run(bold_text)
                r.font.bold = True
                r.font.size = Pt(10)
                r.font.color.rgb = RGBColor(15, 23, 42)
            else:
                r = paragraph.add_run(part)
                r.font.size = Pt(10)
                r.font.color.rgb = RGBColor(51, 65, 85)

    # -----------------------------------------------------------------------
    # PDF Generation (Self-Contained Standards-Compliant PDF 1.4)
    # -----------------------------------------------------------------------

    def export_pdf(
        self,
        title: str,
        subtitle: str,
        content_markdown: str,
        contact_info: str = "",
    ) -> bytes:
        """
        Generates a clean, multi-page, publication-quality PDF 1.4 document.
        Does not require external system binaries or C-extensions.
        """
        page_width, page_height = 612, 792  # Standard US Letter points
        margin_x = 54   # 0.75 in
        margin_top = 738
        margin_bottom = 54
        line_height = 14
        max_chars = 80

        # Construct lines with header information
        raw_lines: List[str] = []
        if title:
            raw_lines.append(f"# {title}")
        if subtitle:
            raw_lines.append(f"## {subtitle}")
        if contact_info:
            raw_lines.append(contact_info)
            raw_lines.append("")

        for l in content_markdown.splitlines():
            raw_lines.append(l)

        # Word wrap lines to max_chars
        wrapped_lines: List[Tuple[str, str]] = []  # (text, style: 'title'|'h2'|'h3'|'body'|'bullet'|'empty')
        for raw in raw_lines:
            line = raw.strip()
            if not line:
                wrapped_lines.append(("", "empty"))
                continue

            style = "body"
            if line.startswith("# "):
                style = "title"
                line = line[2:].strip()
            elif line.startswith("## "):
                style = "h2"
                line = line[3:].strip()
            elif line.startswith("### "):
                style = "h3"
                line = line[4:].strip()
            elif line.startswith(("* ", "- ", "+ ", "• ")) or re.match(r"^\s*[\*\-\+]\s+", line):
                style = "bullet"
                line = "  • " + re.sub(r"^\s*[\*\-\+•]\s+", "", line)

            # Strip markdown bold tags for clean PDF stream
            line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)

            # Wrap line
            while len(line) > max_chars:
                split_idx = line.rfind(" ", 0, max_chars)
                if split_idx == -1:
                    split_idx = max_chars
                wrapped_lines.append((line[:split_idx], style))
                line = ("    " if style == "bullet" else "") + line[split_idx:].lstrip()
            if line:
                wrapped_lines.append((line, style))

        # Partition lines into pages
        lines_per_page = int((margin_top - margin_bottom) / line_height)
        pages_lines: List[List[Tuple[str, str]]] = []
        for i in range(0, max(1, len(wrapped_lines)), lines_per_page):
            pages_lines.append(wrapped_lines[i : i + lines_per_page])

        page_count = len(pages_lines)

        # Build PDF stream objects
        stream_objs: List[bytes] = []
        for plines in pages_lines:
            stream = (
                f"BT /F1 10 Tf {margin_x} {margin_top} Td {line_height} TL "
            )
            for text, style in plines:
                if style == "empty":
                    stream += "T* "
                    continue

                clean_text = (
                    text.replace("\\", "\\\\")
                    .replace("(", "\\(")
                    .replace(")", "\\)")
                )

                if style == "title":
                    stream += f"/F2 16 Tf ({clean_text}) ' /F1 10 Tf "
                elif style == "h2":
                    stream += f"/F2 12 Tf ({clean_text}) ' /F1 10 Tf "
                elif style == "h3":
                    stream += f"/F2 10.5 Tf ({clean_text}) ' /F1 10 Tf "
                else:
                    stream += f"({clean_text}) ' "

            stream += "ET"
            stream_objs.append(stream.encode("latin-1", "replace"))

        # Assembly PDF Objects
        # 1: Catalog, 2: Pages, 3: F1 (Helvetica), 4: F2 (Helvetica-Bold)
        # 5 + i*2: Page obj, 6 + i*2: Contents stream obj
        objs: List[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            f"<< /Type /Pages /Kids [{' '.join(f'{5 + i*2} 0 R' for i in range(page_count))}] /Count {page_count} >>".encode(),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        ]

        for i in range(page_count):
            content_num = 6 + i * 2
            sb = stream_objs[i]
            objs.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
                f"/Contents {content_num} 0 R /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>".encode()
            )
            objs.append(b"<< /Length " + str(len(sb)).encode() + b" >>\nstream\n" + sb + b"\nendstream")

        out = [b"%PDF-1.4\n"]
        offsets: List[int] = []
        for i, o in enumerate(objs, 1):
            offsets.append(sum(len(x) for x in out))
            out.append(f"{i} 0 obj\n".encode() + o + b"\nendobj\n")

        xref_offset = sum(len(x) for x in out)
        out.append(b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n")
        for off in offsets:
            out.append(f"{off:010d} 00000 n \n".encode())

        out.append(
            b"trailer\n<< /Size "
            + str(len(objs) + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n"
            + str(xref_offset).encode()
            + b"\n%%EOF\n"
        )

        pdf_bytes = b"".join(out)

        # Validate with pypdf
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            if len(reader.pages) < 1:
                logger.warning("Generated PDF has no pages.")
        except Exception as exc:
            logger.error("Generated PDF validation warning: %s", exc)

        return pdf_bytes

    # -----------------------------------------------------------------------
    # Workspace Integration
    # -----------------------------------------------------------------------

    def save_package_to_workspace(
        self,
        job_id: str,
        version: int,
        resume_md: str,
        cover_letter_md: str,
        resume_docx: bytes,
        resume_pdf: bytes,
        cover_letter_docx: bytes,
        cover_letter_pdf: bytes,
    ) -> Dict[str, str]:
        """Saves generated documents into the file workspace directory structure."""
        if not self.workspace_root:
            return {}

        base_dir = self.workspace_root / "job_hunting" / "documents" / job_id
        base_dir.mkdir(parents=True, exist_ok=True)

        res_docx_path = base_dir / f"v{version}_resume.docx"
        res_pdf_path = base_dir / f"v{version}_resume.pdf"
        res_md_path = base_dir / f"v{version}_resume.md"

        cl_docx_path = base_dir / f"v{version}_cover_letter.docx"
        cl_pdf_path = base_dir / f"v{version}_cover_letter.pdf"
        cl_md_path = base_dir / f"v{version}_cover_letter.md"

        res_docx_path.write_bytes(resume_docx)
        res_pdf_path.write_bytes(resume_pdf)
        res_md_path.write_text(resume_md, encoding="utf-8")

        cl_docx_path.write_bytes(cover_letter_docx)
        cl_pdf_path.write_bytes(cover_letter_pdf)
        cl_md_path.write_text(cover_letter_md, encoding="utf-8")

        return {
            "docx_resume_path": str(res_docx_path.resolve()),
            "pdf_resume_path": str(res_pdf_path.resolve()),
            "docx_cover_letter_path": str(cl_docx_path.resolve()),
            "pdf_cover_letter_path": str(cl_pdf_path.resolve()),
        }

