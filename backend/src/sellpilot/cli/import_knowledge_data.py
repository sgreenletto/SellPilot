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

from sellpilot.core.config import REPOSITORY_ROOT
from sellpilot.db.session import get_session_factory
from sellpilot.services.knowledge_ingestion import (
    KnowledgeIngestionError,
    KnowledgeIngestionService,
)

DEFAULT_DATA_DIR = REPOSITORY_ROOT / "data" / "demo" / "shopee_mock"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import mock CSV data into the knowledge base"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Directory containing products/reviews/messages/sessions CSV files (default: {DEFAULT_DATA_DIR})",
    )
    return parser.parse_args()


async def import_knowledge(data_dir: Path) -> dict:
    async with get_session_factory()() as session:
        try:
            result = await KnowledgeIngestionService(session).import_package(data_dir)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return result


def main() -> None:
    args = parse_args()
    try:
        summary = asyncio.run(import_knowledge(args.data_dir.resolve()))
    except KnowledgeIngestionError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
