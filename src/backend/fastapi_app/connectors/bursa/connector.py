from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from fastapi_app.connectors.base import BaseConnector, DocumentMetadata

logger = logging.getLogger(__name__)

BURSA_DISCLOSURE_BASE = "https://disclosure.bursa.com.my"


class BursaConnector(BaseConnector):
    source_key = "bursa"

    async def discover(self, since: Optional[datetime] = None) -> list[DocumentMetadata]:
        """Discover annual report PDFs from Bursa Malaysia disclosure portal."""
        docs: list[DocumentMetadata] = []
        # Bursa uses a search API; query for annual reports
        search_url = f"{BURSA_DISCLOSURE_BASE}/html/portal/en/investor/latest_disclosure.html"

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                resp = await client.get(search_url)
                resp.raise_for_status()
            except Exception as e:
                logger.warning("Bursa disclosure fetch failed: %s", e)
                return docs

            soup = BeautifulSoup(resp.text, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if not href.lower().endswith(".pdf"):
                    continue
                url = href if href.startswith("http") else f"{BURSA_DISCLOSURE_BASE}{href}"
                title = link.get_text(strip=True) or Path(url).stem

                doc_type = "annual_report" if "annual" in title.lower() else "financial_report"
                docs.append(DocumentMetadata(
                    external_id=url,
                    title=title,
                    source_url=url,
                    doc_type=doc_type,
                    language="en",
                    metadata={"source": "bursa"},
                ))

        logger.info("Bursa: discovered %d documents", len(docs))
        return docs

    async def download(self, doc_meta: DocumentMetadata, dest_dir: Path) -> Path:
        from fastapi_app.ocr.ocr_router import download_pdf
        dest = dest_dir / f"bursa_{Path(doc_meta.source_url).stem}.pdf"
        await download_pdf(doc_meta.source_url, dest)
        return dest
