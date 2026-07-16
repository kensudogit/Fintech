"""Sales support helpers for bank relationship managers."""

from __future__ import annotations

from typing import Any

from app.tempest.matching import matching_engine


class SalesSupportEngine:
    """Generate talk tracks and next actions for RM / 法人営業."""

    def support(self, query: str) -> dict[str, Any]:
        match = matching_engine.search(query, top_k=2)
        source = match["source_company"]
        top = match["matches"][0] if match["matches"] else None
        talk = [
            f"導入: {source['name']}様の現状課題（{', '.join(source['needs'][:2])}）を確認する",
            "価値: 当行ネットワークとTempestAIマッチングで補完企業を可視化できる点を伝える",
        ]
        if top:
            c = top["company"]
            talk.append(
                f"提案: {c['name']}（{c['industry']}）との商談機会を具体日で提示する"
            )
            talk.append(f"根拠: {'; '.join(top['reasons'][:2])}")
        talk.append("クロージング: 紹介承諾と次回同行訪問の日程を取る")

        message = (
            "【TempestAI営業支援】\n"
            + "\n".join(f"{i}. {t}" for i, t in enumerate(talk, 1))
            + "\n\nFAQ連携: 融資条件・手数料はナレッジエージェントへ引き継ぎ可能です。"
        )
        return {
            "product": "TempestAI営業支援",
            "talk_track": talk,
            "related_matches": match["matches"],
            "message": message,
            "next_actions": [
                "CRMに活動予定を登録",
                "必要なら融資稟議AIで資金ニーズを事前審査",
                "FAQエージェントで商品説明を補強",
            ],
        }


sales_engine = SalesSupportEngine()
