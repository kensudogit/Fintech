# Fintech AI Platform

自然言語操作支援・行動分析パーソナライズ・ナレッジ連携 RAG・マルチエージェント・オーケストレーションを備えた Fintech 向け AI 基盤です。

## 技術スタック

| 領域 | 技術 |
|---|---|
| Frontend | Next.js + React + TypeScript |
| API | FastAPI |
| Ops UI | Streamlit |
| LLM | LangChain / LangGraph（OpenAI / Google / Mock） |
| DB | PostgreSQL 16 |
| Cloud | GCP（Cloud Run / Cloud SQL / GCS / Secret Manager） |

## アーキテクチャ

```text
User (Next.js / Streamlit)
        │
        ▼
   FastAPI Gateway
        │
        ▼
 LangGraph Orchestrator
   ├─ Intent Classifier
   ├─ Operations Agent      … 自然言語 → 操作サポート
   ├─ Personalization Agent … 行動データ分析・提案
   └─ Knowledge Agent (RAG) … PostgreSQL ナレッジDB連携
        │
        ▼
 PostgreSQL (users / events / dialogues / knowledge / agent_runs)
```

## デプロイ（Dockerfile）

リポジトリ直下に `Dockerfile` を置いています。Railway 等で
`couldn't locate the dockerfile at path Dockerfile` となる場合は、
**Root Directory をリポジトリルート**、**Dockerfile Path を `Dockerfile`** にしてください。

```bash
docker build -t fintech-api .
docker run --rm -p 8080:8080 -e DATABASE_URL=... fintech-api
```

## クイックスタート

### 1. 前提

- Docker Desktop
- Python 3.12+（ローカル API 起動時）
- Node.js 20+

### 2. 環境変数

```powershell
cd C:\devlop\Fintech
copy .env.example .env
```

API キーなしでも `LLM_PROVIDER=mock` で動作します。本番相当の応答には:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

または

```env
LLM_PROVIDER=google
GOOGLE_API_KEY=...
```

### 3. PostgreSQL + API + Streamlit（Docker）

```powershell
cd C:\devlop\Fintech
docker compose up -d --build
```

- API docs: http://localhost:8080/docs
- Streamlit: http://localhost:8501
- PostgreSQL: `localhost:15432` / user=`fintech` / pass=`fintech_secret` / db=`fintech_ai`

### 4. フロントエンド（Next.js）

```powershell
cd C:\devlop\Fintech\frontend
copy .env.local.example .env.local
npm install
npm run dev
```

http://localhost:3000

### 5. ローカル Python API（Docker なし）

```powershell
cd C:\devlop\Fintech
docker compose up -d postgres
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

デモ行動データの投入:

```powershell
python -m scripts.seed_events
```

## 主要 API

| Method | Path | 説明 |
|---|---|---|
| POST | `/api/v1/chat` | マルチエージェント対話 |
| POST | `/api/v1/events` | 行動イベント登録 |
| GET | `/api/v1/users/{id}/suggestions` | パーソナライズ提案 |
| GET/POST | `/api/v1/knowledge` | ナレッジ参照・追加 |
| POST | `/api/v1/rag/reindex` | RAG インデックス再構築 |

### Chat 例

```powershell
curl -X POST http://localhost:8080/api/v1/chat `
  -H "Content-Type: application/json" `
  -d '{"message":"振込手数料を教えて","external_id":"demo-user-001"}'
```

## 実装機能マップ

1. **自然言語操作サポート** — `operations` エージェント
2. **行動データ分析・提案** — `personalization` エンジン + エージェント
3. **ナレッジDB連携対話** — PostgreSQL + RAG パイプライン
4. **オーケストレーション** — LangGraph による意図分類とルーティング
5. **パーソナライズ学習** — 行動イベント + 対話履歴からプロファイル更新
6. **RAG / NLP** — 埋め込み検索 + LLM 回答生成（API キー未設定時は Mock）

## ディレクトリ

```text
Fintech/
├── backend/           # FastAPI + LangGraph + RAG
├── frontend/          # Next.js + React + TS
├── streamlit_app/     # 運用ダッシュボード
├── gcp/               # GCP 展開メモ・認証情報置き場
├── docker-compose.yml
└── .env.example
```

## GCP

詳細は [`gcp/README.md`](./gcp/README.md) を参照してください。
"# Fintech" 
