import csv
import shutil
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sellpilot.db.models.commerce import (
    CategoryTrend,
    CustomerMessage,
    CustomerSession,
    InventoryRecord,
    LogisticsRecord,
    LogisticsTrack,
    Order,
    OrderItem,
    Product,
    ReturnRefund,
    Review,
    Shop,
    Sku,
)
from sellpilot.services.commerce_import import CommerceImportError, CommerceImportService

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "demo" / "shopee_mock"

EXPECTED_COUNTS = {
    Shop: 1,
    Product: 100,
    Sku: 260,
    InventoryRecord: 260,
    Order: 500,
    OrderItem: 1229,
    Review: 1000,
    LogisticsRecord: 443,
    LogisticsTrack: 1711,
    CustomerSession: 100,
    CustomerMessage: 596,
    ReturnRefund: 50,
    CategoryTrend: 2880,
}


async def count_rows(session, model) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


@pytest.mark.asyncio
async def test_imports_full_package_and_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
):
    async with session_factory() as session:
        first = await CommerceImportService(session).import_package(DATA_DIR)
        await session.commit()

        assert first.files == 12
        assert first.rows_validated == 9129
        assert first.inserted_total == 9130
        assert first.skipped_total == 0
        for model, expected in EXPECTED_COUNTS.items():
            assert await count_rows(session, model) == expected

        shops = (await session.execute(select(Shop))).scalars().all()
        assert len(shops) == 1
        assert shops[0].external_id == "SELLPILOT_MOCK_SHOP"
        source_shop_ids = set(
            (await session.execute(select(Product.source_shop_external_id))).scalars()
        )
        assert source_shop_ids == {f"SHOP00{index}" for index in range(1, 7)}

        second = await CommerceImportService(session).import_package(DATA_DIR)
        await session.commit()

        assert second.inserted_total == 0
        assert second.skipped_total == 9130
        for model, expected in EXPECTED_COUNTS.items():
            assert await count_rows(session, model) == expected


@pytest.mark.asyncio
async def test_rejects_non_mock_row_without_partial_writes(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
):
    invalid_dir = tmp_path / "invalid-data"
    shutil.copytree(DATA_DIR, invalid_dir)
    products_path = invalid_dir / "products.csv"
    with products_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    rows[0]["is_mock_data"] = "false"
    with products_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    async with session_factory() as session:
        with pytest.raises(CommerceImportError, match="products.csv failed schema validation"):
            await CommerceImportService(session).import_package(invalid_dir)
        await session.rollback()
        assert await count_rows(session, Shop) == 0
        assert await count_rows(session, Product) == 0
