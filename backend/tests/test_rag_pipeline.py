from app.rag.pipeline import KnowledgeRAG


def test_seed_from_files_and_retrieve():
    rag = KnowledgeRAG()
    rag._seed_from_files()
    assert len(rag._docs) >= 1
    # build vectors via mock embeddings
    texts = [f"{d['title']}\n{d['content']}" for d in rag._docs]
    rag._vectors = rag.embeddings.embed_documents(texts)
    rag._ready = True
    chunks = rag.retrieve("振込手数料")
    assert isinstance(chunks, list)
