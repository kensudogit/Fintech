# TempestAI｜金融AIパッケージ

銀行・証券など金融機関向けに、生成AIによる業務改善・意思決定支援を提供する Fintech パッケージです。
**金融・経済情報に眠る定性・定量データを統合し、業務効率化ではなく意思決定構造そのものを変革**します。

## Fintechパッケージ事業

| プロダクト | 概要 |
|---|---|
| **TempestAI企業価値推定・高度予測** | 生成AI×時系列×深層融合で、財務/株価/金利とニュース/BM/センチメントから真のEVを推定 |
| **TempestAI意思決定構造エンジン** | 定性×定量の Evidence Ledger、基準木、シナリオ分岐、反対仮説で決裁構造を再設計 |
| **TempestAI融資稟議AIシステム** | 定性情報を含む稟議資料を解析し、迅速・高精度な融資判断をサポート |
| **TempestAIビジネスマッチングAIシステム** | 取引先データや外部情報を解析し、企業間マッチングを自動化・高度化 |
| **金融業務AIスイート** | FAQ対応・信用審査補助・営業支援を同一オーケストレーションで提供 |

## 実務ソリューション

- 融資稟議 / 信用審査（定量×定性スコア、承認・条件付・否決）
- FAQ対応（ナレッジRAG）
- 営業支援（トークスクリプト・次アクション）
- リテール操作デモ（残高・振込下書き・カード停止）

## アーキテクチャ

```text
User (Web UI)
   │
   ▼
FastAPI Gateway
   │
   ▼
LangGraph Orchestrator
   ├─ value_forecast      → 企業価値推定・高度予測（GenAI×TS×DL）
   ├─ decision_structure  → 意思決定構造エンジン（定性×定量）
   ├─ loan_screening      → TempestAI融資稟議AI
   ├─ b2b_matching        → TempestAIビジネスマッチングAI
   ├─ sales_support       → 営業支援
   └─ knowledge           → FAQ / RAG
          │
          ▼
Quant + Qual NLP + Evidence Ledger + PostgreSQL + FAISS
```

## クイックスタート

```powershell
cd C:\devlop\Fintech
copy .env.example .env
docker compose up -d postgres

cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

- サービス画面: http://127.0.0.1:8080/
- API Docs: http://127.0.0.1:8080/docs
- PostgreSQL: `127.0.0.1:15432` / `fintech` / `fintech_secret` / `fintech_ai`

API キーなしでも `LLM_PROVIDER=mock` で動作します。

## 主要 API

| Method | Path | 説明 |
|---|---|---|
| GET | `/api/v1/tempest/packages` | パッケージ一覧 |
| POST | `/api/v1/tempest/valuation/analyze` | 企業価値推定・高度予測 |
| GET | `/api/v1/tempest/valuation/universe` | 対象銘柄ユニバース |
| POST | `/api/v1/tempest/decision/transform` | 意思決定構造変革 |
| GET | `/api/v1/tempest/decision/cases` | 意思決定ケース一覧 |
| POST | `/api/v1/tempest/loan/analyze` | 融資稟議解析 |
| GET | `/api/v1/tempest/loan/applications` | サンプル稟議案件 |
| POST | `/api/v1/tempest/matching/search` | ビジネスマッチング |
| GET | `/api/v1/tempest/matching/companies` | サンプル企業 |
| POST | `/api/v1/tempest/sales/support` | 営業支援 |
| POST | `/api/v1/chat` | マルチエージェント対話 |
| GET | `/api/v1/dashboard` | 画面用集計（パッケージ含む） |

### 発話例

```text
ノースウィンド製造の企業価値を推定して
メディブリッジの株価を高度予測して
グリーンロジのセンチメントを踏まえて公正価値を出して
定性・定量を統合して意思決定構造を変革して
ノースウィンド製造の融資稟議を審査して
```

## ディレクトリ

```text
Fintech/
├── backend/
│   ├── app/tempest/   # TempestAI packages (loan / matching / sales)
│   ├── app/agents/    # LangGraph orchestration
│   └── app/static/    # サービス画面
├── frontend/          # Next.js (オプション)
├── streamlit_app/     # 運用コンソール
├── docker-compose.yml
└── Dockerfile         # Railway 等向け
```

## デプロイ

ルート `Dockerfile` + `railway.toml` を同梱。GitHub `main` 連携時は push で自動デプロイされます。
Railway Postgres の `DATABASE_URL` は起動時に `postgresql+asyncpg://` へ自動変換されます。
