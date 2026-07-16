from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings
from app.db_url import to_asyncpg_url


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(
    to_asyncpg_url(settings.database_url),
    echo=settings.debug and settings.app_env == "development",
    pool_pre_ping=True,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create tables on first boot (Railway / fresh Postgres)."""
    # Import models so metadata is populated
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _seed_if_empty()


async def _seed_if_empty() -> None:
    from sqlalchemy import func, select

    from app.db.models import KnowledgeDocument, User

    async with SessionLocal() as session:
        user_count = await session.scalar(select(func.count()).select_from(User))
        if not user_count:
            session.add(
                User(
                    external_id="demo-user-001",
                    display_name="Demo User",
                    email="demo@fintech.local",
                    segment="retail",
                    risk_tolerance="moderate",
                )
            )

        doc_count = await session.scalar(select(func.count()).select_from(KnowledgeDocument))
        if not doc_count:
            session.add_all(
                [
                    KnowledgeDocument(
                        source="policy/faq",
                        title="口座開設の流れ",
                        content="口座開設は本人確認書類の提出、メール認証、初期入金の3ステップです。審査は通常1〜2営業日で完了します。",
                        category="onboarding",
                        metadata_={"lang": "ja"},
                    ),
                    KnowledgeDocument(
                        source="policy/faq",
                        title="振込手数料",
                        content="同行宛ての振込は無料です。他行宛ては1件あたり145円（税込）です。プレミアムプランは月5回まで他行振込が無料になります。",
                        category="payments",
                        metadata_={"lang": "ja"},
                    ),
                    KnowledgeDocument(
                        source="policy/faq",
                        title="投資信託の購入",
                        content="アプリの「投資」タブから銘柄を検索し、金額または口数を指定して購入できます。つみたてNISA対応商品には専用バッジが表示されます。",
                        category="investments",
                        metadata_={"lang": "ja"},
                    ),
                    KnowledgeDocument(
                        source="policy/security",
                        title="不正利用への対応",
                        content="身に覚えのない取引を見つけた場合はアプリ内の「サポート」から即座にカード停止が可能です。24時間監視チームが対応します。",
                        category="security",
                        metadata_={"lang": "ja"},
                    ),
                    KnowledgeDocument(
                        source="product/guide",
                        title="家計分析の見方",
                        content="行動データをもとに支出カテゴリ別の傾向と節約提案を表示します。週次レポートは毎週月曜に通知されます。",
                        category="personalization",
                        metadata_={"lang": "ja"},
                    ),
                ]
            )
        await session.commit()
