"""Offline-friendly mock LLM / embeddings for local development without API keys."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any


class MockEmbeddings:
    """Deterministic bag-of-words style embeddings."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = re.findall(r"[\wぁ-んァ-ン一-龥]+", text.lower())
        if not tokens:
            tokens = ["empty"]
        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % self.dim
            sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class MockChatModel:
    """Rule-based response generator used when no LLM API key is configured."""

    def invoke(self, messages: list[Any], **_: Any) -> Any:
        content = self._extract_user_content(messages)
        answer = self._generate(content)

        class _Msg:
            def __init__(self, text: str) -> None:
                self.content = text

        return _Msg(answer)

    async def ainvoke(self, messages: list[Any], **kwargs: Any) -> Any:
        return self.invoke(messages, **kwargs)

    def _extract_user_content(self, messages: list[Any]) -> str:
        texts: list[str] = []
        for msg in messages:
            if isinstance(msg, dict):
                texts.append(str(msg.get("content", "")))
            elif hasattr(msg, "content"):
                texts.append(str(msg.content))
            else:
                texts.append(str(msg))
        return "\n".join(texts)

    def _generate(self, content: str) -> str:
        lower = content.lower()
        if "intent" in lower or "意図" in content:
            if any(k in content for k in ("手数料", "口座開設", "FAQ", "とは", "教えて", "knowledge", "流れ", "不正")):
                return "knowledge"
            if any(k in content for k in ("提案", "おすすめ", "分析", "suggest", "recommend", "節約")):
                return "personalization"
            if any(k in content for k in ("振込して", "送金して", "支払いして", "カード停止", "残高確認", "操作", "transfer", "pay")):
                return "operations"
            return "knowledge"

        if "操作" in content or "operations" in lower:
            return (
                "ご依頼を解釈しました。利用可能な操作として「残高確認」「振込開始」「カード停止」を提案します。"
                "続行する場合は対象口座と金額を教えてください。"
            )

        if "パーソナライズ" in content or "personal" in lower or "提案" in content:
            return (
                "行動データを踏まえると、今月は飲食費の比率が高めです。"
                "週次の家計レポート通知を有効化し、つみたて投資の自動入金を5,000円から検討することをおすすめします。"
            )

        if "コンテキスト" in content or "context" in lower or "知識" in content:
            # Prefer answering from retrieved context block if present
            if "【検索結果】" in content or "Context:" in content:
                return (
                    "ナレッジDBの情報に基づく回答です。関連する公式ガイドを参照しつつ、"
                    "必要であればサポート窓口への案内も可能です。"
                )
            return "関連するナレッジが見つかりました。詳細な手順や手数料についてご案内できます。"

        return (
            "ご質問を受け付けました。口座・投資・手数料・セキュリティに関するサポートが可能です。"
            "具体的な操作内容を教えてください。"
        )
