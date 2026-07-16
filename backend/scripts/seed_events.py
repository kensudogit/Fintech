"""Seed sample behavior events for the demo user."""

from __future__ import annotations

import asyncio

from app.db.session import SessionLocal
from app.personalization.engine import personalization_engine


async def main() -> None:
    samples = [
        ("transfer", {"category": "生活費", "amount": 30000, "product": "普通預金"}),
        ("expense", {"category": "飲食", "amount": 1800, "product": "デビット"}),
        ("expense", {"category": "飲食", "amount": 2200, "product": "デビット"}),
        ("invest_view", {"category": "投資", "product": "つみたてNISA"}),
        ("invest_view", {"category": "投資", "product": "全世界株式"}),
        ("card_use", {"category": "交通", "amount": 540, "product": "クレジットカード"}),
        ("login", {"category": "app", "product": "mobile"}),
    ]
    async with SessionLocal() as session:
        user = await personalization_engine.ensure_user(session, "demo-user-001", "Demo User")
        for event_type, payload in samples:
            await personalization_engine.record_event(session, user, event_type, payload)
        profile = await personalization_engine.rebuild_profile(session, user)
        print("seeded events:", len(samples))
        print("activity_score:", profile.activity_score)
        print("interests:", profile.interests)


if __name__ == "__main__":
    asyncio.run(main())
