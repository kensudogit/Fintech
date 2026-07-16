"""Decision Structure Intelligence — transform how decisions are made, not just speed them up.

Integrates latent qualitative + quantitative financial/economic data into an explicit
decision architecture: criteria trees, scenario branches, evidence ledgers, and
governance roles that replace ad-hoc judgment with structured, challengeable decisions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.tempest.loan import loan_engine
from app.tempest.matching import matching_engine

# Late import avoided in methods to prevent cycles; evidence_store injected at call time.


@dataclass
class QuantSignal:
    signal_id: str
    name: str
    value: float
    unit: str
    source: str
    trend: str  # up / down / flat
    weight: float = 1.0


@dataclass
class QualSignal:
    signal_id: str
    name: str
    narrative: str
    polarity: str  # positive / negative / mixed
    source: str
    confidence: float = 0.7
    weight: float = 1.0


@dataclass
class DecisionCase:
    case_id: str
    title: str
    domain: str
    decision_question: str
    traditional_frame: str
    quant_signals: list[QuantSignal] = field(default_factory=list)
    qual_signals: list[QualSignal] = field(default_factory=list)
    stakeholders: list[str] = field(default_factory=list)


SAMPLE_CASES: list[DecisionCase] = [
    DecisionCase(
        case_id="DEC-LOAN-0142",
        title="設備資金融資 — ノースウィンド製造",
        domain="credit",
        decision_question="80百万円の設備資金を、いかなる決裁構造で判断すべきか？",
        traditional_frame=(
            "担当者感想 → 支店長決裁 → 本部稟議。定量は財務三表、定性は口頭補足が中心で、"
            "反対意見・シナリオ分岐が残らない。"
        ),
        quant_signals=[
            QuantSignal("Q1", "営業利益率", 0.0497, "ratio", "決算書", "flat", 1.2),
            QuantSignal("Q2", "自己資本比率", 0.34, "ratio", "決算書", "up", 1.3),
            QuantSignal("Q3", "DSCR", 1.45, "x", "返済試算", "up", 1.5),
            QuantSignal("Q4", "業況DI（製造業）", 8.0, "index", "日銀短観相当", "up", 0.8),
            QuantSignal("Q5", "原材料価格指数", 112.0, "index", "経済統計", "up", 1.0),
        ],
        qual_signals=[
            QualSignal(
                "K1",
                "経営者実行力",
                "二代目経営者の現場掌握が強く、設備投資計画と人員配置が一致している。",
                "positive",
                "面談録",
                0.85,
                1.2,
            ),
            QualSignal(
                "K2",
                "原材料変動リスク",
                "価格転嫁の交渉力はあるが、特定サプライヤ依存が残る。",
                "mixed",
                "業界ヒアリング",
                0.75,
                1.1,
            ),
            QualSignal(
                "K3",
                "ESG投資姿勢",
                "省エネ設備への投資意図が明確で、中期の資金繰り説明と整合。",
                "positive",
                "事業計画書",
                0.8,
                0.9,
            ),
        ],
        stakeholders=["法人担当", "審査役", "支店長", "本部決裁者"],
    ),
    DecisionCase(
        case_id="DEC-MATCH-A01",
        title="ビジネスマッチング優先順位 — アトラス精密",
        domain="matching",
        decision_question="どの提携先紹介を『今四半期の戦略案件』として意思決定すべきか？",
        traditional_frame=(
            "担当者の人脈と感覚で紹介先を選ぶ。定量の適合度も、反対仮説も残らない。"
        ),
        quant_signals=[
            QuantSignal("Q1", "推定シナジー売上", 180.0, "百万円", "社内推計", "up", 1.2),
            QuantSignal("Q2", "地域GDP成長", 1.1, "%", "地域経済統計", "flat", 0.7),
            QuantSignal("Q3", "設備投資意欲指数", 14.0, "index", "短観相当", "up", 1.0),
        ],
        qual_signals=[
            QualSignal(
                "K1",
                "販路補完性",
                "商社の全国販路と精密加工の試作力が相互補完する叙述が複数ソースで一致。",
                "positive",
                "取引先カルテ",
                0.82,
                1.3,
            ),
            QualSignal(
                "K2",
                "関係性リスク",
                "過去の紹介案件でフォロー不足があったため、同行設計が必須。",
                "negative",
                "活動履歴",
                0.7,
                1.0,
            ),
        ],
        stakeholders=["法人営業", "支店長", "事業性評価担当"],
    ),
    DecisionCase(
        case_id="DEC-MACRO-01",
        title="業況判断 — 金利・景況の統合",
        domain="macro",
        decision_question="今期の与信スタンスを積極 / 中立 / 慎重のどれに構造化すべきか？",
        traditional_frame=(
            "マクロ指標を別資料、現場感を別会議で議論し、統合されたスタンス文書が残らない。"
        ),
        quant_signals=[
            QuantSignal("Q1", "政策金利相当", 0.5, "%", "市場", "up", 1.1),
            QuantSignal("Q2", "業況DI", 5.0, "index", "短観相当", "flat", 1.2),
            QuantSignal("Q3", "倒産件数増減", 6.0, "%", "信用情報", "up", 1.3),
            QuantSignal("Q4", "貸出残高伸び", 2.1, "%", "金融統計", "up", 0.9),
        ],
        qual_signals=[
            QualSignal(
                "K1",
                "現場感（営業ヒアリング）",
                "設備需要は残るが、金利上昇を理由に案件先送りが増えている。",
                "mixed",
                "営業ヒアリング集約",
                0.78,
                1.2,
            ),
            QualSignal(
                "K2",
                "信用コスト見通し",
                "中小の借入依存先で条件改定交渉が増加。慎重スタンスへの圧力。",
                "negative",
                "審査部コメント",
                0.8,
                1.1,
            ),
        ],
        stakeholders=["審査部", "営業企画", "リスク管理", "経営会議"],
    ),
]


class DecisionStructureEngine:
    """Build an AI-native decision structure from qualitative + quantitative evidence."""

    def __init__(self) -> None:
        self._cases = {c.case_id: c for c in SAMPLE_CASES}

    def list_cases(self) -> list[dict[str, Any]]:
        return [
            {
                "case_id": c.case_id,
                "title": c.title,
                "domain": c.domain,
                "decision_question": c.decision_question,
            }
            for c in self._cases.values()
        ]

    def transform(
        self,
        query: str,
        case_id: str | None = None,
        *,
        include_ingested: bool = True,
    ) -> dict[str, Any]:
        from app.tempest.evidence import evidence_store

        base_case = self._resolve_case(query, case_id)
        ingested_rows: list[dict[str, Any]] = []
        if include_ingested:
            case, ingested_rows = evidence_store.apply_to_case(base_case)
        else:
            case = base_case

        quant_score = self._aggregate_quant(case.quant_signals)
        qual_score = self._aggregate_qual(case.qual_signals)
        integrated = round(quant_score["score"] * 0.52 + qual_score["score"] * 0.48, 1)

        # Enrich with package engines when domain overlaps
        enrichment = self._enrich(case, query)

        criteria = self._criteria_tree(case, quant_score, qual_score)
        scenarios = self._scenarios(case, integrated, quant_score, qual_score)
        governance = self._governance(case, integrated)
        challenges = self._challenge_board(case, quant_score, qual_score)
        traditional_vs_new = self._structure_shift(case, criteria, scenarios, governance)

        stance = self._stance(integrated, case.domain)
        message = self._format_message(
            case, integrated, quant_score, qual_score, stance, traditional_vs_new, scenarios
        )
        if ingested_rows:
            message += (
                f"\n\n▼ ユーザー投入エビデンス（{len(ingested_rows)}件）を反映済み\n"
                + "\n".join(
                    f"・[{r.get('kind')}] {r.get('title')} — {r.get('decision_relevance') or r.get('source')}"
                    for r in ingested_rows[:5]
                )
            )

        ledger = self._evidence_ledger(case)
        for r in ingested_rows:
            ledger.append(
                {
                    "evidence_id": r["evidence_id"],
                    "kind": r["kind"],
                    "name": r.get("title"),
                    "payload": r.get("narrative")
                    or f"{r.get('value')}{r.get('unit', '')}",
                    "source": r.get("source"),
                    "maps_to": "ユーザー投入 → 意思決定ノード",
                    "decision_relevance": r.get("decision_relevance"),
                    "ingested": True,
                }
            )

        return {
            "product": "TempestAI意思決定構造エンジン",
            "thesis": (
                "業務効率化ではなく、定性・定量データを同一の意思決定グラフに載せ、"
                "誰が・何を根拠に・どの反対仮説を残して決めるかを構造化する。"
            ),
            "case": {
                "case_id": case.case_id,
                "title": case.title,
                "domain": case.domain,
                "decision_question": case.decision_question,
            },
            "scores": {
                "quantitative": quant_score,
                "qualitative": qual_score,
                "integrated": integrated,
            },
            "stance": stance,
            "traditional_frame": case.traditional_frame,
            "transformed_structure": traditional_vs_new,
            "criteria_tree": criteria,
            "scenarios": scenarios,
            "governance": governance,
            "challenge_board": challenges,
            "evidence_ledger": ledger,
            "ingested_evidence": ingested_rows,
            "enrichment": enrichment,
            "message": message,
            "next_actions": [
                "決裁会議で本構造（基準木・シナリオ・反対仮説）を共通アジェンダにする",
                "Evidence Ledger を議事録テンプレとして固定し、口頭補足を禁止する",
                "追加の意思決定情報があれば Evidence 投入 API / 画面から継続投入する",
                "四半期ごとに基準ウェイトを実績で再学習し、意思決定構造を更新する",
            ],
        }

    def _resolve_case(self, query: str, case_id: str | None) -> DecisionCase:
        if case_id and case_id in self._cases:
            return self._cases[case_id]
        for c in self._cases.values():
            if c.case_id in query or c.title.split("—")[0].strip() in query:
                return c
        if any(k in query for k in ("マッチ", "紹介", "提携")):
            return self._cases["DEC-MATCH-A01"]
        if any(k in query for k in ("金利", "業況", "マクロ", "スタンス", "与信方針")):
            return self._cases["DEC-MACRO-01"]
        if any(k in query for k in ("融資", "稟議", "ノース", "与信", "設備")):
            return self._cases["DEC-LOAN-0142"]
        m = re.search(r"DEC-[A-Z]+-\d+", query, re.I)
        if m:
            return self._cases.get(m.group(0).upper(), SAMPLE_CASES[0])
        return SAMPLE_CASES[0]

    def _enrich(self, case: DecisionCase, query: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if case.domain == "credit":
            loan = loan_engine.analyze(query or case.title)
            out["loan_bridge"] = {
                "decision": loan.get("decision"),
                "blended": (loan.get("scores") or {}).get("blended"),
                "application_id": (loan.get("application") or {}).get("application_id"),
            }
        if case.domain == "matching":
            match = matching_engine.search(query or "精密加工")
            top = (match.get("matches") or [{}])[0]
            out["matching_bridge"] = {
                "top_company": (top.get("company") or {}).get("name"),
                "score": top.get("score"),
            }
        return out

    @staticmethod
    def _aggregate_quant(signals: list[QuantSignal]) -> dict[str, Any]:
        if not signals:
            return {"score": 50.0, "drivers": [], "commentary": "定量シグナルなし"}
        # Normalize heterogeneous signals into a 0-100 contribution
        parts: list[tuple[str, float, float]] = []
        for s in signals:
            if "利益率" in s.name and s.unit == "ratio":
                # 3%→55, 5%→70, 8%→85
                raw = min(100.0, max(0.0, 40 + s.value * 600))
            elif "自己資本" in s.name and s.unit == "ratio":
                raw = min(100.0, max(0.0, s.value * 180))
            elif s.unit == "ratio":
                raw = min(100.0, max(0.0, s.value * 100))
            elif s.unit == "x":
                raw = min(100.0, max(0.0, (s.value - 0.5) * 50))
            elif s.unit == "%":
                raw = 50 + s.value * 3
                if "倒産" in s.name:
                    raw = 70 - s.value * 4
            else:
                raw = 55 + (s.value - 10) * 0.8 if s.value < 50 else 50 + (s.value - 100) * 0.25
                if s.trend == "up" and "価格" in s.name:
                    raw -= 10
                if "DI" in s.name:
                    raw = 50 + s.value * 1.5
            raw = max(0.0, min(100.0, raw))
            parts.append((s.name, raw, s.weight))
        total_w = sum(w for _, _, w in parts) or 1.0
        score = round(sum(v * w for _, v, w in parts) / total_w, 1)
        drivers = sorted(parts, key=lambda x: x[1] * x[2], reverse=True)[:3]
        return {
            "score": score,
            "drivers": [{"name": n, "contribution": round(v, 1)} for n, v, _ in drivers],
            "commentary": "定量シグナルを正規化し加重平均。効率指標ではなく意思決定入力として扱う。",
            "signals": [
                {
                    "id": s.signal_id,
                    "name": s.name,
                    "value": s.value,
                    "unit": s.unit,
                    "source": s.source,
                    "trend": s.trend,
                }
                for s in signals
            ],
        }

    @staticmethod
    def _aggregate_qual(signals: list[QualSignal]) -> dict[str, Any]:
        if not signals:
            return {"score": 50.0, "drivers": [], "commentary": "定性シグナルなし"}
        score = 50.0
        drivers: list[dict[str, Any]] = []
        for s in signals:
            delta = {"positive": 12, "mixed": 2, "negative": -12}.get(s.polarity, 0)
            contrib = delta * s.weight * s.confidence
            score += contrib * 0.35
            drivers.append({"name": s.name, "polarity": s.polarity, "contribution": round(contrib, 1)})
        score = max(0.0, min(100.0, round(score, 1)))
        drivers.sort(key=lambda d: abs(d["contribution"]), reverse=True)
        return {
            "score": score,
            "drivers": drivers[:4],
            "commentary": "叙述・ヒアリング・計画書の極性と確信度を意思決定ノードへ写像。",
            "signals": [
                {
                    "id": s.signal_id,
                    "name": s.name,
                    "narrative": s.narrative,
                    "polarity": s.polarity,
                    "source": s.source,
                    "confidence": s.confidence,
                }
                for s in signals
            ],
        }

    def _criteria_tree(self, case: DecisionCase, quant: dict, qual: dict) -> list[dict[str, Any]]:
        return [
            {
                "node": "収益・返済の持続性",
                "type": "quantitative",
                "weight": 0.34,
                "score": quant["score"],
                "evidence_ids": [s.signal_id for s in case.quant_signals[:3]],
                "decision_rule": "閾値未満なら『条件付』ノードへ分岐（否決ではない）",
            },
            {
                "node": "経営・事業の実行蓋然性",
                "type": "qualitative",
                "weight": 0.28,
                "score": qual["score"],
                "evidence_ids": [s.signal_id for s in case.qual_signals],
                "decision_rule": "否定仮説が2つ以上残る場合、単独決裁を禁止",
            },
            {
                "node": "マクロ・外部環境整合",
                "type": "hybrid",
                "weight": 0.22,
                "score": round((quant["score"] + qual["score"]) / 2, 1),
                "evidence_ids": [s.signal_id for s in case.quant_signals if "DI" in s.name or "金利" in s.name]
                or [case.quant_signals[-1].signal_id],
                "decision_rule": "外部悪化シナリオでモニタリング指標を必須化",
            },
            {
                "node": "組織学習・再現性",
                "type": "governance",
                "weight": 0.16,
                "score": 70.0 if case.stakeholders else 50.0,
                "evidence_ids": [],
                "decision_rule": "決裁後に反対仮説の検証結果を必ずフィードバック",
            },
        ]

    def _scenarios(
        self, case: DecisionCase, integrated: float, quant: dict, qual: dict
    ) -> list[dict[str, Any]]:
        base = {
            "name": "ベース",
            "probability": 0.55,
            "integrated_score": integrated,
            "action": self._stance(integrated, case.domain)["label"],
            "narrative": "現行の定量トレンドと定性評価が概ね持続する前提。",
        }
        upside = {
            "name": "アップサイド",
            "probability": 0.2,
            "integrated_score": min(100.0, round(integrated + 8, 1)),
            "action": "積極拡大 / 条件緩和の検討",
            "narrative": "外部需要と実行力が同時に上振れ。追加与信や戦略紹介を前倒し。",
        }
        downside = {
            "name": "ダウンサイド",
            "probability": 0.25,
            "integrated_score": max(0.0, round(integrated - 12, 1)),
            "action": "条件強化・モニタリング濃密化",
            "narrative": "定量悪化または定性の否定仮説が顕在化。決裁権限を一段引き上げ。",
            "triggers": [d["name"] for d in (quant.get("drivers") or [])[:1]]
            + [d["name"] for d in (qual.get("drivers") or []) if d.get("polarity") != "positive"][:1],
        }
        return [base, upside, downside]

    def _governance(self, case: DecisionCase, integrated: float) -> dict[str, Any]:
        if integrated >= 72:
            authority = "支店長決裁（構造チェックリスト必須）"
        elif integrated >= 55:
            authority = "本部合議（審査役 + 営業企画）"
        else:
            authority = "経営会議相当（否決または抜本条件）"
        return {
            "decision_authority": authority,
            "required_artifacts": [
                "Evidence Ledger（定性・定量の対応表）",
                "シナリオ3分岐とトリガー",
                "Challenge Board（反対仮説への回答）",
            ],
            "roles": [
                {"role": s, "responsibility": self._role_duty(s)} for s in case.stakeholders
            ],
            "anti_patterns": [
                "定性を『補足コメント』に落とす",
                "定量だけで決裁し叙述を残さない",
                "反対意見を議事録から削除する",
            ],
        }

    @staticmethod
    def _role_duty(role: str) -> str:
        mapping = {
            "法人担当": "現場事実と顧客叙述の一次証拠を提出",
            "審査役": "基準木の閾値適用と反対仮説の検証",
            "支店長": "構造充足の確認と権限内決裁",
            "本部決裁者": "シナリオ横断の方針一貫性を担保",
            "法人営業": "マッチ候補の実行計画と同行設計",
            "事業性評価担当": "定性シグナルの再現性評価",
            "審査部": "与信スタンス基準の更新",
            "営業企画": "ポートフォリオ配分への反映",
            "リスク管理": "ダウンサイドトリガー監視",
            "経営会議": "構造そのものの承認・改定",
        }
        return mapping.get(role, "意思決定ノードへの証拠提出")

    def _challenge_board(self, case: DecisionCase, quant: dict, qual: dict) -> list[dict[str, str]]:
        challenges = [
            {
                "challenge": "もし定量が正しく、定性の楽観が誤りなら？",
                "response_required_from": "審査役",
                "impact": "条件付ノードへ強制分岐",
            },
            {
                "challenge": "もし現場叙述が正しく、マクロ定量が遅行指標なら？",
                "response_required_from": "リスク管理" if "リスク管理" in case.stakeholders else "支店長",
                "impact": "モニタリング頻度を四半期→月次へ",
            },
        ]
        neg = [s for s in case.qual_signals if s.polarity in ("negative", "mixed")]
        if neg:
            challenges.append(
                {
                    "challenge": f"「{neg[0].name}」が顕在化した場合の撤退・条件変更は？",
                    "response_required_from": case.stakeholders[0] if case.stakeholders else "担当",
                    "impact": "ダウンサイド・シナリオのトリガー定義",
                }
            )
        return challenges

    def _structure_shift(
        self,
        case: DecisionCase,
        criteria: list[dict[str, Any]],
        scenarios: list[dict[str, Any]],
        governance: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "from": case.traditional_frame,
            "to": (
                "単線稟議を廃止し、①基準木 ②シナリオ分岐 ③反対仮説ボード ④役割責任 "
                "を同一成果物として決裁する構造へ転換。"
            ),
            "structural_changes": [
                "定性を『感想』から『採点可能な意思決定ノード』へ昇格",
                "定量を『報告指標』から『分岐トリガー』へ再定義",
                f"決裁権限をスコア帯で自動化: {governance['decision_authority']}",
                f"必須成果物を {len(governance['required_artifacts'])} 点に固定",
                f"シナリオを {len(scenarios)} 分岐で事前コミット",
            ],
            "criteria_count": len(criteria),
            "efficiency_is_not_the_goal": (
                "処理時間短縮は副次効果。主目的は再現可能・反証可能な意思決定構造の確立。"
            ),
        }

    def _evidence_ledger(self, case: DecisionCase) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for s in case.quant_signals:
            rows.append(
                {
                    "evidence_id": s.signal_id,
                    "kind": "quantitative",
                    "name": s.name,
                    "payload": f"{s.value}{s.unit}",
                    "source": s.source,
                    "maps_to": "収益・返済 / マクロ整合",
                }
            )
        for s in case.qual_signals:
            rows.append(
                {
                    "evidence_id": s.signal_id,
                    "kind": "qualitative",
                    "name": s.name,
                    "payload": s.narrative,
                    "source": s.source,
                    "maps_to": "実行蓋然性 / Challenge Board",
                }
            )
        return rows

    @staticmethod
    def _stance(integrated: float, domain: str) -> dict[str, Any]:
        if integrated >= 72:
            code, label = "expand", "積極（構造充足のうえ推進）"
        elif integrated >= 55:
            code, label = "selective", "選別的（条件・モニタリング付き推進）"
        else:
            code, label = "defend", "防御的（縮小・差戻し・再設計）"
        if domain == "macro":
            label = {"expand": "与信スタンス: 積極", "selective": "与信スタンス: 中立〜選別", "defend": "与信スタンス: 慎重"}[
                code
            ]
        return {"code": code, "label": label, "integrated_score": integrated}

    def _format_message(
        self,
        case: DecisionCase,
        integrated: float,
        quant: dict,
        qual: dict,
        stance: dict,
        shift: dict,
        scenarios: list[dict],
    ) -> str:
        scen_lines = "\n".join(
            f"・{s['name']} ({s['probability']:.0%}): {s['action']} — {s['narrative']}"
            for s in scenarios
        )
        changes = "\n".join(f"・{c}" for c in shift["structural_changes"])
        return (
            f"【TempestAI意思決定構造エンジン】{case.title}\n"
            f"問い: {case.decision_question}\n"
            f"統合スコア: {integrated}（定量 {quant['score']} / 定性 {qual['score']}）\n"
            f"スタンス: {stance['label']}\n\n"
            f"▼ 構造転換\nFrom: {shift['from']}\nTo: {shift['to']}\n{changes}\n\n"
            f"▼ シナリオ分岐\n{scen_lines}\n\n"
            f"{shift['efficiency_is_not_the_goal']}"
        )


decision_engine = DecisionStructureEngine()
