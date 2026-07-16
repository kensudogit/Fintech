-- Fintech AI Platform schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(128) UNIQUE NOT NULL,
    display_name VARCHAR(256) NOT NULL,
    email VARCHAR(320),
    segment VARCHAR(64) DEFAULT 'retail',
    risk_tolerance VARCHAR(32) DEFAULT 'moderate',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(256),
    channel VARCHAR(64) DEFAULT 'web',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    agent_name VARCHAR(64),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS behavior_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    interests JSONB DEFAULT '[]'::jsonb,
    preferred_products JSONB DEFAULT '[]'::jsonb,
    activity_score FLOAT DEFAULT 0,
    summary TEXT,
    features JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(256) NOT NULL,
    title VARCHAR(512) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(128),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES conversation_sessions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    intent VARCHAR(128),
    agents_used JSONB DEFAULT '[]'::jsonb,
    routing_trace JSONB DEFAULT '[]'::jsonb,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON conversation_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_events_user_time ON behavior_events(user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_documents(category);

-- Seed demo user
INSERT INTO users (external_id, display_name, email, segment, risk_tolerance)
VALUES ('demo-user-001', 'Demo User', 'demo@fintech.local', 'retail', 'moderate')
ON CONFLICT (external_id) DO NOTHING;

INSERT INTO knowledge_documents (source, title, content, category, metadata)
VALUES
(
  'policy/faq',
  '口座開設の流れ',
  '口座開設は本人確認書類の提出、メール認証、初期入金の3ステップです。審査は通常1〜2営業日で完了します。',
  'onboarding',
  '{"lang":"ja"}'::jsonb
),
(
  'policy/faq',
  '振込手数料',
  '同行宛ての振込は無料です。他行宛ては1件あたり145円（税込）です。プレミアムプランは月5回まで他行振込が無料になります。',
  'payments',
  '{"lang":"ja"}'::jsonb
),
(
  'policy/faq',
  '投資信託の購入',
  'アプリの「投資」タブから銘柄を検索し、金額または口数を指定して購入できます。つみたてNXP対応商品には専用バッジが表示されます。',
  'investments',
  '{"lang":"ja"}'::jsonb
),
(
  'policy/security',
  '不正利用への対応',
  '身に覚えのない取引を見つけた場合はアプリ内の「サポート」から即座にカード停止が可能です。24時間監視チームが対応します。',
  'security',
  '{"lang":"ja"}'::jsonb
),
(
  'product/guide',
  '家計分析の見方',
  '行動データをもとに支出カテゴリ別の傾向と節約提案を表示します。週次レポートは毎週月曜に通知されます。',
  'personalization',
  '{"lang":"ja"}'::jsonb
)
ON CONFLICT DO NOTHING;
