from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from fastapi_app.connectors.base import BaseConnector, DocumentMetadata

logger = logging.getLogger(__name__)

OECD_API = "https://data.oecd.org/api/content/v1/items"


class OECDConnector(BaseConnector):
    source_key = "oecd"

    async def discover(self, since: Optional[datetime] = None) -> list[DocumentMetadata]:
        docs: list[DocumentMetadata] = []
        params = {
            "filters": "type:indicator,countryCode:MYS",
            "format": "json",
            "lang": "en",
            "count": 50,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(OECD_API, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.warning("OECD API fetch failed: %s", e)
                return docs

            for item in data.get("items", []):
                pdf_url = next(
                    (lnk.get("uri") for lnk in item.get("links", []) if lnk.get("type") == "application/pdf"),
                    None,
                )
                if not pdf_url:
                    continue
                docs.append(DocumentMetadata(
                    external_id=item.get("id", pdf_url),
                    title=item.get("title", {}).get("en", Path(pdf_url).stem),
                    source_url=pdf_url,
                    doc_type="policy_paper",
                    language="en",
                    metadata={"source": "oecd", "doi": item.get("doi", "")},
                ))

        logger.info("OECD: discovered %d documents", len(docs))
        return docs

    async def download(self, doc_meta: DocumentMetadata, dest_dir: Path) -> Path:
        from fastapi_app.ocr.ocr_router import download_pdf
        dest = dest_dir / f"oecd_{Path(doc_meta.source_url).stem}.pdf"
        await download_pdf(doc_meta.source_url, dest)
        return dest
