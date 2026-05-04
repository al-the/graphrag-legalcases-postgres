from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional
from uuid import UUID

import fastapi
from fastapi import Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from fastapi_app.auth.auth_config import current_active_user
from fastapi_app.auth.auth_models import User
from fastapi_app.db.document_models import DocumentSource, GraphragRun
from fastapi_app.dependencies import DBSession

logger = logging.getLogger(__name__)
router = fastapi.APIRouter(prefix="/api", tags=["workflows"])


class IngestRequest(BaseModel):
    source_keys: list[str]
    since_date: Optional[str] = None


@router.post("/workflows/ingest")
async def trigger_ingest(
    body: IngestRequest,
    session: DBSession,
    user: User = Depends(current_active_user),
):
    from fastapi_app.workers.workflow_tasks import orchestrate_ingestion
    task = orchestrate_ingestion.apply_async(
        kwargs={"source_keys": body.source_keys, "since_date": body.since_date},
        queue="low",
    )
    return {"task_id": task.id, "status": "queued", "source_keys": body.source_keys}


@router.get("/workflows/runs")
async def list_runs(
    session: DBSession,
    user: User = Depends(current_active_user),
    limit: int = Query(20, le=100),
):
    rows = await session.execute(
        select(GraphragRun).order_by(GraphragRun.created_at.desc()).limit(limit)
    )
    return [r.to_dict() for r in rows.scalars().all()]


@router.get("/workflows/runs/{run_id}")
async def get_run(
    run_id: UUID,
    session: DBSession,
    user: User = Depends(current_active_user),
):
    row = await session.execute(select(GraphragRun).where(GraphragRun.id == run_id))
    run = row.scalars().first()
    if not run:
        raise HTTPException(404, "Run not found")
    return run.to_dict()


@router.get("/workflows/runs/{run_id}/logs")
async def stream_run_logs(
    run_id: UUID,
    user: User = Depends(current_active_user),
):
    """SSE stream of workflow run status updates."""
    async def event_generator():
        for _ in range(60):  # poll up to 60s
            yield f"data: {json.dumps({'run_id': str(run_id), 'status': 'polling'})}\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/sources")
async def list_sources(
    session: DBSession,
    user: User = Depends(current_active_user),
):
    rows = await session.execute(select(DocumentSource).where(DocumentSource.is_active == True))
    return [s.to_dict() for s in rows.scalars().all()]


@router.post("/sources/{source_key}/crawl")
async def crawl_source(
    source_key: str,
    session: DBSession,
    user: User = Depends(current_active_user),
    since_date: Optional[str] = Query(None),
):
    from fastapi_app.workers.workflow_tasks import orchestrate_ingestion
    task = orchestrate_ingestion.apply_async(
        kwargs={"source_keys": [source_key], "since_date": since_date},
        queue="low",
    )
    return {"task_id": task.id, "source_key": source_key, "status": "queued"}
