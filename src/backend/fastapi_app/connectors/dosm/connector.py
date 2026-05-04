from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from fastapi_app.connectors.base import BaseConnector, DocumentMetadata

logger = logging.getLogger(__name__)

DOSM_BASE = "https://dosm.gov.my"
DOSM_PUBLICATIONS = f"{DOSM_BASE}/portal-main/release-content"


class DOSMConnector(BaseConnector):
    source_key = "dosm"

    async def discover(self, since: Optional[datetime] = None) -> list[DocumentMetadata]:
        docs: list[DocumentMetadata] = []
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                resp = await client.get(DOSM_PUBLICATIONS)
                resp.raise_for_status()
            except Exception as e:
                logger.warning("DOSM fetch failed: %s", e)
                return docs

            soup = BeautifulSoup(resp.text, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if not href.lower().endswith(".pdf"):
                    continue
                url = href if href.startswith("http") else f"{DOSM_BASE}{href}"
                docs.append(DocumentMetadata(
                    external_id=url,
                    title=link.get_text(strip=True) or Path(url).stem,
                    source_url=url,
                    doc_type="dosm_publication",
                    language="bilingual",
                    metadata={"source": "dosm"},
                ))

        logger.info("DOSM: discovered %d documents", len(docs))
        return docs

    async def download(self, doc_meta: DocumentMetadata, dest_dir: Path) -> Path:
        from fastapi_app.ocr.ocr_router import download_pdf
        dest = dest_dir / f"dosm_{Path(doc_meta.source_url).stem}.pdf"
        await download_pdf(doc_meta.source_url, dest)
        return dest
