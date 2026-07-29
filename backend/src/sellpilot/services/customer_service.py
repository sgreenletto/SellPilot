from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.adapters.factory import create_platform_adapter
from sellpilot.core.config import Settings
from sellpilot.core.exceptions import ResourceNotFoundError
from sellpilot.db.models.commerce import CustomerSession, Order, Product

HIGH_RISK_MARKERS = (
    "退款",
    "投诉",
    "赔付",
    "地址修改",
    "修改地址",
    "订单修改",
    "修改订单",
    "refund",
    "complaint",
    "compensation",
    "change address",
    "modify order",
)
LOGISTICS_MARKERS = ("物流", "快递", "运输", "tracking", "shipment", "delivery")
ORDER_MARKERS = ("订单", "order")
POLICY_MARKERS = ("退货", "政策", "规则", "return policy", "policy")
PRODUCT_MARKERS = ("商品", "产品", "规格", "尺寸", "product", "size")


class CustomerServiceService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.adapter = create_platform_adapter(settings, session)

    async def get_context(self, session_id: str) -> dict[str, Any]:
        row = (
            await self.session.execute(
                select(CustomerSession, Order.external_id, Product.external_id)
                .outerjoin(Order, CustomerSession.order_id == Order.id)
                .outerjoin(Product, CustomerSession.product_id == Product.id)
                .where(CustomerSession.external_id == session_id)
            )
        ).first()
        if row is None:
            raise ResourceNotFoundError("Customer session not found")
        session, order_id, product_id = row
        messages = await self.adapter.list_messages(session_id=session.external_id, limit=100)
        return {
            "session_id": session.external_id,
            "language": session.language,
            "declared_intent": session.intent,
            "declared_risk_level": session.risk_level,
            "status": session.status,
            "order_id": order_id,
            "product_id": product_id,
            "messages": messages,
            "is_mock_data": session.is_mock_data,
        }

    @staticmethod
    def classify(context: dict[str, Any], buyer_message: str | None = None) -> dict[str, Any]:
        messages = context.get("messages")
        message_rows = messages if isinstance(messages, list) else []
        buyer_messages = [
            str(item.get("content") or "")
            for item in message_rows
            if isinstance(item, dict) and item.get("sender_type") == "buyer"
        ]
        text = " ".join(
            [
                str(context.get("declared_intent") or ""),
                *buyer_messages[-3:],
                buyer_message or "",
            ]
        ).casefold()
        declared_risk = str(context.get("declared_risk_level") or "").casefold()
        high_risk = declared_risk == "high" or any(marker in text for marker in HIGH_RISK_MARKERS)
        if high_risk:
            branch = "human"
            reason = "请求涉及退款、投诉、赔付或订单关键信息修改"
        elif any(marker in text for marker in LOGISTICS_MARKERS) and context.get("order_id"):
            branch = "logistics"
            reason = "请求需要读取真实物流信息"
        elif any(marker in text for marker in ORDER_MARKERS) and context.get("order_id"):
            branch = "order"
            reason = "请求需要读取真实订单信息"
        elif any(marker in text for marker in POLICY_MARKERS):
            branch = "policy"
            reason = "请求需要引用店铺政策知识"
        elif context.get("product_id") or any(marker in text for marker in PRODUCT_MARKERS):
            branch = "product"
            reason = "请求需要引用商品事实"
        else:
            branch = "policy"
            reason = "普通咨询优先检索可靠知识来源"
        return {
            "branch": branch,
            "risk_level": "high" if high_risk else "read",
            "requires_human": high_risk,
            "reason": reason,
            "query": buyer_message or (buyer_messages[-1] if buyer_messages else text),
        }

    @staticmethod
    def draft(
        context: dict[str, Any],
        classification: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        branch = str(classification["branch"])
        requires_human = bool(classification.get("requires_human"))
        basis: list[dict[str, Any]] = []
        if branch == "human":
            reply = "该请求涉及高风险售后或订单修改，需要转交人工客服处理。"
        elif branch == "logistics":
            logistics = dict(evidence.get("logistics") or {})
            if not logistics:
                reply = "未查询到可靠物流信息，请转交人工客服核对。"
                requires_human = True
            else:
                reply = (
                    f"订单 {logistics.get('order_id')} 当前物流状态为 "
                    f"{logistics.get('status')}，最新位置为 "
                    f"{logistics.get('latest_location') or '暂无更新'}。"
                )
                basis.append({"type": "logistics", "order_id": logistics.get("order_id")})
        elif branch == "order":
            order = dict(evidence.get("order") or {})
            if not order:
                reply = "未查询到可靠订单信息，请转交人工客服核对。"
                requires_human = True
            else:
                reply = (
                    f"订单 {order.get('order_id')} 当前状态为 "
                    f"{order.get('order_status')}，支付状态为 {order.get('payment_status')}。"
                )
                basis.append({"type": "order", "order_id": order.get("order_id")})
        elif branch == "product":
            product = dict(evidence.get("product") or {})
            if not product:
                reply = "未查询到可靠商品信息，请转交人工客服核对。"
                requires_human = True
            else:
                reply = (
                    f"根据商品资料，{product.get('title')} 属于 "
                    f"{product.get('category_name')}，商品说明为：{product.get('description')}。"
                )
                basis.append({"type": "product", "product_id": product.get("product_id")})
        else:
            sources = evidence.get("sources")
            if evidence.get("no_reliable_source") or not sources:
                reply = "当前知识库中没有找到可靠依据，需要转交人工客服处理。"
                requires_human = True
            else:
                reply = str(evidence.get("answer"))
                basis.extend(
                    {
                        "type": "knowledge",
                        "document_id": item.get("document_id"),
                        "source": item.get("source_doc"),
                    }
                    for item in sources[:3]
                    if isinstance(item, dict)
                )
        return {
            "session_id": context["session_id"],
            "reply": reply,
            "branch": branch,
            "risk_level": "high" if requires_human else "read",
            "requires_human": requires_human,
            "can_simulate_send": not requires_human,
            "basis": basis,
            "is_mock_data": bool(context.get("is_mock_data", True)),
        }

    async def send_mock(self, session_id: str, content: str) -> dict[str, Any]:
        result = await self.adapter.send_message(
            {"session_id": session_id, "content": content, "sender_type": "assistant"}
        )
        if not result:
            raise ResourceNotFoundError("Customer session not found")
        return result
