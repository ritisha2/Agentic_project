import os
import glob
from typing import List, Dict, Any, Optional


class RAGAdapter:
    """Universal Documentation Retrieval (RAG) Adapter supporting text, markdown, and PDF files."""

    def __init__(self, docs_dir: Optional[str] = None):
        self.docs_dir = docs_dir
        self.chunks: List[Dict[str, Any]] = []
        if docs_dir and os.path.exists(docs_dir):
            self.index_documents(docs_dir)

    def index_documents(self, docs_dir: str):
        """Reads text, markdown, and PDF files, splits them into logical chunks, and indexes them for retrieval."""
        self.docs_dir = docs_dir
        self.chunks = []
        doc_files = glob.glob(os.path.join(docs_dir, "*.*"))

        for file_path in doc_files:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()

            doc_type = "manual"
            if "troubleshoot" in file_name.lower():
                doc_type = "troubleshooting"
            elif "sop" in file_name.lower() or "maint" in file_name.lower() or "safety" in file_name.lower():
                doc_type = "maintenance_sop"

            content = ""
            if file_ext == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(file_path)
                    pages_text = [page.extract_text() for page in reader.pages if page.extract_text()]
                    content = "\n\n".join(pages_text)
                except Exception:
                    # Graceful skip if pypdf is not installed yet or PDF is image-only
                    continue
            else:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue

            if not content.strip():
                continue

            # Split into logical paragraphs/sections
            paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 20]
            for idx, p in enumerate(paragraphs):
                self.chunks.append({
                    "id": f"{file_name}_{idx}",
                    "file_name": file_name,
                    "doc_type": doc_type,
                    "text": p,
                })

    def search(self, query: str, top_k: int = 3, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Searches document chunks for relevant troubleshooting and operating procedure passages."""
        if not self.chunks:
            return []

        query_terms = [t.lower() for t in query.replace(",", " ").replace(">", " ").replace("<", " ").split() if len(t) > 2]
        scored_results = []

        for chunk in self.chunks:
            if doc_type and chunk["doc_type"] != doc_type:
                continue

            text_lower = chunk["text"].lower()

            # Skip bibliography, reference lists, and license footers
            if "references" in text_lower or "doi.org" in text_lower or "creative commons" in text_lower or "academic editors" in text_lower:
                continue

            score = 0.0
            for term in query_terms:
                if term in text_lower:
                    score += 1.0

            # Boost troubleshooting and exact match
            if score > 0:
                if chunk["doc_type"] == "troubleshooting":
                    score *= 1.5
                scored_results.append((score, chunk))

        scored_results.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, chunk in scored_results[:top_k]:
            results.append({
                "text": chunk["text"],
                "source": chunk["file_name"],
                "doc_type": chunk["doc_type"],
                "score": round(score, 2)
            })

        # Fallback if keyword match returned nothing but chunks exist
        if not results and self.chunks:
            for chunk in self.chunks[:top_k]:
                results.append({
                    "text": chunk["text"],
                    "source": chunk["file_name"],
                    "doc_type": chunk["doc_type"],
                    "score": 0.5
                })

        return results
