"""
Heading-Aware Chunking & Embedding Pipeline for ESP Knowledge Base
Parses text extractions and Docling Markdown files, generates sentence-transformer embeddings,
and indexes vectors into PostgreSQL + pgvector.
"""

import os
import glob
import json
import hashlib
import psycopg2
from sentence_transformers import SentenceTransformer

DB_CONFIG = {
    "dbname": "esp_agent",
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432"))
}

ROOT_DIR = r"x:\TAS\Agentic_project"
TEXT_DIR = os.path.join(ROOT_DIR, "esp-knowledge", "processed", "text")
DOCLING_MD_DIR = os.path.join(ROOT_DIR, "esp-knowledge", "processed", "docling_md")
EMBEDDING_MODEL_NAME = "all-mpnet-base-v2"

def load_embedding_model():
    print(f"[*] Loading SentenceTransformer model '{EMBEDDING_MODEL_NAME}'...")
    return SentenceTransformer(EMBEDDING_MODEL_NAME)

def chunk_text_file(filepath, doc_id):
    """Chunk page-delimited text files into discrete knowledge items"""
    chunks = []
    if not os.path.exists(filepath):
        return chunks
        
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        
    pages = content.split("=== PAGE ")
    for idx, p in enumerate(pages[1:], 1):
        lines = p.strip().split("\n")
        page_num = idx
        page_text = "\n".join(lines[1:]).strip() if len(lines) > 1 else p.strip()
        
        if len(page_text) < 30:
            continue
            
        # Split page into paragraphs of max 500 words
        paragraphs = page_text.split("\n\n")
        curr_chunk = ""
        c_idx = 1
        
        for para in paragraphs:
            if len(curr_chunk) + len(para) > 1200 and len(curr_chunk) > 100:
                chunk_id = f"{doc_id}_p{page_num}_c{c_idx}"
                chunks.append({
                    "knowledge_id": chunk_id,
                    "document_id": doc_id,
                    "page": page_num,
                    "section": f"Page {page_num}",
                    "heading_path": f"Document > Page {page_num}",
                    "text_content": curr_chunk.strip()
                })
                curr_chunk = para + "\n\n"
                c_idx += 1
            else:
                curr_chunk += para + "\n\n"
                
        if curr_chunk.strip():
            chunk_id = f"{doc_id}_p{page_num}_c{c_idx}"
            chunks.append({
                "knowledge_id": chunk_id,
                "document_id": doc_id,
                "page": page_num,
                "section": f"Page {page_num}",
                "heading_path": f"Document > Page {page_num}",
                "text_content": curr_chunk.strip()
            })
            
    return chunks

def process_and_index(conn, model):
    """Chunk all documents and compute pgvector embeddings"""
    cur = conn.cursor()
    
    # Get all registered documents
    cur.execute("SELECT document_id, standardized_filename FROM documents;")
    doc_rows = cur.fetchall()
    
    total_chunks = 0
    
    for doc_id, fname in doc_rows:
        text_file = os.path.join(TEXT_DIR, f"{doc_id}.txt")
        chunks = chunk_text_file(text_file, doc_id)
        
        if not chunks:
            continue
            
        print(f"[*] Processing {doc_id} ({len(chunks)} chunks)...")
        
        texts_to_embed = [c["text_content"] for c in chunks]
        embeddings = model.encode(texts_to_embed, show_progress_bar=False, batch_size=16)
        
        for c, emb in zip(chunks, embeddings):
            k_id = c["knowledge_id"]
            clean_text = c["text_content"].replace("\x00", "").replace("\x00", "")
            c_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
            
            # Insert knowledge item
            cur.execute("""
                INSERT INTO knowledge_items (
                    knowledge_id, document_id, canonical_category, title,
                    section, page, heading_path, text_content, content_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (knowledge_id) DO UPDATE SET
                    text_content = EXCLUDED.text_content;
            """, (
                k_id, c["document_id"], "ingested", f"{doc_id} Chunk",
                c["section"], c["page"], c["heading_path"],
                clean_text, c_hash
            ))
            
            # Insert pgvector embedding
            emb_list = emb.tolist()
            cur.execute("""
                INSERT INTO knowledge_embeddings (
                    knowledge_id, embedding_model, embedding_version, embedding
                ) VALUES (%s, %s, %s, %s)
                ON CONFLICT (knowledge_id, embedding_model) DO UPDATE SET
                    embedding = EXCLUDED.embedding;
            """, (
                k_id, EMBEDDING_MODEL_NAME, "1.0", emb_list
            ))
            
            total_chunks += 1
            
        conn.commit()
        
    cur.close()
    print(f"\n[+] Successfully chunked and embedded {total_chunks} total knowledge items into pgvector!")

def main():
    model = load_embedding_model()
    conn = psycopg2.connect(**DB_CONFIG)
    process_and_index(conn, model)
    conn.close()

if __name__ == "__main__":
    main()
