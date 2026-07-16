from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import BehaviorEvent, ConversationMessage, ConversationSession, User, UserProfile


class PersonalizationEngine:
    """Learn from behavior events + dialogue history to produce suggestions."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def ensure_user(self, session: AsyncSession, external_id: str, display_name: str | None = None) -> User:
        result = await session.execute(select(User).where(User.external_id == external_id))
        user = result.scalar_one_or_none()
        if user:
            return user
        user = User(
            external_id=external_id,
            display_name=display_name or external_id,
            email=f"{external_id}@fintech.local",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def record_event(
        self,
        session: AsyncSession,
        user: User,
        event_type: str,
        payload: dict | None = None,
    ) -> BehaviorEvent:
        event = BehaviorEvent(user_id=user.id, event_type=event_type, payload=payload or {})
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event

    async def rebuild_profile(self, session: AsyncSession, user: User) -> UserProfile:
        since = datetime.now(timezone.utc) - timedelta(days=self.settings.personalization_window_days)
        events_result = await session.execute(
            select(BehaviorEvent)
            .where(BehaviorEvent.user_id == user.id, BehaviorEvent.occurred_at >= since)
            .order_by(BehaviorEvent.occurred_at.desc())
        )
        events = events_result.scalars().all()

        type_counts = Counter(e.event_type for e in events)
        categories = Counter()
        products = Counter()
        for e in events:
            cat = (e.payload or {}).get("category")
            prod = (e.payload or {}).get("product")
            if cat:
                categories[str(cat)] += 1
            if prod:
                products[str(prod)] += 1

        # Dialogue interests from recent user messages
        sessions_result = await session.execute(
            select(ConversationSession.id).where(ConversationSession.user_id == user.id)
        )
        session_ids = [row[0] for row in sessions_result.all()]
        keywords: Counter[str] = Counter()
        if session_ids:
            msg_result = await session.execute(
                select(ConversationMessage)
                .where(
                    ConversationMessage.session_id.in_(session_ids),
                    ConversationMessage.role == "user",
                )
                .order_by(ConversationMessage.created_at.desc())
                .limit(50)
            )
            for msg in msg_result.scalars().all():
                for token in self._tokenize(msg.content):
                    keywords[token] += 1

        interests = [k for k, _ in (categories + keywords).most_common(8)]
        preferred = [p for p, _ in products.most_common(5)]
        activity = min(100.0, len(events) * 2.5 + len(session_ids) * 3.0)
        summary = self._summarize(user, type_counts, interests, preferred, activity)

        result = await session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        profile = result.scalar_one_or_none()
        if not profile:
            profile = UserProfile(user_id=user.id)
            session.add(profile)

        profile.interests = interests
        profile.preferred_products = preferred
        profile.activity_score = activity
        profile.summary = summary
        profile.features = {
            "event_counts": dict(type_counts),
            "top_keywords": [k for k, _ in keywords.most_common(10)],
            "event_total": len(events),
        }
        profile.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(profile)
        return profile

    async def suggest(self, session: AsyncSession, user: User) -> dict:
        profile = await self.rebuild_profile(session, user)
        suggestions: list[str] = []

        interests = profile.interests or []
        preferred = profile.preferred_products or []
        features = profile.features or {}
        event_counts = features.get("event_counts", {})

        if event_counts.get("transfer", 0) >= 3:
            suggestions.append("よく振込を利用されています。他行振込無料回数のあるプレミアムプランをご検討ください。")
        if event_counts.get("invest_view", 0) >= 2 or "投資" in interests:
            suggestions.append("投資関連の閲覧が多いため、リスク許容度に合わせたつみたてプランを提案します。")
        if event_counts.get("expense", 0) >= 3 or "飲食" in interests:
            suggestions.append("支出カテゴリの偏りが見られます。週次の家計分析レポート通知を有効化しましょう。")
        if preferred:
            suggestions.append(f"関心の高い商品: {', '.join(preferred[:3])} の詳細比較を表示できます。")
        if profile.activity_score < 15:
            suggestions.append("利用が少なめです。目標貯蓄額を設定するとパーソナライズ提案が精度向上します。")
        if not suggestions:
            suggestions.append("まずは家計カテゴリの確認と、つみたて投資の少額スタートをおすすめします。")

        return {
            "user_id": str(user.id),
            "external_id": user.external_id,
            "profile_summary": profile.summary,
            "interests": interests,
            "preferred_products": preferred,
            "activity_score": profile.activity_score,
            "suggestions": suggestions,
        }

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        import re

        tokens = re.findall(r"[ぁ-んァ-ン一-龥A-Za-z0-9]{2,}", text)
        stop = {"です", "ます", "して", "ください", "とは", "について", "したい", "できる"}
        return [t for t in tokens if t not in stop][:20]

    @staticmethod
    def _summarize(
        user: User,
        type_counts: Counter,
        interests: list[str],
        preferred: list[str],
        activity: float,
    ) -> str:
        top_events = ", ".join(f"{k}:{v}" for k, v in type_counts.most_common(5)) or "なし"
        interest_text = ", ".join(interests[:5]) or "未検出"
        product_text = ", ".join(preferred[:3]) or "未検出"
        return (
            f"{user.display_name}（segment={user.segment}, risk={user.risk_tolerance}）のプロファイル。"
            f"活動スコア={activity:.1f}。主要イベント=[{top_events}]。"
            f"関心=[{interest_text}]。好み商品=[{product_text}]。"
        )


personalization_engine = PersonalizationEngine()
