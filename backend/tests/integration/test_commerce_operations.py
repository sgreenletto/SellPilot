from pathlib import Path

from sqlalchemy import func, select

from sellpilot.core.enums import ConfirmationStatus, TaskStatus
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.db.models.commerce import InventoryRecord, Product, Sku
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.services.commerce_import import CommerceImportService
from sellpilot.services.commerce_operations import (
    CommerceOperationService,
    build_commerce_confirmation_service,
)

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "demo" / "shopee_mock"


async def test_inventory_write_waits_for_confirmation_and_executes_once(
    session_factory,
    admin_user,
    test_settings,
):
    async with session_factory() as session:
        await CommerceImportService(session).import_package(DATA_DIR)
        await session.commit()

        product_id, sku_id, inventory = (
            await session.execute(
                select(Product.external_id, Sku.external_id, InventoryRecord)
                .join(Sku, Sku.product_id == Product.id)
                .join(InventoryRecord, InventoryRecord.sku_id == Sku.id)
                .limit(1)
            )
        ).one()
        original_stock = inventory.available_stock

        operations = CommerceOperationService(session, test_settings)
        confirmation = await operations.request_inventory_update(
            product_id=product_id,
            sku_id=sku_id,
            available_stock=0,
            idempotency_key="inventory-test-0001",
            created_by=admin_user.id,
        )
        duplicate = await operations.request_inventory_update(
            product_id=product_id,
            sku_id=sku_id,
            available_stock=0,
            idempotency_key="inventory-test-0001",
            created_by=admin_user.id,
        )
        await session.commit()

        assert duplicate.id == confirmation.id
        assert inventory.available_stock == original_stock
        task = await session.get(AgentTask, confirmation.agent_task_id)
        assert task is not None
        assert task.status == TaskStatus.WAITING_CONFIRMATION

        confirmations = build_commerce_confirmation_service(session, test_settings)
        result = await confirmations.confirm(confirmation.id, admin_user.id)
        await session.commit()
        await session.refresh(inventory)
        await session.refresh(task)

        assert result.status == ConfirmationStatus.SUCCEEDED
        assert inventory.available_stock == 0
        assert inventory.stock_status == "out_of_stock"
        assert task.status == TaskStatus.SUCCEEDED
        assert (await session.scalar(select(func.count()).select_from(OperationLog))) == 1

        repeated = await build_commerce_confirmation_service(session, test_settings).confirm(
            confirmation.id, admin_user.id
        )
        await session.commit()
        assert repeated.status == ConfirmationStatus.SUCCEEDED
        assert (await session.scalar(select(func.count()).select_from(OperationLog))) == 1
