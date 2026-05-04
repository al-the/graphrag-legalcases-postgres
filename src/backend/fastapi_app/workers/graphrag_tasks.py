from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi_app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2)
def run_graphrag_pipeline(self, graphrag_run_id: str, document_ids: list[str]) -> dict:
    return asyncio.get_event_loop().run_until_complete(
        _run_graphrag_async(graphrag_run_id, document_ids)
    )


async def _run_graphrag_async(graphrag_run_id: str, document_ids: list[str]) -> dict:
    from datetime import datetime, timezone

    from dotenv import load_dotenv
    from sqlalchemy import select, update

    load_dotenv(override=True)

    from fastapi_app.db.document_models import DocumentChunk, GraphragRun
    from fastapi_app.db.parquet_importer import import_graphrag_output
    from fastapi_app.postgres_engine import create_postgres_engine_from_env

    engine = await create_postgres_engine_from_env()

    async with engine.begin() as conn:
        await conn.execute(
            update(GraphragRun)
            .where(GraphragRun.id == UUID(graphrag_run_id))
            .values(status="running", started_at=datetime.now(timezone.utc))
        )

    try:
        with tempfile.TemporaryDirectory() as workdir:
            input_dir = Path(workdir) / "input"
            input_dir.mkdir()
            output_dir = Path(workdir) / "output"

            # Write chunk text files for graphrag to consume
            async with engine.begin() as conn:
                for doc_id in document_ids:
                    rows = await conn.execute(
                        select(DocumentChunk)
                        .where(DocumentChunk.document_id == UUID(doc_id))
                        .order_by(DocumentChunk.chunk_index)
                    )
                    chunks = rows.scalars().all()
                    if chunks:
                        text = "\n\n".join(c.text for c in chunks)
                        (input_dir / f"{doc_id}.txt").write_text(text, encoding="utf-8")

            # Copy settings.yaml to workdir
            settings_src = Path(__file__).parent.parent.parent.parent.parent / "graphrag_config" / "settings.yaml"
            if settings_src.exists():
                import shutil
                shutil.copy(settings_src, Path(workdir) / "settings.yaml")

            # Run graphrag index
            import subprocess, sys
            result = subprocess.run(
                [sys.executable, "-m", "graphrag", "index", "--root", workdir],
                capture_output=True, text=True, timeout=3600,
                env={**os.environ, "GRAPHRAG_INPUT_BASE_DIR": str(input_dir)},
            )
            if result.returncode != 0:
                raise RuntimeError(f"graphrag index failed: {result.stderr[:500]}")

            stats = await import_graphrag_output(engine, output_dir, graphrag_run_id, document_ids)

        async with engine.begin() as conn:
            await conn.execute(
                update(GraphragRun)
                .where(GraphragRun.id == UUID(graphrag_run_id))
                .values(
                    status="done",
                    completed_at=datetime.now(timezone.utc),
                    entity_count=stats.get("entity_count"),
                    relationship_count=stats.get("relationship_count"),
                    community_count=stats.get("community_count"),
                )
            )

        return stats

    except Exception as exc:
        logger.exception("GraphRAG run %s failed", graphrag_run_id)
        async with engine.begin() as conn:
            await conn.execute(
                update(GraphragRun)
                .where(GraphragRun.id == UUID(graphrag_run_id))
                .values(status="failed", error_message=str(exc)[:1000])
            )
        raise
    finally:
        await engine.dispose()
