import asyncio
import asyncpg

URLS = [
    "postgresql://forge:forge@localhost:5433/forge",
    "postgresql://forge:forge@localhost:5432/forge",
]


async def main() -> None:
    for url in URLS:
        try:
            conn = await asyncpg.connect(url.replace("postgresql://", "postgres://"))
            print(f"OK {url}")
            await conn.close()
        except Exception as exc:
            print(f"FAIL {url} {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
