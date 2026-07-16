"""Seed sample data into PostgreSQL."""

from __future__ import annotations

import asyncio

from app.db.session import SessionLocal
from app.rag.pipeline import rag_service
from app.seed import seed_sample_data


async def main() -> None:
    async with SessionLocal() as session:
        stats = await seed_sample_data(session, force=True)
        indexed = await rag_service.build_index(session)
    print("seed stats:", stats)
    print("indexed documents:", indexed)


if __name__ == "__main__":
    asyncio.run(main())
