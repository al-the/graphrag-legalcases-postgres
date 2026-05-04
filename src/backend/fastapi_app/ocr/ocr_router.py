from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import httpx

from fastapi_app.ocr.models import OCRResult

logger = logging.getLogger(__name__)

# Map doc_type → preferred OCR engine
DOC_TYPE_ENGINE_MAP: dict[str, str] = {
    "hansard_debate":     "marker-pdf",
    "dosm_publication":   "marker-pdf",
    "policy_paper":       "marker-pdf",
    "regulation":         "marker-pdf",
    "annual_report":      "azure-di",
    "financial_report":   "azure-di",
}


def select_engine(doc_type: str) -> str:
    """Return engine name based on doc_type; fallback to marker-pdf."""
    return DOC_TYPE_ENGINE_MAP.get(doc_type, "marker-pdf")


def _azure_di_available() -> bool:
    return bool(os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"))


def _google_docai_available() -> bool:
    return bool(os.environ.get("GOOGLE_DOCAI_PROCESSOR_ID"))


async def run_ocr(document_id: str, pdf_path: Path, doc_type: str, engine: str | None = None) -> OCRResult:
    """Route a PDF to the appropriate OCR engine, with marker-pdf as fallback."""
    chosen = engine or select_engine(doc_type)

    # Degrade gracefully if cloud creds not configured
    if chosen == "azure-di" and not _azure_di_available():
        logger.warning("Azure DI not configured, falling back to marker-pdf")
        chosen = "marker-pdf"
    if chosen == "google-docai" and not _google_docai_available():
        logger.warning("Google Doc AI not configured, falling back to marker-pdf")
        chosen = "marker-pdf"

    logger.info("OCR engine=%s document_id=%s", chosen, document_id)

    if chosen == "azure-di":
        from fastapi_app.ocr.azure_di_adapter import run_azure_di
        result = await run_azure_di(document_id, pdf_path)
    elif chosen == "google-docai":
        from fastapi_app.ocr.google_docai_adapter import run_google_docai
        result = await run_google_docai(document_id, pdf_path)
    else:
        from fastapi_app.ocr.marker_adapter import run_marker
        result = await run_marker(document_id, pdf_path)

    return result


async def download_pdf(url: str, dest: Path) -> None:
    """Stream-download a PDF from a URL to a local path."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type and "octet-stream" not in content_type:
                logger.warning("Unexpected content-type %s for URL %s", content_type, url)
            with open(dest, "wb") as f:
                async for chunk in response.aiter_bytes(65536):
                    f.write(chunk)
