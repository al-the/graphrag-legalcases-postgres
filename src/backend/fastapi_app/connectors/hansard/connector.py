from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from fastapi_app.connectors.base import BaseConnector, DocumentMetadata

logger = logging.getLogger(__name__)

BASE_URL = "https://parlimen.gov.my"
HANSARD_INDEX = f"{BASE_URL}/hansard"


class HansardConnector(BaseConnector):
    source_key = "hansard"

    async def discover(self, since: Optional[datetime] = None) -> list[DocumentMetadata]:
        docs: list[DocumentMetadata] = []
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                resp = await client.get(HANSARD_INDEX)
                resp.raise_for_status()
            except Exception as e:
                logger.warning("Hansard index fetch failed: %s", e)
                return docs

            soup = BeautifulSoup(resp.text, "html.parser")
            # Hansard PDF links typically match patterns like /hansard/...pdf
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if not href.lower().endswith(".pdf"):
                    continue
                url = href if href.startswith("http") else f"{BASE_URL}{href}"

                pub_date = _extract_date_from_url(url)
                if since and pub_date and pub_date < since:
                    continue

                docs.append(DocumentMetadata(
                    external_id=url,
                    title=link.get_text(strip=True) or Path(url).stem,
                    source_url=url,
                    doc_type="hansard_debate",
                    publication_date=pub_date,
                    language="bilingual",
                    metadata={"source": "hansard"},
                ))

        logger.info("Hansard: discovered %d documents", len(docs))
        return docs

    async def download(self, doc_meta: DocumentMetadata, dest_dir: Path) -> Path:
        from fastapi_app.ocr.ocr_router import download_pdf
        dest = dest_dir / f"hansard_{Path(doc_meta.source_url).stem}.pdf"
        await download_pdf(doc_meta.source_url, dest)
        return dest


def _extract_date_from_url(url: str) -> Optional[datetime]:
    match = re.search(r"(\d{4})[_-](\d{1,2})[_-](\d{1,2})", url)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass
    return None
