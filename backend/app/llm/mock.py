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
        if "intent" in lower or "意図" in content or "intents" in lower:
            # Prefer the raw user utterance line when present
            user_line = content
            for line in content.splitlines():
                if "ユーザー入力" in line or line.startswith("ユーザー"):
                    user_line = line
                    break
            found: list[str] = []
            if any(
                k in user_line
                for k in (
                    "企業価値",
                    "真の企業価値",
                    "公正価値",
                    "バリュエーション",
                    "株価予測",
                    "時系列予測",
                    "高度予測",
                    "センチメント",
                    "割安",
                    "割高",
                    "DCF",
                    "EV推定",
                )
            ):
                found.append("value_forecast")
            if any(
                k in user_line
                for k in (
                    "意思決定構造",
                    "意思決定を変革",
                    "決裁構造",
                    "定性・定量",
                    "定性定量",
                    "シナリオ分岐",
                    "反対仮説",
                    "与信スタンス",
                    "業況判断",
                )
            ):
                found.append("decision_structure")
            if any(k in user_line for k in ("稟議", "融資審査", "信用審査", "与信", "融資判断", "LN-")):
                found.append("loan_screening")
            if any(k in user_line for k in ("マッチング", "ビジネスマッチ", "取引先紹介", "企業紹介", "マッチ候補")):
                found.append("b2b_matching")
            if any(k in user_line for k in ("営業支援", "トークスクリプト", "訪問提案", "法人営業", "営業トーク")):
                found.append("sales_support")
            fee_only = "手数料" in user_line and not any(
                k in user_line for k in ("振り込", "残高", "カード停止", "カードを止め")
            )
            if not fee_only and any(
                k in user_line for k in ("残高", "振り込", "振込", "送金", "カード停止", "操作", "transfer", "pay")
            ):
                if not ("手数料" in user_line and "振込" in user_line and "振り込" not in user_line):
                    found.append("operations")
            if any(k in user_line for k in ("おすすめ", "節約", "パーソナライズ", "家計", "改善提案")):
                found.append("personalization")
            if any(
                k in user_line
                for k in ("手数料", "口座開設", "FAQ", "とは", "教えて", "knowledge", "流れ", "不正", "NISA", "審査基準")
            ):
                found.append("knowledge")
            return ",".join(found) if found else "knowledge"

        if "ツール結果" in content or ("操作サポート" in content and "ツール" in content):
            return (
                "ご依頼を解釈しました。利用可能な操作として「残高確認」「振込開始」「カード停止」を提案します。"
                "続行する場合は対象口座と金額を教えてください。"
            )

        if "パーソナライズ提案" in content or "行動データ分析" in content:
            return (
                "行動データを踏まえると、今月は飲食費の比率が高めです。"
                "週次の家計レポート通知を有効化し、つみたて投資の自動入金を5,000円から検討することをおすすめします。"
            )

        if "Context:" in content or "【検索結果】" in content or "ナレッジに基づく" in content:
            if "手数料" in content:
                return (
                    "同行あての振込は無料、他行あては1件あたり145円（税込）です。"
                    "プレミアムプランなら月5回まで他行振込が無料になります。"
                )
            if "残高" in content:
                return "残高照会はアプリの口座画面、または「残高を教えて」と操作エージェントへ依頼できます。"
            return (
                "ナレッジDBの情報に基づく回答です。関連する公式ガイドを参照しつつ、"
                "必要であればサポート窓口への案内も可能です。"
            )

        return (
            "ご質問を受け付けました。口座・投資・手数料・セキュリティに関するサポートが可能です。"
            "具体的な操作内容を教えてください。"
        )
