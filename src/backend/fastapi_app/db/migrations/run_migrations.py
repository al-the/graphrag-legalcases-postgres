"""Run all pending SQL migrations in order."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

from fastapi_app.postgres_engine import create_postgres_engine_from_env

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent


async def run_migrations() -> None:
    engine = await create_postgres_engine_from_env()

    async with engine.begin() as conn:
        # Track applied migrations
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))

        sql_files = sorted(MIGRATIONS_DIR.glob("0*.sql"))
        for sql_file in sql_files:
            result = await conn.execute(
                text("SELECT 1 FROM schema_migrations WHERE filename = :fn"),
                {"fn": sql_file.name},
            )
            if result.fetchone():
                logger.info("Skipping already-applied migration: %s", sql_file.name)
                continue

            logger.info("Applying migration: %s", sql_file.name)
            sql = sql_file.read_text()
            await conn.execute(text(sql))
            await conn.execute(
                text("INSERT INTO schema_migrations (filename) VALUES (:fn)"),
                {"fn": sql_file.name},
            )
            logger.info("Applied: %s", sql_file.name)

    await engine.dispose()
    logger.info("All migrations complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv(override=True)
    asyncio.run(run_migrations())
