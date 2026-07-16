from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import KnowledgeDocument
from app.llm.factory import get_embeddings


@dataclass
class RetrievedChunk:
    title: str
    content: str
    category: str | None
    source: str
    score: float


class KnowledgeRAG:
    """Vector RAG over PostgreSQL knowledge documents with optional FAISS persistence."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.embeddings = get_embeddings()
        self._docs: list[dict] = []
        self._vectors: list[list[float]] = []
        self._faiss_index = None
        self._ready = False
        self._store_dir = Path("./data/vectorstore")
        self._store_dir.mkdir(parents=True, exist_ok=True)

    async def build_index(self, session: AsyncSession) -> int:
        result = await session.execute(select(KnowledgeDocument))
        rows = result.scalars().all()

        if not rows:
            self._seed_from_files()
            rows_data = self._docs
        else:
            rows_data = [
                {
                    "title": r.title,
                    "content": r.content,
                    "category": r.category,
                    "source": r.source,
                }
                for r in rows
            ]
            self._docs = rows_data

        texts = [f"{d['title']}\n{d['content']}" for d in rows_data]
        self._vectors = self.embeddings.embed_documents(texts) if texts else []
        self._build_faiss()
        self._ready = True
        self._write_knowledge_files(rows_data)
        return len(rows_data)

    def _build_faiss(self) -> None:
        try:
            import faiss
            import numpy as np
        except Exception:  # noqa: BLE001
            self._faiss_index = None
            return
        if not self._vectors:
            self._faiss_index = None
            return
        mat = np.array(self._vectors, dtype="float32")
        index = faiss.IndexFlatIP(mat.shape[1])
        faiss.normalize_L2(mat)
        index.add(mat)
        self._faiss_index = index
        try:
            faiss.write_index(index, str(self._store_dir / f"{self.settings.vector_collection}.faiss"))
        except Exception:  # noqa: BLE001
            pass

    def _seed_from_files(self) -> None:
        knowledge_dir = self.settings.knowledge_path
        docs: list[dict] = []
        for path in sorted(knowledge_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            title = path.stem
            docs.append({"title": title, "content": text, "category": "file", "source": str(path)})
        if not docs:
            docs = [
                {
                    "title": "口座開設の流れ",
                    "content": "口座開設は本人確認・メール認証・初期入金の3ステップです。",
                    "category": "onboarding",
                    "source": "fallback",
                }
            ]
        self._docs = docs

    def _write_knowledge_files(self, docs: list[dict]) -> None:
        knowledge_dir = self.settings.knowledge_path
        for doc in docs:
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in doc["title"])[:80]
            path = Path(knowledge_dir) / f"{safe}.md"
            if not path.exists():
                path.write_text(f"# {doc['title']}\n\n{doc['content']}\n", encoding="utf-8")

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        if not self._ready or not self._docs:
            return []

        k = top_k or self.settings.rag_top_k
        q = self.embeddings.embed_query(query)

        if self._faiss_index is not None:
            try:
                import numpy as np

                qv = np.array([q], dtype="float32")
                import faiss

                faiss.normalize_L2(qv)
                scores, idxs = self._faiss_index.search(qv, min(k, len(self._docs)))
                chunks: list[RetrievedChunk] = []
                for score, idx in zip(scores[0], idxs[0], strict=False):
                    if idx < 0 or idx >= len(self._docs):
                        continue
                    doc = self._docs[idx]
                    chunks.append(
                        RetrievedChunk(
                            title=doc["title"],
                            content=doc["content"],
                            category=doc.get("category"),
                            source=doc.get("source", ""),
                            score=float(score),
                        )
                    )
                if chunks:
                    return chunks
            except Exception:  # noqa: BLE001
                pass

        scored: list[tuple[float, dict]] = []
        for doc, vec in zip(self._docs, self._vectors, strict=False):
            score = self._cosine(q, vec)
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)

        chunks = []
        for score, doc in scored[:k]:
            chunks.append(
                RetrievedChunk(
                    title=doc["title"],
                    content=doc["content"],
                    category=doc.get("category"),
                    source=doc.get("source", ""),
                    score=score,
                )
            )
        return chunks

    def format_context(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "関連ナレッジは見つかりませんでした。"
        parts = ["【検索結果】"]
        for i, c in enumerate(chunks, 1):
            parts.append(f"{i}. {c.title} (score={c.score:.3f}, category={c.category})\n{c.content}")
        return "\n\n".join(parts)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        n = min(len(a), len(b))
        dot = sum(a[i] * b[i] for i in range(n))
        na = math.sqrt(sum(a[i] * a[i] for i in range(n))) or 1.0
        nb = math.sqrt(sum(b[i] * b[i] for i in range(n))) or 1.0
        return dot / (na * nb)


rag_service = KnowledgeRAG()
