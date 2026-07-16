"""TempestAI 融資稟議AI — qualitative + quantitative credit memo analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LoanApplication:
    application_id: str
    borrower: str
    industry: str
    requested_amount: int
    purpose: str
    term_months: int
    annual_revenue: int
    operating_profit: int
    equity_ratio: float
    debt_service_coverage: float
    qualitative_notes: str
    management_assessment: str
    industry_outlook: str
    collateral: str
    relationship_years: int
    tags: list[str] = field(default_factory=list)


SAMPLE_APPLICATIONS: list[LoanApplication] = [
    LoanApplication(
        application_id="LN-2026-0142",
        borrower="株式会社ノースウィンド製造",
        industry="精密部品製造",
        requested_amount=80_000_000,
        purpose="設備更新および増産ライン導入",
        term_months=60,
        annual_revenue=1_850_000_000,
        operating_profit=92_000_000,
        equity_ratio=0.34,
        debt_service_coverage=1.45,
        qualitative_notes=(
            "主要取引先との中長期契約が安定。経営者は二代目で現場掌握が強い。"
            "一方、原材料価格の変動リスクが残る。ESG対応投資も並行実施中。"
        ),
        management_assessment="経営計画の具体性が高く、数字根拠と実行体制が整合している。",
        industry_outlook="半導体周辺需要は堅調。価格競争は中程度。",
        collateral="工場土地建物（評価額 1.2億円）",
        relationship_years=11,
        tags=["設備資金", "製造業", "既存取引先"],
    ),
    LoanApplication(
        application_id="LN-2026-0188",
        borrower="合同会社グリーンロジ",
        industry="物流・倉庫",
        requested_amount=35_000_000,
        purpose="運転資金（季節繁忙対応）",
        term_months=24,
        annual_revenue=420_000_000,
        operating_profit=8_500_000,
        equity_ratio=0.18,
        debt_service_coverage=0.92,
        qualitative_notes=(
            "EC需要増で売上は伸長するが、利益率が薄い。"
            "新規荷主依存度が高く、契約更新リスクあり。財務の透明性は改善傾向。"
        ),
        management_assessment="現場オペは優秀だが、中期の財務改善計画がやや抽象的。",
        industry_outlook="物流需要は堅調だが人件費・燃料費圧力が継続。",
        collateral="保証協会保証（80%）",
        relationship_years=3,
        tags=["運転資金", "物流", "保証協会"],
    ),
    LoanApplication(
        application_id="LN-2026-0210",
        borrower="株式会社メディブリッジ",
        industry="医療機器卸",
        requested_amount=50_000_000,
        purpose="在庫拡充および地域病院向け販路拡大",
        term_months=36,
        annual_revenue=980_000_000,
        operating_profit=48_000_000,
        equity_ratio=0.41,
        debt_service_coverage=1.72,
        qualitative_notes=(
            "地域基幹病院との取引が長く、回収サイトも安定。"
            "薬機法コンプライアンス体制は外部監査済み。後継者計画も明確。"
        ),
        management_assessment="ガバナンスと計数管理が良好。成長投資の説明責任が明確。",
        industry_outlook="高齢化需要はプラス。保険償還改定の影響は中立。",
        collateral="売掛債権譲渡担保 + 代表者連帯保証",
        relationship_years=8,
        tags=["成長資金", "ヘルスケア", "優良取引先"],
    ),
]


class LoanScreeningEngine:
    """Analyze loan applications including qualitative narratives."""

    def __init__(self) -> None:
        self._apps = {a.application_id: a for a in SAMPLE_APPLICATIONS}

    def list_applications(self) -> list[dict[str, Any]]:
        return [self._summary(a) for a in self._apps.values()]

    def get_application(self, application_id: str) -> dict[str, Any] | None:
        app = self._apps.get(application_id)
        return self._detail(app) if app else None

    def analyze(self, query: str, application_id: str | None = None) -> dict[str, Any]:
        app = None
        if application_id and application_id in self._apps:
            app = self._apps[application_id]
        if app is None:
            app = self._resolve_from_query(query)
        if app is None:
            app = SAMPLE_APPLICATIONS[0]

        quant = self._score_quantitative(app)
        qual = self._score_qualitative(app)
        blended = round(quant["score"] * 0.55 + qual["score"] * 0.45, 1)
        decision = self._decision(blended, quant, qual, app)
        memo = self._build_memo(app, quant, qual, blended, decision)

        return {
            "product": "TempestAI融資稟議AIシステム",
            "application": self._detail(app),
            "scores": {
                "quantitative": quant,
                "qualitative": qual,
                "blended": blended,
            },
            "decision": decision,
            "risk_flags": self._risk_flags(app, quant, qual),
            "memo": memo,
            "message": memo,
            "next_actions": [
                "稟議書ドラフトを審査部へ共有",
                "追加ヒアリング項目を営業担当へ依頼" if decision["code"] == "conditional" else "決裁ワークフローへ進む",
                "モニタリング指標（DSCR・在庫回転）を四半期レビューに登録",
            ],
        }

    def _resolve_from_query(self, query: str) -> LoanApplication | None:
        for app in self._apps.values():
            if app.application_id in query or app.borrower in query:
                return app
        if any(k in query for k in ("物流", "グリーン", "運転資金")):
            return self._apps["LN-2026-0188"]
        if any(k in query for k in ("医療", "メディ", "ヘルスケア")):
            return self._apps["LN-2026-0210"]
        if any(k in query for k in ("製造", "ノース", "設備")):
            return self._apps["LN-2026-0142"]
        m = re.search(r"LN-\d{4}-\d+", query, re.I)
        if m:
            return self._apps.get(m.group(0).upper())
        return None

    @staticmethod
    def _score_quantitative(app: LoanApplication) -> dict[str, Any]:
        margin = app.operating_profit / max(app.annual_revenue, 1)
        score = 50.0
        score += min(20.0, app.equity_ratio * 40)
        score += min(20.0, max(0.0, (app.debt_service_coverage - 0.8) * 25))
        score += min(10.0, margin * 100)
        if app.relationship_years >= 8:
            score += 5
        score = max(0.0, min(100.0, round(score, 1)))
        return {
            "score": score,
            "operating_margin": round(margin, 4),
            "equity_ratio": app.equity_ratio,
            "dscr": app.debt_service_coverage,
            "commentary": (
                f"自己資本比率 {app.equity_ratio:.0%}、DSCR {app.debt_service_coverage:.2f}、"
                f"営業利益率 {margin:.1%}。"
            ),
        }

    @staticmethod
    def _score_qualitative(app: LoanApplication) -> dict[str, Any]:
        text = f"{app.qualitative_notes} {app.management_assessment} {app.industry_outlook}"
        score = 55.0
        positives = ("安定", "具体", "明確", "良好", "堅調", "整合", "監査")
        negatives = ("薄い", "抽象", "依存", "リスク", "圧力", "変動")
        score += sum(4 for p in positives if p in text)
        score -= sum(5 for n in negatives if n in text)
        if "保証協会" in app.collateral:
            score += 3
        score = max(0.0, min(100.0, round(score, 1)))
        return {
            "score": score,
            "management": app.management_assessment,
            "industry": app.industry_outlook,
            "notes_excerpt": app.qualitative_notes[:160],
            "commentary": "定性情報（経営者評価・業界見通し・叙述）をキーワード評価と文脈重みでスコア化。",
        }

    @staticmethod
    def _decision(blended: float, quant: dict, qual: dict, app: LoanApplication) -> dict[str, Any]:
        if blended >= 72 and quant["dscr"] >= 1.2:
            code, label = "approve", "承認推奨"
        elif blended >= 55:
            code, label = "conditional", "条件付承認"
        else:
            code, label = "reject", "否決・差戻し"
        conditions: list[str] = []
        if code == "conditional":
            if quant["dscr"] < 1.2:
                conditions.append("半期ごとのDSCRモニタリングを必須とする")
            if qual["score"] < 60:
                conditions.append("経営改善計画の定量KPI提出を条件とする")
            if "保証協会" in app.collateral:
                conditions.append("保証協会保証割合の維持を確認する")
            if not conditions:
                conditions.append("担保評価の再査定と資金使途証憑の提出")
        return {
            "code": code,
            "label": label,
            "confidence": round(min(0.95, 0.55 + blended / 200), 2),
            "conditions": conditions,
            "rationale": (
                f"総合スコア {blended}（定量 {quant['score']} / 定性 {qual['score']}）。"
                f"{label}とします。"
            ),
        }

    @staticmethod
    def _risk_flags(app: LoanApplication, quant: dict, qual: dict) -> list[str]:
        flags: list[str] = []
        if quant["dscr"] < 1.0:
            flags.append("元利金返済能力（DSCR）が警戒水準")
        if app.equity_ratio < 0.2:
            flags.append("自己資本比率が低位")
        if "依存" in app.qualitative_notes:
            flags.append("特定取引先依存リスク")
        if qual["score"] < 55:
            flags.append("定性評価が平均未満")
        if not flags:
            flags.append("重大なレッドフラグは検出されず")
        return flags

    def _build_memo(
        self,
        app: LoanApplication,
        quant: dict,
        qual: dict,
        blended: float,
        decision: dict,
    ) -> str:
        cond = ""
        if decision["conditions"]:
            cond = "\n条件:\n" + "\n".join(f"・{c}" for c in decision["conditions"])
        return (
            f"【TempestAI融資稟議AI】{app.borrower}（{app.application_id}）\n"
            f"希望額: ¥{app.requested_amount:,} / 使途: {app.purpose}\n"
            f"総合スコア: {blended}（定量 {quant['score']} / 定性 {qual['score']}）\n"
            f"推奨判断: {decision['label']}（確信度 {decision['confidence']}）\n"
            f"定量: {quant['commentary']}\n"
            f"定性: {qual['notes_excerpt']}\n"
            f"経営者評価: {app.management_assessment}\n"
            f"判断理由: {decision['rationale']}{cond}"
        )

    @staticmethod
    def _summary(app: LoanApplication) -> dict[str, Any]:
        return {
            "application_id": app.application_id,
            "borrower": app.borrower,
            "industry": app.industry,
            "requested_amount": app.requested_amount,
            "purpose": app.purpose,
            "tags": app.tags,
        }

    @staticmethod
    def _detail(app: LoanApplication) -> dict[str, Any]:
        return {
            **LoanScreeningEngine._summary(app),
            "term_months": app.term_months,
            "annual_revenue": app.annual_revenue,
            "operating_profit": app.operating_profit,
            "equity_ratio": app.equity_ratio,
            "debt_service_coverage": app.debt_service_coverage,
            "qualitative_notes": app.qualitative_notes,
            "management_assessment": app.management_assessment,
            "industry_outlook": app.industry_outlook,
            "collateral": app.collateral,
            "relationship_years": app.relationship_years,
        }


loan_engine = LoanScreeningEngine()
