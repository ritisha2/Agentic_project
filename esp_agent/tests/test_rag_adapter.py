from src.adapters.rag import RAGAdapter


def test_rag_adapter_retrieval():
    docs_dir = "knowledge_bases/esp/documents"
    adapter = RAGAdapter(docs_dir=docs_dir)

    results = adapter.search("motor temperature overheating", top_k=2)
    assert len(results) > 0
    sources = [r["source"] for r in results]
    assert any("manual.txt" in s or "troubleshooting.txt" in s for s in sources)
