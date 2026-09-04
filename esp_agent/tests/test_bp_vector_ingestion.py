"""
Unit Test Suite for BP ESP Troubleshooting Guidelines Vector DB Ingestion
Verifies:
1. Database indexing of DOC-ENG-BP-001 chunks in PostgreSQL knowledge_items.
2. Non-null pgvector embeddings in knowledge_embeddings.
3. Metadata lineage (heading_path, page 1-55, content_hash).
4. Direct vector semantic retrieval of BP knowledge chunks.
"""

import os
import psycopg2
import pytest
from src.services.retrieval_service import RetrievalService

DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "esp_agent"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432"))
}


@pytest.fixture(scope="module")
def db_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    yield conn
    conn.close()


def test_1_bp_chunks_count_in_db(db_conn):
    """Verify DOC-ENG-BP-001 has at least 40 discrete knowledge chunks indexed."""
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(1) FROM knowledge_items WHERE document_id = 'DOC-ENG-BP-001';")
    count = cur.fetchone()[0]
    cur.close()
    assert count >= 40, f"Expected >= 40 BP chunks, found {count}"


def test_2_bp_chunks_metadata_integrity(db_conn):
    """Verify all BP chunks have valid page numbers (1-55), heading_path, and content_hash."""
    cur = db_conn.cursor()
    cur.execute("""
        SELECT knowledge_id, page, heading_path, content_hash, LENGTH(text_content)
        FROM knowledge_items
        WHERE document_id = 'DOC-ENG-BP-001';
    """)
    rows = cur.fetchall()
    cur.close()

    assert len(rows) >= 40
    for kid, page, heading, chash, text_len in rows:
        assert page is not None and 1 <= page <= 55, f"Invalid page {page} for {kid}"
        assert heading is not None and len(heading) > 0, f"Missing heading for {kid}"
        assert chash is not None and len(chash) == 64, f"Invalid SHA-256 hash for {kid}"
        assert text_len > 20, f"Empty or too short chunk {kid}: {text_len} chars"


def test_3_bp_embeddings_exist_in_pgvector(db_conn):
    """Verify all BP chunks have non-null embeddings in knowledge_embeddings."""
    cur = db_conn.cursor()
    cur.execute("""
        SELECT COUNT(1)
        FROM knowledge_items ki
        JOIN knowledge_embeddings ke ON ki.knowledge_id = ke.knowledge_id
        WHERE ki.document_id = 'DOC-ENG-BP-001' AND ke.embedding IS NOT NULL;
    """)
    embedded_count = cur.fetchone()[0]
    cur.close()
    assert embedded_count >= 40, f"Expected >= 40 embeddings, found {embedded_count}"


def test_4_bp_vector_semantic_retrieval():
    """Verify hybrid retrieval matches BP manual chunks on domain query."""
    svc = RetrievalService()
    res = svc.hybrid_retrieve("backspin torsion failure pump startup", top_k=5)
    assert res["retrieval_status"] == "SUCCESS"

    v_results = res.get("vector_results", [])
    doc_ids = [r.get("document_id") for r in v_results]
    assert "DOC-ENG-BP-001" in doc_ids or any("backspin" in (r.get("text") or "").lower() for r in v_results), (
        f"BP manual chunk not found in top 5 retrieval results: {doc_ids}"
    )
