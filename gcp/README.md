# GCP 開発ガイド

このプロジェクトはローカル（Docker + PostgreSQL）で完結しつつ、GCP へ段階的に展開できます。

## 推奨構成

| コンポーネント | ローカル | GCP |
|---|---|---|
| API (FastAPI) | Docker / uvicorn | Cloud Run |
| DB | PostgreSQL 16 | Cloud SQL for PostgreSQL |
| フロント (Next.js) | `npm run dev` | Cloud Run / Firebase Hosting |
| Streamlit | Docker | Cloud Run |
| ナレッジファイル | ローカル volume | Cloud Storage |
| シークレット | `.env` | Secret Manager |

## セットアップ手順

1. GCP プロジェクトを作成し、課金を有効化
2. 必要な API を有効化
   ```bash
   gcloud services enable run.googleapis.com sqladmin.googleapis.com \
     secretmanager.googleapis.com storage.googleapis.com aiplatform.googleapis.com
   ```
3. サービスアカウントキーを `gcp/credentials.json` に配置（`.gitignore` 済み）
4. `.env` に以下を設定
   - `GCP_PROJECT_ID`
   - `GCP_REGION=asia-northeast1`
   - `GCS_BUCKET`
   - `CLOUD_SQL_INSTANCE`
   - `GOOGLE_API_KEY`（Gemini 利用時）または `OPENAI_API_KEY`

## Cloud Run デプロイ例

```bash
gcloud run deploy fintech-api \
  --source ./backend \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars LLM_PROVIDER=google
```

## Cloud SQL 接続

ローカル開発では Docker PostgreSQL を使用し、本番のみ Cloud SQL Auth Proxy / Unix socket を利用してください。
