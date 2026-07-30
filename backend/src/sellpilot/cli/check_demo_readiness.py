"""Report demo readiness without exposing connection strings or secrets."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Final

from sqlalchemy import text

from sellpilot.core.config import Settings, get_settings
from sellpilot.db.session import get_session_factory

CORE_QUERIES: Final[dict[str, str]] = {
    "administrators": 'SELECT COUNT(*) FROM "users"',
    "products": 'SELECT COUNT(*) FROM "products"',
    # Intelligent selection reads imported market snapshots directly from products.
    # selection_candidates is an unrelated user-owned persistence table and may
    # legitimately be empty before the first analysis is saved.
    "market_products": (
        'SELECT COUNT(*) FROM "products" '
        "WHERE site IS NOT NULL AND category_external_id IS NOT NULL"
    ),
    "reviews": 'SELECT COUNT(*) FROM "reviews"',
    "skus": 'SELECT COUNT(*) FROM "skus"',
    "inventory": 'SELECT COUNT(*) FROM "inventory_records"',
    "orders": 'SELECT COUNT(*) FROM "orders"',
    "logistics": 'SELECT COUNT(*) FROM "logistics_records"',
    "customer_sessions": 'SELECT COUNT(*) FROM "customer_sessions"',
}


def classify_readiness(
    counts: dict[str, int],
    *,
    indexed_documents: int,
    indexed_chunks: int,
) -> str:
    if any(counts.get(name, 0) <= 0 for name in CORE_QUERIES):
        return "NOT_READY"
    if indexed_documents <= 0 or indexed_chunks <= 0:
        return "BLOCKED_RAG_DATA"
    return "READY"


def classify_knowledge_readiness(*, real_documents: int, real_chunks: int) -> str:
    return "READY" if real_documents > 0 and real_chunks > 0 else "BLOCKED_RAG_DATA"


async def readiness_snapshot(settings: Settings) -> dict[str, object]:
    async with get_session_factory()() as session:
        await session.execute(text("SELECT 1"))
        counts = {
            name: int(await session.scalar(text(query)) or 0)
            for name, query in CORE_QUERIES.items()
        }
        indexed_documents = int(
            await session.scalar(
                text("SELECT COUNT(*) FROM knowledge_documents WHERE status = 'indexed'")
            )
            or 0
        )
        indexed_chunks = int(
            await session.scalar(
                text(
                    "SELECT COUNT(*) FROM knowledge_chunks AS chunk "
                    "JOIN knowledge_documents AS document ON document.id = chunk.document_id "
                    "WHERE document.status = 'indexed'"
                )
            )
            or 0
        )
        embedded_chunks = int(
            await session.scalar(
                text("SELECT COUNT(*) FROM knowledge_chunks WHERE embedding_status = 'embedded'")
            )
            or 0
        )
        real_documents = int(
            await session.scalar(
                text(
                    "SELECT COUNT(*) FROM knowledge_documents "
                    "WHERE status = 'indexed' AND is_mock_data IS FALSE"
                )
            )
            or 0
        )
        real_chunks = int(
            await session.scalar(
                text(
                    "SELECT COUNT(*) FROM knowledge_chunks AS chunk "
                    "JOIN knowledge_documents AS document ON document.id = chunk.document_id "
                    "WHERE document.status = 'indexed' "
                    "AND document.is_mock_data IS FALSE "
                    "AND chunk.is_mock_data IS FALSE"
                )
            )
            or 0
        )
        legacy_demo_documents = int(
            await session.scalar(
                text(
                    "SELECT COUNT(*) FROM knowledge_documents "
                    "WHERE source LIKE 'products.csv#%' "
                    "OR source LIKE 'reviews.csv#%' "
                    "OR source LIKE 'customer_messages.csv#%'"
                )
            )
            or 0
        )
        legacy_demo_chunks = int(
            await session.scalar(
                text(
                    "SELECT COUNT(*) FROM knowledge_chunks AS chunk "
                    "JOIN knowledge_documents AS document ON document.id = chunk.document_id "
                    "WHERE document.source LIKE 'products.csv#%' "
                    "OR document.source LIKE 'reviews.csv#%' "
                    "OR document.source LIKE 'customer_messages.csv#%'"
                )
            )
            or 0
        )
        user_uploaded_documents = int(
            await session.scalar(
                text(
                    "SELECT COUNT(*) FROM knowledge_documents "
                    "WHERE COALESCE(source, '') NOT LIKE 'products.csv#%' "
                    "AND COALESCE(source, '') NOT LIKE 'reviews.csv#%' "
                    "AND COALESCE(source, '') NOT LIKE 'customer_messages.csv#%' "
                    "AND COALESCE(source, '') <> 'knowledge_mock/return-policy.md'"
                )
            )
            or 0
        )
        user_uploaded_chunks = int(
            await session.scalar(
                text(
                    "SELECT COUNT(*) FROM knowledge_chunks AS chunk "
                    "JOIN knowledge_documents AS document ON document.id = chunk.document_id "
                    "WHERE COALESCE(document.source, '') NOT LIKE 'products.csv#%' "
                    "AND COALESCE(document.source, '') NOT LIKE 'reviews.csv#%' "
                    "AND COALESCE(document.source, '') NOT LIKE 'customer_messages.csv#%' "
                    "AND COALESCE(document.source, '') <> 'knowledge_mock/return-policy.md'"
                )
            )
            or 0
        )
        alembic_version = await session.scalar(text("SELECT version_num FROM alembic_version"))

    llm_key = settings.llm_api_key.get_secret_value().strip()
    bailian_key = (
        settings.bailian_api_key.get_secret_value().strip() if settings.bailian_api_key else ""
    )
    return {
        "overall_status": classify_readiness(
            counts,
            indexed_documents=real_documents,
            indexed_chunks=real_chunks,
        ),
        "database": {
            "reachable": True,
            "dialect": "postgresql",
            "alembic_version": str(alembic_version or ""),
        },
        "data": counts,
        "knowledge": {
            "status": classify_knowledge_readiness(
                real_documents=real_documents,
                real_chunks=real_chunks,
            ),
            "indexed_documents": indexed_documents,
            "indexed_chunks": indexed_chunks,
            "embedded_chunks": embedded_chunks,
            "real_documents": real_documents,
            "real_chunks": real_chunks,
            "mock_documents": indexed_documents - real_documents,
            "mock_chunks": indexed_chunks - real_chunks,
            "legacy_demo_documents": legacy_demo_documents,
            "legacy_demo_chunks": legacy_demo_chunks,
            "user_uploaded_documents": user_uploaded_documents,
            "user_uploaded_chunks": user_uploaded_chunks,
        },
        "configuration": {
            "app_env": settings.app_env,
            "platform_adapter": settings.platform_adapter,
            "content_model_provider": settings.content_model_provider,
            "llm_configured": bool(llm_key and llm_key != "replace_me"),
            "bailian_configured": bool(bailian_key and settings.bailian_base_url),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check PostgreSQL demo data and configuration without printing secrets"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless core data and knowledge data are both ready",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    try:
        snapshot = asyncio.run(readiness_snapshot(settings))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "overall_status": "NOT_READY",
                    "database": {"reachable": False},
                    "error_type": type(exc).__name__,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(1) from None
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    if args.strict and snapshot["overall_status"] != "READY":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
