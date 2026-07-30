import hashlib
import json
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.adapters.factory import create_platform_adapter
from sellpilot.core.config import Settings
from sellpilot.core.enums import OperationStatus, ToolRiskLevel
from sellpilot.core.exceptions import IdempotencyConflictError, ResourceNotFoundError
from sellpilot.db.models.commerce import InventoryRecord, Product, SelectionCandidate, Sku
from sellpilot.db.models.confirmation_task import ConfirmationTask
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.repositories.operation_log import OperationLogRepository
from sellpilot.services.confirmation import ConfirmationService
from sellpilot.services.task import TaskService

PUBLISH = "commerce.publish_product"
UNPUBLISH = "commerce.unpublish_product"
UPDATE_PRICE = "commerce.update_price"
UPDATE_INVENTORY = "commerce.update_inventory"
SAVE_PRODUCT_DRAFT = "commerce.save_product_draft"
IMPORT_PRODUCTS = "commerce.import_products"
ADD_CANDIDATE = "commerce.add_selection_candidate"
REMOVE_CANDIDATE = "commerce.remove_selection_candidate"
CANDIDATE_SITE_CODES = {
    "Singapore": "sg",
    "Malaysia": "my",
    "Philippines": "ph",
    "Thailand": "th",
    "Vietnam": "vn",
    "Indonesia": "id",
}


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

    async def request_product_draft(
        self,
        *,
        product: dict[str, Any],
        idempotency_key: str,
        created_by: UUID,
    ) -> ConfirmationTask:
        product_id = product.get("product_id")
        before = await self.adapter.get_product(product_id) if product_id else {}
        return await self._create_confirmation(
            operation=SAVE_PRODUCT_DRAFT,
            target_type="product",
            target_id=product_id or f"new:{idempotency_key}",
            before=before,
            after=product,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )

    async def request_product_import(
        self,
        *,
        products: list[dict[str, Any]],
        idempotency_key: str,
        created_by: UUID,
    ) -> ConfirmationTask:
        # 手工导入属于业务写操作：此处只保存待确认快照，不立即写入商品表。
        return await self._create_confirmation(
            operation=IMPORT_PRODUCTS,
            target_type="product_import",
            target_id=f"batch:{idempotency_key}",
            before={"count": 0},
            after={"products": products},
            idempotency_key=idempotency_key,
            created_by=created_by,
        )

    async def request_candidate_change(
        self,
        *,
        product_id: str,
        add: bool,
        title: str,
        source_type: str,
        is_mock_data: bool,
        idempotency_key: str,
        created_by: UUID,
    ) -> ConfirmationTask:
        # 候选清单只保存稳定商品业务 ID 和必要快照，不复制整份商品实体。
        existing = await self.session.scalar(
            select(SelectionCandidate).where(
                SelectionCandidate.created_by == created_by,
                SelectionCandidate.product_external_id == product_id,
            )
        )
        operation = ADD_CANDIDATE if add else REMOVE_CANDIDATE
        return await self._create_confirmation(
            operation=operation,
            target_type="selection_candidate",
            target_id=product_id,
            before={"selected": existing is not None},
            after={
                "selected": add,
                "title": title,
                "source_type": source_type,
                "is_mock_data": is_mock_data,
            },
            idempotency_key=idempotency_key,
            created_by=created_by,
        )

    async def list_candidates(self, created_by: UUID) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                select(SelectionCandidate, Product.site)
                .outerjoin(Product, Product.external_id == SelectionCandidate.product_external_id)
                .where(SelectionCandidate.created_by == created_by)
                .order_by(SelectionCandidate.created_at.desc())
            )
        ).all()
        return [
            {
                "product_id": item.product_external_id,
                "title": item.title_snapshot,
                "site": CANDIDATE_SITE_CODES.get(site) if site else None,
                "source_type": item.source_type,
                "is_mock_data": item.is_mock_data,
                "created_at": item.created_at,
            }
            for item, site in rows
        ]

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
        confirmations.register_executor(SAVE_PRODUCT_DRAFT, self._execute)
        confirmations.register_executor(IMPORT_PRODUCTS, self._execute)
        confirmations.register_executor(ADD_CANDIDATE, self._execute)
        confirmations.register_executor(REMOVE_CANDIDATE, self._execute)

    async def _execute(self, confirmation: ConfirmationTask) -> dict[str, Any]:
        """仅在确认成功后执行平台写操作，并保存任务结果与操作日志。"""
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
            elif confirmation.operation_type == UPDATE_INVENTORY:
                result = await self.adapter.update_inventory(str(product_id), payload)
            elif confirmation.operation_type == SAVE_PRODUCT_DRAFT:
                result = (
                    await self.adapter.update_product(str(product_id), payload)
                    if payload.get("product_id")
                    else await self.adapter.create_product(payload)
                )
            elif confirmation.operation_type == IMPORT_PRODUCTS:
                imported = []
                for product in payload.get("products", []):
                    # 手工确认导入按稳定 product_id 更新；不存在时才创建。
                    # 这不同于初始化数据包导入的“已有记录直接跳过”策略。
                    existing = (
                        await self.adapter.get_product(str(product["product_id"]))
                        if product.get("product_id")
                        else {}
                    )
                    imported.append(
                        await self.adapter.update_product(str(product["product_id"]), product)
                        if existing
                        else await self.adapter.create_product(product)
                    )
                result = {"imported_count": len(imported), "products": imported}
            elif confirmation.operation_type == ADD_CANDIDATE:
                existing = await self.session.scalar(
                    select(SelectionCandidate).where(
                        SelectionCandidate.created_by == confirmation.created_by,
                        SelectionCandidate.product_external_id == confirmation.target_id,
                    )
                )
                if existing is None:
                    self.session.add(
                        SelectionCandidate(
                            created_by=confirmation.created_by,
                            product_external_id=confirmation.target_id,
                            source_type=payload["source_type"],
                            title_snapshot=payload["title"],
                            is_mock_data=payload["is_mock_data"],
                        )
                    )
                await self.session.flush()
                result = {"product_id": confirmation.target_id, "selected": True}
            else:
                await self.session.execute(
                    delete(SelectionCandidate).where(
                        SelectionCandidate.created_by == confirmation.created_by,
                        SelectionCandidate.product_external_id == confirmation.target_id,
                    )
                )
                result = {"product_id": confirmation.target_id, "selected": False}
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
