"""Fintech package catalog — PoC to production offerings."""

from __future__ import annotations

from typing import Any

PACKAGE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "tempest-valuation",
        "brand": "TempestAI",
        "name": "企業価値推定・高度予測エージェント",
        "tagline": "生成AI×時系列予測×深層学習で、定量・定性を統合し真の企業価値と高度予測を実現",
        "capabilities": [
            "財務諸表・株価・金利などの定量処理",
            "ニュース・ビジネスモデル・センチメントの言語処理",
            "時系列予測（トレンド＋平滑化＋変動バンド）",
            "深層融合ネットワークによる意思決定スコア",
        ],
        "intents": ["value_forecast"],
        "apis": ["/api/v1/tempest/valuation/analyze", "/api/v1/tempest/valuation/universe"],
    },
    {
        "id": "tempest-decision",
        "brand": "TempestAI",
        "name": "意思決定構造エンジン",
        "tagline": "金融・経済の定性・定量データを統合し、業務効率化ではなく意思決定構造そのものを変革",
        "capabilities": [
            "定性・定量の同一 Evidence Ledger 化",
            "基準木・シナリオ3分岐・反対仮説ボード",
            "決裁権限と役割責任の構造化",
            "効率化ではなく再現可能・反証可能な意思決定へ転換",
        ],
        "intents": ["decision_structure"],
        "apis": ["/api/v1/tempest/decision/transform", "/api/v1/tempest/decision/cases"],
    },
    {
        "id": "tempest-loan",
        "brand": "TempestAI",
        "name": "融資稟議AIシステム",
        "tagline": "定性情報を含む稟議資料を解析し、迅速かつ高精度な融資判断をサポート",
        "capabilities": [
            "稟議書・定性情報の構造化解析",
            "定量指標と定性評価の統合スコア",
            "リスクフラグと推奨判断（承認 / 条件付 / 否決）",
            "審査メモ自動生成（現場で毎日使える出力）",
        ],
        "intents": ["loan_screening", "decision_structure"],
        "apis": ["/api/v1/tempest/loan/analyze", "/api/v1/tempest/loan/applications"],
    },
    {
        "id": "tempest-matching",
        "brand": "TempestAI",
        "name": "ビジネスマッチングAIシステム",
        "tagline": "取引先データや外部情報を解析し、企業間マッチングを自動化・高度化",
        "capabilities": [
            "取引先プロファイルとニーズのベクトル照合",
            "外部シグナル（業界動向・ニュース）の加味",
            "マッチ候補のスコアリングと理由説明",
            "営業フォロー提案の自動生成",
        ],
        "intents": ["b2b_matching", "sales_support"],
        "apis": ["/api/v1/tempest/matching/search", "/api/v1/tempest/matching/companies"],
    },
    {
        "id": "tempest-ops",
        "brand": "TempestAI",
        "name": "金融業務AIスイート",
        "tagline": "FAQ対応・信用審査補助・営業支援をマルチエージェントで一気通貫",
        "capabilities": [
            "FAQ / ナレッジRAG対応",
            "信用審査補助（融資稟議と連携）",
            "営業トーク・次アクション提案",
            "PoCから本番運用まで同一オーケストレーション",
        ],
        "intents": ["knowledge", "loan_screening", "sales_support"],
        "apis": ["/api/v1/chat", "/api/v1/knowledge"],
    },
]


def list_packages() -> list[dict[str, Any]]:
    return PACKAGE_CATALOG
