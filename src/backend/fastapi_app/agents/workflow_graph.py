"""LangGraph-based agentic ingestion workflow."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi_app.agents.state import WorkflowState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

async def discover_documents(state: WorkflowState) -> WorkflowState:
    """Run connectors to discover and download documents."""
    from fastapi_app.connectors.registry import ConnectorRegistry
    registry = ConnectorRegistry()
    all_ids: list[str] = []

    for key in state["source_keys"]:
        connector = registry.get(key)
        if not connector:
            state["errors"].append(f"No connector for: {key}")
            continue
        try:
            ids = await connector.run(since=state.get("since_date"))
            all_ids.extend(ids)
        except Exception as e:
            state["errors"].append(f"{key}: {e}")

    state["discovered_docs"] = all_ids
    logger.info("Discovered %d documents", len(all_ids))
    return state


async def wait_ocr_completion(state: WorkflowState) -> WorkflowState:
    """Poll until all OCR jobs for discovered documents finish or fail."""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    from fastapi_app.db.document_models import Document
    from fastapi_app.postgres_engine import create_postgres_engine_from_env
    from sqlalchemy import select

    if not state["discovered_docs"]:
        return state

    engine = await create_postgres_engine_from_env()
    completed, failed = [], []
    max_polls = 120  # 10 min at 5s interval

    for _ in range(max_polls):
        async with engine.begin() as conn:
            rows = await conn.execute(
                select(Document.id, Document.ocr_status)
                .where(Document.id.in_([uuid.UUID(d) for d in state["discovered_docs"]]))
            )
            statuses = {str(r.id): r.ocr_status for r in rows}

        completed = [d for d, s in statuses.items() if s == "done"]
        failed = [d for d, s in statuses.items() if s == "failed"]
        pending = [d for d, s in statuses.items() if s in ("pending", "queued", "processing")]

        if not pending:
            break
        await asyncio.sleep(5)

    await engine.dispose()
    state["ocr_completed"] = completed
    state["ocr_failed"] = failed
    if failed:
        state["errors"].extend([f"OCR failed: {d}" for d in failed])
    return state


async def run_graphrag(state: WorkflowState) -> WorkflowState:
    """Dispatch GraphRAG pipeline for completed documents."""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    from fastapi_app.db.document_models import GraphragRun
    from fastapi_app.postgres_engine import create_postgres_engine_from_env

    doc_ids = state["ocr_completed"]
    if not doc_ids:
        state["errors"].append("No OCR-completed documents to process")
        return state

    engine = await create_postgres_engine_from_env()
    run_id = str(uuid.uuid4())
    async with engine.begin() as conn:
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        run = GraphragRun(id=uuid.UUID(run_id), status="queued", document_ids=[uuid.UUID(d) for d in doc_ids])
        session.add(run)
        await session.commit()

    await engine.dispose()

    from fastapi_app.workers.graphrag_tasks import run_graphrag_pipeline
    run_graphrag_pipeline.apply_async(args=[run_id, doc_ids], queue="low")
    state["graphrag_run_id"] = run_id
    return state


async def validate_results(state: WorkflowState) -> WorkflowState:
    """Check that entity and community counts are above thresholds."""
    if not state.get("graphrag_run_id"):
        state["validation_passed"] = False
        return state

    from dotenv import load_dotenv
    load_dotenv(override=True)
    from fastapi_app.db.document_models import GraphragRun
    from fastapi_app.postgres_engine import create_postgres_engine_from_env
    from sqlalchemy import select
    import uuid

    engine = await create_postgres_engine_from_env()
    max_polls = 180  # 15 min
    for _ in range(max_polls):
        async with engine.begin() as conn:
            row = await conn.execute(
                select(GraphragRun.status, GraphragRun.entity_count)
                .where(GraphragRun.id == uuid.UUID(state["graphrag_run_id"]))
            )
            run = row.fetchone()
            if run and run.status in ("done", "failed"):
                break
        await asyncio.sleep(5)

    await engine.dispose()
    state["validation_passed"] = bool(run and run.status == "done" and (run.entity_count or 0) > 0)
    if not state["validation_passed"]:
        state["errors"].append("GraphRAG validation failed: no entities or run failed")
    return state


async def finalize(state: WorkflowState) -> WorkflowState:
    state["status"] = "done" if state["validation_passed"] else (
        "partial" if state["ocr_completed"] else "failed"
    )
    logger.info("Workflow %s complete: status=%s docs=%d",
                state["run_id"], state["status"], len(state["ocr_completed"]))
    return state


# ---------------------------------------------------------------------------
# Build the LangGraph
# ---------------------------------------------------------------------------

def build_workflow():
    try:
        from langgraph.graph import StateGraph, END
    except ImportError:
        raise RuntimeError("langgraph is required: pip install langgraph")

    graph = StateGraph(WorkflowState)
    graph.add_node("discover", discover_documents)
    graph.add_node("wait_ocr", wait_ocr_completion)
    graph.add_node("run_graphrag", run_graphrag)
    graph.add_node("validate", validate_results)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("discover")
    graph.add_edge("discover", "wait_ocr")
    graph.add_edge("wait_ocr", "run_graphrag")
    graph.add_edge("run_graphrag", "validate")
    graph.add_edge("validate", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


async def run_ingestion_workflow(
    source_keys: list[str],
    since_date: Optional[datetime] = None,
) -> WorkflowState:
    workflow = build_workflow()
    initial_state: WorkflowState = {
        "run_id": str(uuid.uuid4()),
        "source_keys": source_keys,
        "since_date": since_date,
        "discovered_docs": [],
        "ocr_completed": [],
        "ocr_failed": [],
        "graphrag_run_id": None,
        "validation_passed": False,
        "errors": [],
        "status": "running",
    }
    return await workflow.ainvoke(initial_state)
