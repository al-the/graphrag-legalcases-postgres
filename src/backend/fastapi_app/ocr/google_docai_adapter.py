from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi_app.ocr.models import OCRResult

logger = logging.getLogger(__name__)


async def run_google_docai(document_id: str, pdf_path: Path) -> OCRResult:
    """Extract text using Google Cloud Document AI."""
    from google.api_core.client_options import ClientOptions
    from google.cloud import documentai

    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ.get("GOOGLE_DOCAI_LOCATION", "us")
    processor_id = os.environ["GOOGLE_DOCAI_PROCESSOR_ID"]

    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceAsyncClient(client_options=opts)
    processor_name = client.processor_path(project_id, location, processor_id)

    with open(pdf_path, "rb") as f:
        raw_document = documentai.RawDocument(content=f.read(), mime_type="application/pdf")

    request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)
    result = await client.process_document(request=request)
    doc = result.document

    # Build markdown-style text from Document AI layout
    lines: list[str] = []
    for page in doc.pages:
        lines.append(f"\n<!-- page {page.page_number} -->\n")
        for block in page.blocks:
            for para in block.paragraphs:
                para_text = "".join(
                    t.layout.text_anchor.content
                    for t in para.words
                    if t.layout and t.layout.text_anchor
                )
                if para_text.strip():
                    lines.append(para_text.strip())

    if not lines and doc.text:
        lines = [doc.text]

    markdown_text = "\n".join(lines)
    page_count = len(doc.pages)
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
