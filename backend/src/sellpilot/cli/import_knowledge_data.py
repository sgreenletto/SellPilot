"""将模拟数据导入知识库。

数据来源: data/demo/shopee_mock/
- products.csv → 商品知识 (category=product)
- reviews.csv → 用户评论 (category=review)
- customer_messages.csv + customer_sessions.csv → FAQ (category=faq)
"""

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from sellpilot.core.config import REPOSITORY_ROOT
from sellpilot.db.models.user import User
from sellpilot.db.session import get_session_factory
from sellpilot.services.knowledge_ingestion import (
    KnowledgeIngestionError,
    KnowledgeIngestionService,
)

DEFAULT_DATA_DIR = REPOSITORY_ROOT / "data" / "demo" / "shopee_mock"
DEFAULT_POLICY_PATH = REPOSITORY_ROOT / "data" / "demo" / "knowledge_mock" / "return-policy.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import SellPilot Mock knowledge data")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=(
            "Directory containing products/reviews/messages/sessions CSV files "
            f"(default: {DEFAULT_DATA_DIR})"
        ),
    )
    parser.add_argument(
        "--full-rebuild",
        action="store_true",
        help="Explicitly rebuild the legacy CSV knowledge index (destructive)",
    )
    return parser.parse_args()


async def import_knowledge(data_dir: Path, *, full_rebuild: bool = False) -> dict:
    async with get_session_factory()() as session:
        try:
            service = KnowledgeIngestionService(session)
            if full_rebuild:
                result = await service.import_package(data_dir)
            else:
                owner = await session.scalar(
                    select(User).where(User.is_active.is_(True)).order_by(User.created_at)
                )
                if owner is None:
                    raise KnowledgeIngestionError(
                        "an active user is required before importing knowledge"
                    )
                result = await service.ensure_assistant_demo_policy(
                    DEFAULT_POLICY_PATH,
                    created_by=owner.id,
                )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return result


def main() -> None:
    args = parse_args()
    try:
        summary = asyncio.run(
            import_knowledge(args.data_dir.resolve(), full_rebuild=args.full_rebuild)
        )
    except KnowledgeIngestionError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
