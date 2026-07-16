"""TempestAI ビジネスマッチングAI — company-to-company matching."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompanyProfile:
    company_id: str
    name: str
    industry: str
    region: str
    employees: int
    revenue_band: str
    strengths: list[str]
    needs: list[str]
    products: list[str]
    external_signals: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


SAMPLE_COMPANIES: list[CompanyProfile] = [
    CompanyProfile(
        company_id="CO-A01",
        name="株式会社アトラス精密",
        industry="精密加工",
        region="愛知",
        employees=120,
        revenue_band="20-50億",
        strengths=["五軸加工", "短納期", "自動車Tier2実績"],
        needs=["新規販路（半導体装置）", "共同調達", "人材紹介"],
        products=["精密部品", "治具"],
        external_signals=["半導体装置需要の回復ニュース", "県内ものづくり補助金採択"],
        keywords=["製造", "精密", "半導体", "加工"],
    ),
    CompanyProfile(
        company_id="CO-B12",
        name="テックブリッジ株式会社",
        industry="産業機械商社",
        region="東京",
        employees=85,
        revenue_band="50-100億",
        strengths=["全国販路", "装置メーカー代理店", "ファイナンス提案"],
        needs=["優良加工パートナー", "試作対応力", "地方拠点連携"],
        products=["工作機械", "計測器"],
        external_signals=["設備投資意欲の回復（日銀短観関連）"],
        keywords=["商社", "装置", "販路", "マッチング"],
    ),
    CompanyProfile(
        company_id="CO-C07",
        name="ヘルスリンク合同会社",
        industry="ヘルスケアIT",
        region="大阪",
        employees=40,
        revenue_band="5-10億",
        strengths=["電子カルテ連携", "クラウド運用", "セキュリティ認証"],
        needs=["地域病院チャネル", "医療機器卸との協業", "資金調達支援"],
        products=["遠隔モニタリングSaaS"],
        external_signals=["遠隔医療関連の規制緩和動向"],
        keywords=["医療", "IT", "病院", "SaaS"],
    ),
    CompanyProfile(
        company_id="CO-D03",
        name="株式会社メディブリッジ",
        industry="医療機器卸",
        region="大阪",
        employees=210,
        revenue_band="50-100億",
        strengths=["基幹病院ネットワーク", "物流拠点", "薬機法体制"],
        needs=["デジタルヘルスケア商品", "在庫最適化", "共同セミナー"],
        products=["医療機器", "消耗品"],
        external_signals=["地域包括ケア需要増"],
        keywords=["医療", "卸", "病院", "ヘルスケア"],
    ),
    CompanyProfile(
        company_id="CO-E15",
        name="グリーンロジHD",
        industry="物流",
        region="埼玉",
        employees=300,
        revenue_band="100億超",
        strengths=["低温物流", "ECフルフィルメント", "共同配送"],
        needs=["製造業の保管需要", "システム連携パートナー"],
        products=["3PL", "倉庫"],
        external_signals=["EC物流ピーク対応の外注需要"],
        keywords=["物流", "倉庫", "EC", "保管"],
    ),
]


class MatchingEngine:
    """Rank B2B match candidates from internal + external signals."""

    def __init__(self) -> None:
        self._companies = {c.company_id: c for c in SAMPLE_COMPANIES}

    def list_companies(self) -> list[dict[str, Any]]:
        return [self._to_dict(c) for c in self._companies.values()]

    def search(self, query: str, source_company_id: str | None = None, top_k: int = 3) -> dict[str, Any]:
        source = self._resolve_source(query, source_company_id)
        candidates = [c for c in self._companies.values() if c.company_id != source.company_id]
        ranked: list[dict[str, Any]] = []
        for c in candidates:
            score, reasons = self._score_pair(source, c, query)
            ranked.append(
                {
                    "company": self._to_dict(c),
                    "score": score,
                    "reasons": reasons,
                    "suggested_intro": (
                        f"{source.name} の強み（{', '.join(source.strengths[:2])}）と "
                        f"{c.name} のニーズ（{', '.join(c.needs[:2])}）が適合します。"
                    ),
                }
            )
        ranked.sort(key=lambda x: x["score"], reverse=True)
        top = ranked[: max(1, min(top_k, 5))]
        message = self._format_message(source, top)
        return {
            "product": "TempestAIビジネスマッチングAIシステム",
            "source_company": self._to_dict(source),
            "matches": top,
            "external_signals_used": source.external_signals + [
                s for m in top for s in m["company"].get("external_signals", [])[:1]
            ],
            "message": message,
            "next_actions": [
                "上位候補へ同行訪問を設定",
                "マッチ理由を営業トークに落とし込み",
                "紹介状ドラフトを生成して支店長承認へ",
            ],
        }

    def _resolve_source(self, query: str, source_company_id: str | None) -> CompanyProfile:
        if source_company_id and source_company_id in self._companies:
            return self._companies[source_company_id]
        for c in self._companies.values():
            if c.company_id in query or c.name in query:
                return c
        if any(k in query for k in ("医療", "ヘルスケア", "病院")):
            return self._companies["CO-C07"]
        if any(k in query for k in ("物流", "倉庫", "EC")):
            return self._companies["CO-E15"]
        if any(k in query for k in ("商社", "装置", "販路")):
            return self._companies["CO-B12"]
        if any(k in query for k in ("精密", "製造", "加工")):
            return self._companies["CO-A01"]
        return SAMPLE_COMPANIES[0]

    def _score_pair(self, source: CompanyProfile, target: CompanyProfile, query: str) -> tuple[float, list[str]]:
        score = 40.0
        reasons: list[str] = []

        # Need ↔ strength overlap
        for need in source.needs:
            for strength in target.strengths:
                if self._overlap(need, strength) or self._overlap(need, " ".join(target.products)):
                    score += 12
                    reasons.append(f"ニーズ「{need}」と強み「{strength}」が一致")
                    break
        for need in target.needs:
            for strength in source.strengths:
                if self._overlap(need, strength):
                    score += 10
                    reasons.append(f"先方ニーズ「{need}」に自社強み「{strength}」が対応")
                    break

        if source.region == target.region:
            score += 8
            reasons.append(f"同一地域（{source.region}）で接点作りやすい")
        elif source.region in ("大阪", "東京") and target.region in ("大阪", "東京"):
            score += 4

        # Industry adjacency
        if source.industry == target.industry:
            score += 3
        if {"ヘルスケアIT", "医療機器卸"} <= {source.industry, target.industry}:
            score += 15
            reasons.append("ヘルスケアバリューチェーン上の補完関係")
        if {"精密加工", "産業機械商社"} <= {source.industry, target.industry}:
            score += 14
            reasons.append("加工能力と販路の補完関係")

        # Query keyword boost
        q = query.lower()
        for kw in target.keywords + target.strengths:
            if kw.lower() in q or kw in query:
                score += 5
                reasons.append(f"クエリキーワード「{kw}」に適合")

        # External signals
        if target.external_signals:
            score += 4
            reasons.append(f"外部シグナル: {target.external_signals[0]}")

        score = max(0.0, min(100.0, round(score, 1)))
        if not reasons:
            reasons.append("業種・規模の近接性による基礎スコア")
        return score, reasons[:4]

    @staticmethod
    def _overlap(a: str, b: str) -> bool:
        tokens = [t for t in re.split(r"[\s/・（）()]+", a) if len(t) >= 2]
        return any(t in b for t in tokens)

    def _format_message(self, source: CompanyProfile, matches: list[dict[str, Any]]) -> str:
        lines = [
            f"【TempestAIビジネスマッチングAI】起点: {source.name}（{source.industry} / {source.region}）",
            "上位マッチ候補:",
        ]
        for i, m in enumerate(matches, 1):
            c = m["company"]
            lines.append(
                f"{i}. {c['name']}（スコア {m['score']}）— {'; '.join(m['reasons'][:2])}"
            )
            lines.append(f"   紹介案: {m['suggested_intro']}")
        return "\n".join(lines)

    @staticmethod
    def _to_dict(c: CompanyProfile) -> dict[str, Any]:
        return {
            "company_id": c.company_id,
            "name": c.name,
            "industry": c.industry,
            "region": c.region,
            "employees": c.employees,
            "revenue_band": c.revenue_band,
            "strengths": c.strengths,
            "needs": c.needs,
            "products": c.products,
            "external_signals": c.external_signals,
        }


matching_engine = MatchingEngine()
