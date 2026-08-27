"""
Phase 3 Column Migration: Add authority/tenant/lifecycle columns to existing tables.
Uses IF NOT EXISTS check to be idempotent.
"""
import psycopg2, os

DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "esp_agent"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432"))
}

MIGRATIONS = [
    # documents table
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS authority_level VARCHAR(2) DEFAULT 'E'",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS tenant_scope VARCHAR(50) DEFAULT 'GLOBAL'",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS effective_from DATE",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS effective_to DATE",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(20) DEFAULT 'PUBLISHED'",
    # knowledge_items table
    "ALTER TABLE knowledge_items ADD COLUMN IF NOT EXISTS authority_level VARCHAR(2) DEFAULT 'E'",
    "ALTER TABLE knowledge_items ADD COLUMN IF NOT EXISTS tenant_scope VARCHAR(50) DEFAULT 'GLOBAL'",
    # fault_patterns table
    "ALTER TABLE fault_patterns ADD COLUMN IF NOT EXISTS qualitative_patterns JSONB",
    "ALTER TABLE fault_patterns ADD COLUMN IF NOT EXISTS quantitative_rules JSONB",
    "ALTER TABLE fault_patterns ADD COLUMN IF NOT EXISTS confirmation_checks JSONB",
    "ALTER TABLE fault_patterns ADD COLUMN IF NOT EXISTS contradicting_signals JSONB",
    "ALTER TABLE fault_patterns ADD COLUMN IF NOT EXISTS approved_actions JSONB",
    "ALTER TABLE fault_patterns ADD COLUMN IF NOT EXISTS authority_level VARCHAR(2) DEFAULT 'B'",
    # pump_curves table
    "ALTER TABLE pump_curves ADD COLUMN IF NOT EXISTS manufacturer VARCHAR(100)",
    "ALTER TABLE pump_curves ADD COLUMN IF NOT EXISTS curve_points JSONB",
    "ALTER TABLE pump_curves ADD COLUMN IF NOT EXISTS authority_level VARCHAR(2) DEFAULT 'B'",
]

conn = psycopg2.connect(**DB_CONFIG)
conn.autocommit = True
cur = conn.cursor()

for sql in MIGRATIONS:
    try:
        cur.execute(sql)
        print(f"[+] OK: {sql[:60]}")
    except Exception as e:
        print(f"[-] SKIP: {e}")

cur.close()
conn.close()
print("\n[+] Phase 3 column migrations complete.")
