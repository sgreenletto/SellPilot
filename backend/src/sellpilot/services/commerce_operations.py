import hashlib
import json
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.adapters.factory import create_platform_adapter
from sellpilot.core.config import Settings
from sellpilot.core.enums import OperationStatus, ToolRiskLevel
from sellpilot.core.exceptions import IdempotencyConflictError, ResourceNotFoundError
from sellpilot.db.models.commerce import InventoryRecord, Product, Sku
from sellpilot.db.models.confirmation_task import ConfirmationTask
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.repositories.operation_log import OperationLogRepository
from sellpilot.services.confirmation import ConfirmationService
from sellpilot.services.task import TaskService

PUBLISH = "commerce.publish_product"
UNPUBLISH = "commerce.unpublish_product"
UPDATE_PRICE = "commerce.update_price"
UPDATE_INVENTORY = "commerce.update_inventory"


class CommerceOperationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.adapter = create_platform_adapter(settings, session)
        self.tasks = TaskService(session)
        self.logs = OperationLogRepository(session)

    async def request_product_status(
        self,
        *,
        product_id: str,
        publish: bool,
        idempotency_key: str,
        created_by: UUID,
    ) -> ConfirmationTask:
        before = await self.adapter.get_product(product_id)
        if not before:
            raise ResourceNotFoundError("Product not found")
        after = {**before, "status": "active" if publish else "inactive"}
        operation = PUBLISH if publish else UNPUBLISH
        return await self._create_confirmation(
            operation=operation,
            target_type="product",
            target_id=product_id,
            before=before,
            after=after,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )

    async def request_price_update(
        self,
        *,
        product_id: str,
        sku_id: str,
        price: Any,
        idempotency_key: str,
        created_by: UUID,
    ) -> ConfirmationTask:
        sku = await self.session.scalar(
            select(Sku)
            .join(Product)
            .where(Product.external_id == product_id, Sku.external_id == sku_id)
        )
        if sku is None:
            raise ResourceNotFoundError("SKU not found")
        return await self._create_confirmation(
            operation=UPDATE_PRICE,
            target_type="sku",
            target_id=sku_id,
            before={"product_id": product_id, "sku_id": sku_id, "price": sku.price},
            after={"product_id": product_id, "sku_id": sku_id, "price": price},
            idempotency_key=idempotency_key,
            created_by=created_by,
        )

    async def request_inventory_update(
        self,
        *,
        product_id: str,
        sku_id: str,
        available_stock: int,
        idempotency_key: str,
        created_by: UUID,
    ) -> ConfirmationTask:
        inventory = await self.session.scalar(
            select(InventoryRecord)
            .join(Sku)
            .join(Product)
            .where(Product.external_id == product_id, Sku.external_id == sku_id)
        )
        if inventory is None:
            raise ResourceNotFoundError("Inventory record not found")
        return await self._create_confirmation(
            operation=UPDATE_INVENTORY,
            target_type="inventory",
            target_id=inventory.external_id,
            before={
                "product_id": product_id,
                "sku_id": sku_id,
                "available_stock": inventory.available_stock,
                "stock_status": inventory.stock_status,
            },
            after={
                "product_id": product_id,
                "sku_id": sku_id,
                "available_stock": available_stock,
            },
            idempotency_key=idempotency_key,
            created_by=created_by,
        )

    async def _create_confirmation(
        self,
        *,
        operation: str,
        target_type: str,
        target_id: str,
        before: dict[str, Any],
        after: dict[str, Any],
        idempotency_key: str,
        created_by: UUID,
    ) -> ConfirmationTask:
        confirmations = ConfirmationService(self.session)
        before_snapshot = jsonable_encoder(before)
        after_snapshot = jsonable_encoder(after)
        input_digest = self._operation_digest(before_snapshot, after_snapshot)
        idempotency_scope = confirmations.build_idempotency_scope(
            created_by=created_by,
            operation_type=operation,
            tool_name=None,
            tool_version=None,
            target_type=target_type,
            target_id=target_id,
            idempotency_key=idempotency_key,
        )
        existing = await confirmations.confirmations.get_by_idempotency_scope(idempotency_scope)
        if existing is not None:
            if existing.input_digest != input_digest:
                raise IdempotencyConflictError()
            return existing
        task = await self.tasks.create_internal_task(
            task_type=operation,
            user_input=f"Requested {operation} for {target_type}:{target_id}",
            created_by=created_by,
        )
        await self.tasks.start(task.id)
        await self.tasks.wait_for_confirmation(task.id)
        return await confirmations.create(
            agent_task_id=task.id,
            operation_type=operation,
            target_type=target_type,
            target_id=target_id,
            risk_level=ToolRiskLevel.HIGH_RISK,
            idempotency_key=idempotency_key,
            created_by=created_by,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            input_digest=input_digest,
            risk_warning=f"Confirm high-risk Mock commerce operation: {operation}",
        )

    @staticmethod
    def _operation_digest(
        before_snapshot: dict[str, Any],
        after_snapshot: dict[str, Any],
    ) -> str:
        canonical = json.dumps(
            {
                "before": before_snapshot,
                "after": after_snapshot,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def register_executors(self, confirmations: ConfirmationService) -> None:
        confirmations.register_executor(PUBLISH, self._execute)
        confirmations.register_executor(UNPUBLISH, self._execute)
        confirmations.register_executor(UPDATE_PRICE, self._execute)
        confirmations.register_executor(UPDATE_INVENTORY, self._execute)

    async def _execute(self, confirmation: ConfirmationTask) -> dict[str, Any]:
        payload = confirmation.after_snapshot or {}
        product_id = payload.get("product_id") or confirmation.target_id
        await self.tasks.start(confirmation.agent_task_id)
        try:
            if confirmation.operation_type == PUBLISH:
                result = await self.adapter.publish_product(str(product_id))
            elif confirmation.operation_type == UNPUBLISH:
                result = await self.adapter.unpublish_product(str(product_id))
            elif confirmation.operation_type == UPDATE_PRICE:
                result = await self.adapter.update_price(str(product_id), payload)
            else:
                result = await self.adapter.update_inventory(str(product_id), payload)
            if not result:
                raise ResourceNotFoundError("Commerce operation target not found")
            await self.tasks.complete(confirmation.agent_task_id, jsonable_encoder(result))
        except Exception as exc:
            await self.tasks.fail(
                confirmation.agent_task_id,
                "COMMERCE_OPERATION_FAILED",
                str(exc),
            )
            raise
        await self.logs.add(
            OperationLog(
                actor_id=confirmation.confirmed_by,
                action=confirmation.operation_type,
                target_type=confirmation.target_type,
                target_id=confirmation.target_id,
                request_id=confirmation.idempotency_key[:64],
                agent_task_id=confirmation.agent_task_id,
                confirmation_task_id=confirmation.id,
                before_snapshot=confirmation.before_snapshot,
                after_snapshot=jsonable_encoder(result),
                status=OperationStatus.SUCCEEDED,
            )
        )
        return jsonable_encoder(result)


def build_commerce_confirmation_service(
    session: AsyncSession, settings: Settings
) -> ConfirmationService:
    confirmations = ConfirmationService(session)
    CommerceOperationService(session, settings).register_executors(confirmations)
    return confirmations
