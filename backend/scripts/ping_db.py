import asyncio

import asyncpg


async def main() -> None:
    conn = await asyncpg.connect("postgresql://fintech:fintech_secret@127.0.0.1:15432/fintech_ai")
    print("docs", await conn.fetchval("select count(*) from knowledge_documents"))
    print("users", await conn.fetchval("select count(*) from users"))
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
