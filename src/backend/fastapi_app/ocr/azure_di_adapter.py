from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi_app.ocr.models import OCRResult

logger = logging.getLogger(__name__)


async def run_azure_di(document_id: str, pdf_path: Path) -> OCRResult:
    """Extract text from a PDF using Azure Document Intelligence (layout model)."""
    from azure.ai.formrecognizer.aio import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential

    endpoint = os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"]
    key = os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"]

    client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))

    async with client:
        with open(pdf_path, "rb") as f:
            poller = await client.begin_analyze_document("prebuilt-layout", f)
        result = await poller.result()

    # Convert Azure DI result to markdown-style text
    lines: list[str] = []
    for page in result.pages:
        lines.append(f"\n<!-- page {page.page_number} -->\n")
        for line in (page.lines or []):
            lines.append(line.content)

    # Include detected tables as simple markdown tables
    for table in (result.tables or []):
        lines.append("\n")
        header_row = [c.content for c in table.cells if c.row_index == 0]
        if header_row:
            lines.append("| " + " | ".join(header_row) + " |")
            lines.append("|" + "---|" * len(header_row))
        for row_idx in range(1, table.row_count):
            row_cells = [c.content for c in table.cells if c.row_index == row_idx]
            lines.append("| " + " | ".join(row_cells) + " |")
        lines.append("")

    markdown_text = "\n".join(lines)
    page_count = len(result.pages)
    word_count = len(markdown_text.split())

    from fastapi_app.ocr.language_detector import detect_bilingual
    detected_language = detect_bilingual(markdown_text)

    return OCRResult(
        document_id=document_id,
        markdown_text=markdown_text,
        page_count=page_count,
        word_count=word_count,
        detected_language=detected_language,
        output_path="",
    )
