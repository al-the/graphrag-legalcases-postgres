from __future__ import annotations

import asyncio
import logging

from fastapi_app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def orchestrate_ingestion(self, source_keys: list[str], since_date: str | None = None) -> dict:
    """Full pipeline: discover → download → OCR → GraphRAG for given sources."""
    return asyncio.get_event_loop().run_until_complete(
        _orchestrate_async(source_keys, since_date)
    )


async def _orchestrate_async(source_keys: list[str], since_date: str | None) -> dict:
    from datetime import datetime

    from dotenv import load_dotenv
    load_dotenv(override=True)

    since = datetime.fromisoformat(since_date) if since_date else None

    from fastapi_app.connectors.registry import ConnectorRegistry
    registry = ConnectorRegistry()

    all_document_ids: list[str] = []
    for key in source_keys:
        connector = registry.get(key)
        if not connector:
            logger.warning("No connector for source_key=%s", key)
            continue
        doc_ids = await connector.run(since=since)
        all_document_ids.extend(doc_ids)
        logger.info("Source %s: %d new documents", key, len(doc_ids))

    return {"source_keys": source_keys, "document_count": len(all_document_ids), "document_ids": all_document_ids}
