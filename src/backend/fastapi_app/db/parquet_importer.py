"""Import GraphRAG Parquet output into PostgreSQL tables and Apache AGE graph."""
from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

logger = logging.getLogger(__name__)


async def import_graphrag_output(
    engine,
    output_dir: Path,
    graphrag_run_id: str,
    document_ids: list[str],
) -> dict:
    """Read graphrag Parquet outputs and upsert into PostgreSQL."""
    try:
        import pandas as pd
    except ImportError:
        raise RuntimeError("pandas is required for Parquet import")

    stats = {"entity_count": 0, "relationship_count": 0, "community_count": 0}

    artifacts_dir = output_dir / "artifacts"
    if not artifacts_dir.exists():
        # Try flat output layout
        artifacts_dir = output_dir

    # --- Entities ---
    entity_file = _find_parquet(artifacts_dir, "entities")
    if entity_file:
        df = pd.read_parquet(entity_file)
        async with engine.begin() as conn:
            from sqlalchemy import text
            for _, row in df.iterrows():
                await conn.execute(text("""
                    INSERT INTO final_entities
                        (id, human_readable_id, title, entity_type, description, source_ids, graphrag_run_id)
                    VALUES (:id, :hrid, :title, :etype, :desc, :sids, :run_id)
                    ON CONFLICT (id) DO UPDATE SET
                        description = EXCLUDED.description,
                        entity_type = EXCLUDED.entity_type,
                        graphrag_run_id = EXCLUDED.graphrag_run_id
                """), {
                    "id": str(row.get("id", "")),
                    "hrid": int(row.get("human_readable_id", 0)) if pd.notna(row.get("human_readable_id")) else None,
                    "title": str(row.get("title", "")),
                    "etype": str(row.get("type", "")),
                    "desc": str(row.get("description", "")) if pd.notna(row.get("description")) else None,
                    "sids": list(row.get("text_unit_ids", [])) if hasattr(row.get("text_unit_ids", []), "__iter__") else [],
                    "run_id": graphrag_run_id,
                })
        stats["entity_count"] = len(df)
        logger.info("Imported %d entities", len(df))

    # --- Relationships ---
    rel_file = _find_parquet(artifacts_dir, "relationships")
    if rel_file:
        df = pd.read_parquet(rel_file)
        async with engine.begin() as conn:
            from sqlalchemy import text
            for _, row in df.iterrows():
                await conn.execute(text("""
                    INSERT INTO final_relationships
                        (id, human_readable_id, source_entity_id, target_entity_id,
                         description, weight, source_ids, graphrag_run_id)
                    VALUES (:id, :hrid, :src, :tgt, :desc, :weight, :sids, :run_id)
                    ON CONFLICT (id) DO UPDATE SET
                        description = EXCLUDED.description,
                        weight = EXCLUDED.weight
                """), {
                    "id": str(row.get("id", "")),
                    "hrid": int(row.get("human_readable_id", 0)) if pd.notna(row.get("human_readable_id")) else None,
                    "src": str(row.get("source", "")),
                    "tgt": str(row.get("target", "")),
                    "desc": str(row.get("description", "")) if pd.notna(row.get("description")) else None,
                    "weight": float(row.get("weight", 1.0)),
                    "sids": list(row.get("text_unit_ids", [])) if hasattr(row.get("text_unit_ids", []), "__iter__") else [],
                    "run_id": graphrag_run_id,
                })
        stats["relationship_count"] = len(df)
        logger.info("Imported %d relationships", len(df))

    # --- Communities ---
    comm_file = _find_parquet(artifacts_dir, "communities")
    if comm_file:
        df = pd.read_parquet(comm_file)
        async with engine.begin() as conn:
            from sqlalchemy import text
            for _, row in df.iterrows():
                entity_ids = list(row.get("entity_ids", []))
                await conn.execute(text("""
                    INSERT INTO final_communities (id, community, level, title, entity_ids)
                    VALUES (:id, :comm, :level, :title, :eids)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        entity_ids = EXCLUDED.entity_ids
                """), {
                    "id": str(row.get("id", "")),
                    "comm": int(row.get("community", 0)),
                    "level": int(row.get("level", 0)),
                    "title": str(row.get("title", "")),
                    "eids": entity_ids,
                })
        stats["community_count"] = len(df)
        logger.info("Imported %d communities", len(df))

    # --- Community reports ---
    report_file = _find_parquet(artifacts_dir, "community_reports")
    if report_file:
        df = pd.read_parquet(report_file)
        async with engine.begin() as conn:
            from sqlalchemy import text
            for _, row in df.iterrows():
                await conn.execute(text("""
                    INSERT INTO final_community_reports
                        (community_id, community, level, title, summary, findings, rating, rating_explanation, full_content)
                    VALUES (:cid, :comm, :level, :title, :summary, :findings::jsonb, :rating, :rating_exp, :full)
                    ON CONFLICT (community_id) DO UPDATE SET
                        summary = EXCLUDED.summary,
                        findings = EXCLUDED.findings
                """), {
                    "cid": str(row.get("id", "")),
                    "comm": int(row.get("community", 0)),
                    "level": int(row.get("level", 0)),
                    "title": str(row.get("title", "")),
                    "summary": str(row.get("summary", "")),
                    "findings": str(row.get("findings", "[]")),
                    "rating": float(row.get("rank", 0)) if pd.notna(row.get("rank")) else None,
                    "rating_exp": str(row.get("rank_explanation", "")) if pd.notna(row.get("rank_explanation")) else None,
                    "full": str(row.get("full_content", "")),
                })
        logger.info("Imported %d community reports", len(df))

    await _update_age_graph(engine, graphrag_run_id)

    return stats


