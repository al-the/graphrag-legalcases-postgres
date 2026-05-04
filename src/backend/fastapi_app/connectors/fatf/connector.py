from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from fastapi_app.connectors.base import BaseConnector, DocumentMetadata

logger = logging.getLogger(__name__)

FATF_MER_PAGE = "https://www.fatf-gafi.org/en/countries/detail/Malaysia.html"


class FATFConnector(BaseConnector):
    source_key = "fatf"

    async def discover(self, since: Optional[datetime] = None) -> list[DocumentMetadata]:
        docs: list[DocumentMetadata] = []
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                resp = await client.get(FATF_MER_PAGE)
                resp.raise_for_status()
            except Exception as e:
                logger.warning("FATF page fetch failed: %s", e)
                return docs

            soup = BeautifulSoup(resp.text, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if not href.lower().endswith(".pdf"):
                    continue
                url = href if href.startswith("http") else f"https://www.fatf-gafi.org{href}"
                docs.append(DocumentMetadata(
                    external_id=url,
                    title=link.get_text(strip=True) or Path(url).stem,
                    source_url=url,
                    doc_type="policy_paper",
                    language="en",
                    metadata={"source": "fatf", "country": "Malaysia"},
                ))

        logger.info("FATF: discovered %d documents", len(docs))
        return docs

    async def download(self, doc_meta: DocumentMetadata, dest_dir: Path) -> Path:
        from fastapi_app.ocr.ocr_router import download_pdf
        dest = dest_dir / f"fatf_{Path(doc_meta.source_url).stem}.pdf"
        await download_pdf(doc_meta.source_url, dest)
        return dest
