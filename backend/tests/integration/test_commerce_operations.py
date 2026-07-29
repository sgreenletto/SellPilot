from pathlib import Path

import pytest
from sqlalchemy import func, select

from sellpilot.core.enums import ConfirmationStatus, TaskStatus
from sellpilot.core.exceptions import IdempotencyConflictError
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.db.models.commerce import InventoryRecord, Product, SelectionCandidate, Sku
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
        with pytest.raises(IdempotencyConflictError):
            await operations.request_inventory_update(
                product_id=product_id,
                sku_id=sku_id,
                available_stock=original_stock + 1,
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


async def test_draft_import_and_candidate_writes_require_confirmation(
    session_factory,
    admin_user,
    test_settings,
):
    async with session_factory() as session:
        await CommerceImportService(session).import_package(DATA_DIR)
        await session.commit()
        source = await session.scalar(select(Product).limit(1))
        assert source is not None
        operations = CommerceOperationService(session, test_settings)
        payload = {
            "source_shop_id": source.source_shop_external_id,
            "title": "Confirmed draft",
            "category_id": source.category_external_id,
            "category_name": source.category_name,
            "description": "Persisted only after confirmation",
            "site": source.site,
            "currency": source.currency,
            "price": "12.50",
            "cost": "5.00",
            "shipping_cost": "1.00",
            "source_type": "manual_import",
        }

        draft_confirmation = await operations.request_product_draft(
            product=payload,
            idempotency_key="draft-test-0001",
            created_by=admin_user.id,
        )
        candidate_confirmation = await operations.request_candidate_change(
            product_id=source.external_id,
            add=True,
            title=source.title,
            source_type=source.source_type,
            is_mock_data=True,
            idempotency_key="candidate-test-0001",
            created_by=admin_user.id,
        )
        await session.commit()
        assert (
            await session.scalar(select(Product).where(Product.title == "Confirmed draft")) is None
        )
        assert (
            await session.scalar(
                select(SelectionCandidate).where(
                    SelectionCandidate.product_external_id == source.external_id
                )
            )
            is None
        )

        confirmations = build_commerce_confirmation_service(session, test_settings)
        await confirmations.confirm(draft_confirmation.id, admin_user.id)
        await confirmations.confirm(candidate_confirmation.id, admin_user.id)
        await session.commit()

        draft = await session.scalar(select(Product).where(Product.title == "Confirmed draft"))
        candidate = await session.scalar(
            select(SelectionCandidate).where(
                SelectionCandidate.product_external_id == source.external_id
            )
        )
        assert draft is not None
        assert draft.status == "draft"
        assert candidate is not None
        listed_candidates = await operations.list_candidates(admin_user.id)
        assert listed_candidates == [
            {
                "product_id": source.external_id,
                "title": source.title,
                "site": {
                    "Singapore": "sg",
                    "Malaysia": "my",
                    "Philippines": "ph",
                    "Thailand": "th",
                    "Vietnam": "vn",
                    "Indonesia": "id",
                }[source.site],
                "source_type": source.source_type,
                "is_mock_data": True,
                "created_at": candidate.created_at,
            }
        ]