async def _update_age_graph(engine, graphrag_run_id: str) -> None:
    """Sync final_entities and final_relationships into Apache AGE knowledge_graph."""
    async with engine.begin() as conn:
        from sqlalchemy import text
        # Ensure knowledge_graph exists
        await conn.execute(text("SET search_path = ag_catalog, \"$user\", public"))
        try:
            await conn.execute(text("SELECT create_graph('knowledge_graph')"))
        except Exception:
            pass  # already exists

        # Upsert entity nodes
        entity_rows = await conn.execute(text(
            "SELECT id, title, entity_type, description FROM final_entities "
            "WHERE graphrag_run_id = :run_id"
        ), {"run_id": graphrag_run_id})
        for e in entity_rows:
            cypher = (
                f"MERGE (n:Entity {{id: '{e.id}'}}) "
                f"SET n.title = '{_esc(e.title)}', "
                f"n.type = '{_esc(e.entity_type or '')}', "
                f"n.description = '{_esc((e.description or '')[:200])}'"
            )
            try:
                await conn.execute(text(
                    f"SELECT * FROM ag_catalog.cypher('knowledge_graph', $$ {cypher} $$) AS (v agtype)"
                ))
            except Exception as ex:
                logger.debug("AGE entity upsert error: %s", ex)

        # Upsert relationship edges
        rel_rows = await conn.execute(text(
            "SELECT source_entity_id, target_entity_id, description, weight "
            "FROM final_relationships WHERE graphrag_run_id = :run_id"
        ), {"run_id": graphrag_run_id})
        for r in rel_rows:
            cypher = (
                f"MATCH (a:Entity {{id: '{r.source_entity_id}'}}), "
                f"(b:Entity {{id: '{r.target_entity_id}'}}) "
                f"MERGE (a)-[:RELATED {{weight: {r.weight or 1.0}}}]->(b)"
            )
            try:
                await conn.execute(text(
                    f"SELECT * FROM ag_catalog.cypher('knowledge_graph', $$ {cypher} $$) AS (v agtype)"
                ))
            except Exception as ex:
                logger.debug("AGE rel upsert error: %s", ex)

    logger.info("AGE knowledge_graph updated for run %s", graphrag_run_id)


def _find_parquet(base: Path, name: str) -> Path | None:
    for pattern in [f"*{name}*.parquet", f"**/*{name}*.parquet"]:
        matches = list(base.glob(pattern))
        if matches:
            return matches[0]
    return None


def _esc(s: str) -> str:
    return s.replace("'", "''").replace("\\", "\\\\")
