"""Enterprise value & forecast agent — GenAI + time-series + deep fusion.

Combines quantitative signals (financials, equity prices, rates) with qualitative
NLP (news, business model, sentiment) to estimate intrinsic enterprise value and
produce multi-horizon forecasts for financial decision agents.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class MarketCompany:
    ticker: str
    name: str
    sector: str
    # Financials (百万円)
    revenue: float
    ebit: float
    net_income: float
    equity_book: float
    net_debt: float
    fcf: float
    shares_outstanding_m: float  # 百万株
    # Market
    price_history: list[float]  # 直近月次終値イメージ
    # Qualitative corpus
    business_model: str
    news_items: list[str] = field(default_factory=list)
    analyst_notes: list[str] = field(default_factory=list)


SAMPLE_COMPANIES: list[MarketCompany] = [
    MarketCompany(
        ticker="NWD",
        name="株式会社ノースウィンド製造",
        sector="精密部品",
        revenue=185000,
        ebit=9200,
        net_income=6100,
        equity_book=42000,
        net_debt=18000,
        fcf=7800,
        shares_outstanding_m=12.5,
        price_history=[820, 835, 810, 848, 860, 855, 872, 890, 905, 898, 920, 935],
        business_model=(
            "自動車Tier2向け精密加工を基盤に、半導体装置向け高付加価値部品へ多角化。"
            "顧客との長期契約と内製金型が参入障壁。価格転嫁力は中程度。"
        ),
        news_items=[
            "主要顧客が来期の増産計画を公表、受注残が拡大との報道",
            "原材料価格の上昇が続き、短期的なマージン圧迫が懸念",
            "省エネ設備投資を発表、中期のコスト構造改善に期待",
        ],
        analyst_notes=[
            "ビジネスモデルの転換は明確だが、半導体向け比率上昇は景気感応度を高める",
            "経営陣の実行力は高く、設備投資のROI説明が具体的",
        ],
    ),
    MarketCompany(
        ticker="MDB",
        name="株式会社メディブリッジ",
        sector="医療機器卸",
        revenue=98000,
        ebit=4800,
        net_income=3200,
        equity_book=28000,
        net_debt=9000,
        fcf=4100,
        shares_outstanding_m=8.0,
        price_history=[610, 615, 608, 622, 630, 640, 635, 650, 662, 670, 668, 680],
        business_model=(
            "地域基幹病院ネットワークを持つ医療機器卸。"
            "安定した回収サイトと薬機法コンプライアンスが強み。デジタルヘルス連携が成長ドライバー。"
        ),
        news_items=[
            "遠隔モニタリング企業との業務提携を発表、市場は前向きに評価",
            "保険償還改定の影響は中立との見解が多数",
            "在庫最適化プロジェクトが進捗、運転資本改善に寄与",
        ],
        analyst_notes=[
            "ディフェンシブ需要で下方耐性あり。成長は提携実行次第",
            "ガバナンスとコンプライアンス評価は業界上位",
        ],
    ),
    MarketCompany(
        ticker="GLG",
        name="グリーンロジHD",
        sector="物流",
        revenue=210000,
        ebit=6500,
        net_income=2800,
        equity_book=35000,
        net_debt=52000,
        fcf=2200,
        shares_outstanding_m=20.0,
        price_history=[420, 415, 405, 398, 390, 402, 410, 408, 395, 388, 400, 405],
        business_model=(
            "低温物流とECフルフィルメントが柱。規模メリットはあるが利益率が薄い。"
            "特定荷主依存と人件費・燃料費が構造課題。"
        ),
        news_items=[
            "EC繁忙期の外注需要は堅調だが、価格競争が激化",
            "燃料費高騰で短期業績への警戒感が強まる",
            "システム連携パートナー募集を強化、マッチング期待",
        ],
        analyst_notes=[
            "レバレッジが高く金利上昇局面ではバリュエーションディスカウント",
            "事業は必要不可欠だが、真の企業価値は資本効率改善が鍵",
        ],
    ),
]


class EnterpriseValueAgent:
    """Multi-modal valuation & forecast agent for financial decisions."""

    def __init__(self, policy_rate: float = 0.005) -> None:
        self._companies = {c.ticker: c for c in SAMPLE_COMPANIES}
        self._by_name = {c.name: c for c in SAMPLE_COMPANIES}
        self.policy_rate = policy_rate

    def list_universe(self) -> list[dict[str, Any]]:
        return [
            {
                "ticker": c.ticker,
                "name": c.name,
                "sector": c.sector,
                "last_price": c.price_history[-1],
                "revenue": c.revenue,
            }
            for c in self._companies.values()
        ]

    def analyze(self, query: str, ticker: str | None = None, horizon_months: int = 6) -> dict[str, Any]:
        company = self._resolve(query, ticker)
        rates = self._rate_context()
        quant = self._quantitative_block(company, rates)
        qual = self._qualitative_nlp(company)
        ts = self._time_series_forecast(company.price_history, horizon_months)
        fusion = self._deep_fusion(quant, qual, ts)
        valuation = self._enterprise_value(company, quant, qual, fusion, rates)
        decision = self._decision_view(company, valuation, fusion, ts)

        message = self._format_message(company, valuation, qual, ts, fusion, decision)
        return {
            "product": "TempestAI企業価値推定・高度予測エージェント",
            "thesis": (
                "財務・株価・金利などの定量と、ニュース・ビジネスモデル・センチメントなどの定性を"
                "生成AI×時系列予測×深層融合で統合し、真の企業価値と意思決定用予測を出力する。"
            ),
            "company": {
                "ticker": company.ticker,
                "name": company.name,
                "sector": company.sector,
            },
            "quantitative": quant,
            "qualitative": qual,
            "time_series": ts,
            "deep_fusion": fusion,
            "valuation": valuation,
            "decision": decision,
            "rates": rates,
            "message": message,
            "next_actions": [
                "推定EVと市場価格のギャップを投資/与信委員会の共通指標にする",
                "定性センチメント悪化トリガーでモニタリング頻度を上げる",
                "予測パス（ベース/上下）を意思決定構造エンジンのシナリオに接続する",
            ],
        }

    def _resolve(self, query: str, ticker: str | None) -> MarketCompany:
        if ticker and ticker.upper() in self._companies:
            return self._companies[ticker.upper()]
        for c in self._companies.values():
            if c.ticker in query.upper() or c.name in query:
                return c
        if any(k in query for k in ("医療", "メディ", "ヘルスケア")):
            return self._companies["MDB"]
        if any(k in query for k in ("物流", "グリーン", "EC")):
            return self._companies["GLG"]
        if any(k in query for k in ("製造", "ノース", "精密", "半導体")):
            return self._companies["NWD"]
        m = re.search(r"\b([A-Z]{2,5})\b", query.upper())
        if m and m.group(1) in self._companies:
            return self._companies[m.group(1)]
        return SAMPLE_COMPANIES[0]

    def _rate_context(self) -> dict[str, Any]:
        # Simple rate curve demo (policy + term premium)
        curve = {
            "policy_rate": self.policy_rate,
            "yield_2y": round(self.policy_rate + 0.004, 4),
            "yield_10y": round(self.policy_rate + 0.012, 4),
            "credit_spread_bbb": 0.015,
        }
        wacc_proxy = curve["yield_10y"] + curve["credit_spread_bbb"] + 0.04
        return {**curve, "wacc_proxy": round(wacc_proxy, 4)}

    def _quantitative_block(self, c: MarketCompany, rates: dict[str, Any]) -> dict[str, Any]:
        ebit_margin = c.ebit / max(c.revenue, 1)
        fcf_yield = c.fcf / max(c.equity_book + c.net_debt, 1)
        roe = c.net_income / max(c.equity_book, 1)
        leverage = c.net_debt / max(c.equity_book, 1)
        last = c.price_history[-1]
        market_cap = last * c.shares_outstanding_m  # 百万円単位で揃える近似
        ev_market = market_cap + c.net_debt
        return {
            "financials": {
                "revenue": c.revenue,
                "ebit": c.ebit,
                "net_income": c.net_income,
                "equity_book": c.equity_book,
                "net_debt": c.net_debt,
                "fcf": c.fcf,
                "ebit_margin": round(ebit_margin, 4),
                "roe": round(roe, 4),
                "leverage": round(leverage, 4),
                "fcf_yield_on_ev_book": round(fcf_yield, 4),
            },
            "market": {
                "last_price": last,
                "market_cap_approx": round(market_cap, 1),
                "ev_market_approx": round(ev_market, 1),
                "price_mom_3m": round(last / c.price_history[-4] - 1, 4) if len(c.price_history) >= 4 else 0.0,
                "price_mom_12m": round(last / c.price_history[0] - 1, 4),
            },
            "rates_impact": {
                "wacc_proxy": rates["wacc_proxy"],
                "duration_sensitivity": round(min(1.0, leverage * 0.35 + 0.2), 2),
            },
            "quant_score": round(
                max(
                    0.0,
                    min(
                        100.0,
                        45
                        + ebit_margin * 400
                        + roe * 120
                        + fcf_yield * 200
                        - leverage * 12
                        + (last / c.price_history[0] - 1) * 40,
                    ),
                ),
                1,
            ),
        }

    def _qualitative_nlp(self, c: MarketCompany) -> dict[str, Any]:
        """LLM-style language processing over news / business model / sentiment."""
        corpus = " ".join([c.business_model, *c.news_items, *c.analyst_notes])
        pos = ("拡大", "提携", "改善", "期待", "強み", "安定", "前向き", "具体的", "上位", "増産", "寄与")
        neg = ("懸念", "圧迫", "警戒", "激化", "高騰", "薄い", "依存", "ディスカウント", "課題", "悪化")
        pos_hits = [w for w in pos if w in corpus]
        neg_hits = [w for w in neg if w in corpus]
        raw = 0.15 * len(pos_hits) - 0.18 * len(neg_hits)
        # Business model quality cues
        if "参入障壁" in c.business_model or "長期契約" in c.business_model:
            raw += 0.12
        if "利益率が薄い" in c.business_model or "依存" in c.business_model:
            raw -= 0.15
        sentiment = max(-1.0, min(1.0, raw))
        sentiment_score = round(50 + sentiment * 40, 1)

        themes = []
        if any(k in corpus for k in ("半導体", "増産", "受注")):
            themes.append("需要拡大")
        if any(k in corpus for k in ("提携", "デジタル", "連携")):
            themes.append("成長オプション")
        if any(k in corpus for k in ("原材料", "燃料", "金利", "レバレッジ")):
            themes.append("コスト/金利圧力")
        if any(k in corpus for k in ("ガバナンス", "コンプライアンス")):
            themes.append("ガバナンス評価")

        model_summary = c.business_model[:120] + ("…" if len(c.business_model) > 120 else "")
        return {
            "business_model_summary": model_summary,
            "sentiment": round(sentiment, 3),
            "sentiment_label": "強気" if sentiment > 0.15 else "弱気" if sentiment < -0.15 else "中立",
            "sentiment_score": sentiment_score,
            "themes": themes or ["中立観測"],
            "news_digest": c.news_items[:3],
            "nlp_features": {
                "positive_cues": pos_hits[:6],
                "negative_cues": neg_hits[:6],
                "method": "LLM-oriented lexicon + business-model heuristics (demo; swap-in real LLM)",
            },
            "qual_score": sentiment_score,
        }

    def _time_series_forecast(self, history: list[float], horizon: int) -> dict[str, Any]:
        """Classical + ML-ish time series forecast (trend + residual vol)."""
        y = np.asarray(history, dtype=float)
        n = len(y)
        x = np.arange(n, dtype=float)
        # OLS trend
        coef = np.polyfit(x, y, 1)
        trend = np.poly1d(coef)
        fitted = trend(x)
        resid = y - fitted
        vol = float(np.std(resid)) if n > 2 else float(np.std(y) * 0.05)
        # Exponential smoothing blend
        alpha = 0.35
        level = float(y[0])
        for v in y[1:]:
            level = alpha * float(v) + (1 - alpha) * level
        drift = float(coef[0])

        h = max(1, min(horizon, 12))
        base, upside, downside = [], [], []
        last_x = n - 1
        for i in range(1, h + 1):
            t = last_x + i
            point = 0.55 * float(trend(t)) + 0.45 * (level + drift * i)
            base.append(round(point, 2))
            upside.append(round(point + 1.28 * vol * math.sqrt(i), 2))
            downside.append(round(max(0.01, point - 1.28 * vol * math.sqrt(i)), 2))

        return {
            "method": "OLS trend + exponential smoothing (時系列予測) / residual vol bands",
            "history": [round(float(v), 2) for v in y.tolist()],
            "horizon_months": h,
            "forecast_base": base,
            "forecast_upside": upside,
            "forecast_downside": downside,
            "expected_return_horizon": round(base[-1] / float(y[-1]) - 1, 4),
            "volatility": round(vol, 3),
            "momentum_score": round(max(0.0, min(100.0, 50 + (float(y[-1]) / float(y[0]) - 1) * 120)), 1),
        }

    def _deep_fusion(self, quant: dict, qual: dict, ts: dict) -> dict[str, Any]:
        """Lightweight deep fusion: multi-layer nonlinear mix of modality embeddings."""
        # Build 8-d feature vector
        f = np.array(
            [
                quant["quant_score"] / 100.0,
                qual["qual_score"] / 100.0,
                ts["momentum_score"] / 100.0,
                (1 + ts["expected_return_horizon"]),
                quant["financials"]["ebit_margin"] * 8,
                max(0.0, 1.0 - quant["financials"]["leverage"] / 3),
                (qual["sentiment"] + 1) / 2,
                1.0 - quant["rates_impact"]["duration_sensitivity"] * 0.5,
            ],
            dtype=float,
        )
        rng = np.random.default_rng(42)  # stable demo weights
        w1 = rng.normal(0, 0.35, size=(8, 6))
        b1 = rng.normal(0, 0.05, size=(6,))
        w2 = rng.normal(0, 0.35, size=(6, 3))
        b2 = rng.normal(0, 0.05, size=(3,))
        h1 = np.tanh(f @ w1 + b1)
        h2 = np.tanh(h1 @ w2 + b2)
        # Map head: value_alpha, risk, growth
        value_alpha = float(1 / (1 + math.exp(-h2[0] * 2)))  # 0-1
        risk = float(1 / (1 + math.exp(-h2[1] * 2)))
        growth = float(1 / (1 + math.exp(-h2[2] * 2)))
        fused = round(max(0.0, min(100.0, (value_alpha * 0.45 + growth * 0.35 + (1 - risk) * 0.20) * 100)), 1)
        return {
            "method": "2-layer tanh fusion network over quant/qual/TS embeddings (デモ深層学習)",
            "modality_weights": {
                "quantitative": 0.40,
                "qualitative_nlp": 0.35,
                "time_series": 0.25,
            },
            "heads": {
                "value_alpha": round(value_alpha, 3),
                "risk": round(risk, 3),
                "growth": round(growth, 3),
            },
            "fused_score": fused,
            "embedding_preview": [round(float(x), 3) for x in f.tolist()],
        }

    def _enterprise_value(
        self,
        c: MarketCompany,
        quant: dict,
        qual: dict,
        fusion: dict,
        rates: dict,
    ) -> dict[str, Any]:
        wacc = max(0.06, rates["wacc_proxy"])
        g = max(0.0, min(0.04, 0.008 + fusion["heads"]["growth"] * 0.025))
        # Reference models (百万円) — used as explainability components
        dcf_ev = c.fcf * (1 + g) / max(wacc - g, 0.04)
        ev_ebit = c.ebit * (8 + fusion["heads"]["value_alpha"] * 4)
        book_ev = c.equity_book + c.net_debt
        market_price = c.price_history[-1]
        # price(円) × 百万株 = 百万円の時価総額
        market_cap = market_price * c.shares_outstanding_m
        ev_market = market_cap + c.net_debt
        # Decision-usable fair value: market-anchored tilt from quant/qual/deep heads
        tilt = (
            (quant["quant_score"] - 50) / 350
            + qual["sentiment"] * 0.10
            + (fusion["heads"]["growth"] - 0.5) * 0.08
            - (fusion["heads"]["risk"] - 0.5) * 0.10
            + (fusion["heads"]["value_alpha"] - 0.5) * 0.06
        )
        tilt = max(-0.25, min(0.25, tilt))
        intrinsic_ev = ev_market * (1 + tilt)
        equity_value = intrinsic_ev - c.net_debt
        fair_price = equity_value / max(c.shares_outstanding_m, 0.01)
        upside = fair_price / market_price - 1
        return {
            "intrinsic_ev": round(float(intrinsic_ev), 1),
            "equity_value": round(float(equity_value), 1),
            "fair_price": round(float(fair_price), 2),
            "market_price": market_price,
            "upside_to_fair": round(float(upside), 4),
            "components": {
                "dcf_ev_ref": round(float(dcf_ev), 1),
                "multiple_ev_ref": round(float(ev_ebit), 1),
                "book_ev_ref": round(float(book_ev), 1),
                "ev_market": round(float(ev_market), 1),
                "fundamental_tilt": round(float(tilt), 4),
                "growth_assumption": round(g, 4),
                "wacc": wacc,
            },
            "label": (
                "割安（質的プレミアム込み）"
                if upside > 0.08
                else "割高警戒"
                if upside < -0.08
                else "概ね公正価値"
            ),
        }

    def _decision_view(
        self,
        c: MarketCompany,
        valuation: dict,
        fusion: dict,
        ts: dict,
    ) -> dict[str, Any]:
        upside = valuation["upside_to_fair"]
        if upside > 0.1 and fusion["fused_score"] >= 55:
            stance, action = "accumulate", "積増し / 積極与信・持ち分検討"
        elif upside < -0.1 or fusion["heads"]["risk"] > 0.65:
            stance, action = "reduce", "縮小 / 条件強化・モニタリング"
        else:
            stance, action = "hold", "中立保有 / 選別的対応"
        return {
            "stance": stance,
            "action": action,
            "confidence": round(min(0.92, 0.55 + abs(upside) + fusion["fused_score"] / 400), 2),
            "drivers": [
                f"公正価値ギャップ {upside:.1%}",
                f"深層融合スコア {fusion['fused_score']}",
                f"予測リターン({ts['horizon_months']}M) {ts['expected_return_horizon']:.1%}",
                f"セクター {c.sector}",
            ],
        }

    def _format_message(
        self,
        c: MarketCompany,
        valuation: dict,
        qual: dict,
        ts: dict,
        fusion: dict,
        decision: dict,
    ) -> str:
        return (
            f"【TempestAI企業価値推定・高度予測】{c.name}（{c.ticker}）\n"
            f"真の企業価値(EV): ¥{valuation['intrinsic_ev']:,.1f}百万"
            f" / 公正株価: {valuation['fair_price']}（市場 {valuation['market_price']}）\n"
            f"評価: {valuation['label']}（アップサイド {valuation['upside_to_fair']:.1%}）\n"
            f"定性NLP: {qual['sentiment_label']}（score {qual['qual_score']}）"
            f" テーマ: {', '.join(qual['themes'])}\n"
            f"時系列予測({ts['horizon_months']}M): "
            f"base {ts['forecast_base'][-1]} / up {ts['forecast_upside'][-1]} / down {ts['forecast_downside'][-1]}\n"
            f"深層融合スコア: {fusion['fused_score']} "
            f"(α={fusion['heads']['value_alpha']}, risk={fusion['heads']['risk']}, growth={fusion['heads']['growth']})\n"
            f"意思決定スタンス: {decision['action']}（確信度 {decision['confidence']}）"
        )


valuation_agent = EnterpriseValueAgent()
