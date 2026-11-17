from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from app.core.config import settings


class DocumentParseError(Exception):
    def __init__(self, message: str, code: str = "DOCLING_PARSE_ERROR") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ParsedChunk:
    chunk_index: int
    section_heading: str | None
    page_numbers: list[int]
    content: str


@dataclass
class ParsedDocument:
    page_count: int
    chunks: list[ParsedChunk]
    pages: list[dict[str, Any]] = field(default_factory=list)


class LocalDocumentParser:
    def __init__(
        self,
        max_chunk_chars: int | None = None,
        converter: Any = None,
    ) -> None:
        self.max_chunk_chars = max_chunk_chars or min(settings.extraction_max_chunk_chars, 4000)
        self._converter = converter

    def _get_converter(self) -> Any:
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter, PdfFormatOption
                from docling.datamodel.pipeline_options import PdfPipelineOptions
                from docling.datamodel.base_models import InputFormat

                pipeline_options = PdfPipelineOptions(do_ocr=False, do_table_structure=False)
                self._converter = DocumentConverter(
                    format_options={
                        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                    }
                )
            except ImportError as exc:
                raise DocumentParseError(
                    "Docling is not installed in the local environment.",
                    code="DOCLING_PARSE_ERROR",
                ) from exc
            except Exception:
                try:
                    from docling.document_converter import DocumentConverter

                    self._converter = DocumentConverter()
                except ImportError as exc:
                    raise DocumentParseError(
                        "Docling is not installed in the local environment.",
                        code="DOCLING_PARSE_ERROR",
                    ) from exc
        return self._converter

    def parse_pdf(self, pdf_path: Path) -> ParsedDocument:
        if not pdf_path.exists():
            raise DocumentParseError("PDF file not found on local storage.", code="DOCLING_PARSE_ERROR")

        try:
            converter = self._get_converter()
            result = converter.convert(str(pdf_path))
            doc = result.document
        except DocumentParseError:
            raise
        except Exception as exc:
            raise DocumentParseError(
                f"Docling failed to parse PDF: {type(exc).__name__}",
                code="DOCLING_PARSE_ERROR",
            ) from exc

        page_count = max(len(getattr(doc, "pages", {}) or {}), 1)
        blocks: list[tuple[str | None, int, str]] = []
        page_texts: dict[int, list[str]] = {p: [] for p in range(1, page_count + 1)}
        current_heading: str | None = None

        iterate_items = getattr(doc, "iterate_items", None)
        if callable(iterate_items):
            for item, _level in iterate_items():
                label_name = getattr(getattr(item, "label", None), "name", "") or str(getattr(item, "label", ""))
                prov_list = getattr(item, "prov", None) or []
                raw_page_no = getattr(prov_list[0], "page_no", 1) if prov_list else 1
                page_no = max(int(raw_page_no), 1)
                if page_no not in page_texts:
                    page_texts[page_no] = []

                if "HEADER" in label_name.upper() and hasattr(item, "text") and item.text:
                    current_heading = item.text.strip()
                    block_text = f"## {current_heading}"
                    blocks.append((current_heading, page_no, block_text))
                    page_texts[page_no].append(block_text)
                elif "TABLE" in label_name.upper() and hasattr(item, "export_to_markdown"):
                    try:
                        table_md = item.export_to_markdown(doc=doc).strip()
                    except TypeError:
                        table_md = item.export_to_markdown().strip()
                    if table_md:
                        block_text = f"\n[TABLE]\n{table_md}\n[/TABLE]\n"
                        blocks.append((current_heading, page_no, block_text))
                        page_texts[page_no].append(block_text)
                elif hasattr(item, "text") and item.text and item.text.strip():
                    block_text = item.text.strip()
                    blocks.append((current_heading, page_no, block_text))
                    page_texts[page_no].append(block_text)

        if not blocks:
            export_md = getattr(doc, "export_to_markdown", None)
            markdown_fallback = export_md().strip() if callable(export_md) else ""
            if not markdown_fallback:
                raise DocumentParseError(
                    "No readable text or tables could be extracted from the PDF.",
                    code="DOCLING_PARSE_ERROR",
                )
            blocks.append((None, 1, markdown_fallback))
            page_texts[1] = [markdown_fallback]

        pages_list = [
            {"page_number": p, "text": "\n\n".join(page_texts.get(p, [])).strip()}
            for p in sorted(page_texts.keys())
        ]
        if not pages_list:
            pages_list = [{"page_number": 1, "text": ""}]

        chunks = self._group_blocks_into_chunks(blocks)
        return ParsedDocument(page_count=page_count, chunks=chunks, pages=pages_list)

    def _group_blocks_into_chunks(self, blocks: list[tuple[str | None, int, str]]) -> list[ParsedChunk]:
        chunks: list[ParsedChunk] = []
        buf: list[str] = []
        buf_len = 0
        pages: set[int] = set()
        active_heading: str | None = None
        last_page: int | None = None

        for heading, page_no, text in blocks:
            entry = f"[Page {page_no}] {text}" if page_no != last_page else text
            last_page = page_no
            text_len = len(entry) + 2
            if buf and (buf_len + text_len > self.max_chunk_chars):
                chunks.append(
                    ParsedChunk(
                        chunk_index=len(chunks),
                        section_heading=active_heading,
                        page_numbers=sorted(pages) or [1],
                        content="\n\n".join(buf),
                    )
                )
                buf = []
                buf_len = 0
                pages = set()

            if heading:
                active_heading = heading

            buf.append(entry)
            buf_len += text_len
            pages.add(max(int(page_no), 1))

        if buf:
            chunks.append(
                ParsedChunk(
                    chunk_index=len(chunks),
                    section_heading=active_heading,
                    page_numbers=sorted(pages) or [1],
                    content="\n\n".join(buf),
                )
            )

        return chunks
