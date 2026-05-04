-- Migration 001: Multi-source document framework
-- Additive only — no existing tables are modified or dropped

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- document_sources
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_key      TEXT UNIQUE NOT NULL,
    -- e.g. 'hansard', 'bursa', 'dosm', 'oecd', 'fatf', 'bnm', 'sc_malaysia', 'web', 'manual'
    display_name    TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    -- 'scraper' | 'api' | 'downloader' | 'manual_upload'
    base_url        TEXT,
    config          JSONB NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_crawled_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed well-known Malaysian and international sources
INSERT INTO document_sources (source_key, display_name, source_type, base_url) VALUES
    ('hansard',     'Hansard Malaysia (Parlimen)',          'scraper',   'https://parlimen.gov.my'),
    ('bursa',       'Bursa Malaysia',                      'scraper',   'https://disclosure.bursa.com.my'),
    ('dosm',        'DOSM Malaysia',                       'downloader','https://dosm.gov.my'),
    ('oecd',        'OECD iLibrary',                       'api',       'https://www.oecd-ilibrary.org'),
    ('fatf',        'FATF',                                'downloader','https://www.fatf-gafi.org'),
    ('bnm',         'Bank Negara Malaysia',                'scraper',   'https://www.bnm.gov.my'),
    ('sc_malaysia', 'Securities Commission Malaysia',      'scraper',   'https://www.sc.com.my'),
    ('web',         'Web (unknown domain)',                 'manual_upload', NULL),
    ('manual',      'Manual Upload',                       'manual_upload', NULL)
ON CONFLICT (source_key) DO NOTHING;

-- ---------------------------------------------------------------------------
-- documents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id        UUID NOT NULL REFERENCES document_sources(id),
    external_id      TEXT,
    doc_type         TEXT NOT NULL,
    -- hansard_debate | annual_report | financial_report | dosm_publication
    -- | policy_paper  | regulation
    title            TEXT NOT NULL,
    title_ms         TEXT,
    language         TEXT NOT NULL DEFAULT 'en',
    -- 'en' | 'ms' | 'bilingual'
    source_url       TEXT,
    storage_path     TEXT,
    file_hash        TEXT,
    file_size_bytes  BIGINT,
    page_count       INT,
    publication_date DATE,
    period_start     DATE,
    period_end       DATE,
    metadata         JSONB NOT NULL DEFAULT '{}',
    ocr_status       TEXT NOT NULL DEFAULT 'pending',
    -- pending | queued | processing | done | failed
    graphrag_status  TEXT NOT NULL DEFAULT 'pending',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_id, external_id),
    UNIQUE (file_hash)
);

CREATE INDEX IF NOT EXISTS idx_documents_source_id        ON documents (source_id);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type         ON documents (doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_ocr_status       ON documents (ocr_status);
CREATE INDEX IF NOT EXISTS idx_documents_graphrag_status  ON documents (graphrag_status);
CREATE INDEX IF NOT EXISTS idx_documents_publication_date ON documents (publication_date);
CREATE INDEX IF NOT EXISTS idx_documents_metadata         ON documents USING GIN (metadata);

-- ---------------------------------------------------------------------------
-- ocr_jobs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ocr_jobs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id       UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    status            TEXT NOT NULL DEFAULT 'pending',
    -- pending | running | done | failed | retrying
    ocr_engine        TEXT NOT NULL DEFAULT 'marker-pdf',
    -- 'marker-pdf' | 'azure-di' | 'google-docai'
    attempt_count     INT NOT NULL DEFAULT 0,
    max_attempts      INT NOT NULL DEFAULT 3,
    started_at        TIMESTAMPTZ,
    completed_at      TIMESTAMPTZ,
    error_message     TEXT,
    output_path       TEXT,
    page_count        INT,
    word_count        INT,
    detected_language TEXT,
    ocr_config        JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ocr_jobs_document_id ON ocr_jobs (document_id);
CREATE INDEX IF NOT EXISTS idx_ocr_jobs_status      ON ocr_jobs (status);

-- ---------------------------------------------------------------------------
-- document_chunks
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_chunks (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id           UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index           INT NOT NULL,
    page_start            INT,
    page_end              INT,
    section_title         TEXT,
    text                  TEXT NOT NULL,
    language              TEXT NOT NULL DEFAULT 'en',
    n_tokens              INT,
    chunk_vector          vector(1536),
    graphrag_text_unit_id TEXT,
    metadata              JSONB NOT NULL DEFAULT '{}',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id     ON document_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_graphrag_tuid   ON document_chunks (graphrag_text_unit_id)
    WHERE graphrag_text_unit_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS hnsw_chunks_vector ON document_chunks
    USING hnsw (chunk_vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ---------------------------------------------------------------------------
-- graphrag_runs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS graphrag_runs (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_type           TEXT NOT NULL DEFAULT 'full',
    -- 'full' | 'incremental' | 'update'
    status             TEXT NOT NULL DEFAULT 'pending',
    document_ids       UUID[],
    entity_count       INT,
    relationship_count INT,
    community_count    INT,
    started_at         TIMESTAMPTZ,
    completed_at       TIMESTAMPTZ,
    error_message      TEXT,
    config_snapshot    JSONB,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
