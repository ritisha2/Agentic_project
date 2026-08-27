"""
PostgreSQL Schema Migration & Database Initialization Script for ESP Knowledge Base
Creates database `esp_agent`, enables `pgvector`, and executes schema migrations.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_CONFIG = {
    "dbname": "esp_agent",
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432"))
}

SCHEMA_SQL = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Source documents registry
CREATE TABLE IF NOT EXISTS documents (
    document_id         VARCHAR(100) PRIMARY KEY,
    title               TEXT NOT NULL,
    canonical_category  VARCHAR(50),
    doc_type            VARCHAR(50),
    author_publisher    TEXT,
    publication_year    VARCHAR(20),
    source_filename     TEXT,
    standardized_filename TEXT,
    file_path           TEXT,
    file_size_bytes     BIGINT,
    sha256_checksum     VARCHAR(64) UNIQUE NOT NULL,
    total_pages         INTEGER,
    extracted_char_count BIGINT,
    status              VARCHAR(30) DEFAULT 'PARSED_AND_NORMALIZED',
    authority_level     VARCHAR(2) DEFAULT 'E',  -- A=Installed B=OEM C=Client D=History E=Industry F=LLM
    tenant_scope        VARCHAR(50) DEFAULT 'GLOBAL',
    effective_from      DATE,
    effective_to        DATE,
    lifecycle_status    VARCHAR(20) DEFAULT 'PUBLISHED',
    created_at          TIMESTAMP DEFAULT NOW()
);

-- 2. Parsed knowledge items / text chunks
CREATE TABLE IF NOT EXISTS knowledge_items (
    knowledge_id        VARCHAR(120) PRIMARY KEY,
    document_id         VARCHAR(100) REFERENCES documents(document_id),
    canonical_category  VARCHAR(50),
    title               TEXT,
    section             TEXT,
    page                INTEGER,
    heading_path        TEXT,
    text_content        TEXT NOT NULL,
    tables_json         JSONB,
    content_hash        VARCHAR(64),
    safety_class        VARCHAR(30) DEFAULT 'STANDARD',
    access_policy       VARCHAR(30) DEFAULT 'UNRESTRICTED_INTERNAL',
    authority_level     VARCHAR(2) DEFAULT 'E',
    tenant_scope        VARCHAR(50) DEFAULT 'GLOBAL',
    status              VARCHAR(20) DEFAULT 'PUBLISHED',
    created_at          TIMESTAMP DEFAULT NOW()
);

-- 3. Vector embeddings (pgvector 768-dim)
CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    knowledge_id      VARCHAR(120) REFERENCES knowledge_items(knowledge_id) ON DELETE CASCADE,
    embedding_model   VARCHAR(100) NOT NULL,
    embedding_version VARCHAR(20) DEFAULT '1.0',
    embedding         vector(768) NOT NULL,
    created_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (knowledge_id, embedding_model)
);

-- Index for vector cosine similarity search
CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings_cosine 
ON knowledge_embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. Fault patterns taxonomy
CREATE TABLE IF NOT EXISTS fault_patterns (
    fault_id            VARCHAR(50) PRIMARY KEY,
    category            VARCHAR(30) NOT NULL, -- HYDRAULIC/MECHANICAL/ELECTRICAL/THERMAL/WELL_PROCESS
    preferred_name      TEXT NOT NULL,
    synonyms            JSONB,
    canonical_metric    VARCHAR(60),
    symptoms            JSONB,
    contributing_factors JSONB,
    evidence_required   JSONB,
    qualitative_patterns JSONB,   -- e.g. {"PIP": "rising", "flow": "declining"}
    quantitative_rules  JSONB,   -- e.g. [{"metric": "motor_temp", "op": ">", "threshold": 130, "unit": "C"}]
    confirmation_checks JSONB,   -- ordered list of verification steps
    contradicting_signals JSONB, -- signals that rule out this fault
    approved_actions    JSONB,   -- recommended operator/engineering actions
    severity_range      VARCHAR(30),
    escalation          TEXT,
    source              TEXT,
    authority_level     VARCHAR(2) DEFAULT 'B',
    version             VARCHAR(20) DEFAULT '1.0',
    status              VARCHAR(20) DEFAULT 'ACTIVE'
);

-- 5. Pump performance curves & boundaries
CREATE TABLE IF NOT EXISTS pump_curves (
    curve_id            VARCHAR(50) PRIMARY KEY,
    pump_model          VARCHAR(100) NOT NULL,
    manufacturer        VARCHAR(100),
    stage_count         INTEGER,
    frequency_hz        FLOAT,
    ror_min_bpd         FLOAT,
    ror_max_bpd         FLOAT,
    bep_bpd             FLOAT,
    curve_points        JSONB,   -- [{"flow_bpd": 1500, "head_ft": 42.3, "efficiency_pct": 68},...]
    source_document     VARCHAR(100),
    source_page         INTEGER,
    authority_level     VARCHAR(2) DEFAULT 'B',
    version             VARCHAR(20) DEFAULT '1.0'
);

-- 10. Historical case library (teardowns, RCAs, confirmed diagnoses)
CREATE TABLE IF NOT EXISTS historical_cases (
    case_id             VARCHAR(100) PRIMARY KEY,
    asset_id            VARCHAR(50),
    well_id             VARCHAR(50),
    equipment_model     VARCHAR(100),
    event_time          TIMESTAMP,
    symptom_summary     TEXT,
    telemetry_signature JSONB,   -- key signal patterns at time of event
    event_sequence      JSONB,   -- trip/start/stop/maintenance timeline
    confirmed_cause     VARCHAR(100),
    candidate_causes    JSONB,
    operator_action     TEXT,
    action_outcome      TEXT,
    production_impact   TEXT,
    source_reports      JSONB,   -- RCA/workover report references
    approval_status     VARCHAR(20) DEFAULT 'PENDING',
    created_at          TIMESTAMP DEFAULT NOW()
);

-- 6. Glossary terms
CREATE TABLE IF NOT EXISTS glossary_terms (
    term_id         VARCHAR(50) PRIMARY KEY,
    preferred_term  TEXT NOT NULL,
    synonyms        JSONB,
    definition      TEXT NOT NULL,
    domain          VARCHAR(40),
    unit            VARCHAR(20),
    version         VARCHAR(20) DEFAULT '1.0'
);

-- 7. Agent objective definitions
CREATE TABLE IF NOT EXISTS agent_objectives (
    objective_id        VARCHAR(50) PRIMARY KEY,
    name                TEXT NOT NULL,
    trigger_keywords    JSONB,
    description         TEXT,
    required_tools      JSONB,
    optional_tools      JSONB,
    success_criteria    TEXT,
    safety_policy       JSONB,
    version             VARCHAR(20) DEFAULT '1.0',
    status              VARCHAR(20) DEFAULT 'ACTIVE'
);

-- 8. Evidence pack audit trail
CREATE TABLE IF NOT EXISTS evidence_records (
    evidence_id     BIGSERIAL PRIMARY KEY,
    run_id          VARCHAR(100) NOT NULL,
    asset_id        VARCHAR(50) NOT NULL,
    objective_id    VARCHAR(50),
    evidence_type   VARCHAR(30),  -- KNOWLEDGE/TELEMETRY/MODEL/CALCULATION
    source          TEXT,
    source_id       VARCHAR(100),
    claim           TEXT,
    payload_hash    VARCHAR(64),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 9. Agent run logs
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id          VARCHAR(100) PRIMARY KEY,
    asset_id        VARCHAR(50) NOT NULL,
    objective_id    VARCHAR(50),
    user_query      TEXT,
    kb_id           VARCHAR(50),
    response        JSONB,
    confidence      FLOAT,
    latency_ms      INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);
"""

def create_database_if_not_exists():
    """Ensure target database exists on Postgres server"""
    target_db = DB_CONFIG["dbname"]
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"]
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s;", (target_db,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{target_db}";')
            print(f"[+] Created PostgreSQL database: {target_db}")
        else:
            print(f"[*] Database '{target_db}' already exists.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[-] Database check/creation error: {e}")
        sys.exit(1)

def run_migrations():
    """Execute SQL migrations on esp_agent database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print(f"[*] Connecting to '{DB_CONFIG['dbname']}' and running migrations...")
        cur.execute(SCHEMA_SQL)
        conn.commit()
        print("[+] Schema migration completed successfully!")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[-] Migration error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_database_if_not_exists()
    run_migrations()
