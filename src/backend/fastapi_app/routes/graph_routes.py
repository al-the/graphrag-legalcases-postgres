from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

import fastapi
from fastapi import Depends, HTTPException, Query
from sqlalchemy import func, select, text

from fastapi_app.auth.auth_config import current_active_user, current_admin_user
from fastapi_app.auth.auth_models import User
from fastapi_app.db.document_models import Document
from fastapi_app.dependencies import DBSession

logger = logging.getLogger(__name__)
router = fastapi.APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/entities")
async def list_entities(
    session: DBSession,
    user: User = Depends(current_active_user),
    entity_type: Optional[str] = Query(None),
    source_key: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """Paginated entity list with optional type/source/text filters."""
    filters = ["1=1"]
    params: dict = {}

    if entity_type:
        filters.append("e.entity_type = :entity_type")
        params["entity_type"] = entity_type
    if q:
        filters.append("e.title ILIKE :q")
        params["q"] = f"%{q}%"

    where = " AND ".join(filters)
    sql = text(f"""
        SELECT e.id, e.title, e.entity_type, e.description,
               e.degree, e.frequency, e.community_ids
        FROM final_entities e
        WHERE {where}
        ORDER BY e.degree DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    rows = await session.execute(sql, {**params, "limit": limit, "offset": offset})
    return [dict(r._mapping) for r in rows]


@router.get("/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    session: DBSession,
    user: User = Depends(current_active_user),
):
    row = await session.execute(
        text("SELECT * FROM final_entities WHERE id = :id"),
        {"id": entity_id},
    )
    entity = row.fetchone()
    if not entity:
        raise HTTPException(404, "Entity not found")

    # Related entities via final_relationships
    rels = await session.execute(
        text("""
            SELECT r.id, r.source_entity_id, r.target_entity_id, r.description, r.weight,
                   CASE WHEN r.source_entity_id = :id THEN e2.title ELSE e1.title END AS related_title,
                   CASE WHEN r.source_entity_id = :id THEN e2.entity_type ELSE e1.entity_type END AS related_type
            FROM final_relationships r
            JOIN final_entities e1 ON e1.id = r.source_entity_id
            JOIN final_entities e2 ON e2.id = r.target_entity_id
            WHERE r.source_entity_id = :id OR r.target_entity_id = :id
            ORDER BY r.weight DESC NULLS LAST
            LIMIT 50
        """),
        {"id": entity_id},
    )
    return {
        **dict(entity._mapping),
        "relationships": [dict(r._mapping) for r in rels],
    }


@router.get("/entities/{entity_id}/docs")
async def get_entity_documents(
    entity_id: str,
    session: DBSession,
    user: User = Depends(current_active_user),
):
    row = await session.execute(
        text("SELECT document_ids FROM final_entities WHERE id = :id"),
        {"id": entity_id},
    )
    entity = row.fetchone()
    if not entity or not entity.document_ids:
        return []
    docs = await session.execute(
        select(Document).where(Document.id.in_([UUID(d) for d in entity.document_ids]))
    )
    return [d.to_dict() for d in docs.scalars().all()]


@router.get("/communities")
async def list_communities(
    session: DBSession,
    user: User = Depends(current_active_user),
    level: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
):
    where = "WHERE level = :level" if level is not None else ""
    sql = text(f"""
        SELECT id, community, level, title, entity_ids
        FROM final_communities
        {where}
        ORDER BY community
        LIMIT :limit
    """)
    params = {"limit": limit}
    if level is not None:
        params["level"] = level
    rows = await session.execute(sql, params)
    return [dict(r._mapping) for r in rows]


@router.get("/communities/{community_id}")
async def get_community(
    community_id: str,
    session: DBSession,
    user: User = Depends(current_active_user),
):
    row = await session.execute(
        text("SELECT * FROM final_communities WHERE id = :id"),
        {"id": community_id},
    )
    community = row.fetchone()
    if not community:
        raise HTTPException(404, "Community not found")

    report = await session.execute(
        text("SELECT * FROM final_community_reports WHERE community_id = :cid LIMIT 1"),
        {"cid": community_id},
    )
    report_row = report.fetchone()
    return {
        **dict(community._mapping),
        "report": dict(report_row._mapping) if report_row else None,
    }


@router.get("/subgraph")
async def get_subgraph(
    session: DBSession,
    user: User = Depends(current_active_user),
    entity_id: str = Query(...),
    hops: int = Query(2, le=3),
):
    """Return ego-graph: entity + N-hop neighbors via Apache AGE."""
    # Use recursive CTE over relational tables (faster than AGE for small hops)
    sql = text("""
        WITH RECURSIVE subgraph(entity_id, depth) AS (
            SELECT :entity_id::text, 0
            UNION
            SELECT
                CASE WHEN r.source_entity_id = s.entity_id
                     THEN r.target_entity_id
                     ELSE r.source_entity_id END,
                s.depth + 1
            FROM subgraph s
            JOIN final_relationships r
              ON (r.source_entity_id = s.entity_id OR r.target_entity_id = s.entity_id)
            WHERE s.depth < :hops
        )
        SELECT DISTINCT e.id, e.title, e.entity_type, e.description, e.degree,
                        sg.depth
        FROM subgraph sg
        JOIN final_entities e ON e.id = sg.entity_id
    """)
    nodes_rows = await session.execute(sql, {"entity_id": entity_id, "hops": hops})
    node_ids = {r.id for r in nodes_rows}
    nodes_rows = await session.execute(sql, {"entity_id": entity_id, "hops": hops})
    nodes = [dict(r._mapping) for r in nodes_rows]

    edges_sql = text("""
        SELECT r.id, r.source_entity_id, r.target_entity_id, r.description, r.weight
        FROM final_relationships r
        WHERE r.source_entity_id = ANY(:ids) AND r.target_entity_id = ANY(:ids)
    """)
    edges_rows = await session.execute(edges_sql, {"ids": list(node_ids)})
    edges = [dict(r._mapping) for r in edges_rows]

    return {"nodes": nodes, "edges": edges}


@router.get("/search")
async def search_entities(
    session: DBSession,
    user: User = Depends(current_active_user),
    q: str = Query(..., min_length=1),
    entity_types: Optional[str] = Query(None, description="Comma-separated types"),
    limit: int = Query(20, le=100),
):
    types_filter = ""
    params: dict = {"q": f"%{q}%", "limit": limit}
    if entity_types:
        types = [t.strip() for t in entity_types.split(",")]
        types_filter = "AND entity_type = ANY(:types)"
        params["types"] = types
    sql = text(f"""
        SELECT id, title, entity_type, description, degree
        FROM final_entities
        WHERE title ILIKE :q {types_filter}
        ORDER BY degree DESC NULLS LAST
        LIMIT :limit
    """)
    rows = await session.execute(sql, params)
    return [dict(r._mapping) for r in rows]


@router.post("/cypher")
async def run_cypher(
    body: dict,
    session: DBSession,
    user: User = Depends(current_admin_user),
):
    """Execute a raw OpenCypher query via Apache AGE (admin only)."""
    cypher_query = body.get("query", "")
    if not cypher_query:
        raise HTTPException(400, "query is required")
    sql = text("""
        SELECT * FROM ag_catalog.cypher('knowledge_graph', $$ :query $$ ) AS (result agtype)
    """.replace(":query", cypher_query))
    rows = await session.execute(sql)
    return [dict(r._mapping) for r in rows]
