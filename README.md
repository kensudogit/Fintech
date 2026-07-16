# LLM × マルチエージェント｜金融AIプロダクト

自然言語での金融操作サポート、行動データに基づくパーソナライズ提案、ナレッジDB連携RAGを、
**LangGraph マルチエージェント**で統括する Fintech AI プロダクトです。

## プロダクト機能

| 機能 | 説明 |
|---|---|
| マルチエージェント | 複合意図を fan-out（operations / personalization / knowledge）→ synthesize |
| 自然言語操作 | 残高照会・振込下書き・カード停止（確認ID付き、デモ実行） |
| パーソナライズ | 行動イベント + 対話履歴から提案生成 |
| RAG | PostgreSQL ナレッジ + FAISS/コサイン検索 |
| ダッシュボード | ナレッジ・行動イベント・口座残高を画面表示 |

## アーキテクチャ

```text
User (Web UI / Next.js / Streamlit)
        │
        ▼
   FastAPI Gateway  (:8080)
        │
        ▼
 LangGraph Orchestrator
   ├─ Intent Classifier（複数意図可）
   ├─ Operations Agent + Finance Toolkit
   ├─ Personalization Agent
   ├─ Knowledge Agent (RAG)
   └─ Synthesizer
        │
        ▼
 PostgreSQL + FAISS vectorstore
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

- サービス画面: http://127.0.0.1:8080/（利用手順パレット・確認実行 UI 付き）
- API Docs: http://127.0.0.1:8080/docs
- PostgreSQL: `127.0.0.1:15432` / `fintech` / `fintech_secret` / `fintech_ai`
- デモユーザー: `demo-user-001`

API キーなしでも `LLM_PROVIDER=mock` で動作します。

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

## 主要 API

| Method | Path | 説明 |
|---|---|---|
| POST | `/api/v1/chat` | マルチエージェント対話 |
| GET | `/api/v1/accounts/{id}` | デモ口座残高 |
| POST | `/api/v1/actions/confirm` | 振込/カード停止の確定実行 |
| POST | `/api/v1/actions/cancel` | 下書きキャンセル |
| GET | `/api/v1/dashboard` | 画面用集計 |
| POST | `/api/v1/seed` | サンプルデータ投入 |
| GET/POST | `/api/v1/knowledge` | ナレッジ参照・追加 |

### 複合質問の例

```json
{
  "message": "振込手数料について教えて。あと家計の改善提案もして",
  "external_id": "demo-user-001"
}
```

→ `knowledge` + `personalization` が並列実行され、orchestrator が統合回答します。

### 振込（確認フロー）

1. 「太郎へ3000円振り込みたい」→ `pending_action`（確認ID）が返る  
2. `POST /api/v1/actions/confirm` または画面の「確認して実行」

## ディレクトリ

```text
Fintech/
├── backend/           # FastAPI + LangGraph + RAG + Finance tools
├── frontend/          # Next.js (オプション)
├── streamlit_app/     # 運用コンソール
├── docker-compose.yml
└── Dockerfile         # Railway 等向け
```

## デプロイ

ルート `Dockerfile` + `railway.toml` を同梱。Railway Postgres の `DATABASE_URL` は
起動時に `postgresql+asyncpg://` へ自動変換されます。
