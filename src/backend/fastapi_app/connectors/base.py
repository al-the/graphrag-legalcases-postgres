from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class DocumentMetadata:
    external_id: str
    title: str
    source_url: str
    doc_type: str
    publication_date: Optional[datetime] = None
    language: str = "en"
    metadata: dict = field(default_factory=dict)


class BaseConnector(ABC):
    source_key: str

    @abstractmethod
    async def discover(self, since: Optional[datetime] = None) -> list[DocumentMetadata]:
        """Return list of new/updated documents since given date."""

    @abstractmethod
    async def download(self, doc_meta: DocumentMetadata, dest_dir: Path) -> Path:
        """Download PDF to dest_dir, return local path."""

    async def run(self, since: Optional[datetime] = None) -> list[str]:
        """Full cycle: discover → download → create document records → enqueue OCR."""
        from fastapi_app.postgres_engine import create_postgres_engine_from_env
        from fastapi_app.routes.document_routes import _get_or_create_source
        from fastapi_app.db.document_models import Document, OcrJob
        from fastapi_app.ocr.ocr_router import select_engine
        from sqlalchemy import select
        import hashlib, tempfile
        from pathlib import Path

        discovered = await self.discover(since=since)
        if not discovered:
            return []

        engine = await create_postgres_engine_from_env()
        document_ids: list[str] = []

        import os
        storage_dir = Path(os.environ.get("PDF_STORAGE_DIR", "/tmp/mykg_pdfs"))
        storage_dir.mkdir(parents=True, exist_ok=True)

        async with engine.begin() as conn:
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy.orm import sessionmaker
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            src = await _get_or_create_source(session, self.source_key)

            for meta in discovered:
                # Dedup by external_id
                existing = await session.execute(
                    select(Document).where(
                        Document.source_id == src.id,
                        Document.external_id == meta.external_id,
                    )
                )
                if existing.scalars().first():
                    continue

                try:
                    pdf_path = await self.download(meta, storage_dir)
                    sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()

                    dup = await session.execute(
                        select(Document).where(Document.file_hash == sha256)
                    )
                    if dup.scalars().first():
                        continue

                    doc = Document(
                        source_id=src.id,
                        external_id=meta.external_id,
                        doc_type=meta.doc_type,
                        title=meta.title,
                        source_url=meta.source_url,
                        storage_path=str(pdf_path),
                        file_hash=sha256,
                        file_size_bytes=pdf_path.stat().st_size,
                        language=meta.language,
                        publication_date=meta.publication_date,
                        metadata_=meta.metadata,
                        ocr_status="queued",
                    )
                    session.add(doc)
                    await session.flush()

                    job = OcrJob(
                        document_id=doc.id,
                        ocr_engine=select_engine(meta.doc_type),
                    )
                    session.add(job)
                    await session.flush()

                    document_ids.append(str(doc.id))
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(
                        "Failed to process %s: %s", meta.external_id, e
                    )

            await session.commit()

        # Dispatch OCR tasks
        from fastapi_app.workers.ocr_tasks import process_ocr_job
        for doc_id in document_ids:
            process_ocr_job.apply_async(args=[doc_id], queue="default")

        await engine.dispose()
        return document_ids
