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


def csv_row_count(filename: str) -> int:
    with (DATA_DIR / filename).open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


EXPECTED_COUNTS = {
    Shop: 1,
    Product: csv_row_count("products.csv"),
    Sku: csv_row_count("skus.csv"),
    InventoryRecord: csv_row_count("inventory.csv"),
    Order: csv_row_count("orders.csv"),
    OrderItem: csv_row_count("order_items.csv"),
    Review: csv_row_count("reviews.csv"),
    LogisticsRecord: csv_row_count("logistics.csv"),
    LogisticsTrack: csv_row_count("logistics_tracks.csv"),
    CustomerSession: csv_row_count("customer_sessions.csv"),
    CustomerMessage: csv_row_count("customer_messages.csv"),
    ReturnRefund: csv_row_count("returns_refunds.csv"),
    CategoryTrend: csv_row_count("category_trends.csv"),
}
EXPECTED_VALIDATED_ROWS = sum(csv_row_count(path.name) for path in DATA_DIR.glob("*.csv"))
EXPECTED_INSERTED_ROWS = sum(EXPECTED_COUNTS.values())


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
        assert first.rows_validated == EXPECTED_VALIDATED_ROWS
        assert first.inserted_total == EXPECTED_INSERTED_ROWS
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
        assert second.skipped_total == EXPECTED_INSERTED_ROWS
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
