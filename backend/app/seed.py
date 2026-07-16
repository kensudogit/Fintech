"""Sample data seeder for PostgreSQL (local + Railway)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BehaviorEvent,
    ConversationMessage,
    ConversationSession,
    KnowledgeDocument,
    User,
    UserProfile,
)
from app.personalization.engine import personalization_engine

SAMPLE_KNOWLEDGE = [
    {
        "source": "policy/faq",
        "title": "口座開設の流れ",
        "content": "口座開設は本人確認書類の提出、メール認証、初期入金の3ステップです。審査は通常1〜2営業日で完了します。",
        "category": "onboarding",
    },
    {
        "source": "policy/faq",
        "title": "振込手数料",
        "content": "同行宛ての振込は無料です。他行宛ては1件あたり145円（税込）です。プレミアムプランは月5回まで他行振込が無料になります。",
        "category": "payments",
    },
    {
        "source": "policy/faq",
        "title": "投資信託の購入",
        "content": "アプリの「投資」タブから銘柄を検索し、金額または口数を指定して購入できます。つみたてNISA対応商品には専用バッジが表示されます。",
        "category": "investments",
    },
    {
        "source": "policy/security",
        "title": "不正利用への対応",
        "content": "身に覚えのない取引を見つけた場合はアプリ内の「サポート」から即座にカード停止が可能です。24時間監視チームが対応します。",
        "category": "security",
    },
    {
        "source": "product/guide",
        "title": "家計分析の見方",
        "content": "行動データをもとに支出カテゴリ別の傾向と節約提案を表示します。週次レポートは毎週月曜に通知されます。",
        "category": "personalization",
    },
    {
        "source": "product/guide",
        "title": "つみたてNISAの始め方",
        "content": "つみたてNISA口座を開設後、毎月の積立額と銘柄を設定すると自動で買付されます。最低積立額は100円からです。",
        "category": "investments",
    },
    {
        "source": "tempest/valuation",
        "title": "企業価値推定と高度予測の枠組み",
        "content": (
            "TempestAI企業価値推定エージェントは、財務諸表・株価・金利などの定量情報と、"
            "ニュース・ビジネスモデル・センチメントなどの定性情報を、生成AI・時系列予測・深層融合で統合します。"
            "DCFとマルチプルに定性調整を加え、公正価値ギャップと予測パスを意思決定に接続します。"
        ),
        "category": "value_forecast",
    },
    {
        "source": "tempest/decision",
        "title": "意思決定構造変革の原則",
        "content": (
            "TempestAI意思決定構造エンジンは、金融・経済情報に眠る定性・定量データを同一の Evidence Ledger に統合し、"
            "業務効率化ではなく意思決定構造そのものを変革します。"
            "基準木・シナリオ3分岐・反対仮説ボード・役割責任を必須成果物とし、単線稟議と口頭補足を廃止します。"
        ),
        "category": "decision_structure",
    },
    {
        "source": "tempest/loan",
        "title": "融資稟議の審査観点",
        "content": (
            "TempestAI融資稟議AIは定量（収益性・安全性・返済能力）と定性（経営者資質・業界見通し・叙述情報）を統合評価します。"
            "DSCR1.2未満は条件付、自己資本比率20%未満は要注意。稟議書は現場決裁で毎日使える要約形式で出力します。"
        ),
        "category": "loan_screening",
    },
    {
        "source": "tempest/loan",
        "title": "信用審査の追加ヒアリング項目",
        "content": (
            "条件付承認時は、資金使途証憑、取引先依存度、在庫回転、保証条件の再確認を必須とします。"
            "定性情報に「抽象的」「依存」が含まれる場合は改善計画のKPI提出を求めます。"
        ),
        "category": "loan_screening",
    },
    {
        "source": "tempest/matching",
        "title": "ビジネスマッチング運用ガイド",
        "content": (
            "TempestAIビジネスマッチングAIは取引先の強み・ニーズ・地域・外部シグナルを照合し候補をスコアリングします。"
            "上位候補は紹介理由と営業トーク付きで出力し、同行訪問まで一気通貫で支援します。"
        ),
        "category": "b2b_matching",
    },
    {
        "source": "tempest/sales",
        "title": "法人営業支援の進め方",
        "content": (
            "営業支援では課題確認→価値提示→具体候補提示→日程クロージングの順でトークを構成します。"
            "資金ニーズがあれば融資稟議AI、商品説明はFAQナレッジへ連携します。"
        ),
        "category": "sales_support",
    },
]

SAMPLE_EVENTS = [
    ("transfer", {"category": "生活費", "amount": 30000, "product": "普通預金"}),
    ("transfer", {"category": "家賃", "amount": 85000, "product": "普通預金"}),
    ("expense", {"category": "飲食", "amount": 1800, "product": "デビット"}),
    ("expense", {"category": "飲食", "amount": 2200, "product": "デビット"}),
    ("expense", {"category": "日用品", "amount": 3200, "product": "クレジットカード"}),
    ("invest_view", {"category": "投資", "product": "つみたてNISA"}),
    ("invest_view", {"category": "投資", "product": "全世界株式"}),
    ("card_use", {"category": "交通", "amount": 540, "product": "クレジットカード"}),
    ("card_use", {"category": "買い物", "amount": 4800, "product": "クレジットカード"}),
    ("login", {"category": "app", "product": "mobile"}),
    ("login", {"category": "app", "product": "web"}),
]

SAMPLE_DIALOGUE = [
    ("user", "振込手数料について教えて", None),
    (
        "assistant",
        "同行宛ては無料、他行宛ては145円です。プレミアムプランなら月5回まで他行振込が無料になります。",
        "knowledge",
    ),
    ("user", "ノースウィンド製造の融資稟議を審査して", None),
    (
        "assistant",
        "【TempestAI融資稟議AI】定量・定性を統合し、承認/条件付/否決の推奨と判断理由を提示します。",
        "loan_screening",
    ),
    ("user", "精密加工企業のビジネスマッチング候補を出して", None),
    (
        "assistant",
        "【TempestAIビジネスマッチングAI】強みとニーズの適合度で候補企業をスコアリングし紹介案を生成します。",
        "b2b_matching",
    ),
]


async def seed_sample_data(session: AsyncSession, *, force: bool = False) -> dict:
    """Insert demo user, knowledge, behavior events, and sample dialogue."""
    stats = {"users": 0, "knowledge": 0, "events": 0, "messages": 0, "forced": force}

    if force:
        await session.execute(delete(ConversationMessage))
        await session.execute(delete(ConversationSession))
        await session.execute(delete(BehaviorEvent))
        await session.execute(delete(UserProfile))
        await session.execute(delete(KnowledgeDocument))
        # keep users table clean for demo id
        await session.execute(delete(User).where(User.external_id == "demo-user-001"))
        await session.commit()

    user = await personalization_engine.ensure_user(session, "demo-user-001", "Demo User")
    user.display_name = "Demo User"
    user.segment = "retail"
    user.risk_tolerance = "moderate"
    stats["users"] = 1

    doc_count = await session.scalar(select(func.count()).select_from(KnowledgeDocument))
    if not doc_count or force:
        if doc_count and force:
            pass  # already deleted
        for item in SAMPLE_KNOWLEDGE:
            exists = await session.scalar(
                select(KnowledgeDocument.id).where(KnowledgeDocument.title == item["title"]).limit(1)
            )
            if exists:
                continue
            session.add(
                KnowledgeDocument(
                    source=item["source"],
                    title=item["title"],
                    content=item["content"],
                    category=item["category"],
                    metadata_={"lang": "ja", "sample": True},
                )
            )
            stats["knowledge"] += 1

    event_count = await session.scalar(
        select(func.count()).select_from(BehaviorEvent).where(BehaviorEvent.user_id == user.id)
    )
    if not event_count or force:
        now = datetime.now(timezone.utc)
        for i, (event_type, payload) in enumerate(SAMPLE_EVENTS):
            session.add(
                BehaviorEvent(
                    user_id=user.id,
                    event_type=event_type,
                    payload=payload,
                    occurred_at=now - timedelta(hours=i * 5 + 1),
                )
            )
            stats["events"] += 1

    msg_count = await session.scalar(
        select(func.count())
        .select_from(ConversationMessage)
        .join(ConversationSession, ConversationMessage.session_id == ConversationSession.id)
        .where(ConversationSession.user_id == user.id)
    )
    if not msg_count or force:
        conv = ConversationSession(
            user_id=user.id,
            title="サンプル対話: 手数料と家計提案",
            channel="seed",
        )
        session.add(conv)
        await session.flush()
        base = datetime.now(timezone.utc) - timedelta(days=1)
        for i, (role, content, agent) in enumerate(SAMPLE_DIALOGUE):
            session.add(
                ConversationMessage(
                    session_id=conv.id,
                    role=role,
                    content=content,
                    agent_name=agent,
                    metadata_={"sample": True},
                    created_at=base + timedelta(minutes=i * 3),
                )
            )
            stats["messages"] += 1

    await session.commit()
    await personalization_engine.rebuild_profile(session, user)
    return stats
