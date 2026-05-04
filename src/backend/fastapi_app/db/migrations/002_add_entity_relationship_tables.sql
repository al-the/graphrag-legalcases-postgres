-- Migration 002: Add relational entity/relationship tables and provenance columns
-- These complement the Apache AGE graph; enable SQL-friendly filtering/aggregation.

-- ---------------------------------------------------------------------------
-- final_entities  (relational mirror of AGE Entity nodes)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS final_entities (
    id                  TEXT PRIMARY KEY,
    human_readable_id   INT,
    title               TEXT NOT NULL,
    entity_type         TEXT,
    description         TEXT,
    description_vector  vector(1536),
    source_ids          TEXT[],
    document_ids        UUID[],
    community_ids       TEXT[],
    degree              INT DEFAULT 0,
    frequency           INT DEFAULT 0,
    graphrag_run_id     UUID REFERENCES graphrag_runs(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entities_entity_type      ON final_entities (entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_title_trgm       ON final_entities USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_entities_document_ids     ON final_entities USING GIN (document_ids);
CREATE INDEX IF NOT EXISTS hnsw_entities_description     ON final_entities
    USING hnsw (description_vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE description_vector IS NOT NULL;

-- ---------------------------------------------------------------------------
-- final_relationships  (relational mirror of AGE RELATED edges)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS final_relationships (
    id                TEXT PRIMARY KEY,
    human_readable_id INT,
    source_entity_id  TEXT NOT NULL,
    target_entity_id  TEXT NOT NULL,
    description       TEXT,
    weight            FLOAT DEFAULT 1.0,
    combined_degree   INT,
    source_ids        TEXT[],
    document_ids      UUID[],
    graphrag_run_id   UUID REFERENCES graphrag_runs(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rels_source ON final_relationships (source_entity_id);
CREATE INDEX IF NOT EXISTS idx_rels_target ON final_relationships (target_entity_id);

-- ---------------------------------------------------------------------------
-- Additive provenance columns on existing GraphRAG tables
-- ---------------------------------------------------------------------------
ALTER TABLE final_documents
    ADD COLUMN IF NOT EXISTS document_id UUID REFERENCES documents(id),
    ADD COLUMN IF NOT EXISTS source_id   UUID REFERENCES document_sources(id);

ALTER TABLE final_text_units
    ADD COLUMN IF NOT EXISTS chunk_id    UUID REFERENCES document_chunks(id),
    ADD COLUMN IF NOT EXISTS document_id UUID REFERENCES documents(id);

-- pg_trgm for title search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
