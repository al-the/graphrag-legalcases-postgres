from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi_app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_ocr_job(self, ocr_job_id: str) -> dict:
    """Download PDF, run OCR, store chunks with embeddings."""
    return asyncio.get_event_loop().run_until_complete(_process_ocr_job_async(ocr_job_id))


async def _process_ocr_job_async(ocr_job_id: str) -> dict:
    import hashlib
    from datetime import datetime, timezone

    from dotenv import load_dotenv
    from sqlalchemy import select, update

    load_dotenv(override=True)

    from fastapi_app.db.document_models import Document, DocumentChunk, OcrJob
    from fastapi_app.ocr.chunk_builder import build_chunks
    from fastapi_app.ocr.ocr_router import download_pdf, run_ocr
    from fastapi_app.postgres_engine import create_postgres_engine_from_env

    engine = await create_postgres_engine_from_env()

    async with engine.begin() as conn:
        # Load job + document
        row = await conn.execute(
            select(OcrJob).where(OcrJob.id == UUID(ocr_job_id))
        )
        job = row.scalars().first()
        if not job:
            raise ValueError(f"OCR job {ocr_job_id} not found")

        doc_row = await conn.execute(
            select(Document).where(Document.id == job.document_id)
        )
        doc = doc_row.scalars().first()
        if not doc:
            raise ValueError(f"Document {job.document_id} not found")

        # Mark running
        await conn.execute(
            update(OcrJob)
            .where(OcrJob.id == job.id)
            .values(status="running", started_at=datetime.now(timezone.utc), attempt_count=job.attempt_count + 1)
        )
        await conn.execute(
            update(Document).where(Document.id == doc.id).values(ocr_status="processing")
        )

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = Path(tmp.name)

        if doc.source_url:
            await download_pdf(doc.source_url, pdf_path)
        elif doc.storage_path:
            # already on disk / blob; assume storage_path is local for workers
            pdf_path = Path(doc.storage_path)
        else:
            raise ValueError("No source_url or storage_path on document")

        ocr_result = await run_ocr(
            document_id=str(doc.id),
            pdf_path=pdf_path,
            doc_type=doc.doc_type,
            engine=job.ocr_engine,
        )

        chunks = build_chunks(ocr_result.markdown_text)

        # Generate embeddings in batches
        embeddings = await _embed_chunks(chunks)

        async with engine.begin() as conn:
            for chunk, vector in zip(chunks, embeddings):
                await conn.execute(
                    DocumentChunk.__table__.insert().values(
                        document_id=doc.id,
                        chunk_index=chunk.chunk_index,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        section_title=chunk.section_title,
                        text=chunk.text,
                        language=chunk.language,
                        n_tokens=chunk.n_tokens,
                        chunk_vector=vector,
                        metadata={},
                    )
                )

            await conn.execute(
                update(OcrJob)
                .where(OcrJob.id == job.id)
                .values(
                    status="done",
                    completed_at=datetime.now(timezone.utc),
                    page_count=ocr_result.page_count,
                    word_count=ocr_result.word_count,
                    detected_language=ocr_result.detected_language,
                )
            )
            await conn.execute(
                update(Document)
                .where(Document.id == doc.id)
                .values(ocr_status="done", page_count=ocr_result.page_count)
            )

        return {"status": "done", "chunk_count": len(chunks)}

    except Exception as exc:
        logger.exception("OCR job %s failed", ocr_job_id)
        async with engine.begin() as conn:
            await conn.execute(
                update(OcrJob)
                .where(OcrJob.id == UUID(ocr_job_id))
                .values(status="failed", error_message=str(exc)[:1000])
            )
            await conn.execute(
                update(Document)
                .where(Document.id == UUID(str(doc.id)))
                .values(ocr_status="failed")
            )
        raise
    finally:
        await engine.dispose()


async def _embed_chunks(chunks) -> list:
    """Generate embeddings for all chunks via Azure OpenAI."""
    import os
    from openai import AsyncAzureOpenAI

    client = AsyncAzureOpenAI(
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )
    model = os.environ.get("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-small")

    BATCH = 16
    vectors = []
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i: i + BATCH]
        resp = await client.embeddings.create(
            model=model,
            input=[c.text for c in batch],
        )
        vectors.extend([item.embedding for item in resp.data])
    return vectors
