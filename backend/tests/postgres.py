import asyncio

import asyncpg
from sqlalchemy.engine import URL, make_url

from sellpilot.core.config import Settings

TEST_DATABASE_NAME = "sellpilot_test"


class TestDatabaseUrl(str):
    __test__ = False

    def __repr__(self) -> str:
        url = make_url(str(self))
        return repr(url.render_as_string(hide_password=True))


def _postgres_url(database: str) -> URL:
    url = make_url(Settings().database_url)
    if not url.drivername.startswith("postgresql"):
        raise RuntimeError("SellPilot tests require a PostgreSQL DATABASE_URL")
    return url.set(database=database)


async def _ensure_database() -> None:
    admin_url = _postgres_url("postgres")
    connection = await asyncpg.connect(
        user=admin_url.username,
        password=admin_url.password,
        host=admin_url.host,
        port=admin_url.port or 5432,
        database=admin_url.database,
    )
    try:
        exists = await connection.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            TEST_DATABASE_NAME,
        )
        if not exists:
            await connection.execute(f'CREATE DATABASE "{TEST_DATABASE_NAME}"')
    finally:
        await connection.close()


async def _reset_schema(database_url: str) -> None:
    url = make_url(database_url)
    connection = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port or 5432,
        database=url.database,
    )
    try:
        await connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        await connection.execute("CREATE SCHEMA public")
    finally:
        await connection.close()


def ensure_test_database_url() -> TestDatabaseUrl:
    asyncio.run(_ensure_database())
    return TestDatabaseUrl(_postgres_url(TEST_DATABASE_NAME).render_as_string(hide_password=False))


def reset_test_schema(database_url: str) -> None:
    asyncio.run(_reset_schema(database_url))
