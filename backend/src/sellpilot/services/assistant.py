from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from sellpilot.core.enums import ToolRiskLevel, WorkflowNodeType
from sellpilot.core.exceptions import ParameterError
from sellpilot.schemas.assistant import (
    AssistantAvailability,
    AssistantCapabilityResponse,
    AssistantIntent,
    AssistantPlanResponse,
    AssistantPlanStep,
    AssistantWorkflowReference,
)
from sellpilot.services.commerce_normalization import extract_category_external_id
from sellpilot.tools.registry import ToolRegistry
from sellpilot.workflows.registry import WorkflowRegistry

_RISK_ORDER = {
    ToolRiskLevel.READ: 0,
    ToolRiskLevel.WRITE: 1,
    ToolRiskLevel.HIGH_RISK: 2,
}
_UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)


class AssistantCapabilityDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capability_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=100)
    display_name: str = Field(min_length=1, max_length=100)
    intent: AssistantIntent
    workflow_name: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    workflow_version: str | None = Field(
        default=None,
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$",
    )
    required_parameters: tuple[str, ...] = ()
    optional_parameters: tuple[str, ...] = ()
    tool_names: tuple[str, ...] = ()
    availability: AssistantAvailability
    unavailable_reason: str | None = Field(default=None, max_length=500)
    example_message: str = Field(min_length=1, max_length=500)
    target_path: str = Field(pattern=r"^/[a-z0-9/_-]*$", max_length=200)

    @model_validator(mode="after")
    def validate_contract(self) -> AssistantCapabilityDefinition:
        if self.intent is AssistantIntent.UNKNOWN:
            raise ValueError("unknown is not a registrable capability")
        if (self.workflow_name is None) != (self.workflow_version is None):
            raise ValueError("workflow name and version must be declared together")
        if set(self.required_parameters) & set(self.optional_parameters):
            raise ValueError("required and optional parameters must not overlap")
        all_parameters = (*self.required_parameters, *self.optional_parameters)
        if len(all_parameters) != len(set(all_parameters)):
            raise ValueError("capability parameters must be unique")
        if len(self.tool_names) != len(set(self.tool_names)):
            raise ValueError("capability tools must be unique")
        if self.availability is AssistantAvailability.AVAILABLE and not self.workflow_name:
            raise ValueError("available capabilities require a registered workflow")
        if self.availability is not AssistantAvailability.AVAILABLE and not self.unavailable_reason:
            raise ValueError("non-available capabilities require an unavailable reason")
        return self


class AssistantCapabilityRegistry:
    """Assistant mappings over the existing workflow and tool registries."""

    def __init__(
        self,
        workflows: WorkflowRegistry,
        tools: ToolRegistry,
    ) -> None:
        self.workflows = workflows
        self.tools = tools
        self._definitions: dict[str, AssistantCapabilityDefinition] = {}

    def register(self, definition: AssistantCapabilityDefinition) -> None:
        if definition.capability_key in self._definitions:
            raise ParameterError(
                f"Assistant capability '{definition.capability_key}' is already registered"
            )
        if any(item.intent is definition.intent for item in self._definitions.values()):
            raise ParameterError(f"Assistant intent '{definition.intent}' is already mapped")
        self._validate_references(definition)
        self._definitions[definition.capability_key] = definition

    def validate_references(self) -> None:
        for definition in self._definitions.values():
            self._validate_references(definition)

    def get_by_intent(self, intent: AssistantIntent) -> AssistantCapabilityDefinition | None:
        return next(
            (item for item in self._definitions.values() if item.intent is intent),
            None,
        )

    def list(self) -> list[AssistantCapabilityDefinition]:
        return [self._definitions[key] for key in sorted(self._definitions)]

    def list_public(self) -> list[AssistantCapabilityResponse]:
        return [self.public_summary(definition) for definition in self.list()]

    def public_summary(
        self,
        definition: AssistantCapabilityDefinition,
    ) -> AssistantCapabilityResponse:
        risk_level = self.risk_level(definition.tool_names)
        return AssistantCapabilityResponse(
            capability_key=definition.capability_key,
            display_name=definition.display_name,
            intent=definition.intent,
            workflow_name=definition.workflow_name,
            workflow_version=definition.workflow_version,
            required_parameters=list(definition.required_parameters),
            optional_parameters=list(definition.optional_parameters),
            tool_names=list(definition.tool_names),
            risk_level=risk_level,
            requires_confirmation=risk_level is not ToolRiskLevel.READ,
            availability=definition.availability,
            unavailable_reason=definition.unavailable_reason,
            example_message=definition.example_message,
            target_path=definition.target_path,
        )

    def risk_level(self, tool_names: Iterable[str]) -> ToolRiskLevel:
        definitions = [self.tools.get(name) for name in tool_names]
        if not definitions:
            return ToolRiskLevel.READ
        return max(
            (definition.risk_level for definition in definitions),
            key=_RISK_ORDER.__getitem__,
        )

    def _validate_references(self, definition: AssistantCapabilityDefinition) -> None:
        for tool_name in definition.tool_names:
            if not self.tools.contains(tool_name):
                raise ParameterError(
                    f"Assistant capability '{definition.capability_key}' references "
                    f"unregistered tool '{tool_name}'"
                )
            self.tools.get(tool_name)
        if definition.workflow_name is None:
            return
        if not self.workflows.contains(definition.workflow_name):
            raise ParameterError(
                f"Assistant capability '{definition.capability_key}' references "
                f"unregistered workflow '{definition.workflow_name}'"
            )
        workflow = self.workflows.get(
            definition.workflow_name,
            required_version=definition.workflow_version,
        )
        workflow_tools = {
            node.tool_name
            for node in workflow.nodes
            if node.node_type is WorkflowNodeType.TOOL and node.tool_name is not None
        }
        missing_tools = workflow_tools - set(definition.tool_names)
        if missing_tools:
            missing = ", ".join(sorted(missing_tools))
            raise ParameterError(
                f"Assistant capability '{definition.capability_key}' omits workflow "
                f"tools: {missing}"
            )


class AssistantPlanService:
    def __init__(self, registry: AssistantCapabilityRegistry) -> None:
        self.registry = registry

    def plan(self, message: str) -> AssistantPlanResponse:
        normalized = unicodedata.normalize("NFKC", message).strip()
        intent = (
            AssistantIntent.UNKNOWN
            if self._contains_tool_injection(normalized)
            else self._detect_intent(normalized)
        )
        capability = self.registry.get_by_intent(intent)
        if capability is None:
            return self._unknown_plan()

        parameters = self._extract_parameters(intent, normalized)
        missing = [
            name
            for name in capability.required_parameters
            if name not in parameters or parameters[name] in ("", None, [])
        ]
        if (
            intent is AssistantIntent.PRODUCT_IMPROVEMENT
            and "product_id" not in parameters
            and "analysis_id" not in parameters
        ):
            missing = ["product_id"]
        selected_tools = self._select_tools(capability, parameters)
        risk_level = self.registry.risk_level(selected_tools)
        steps = self._build_steps(capability, selected_tools)
        workflow = (
            AssistantWorkflowReference(
                name=capability.workflow_name,
                version=capability.workflow_version or "",
            )
            if capability.workflow_name
            else None
        )
        available = capability.availability is AssistantAvailability.AVAILABLE
        return AssistantPlanResponse(
            detected_intent=intent,
            extracted_parameters=parameters,
            missing_parameters=missing,
            selected_capability=capability.capability_key,
            selected_workflow=workflow,
            tool_names=list(selected_tools),
            steps=steps,
            risk_summary=self._risk_summary(risk_level),
            requires_confirmation=risk_level is not ToolRiskLevel.READ,
            availability=capability.availability,
            unavailable_reason=capability.unavailable_reason,
            can_execute=available and not missing,
            target_path=capability.target_path,
            mock_notice=(
                "当前为 Mock 计划模式：仅生成确定性执行计划，不创建任务、不调用工具，"
                "也不会连接真实 Shopee。"
            ),
        )

    def _contains_tool_injection(self, message: str) -> bool:
        lowered = message.casefold()
        return any(
            definition.name.casefold() in lowered for definition in self.registry.tools.list()
        )

    @staticmethod
    def _detect_intent(message: str) -> AssistantIntent:
        lowered = message.casefold()
        rules = (
            (
                AssistantIntent.CUSTOMER_SERVICE_REPLY,
                ("客服回复", "回复买家", "回复客户", "customer service reply"),
            ),
            (
                AssistantIntent.KNOWLEDGE_QUERY,
                ("知识库", "知识检索", "rag", "faq", "knowledge"),
            ),
            (
                AssistantIntent.LOGISTICS_QUERY,
                ("物流", "快递", "tracking", "shipment", "logistics"),
            ),
            (
                AssistantIntent.INVENTORY_REPLENISHMENT,
                (
                    "库存补货",
                    "补货分析",
                    "补货建议",
                    "replenishment",
                ),
            ),
            (
                AssistantIntent.LOW_STOCK_CHECK,
                ("低库存", "库存不足", "缺货", "low stock"),
            ),
            (
                AssistantIntent.PRODUCT_IMPROVEMENT,
                ("产品改良", "商品改良", "改良建议", "product improvement"),
            ),
            (
                AssistantIntent.REVIEW_ANALYSIS,
                ("评论分析", "评价分析", "用户评论", "review analysis"),
            ),
            (
                AssistantIntent.SELECTION_ANALYSIS,
                ("智能选品", "选品分析", "选品机会", "商品机会", "selection analysis"),
            ),
            (
                AssistantIntent.CONTENT_GENERATION,
                ("内容生成", "生成文案", "商品文案", "listing content", "content generation"),
            ),
            (
                AssistantIntent.ORDER_QUERY,
                ("订单", "order"),
            ),
        )
        return next(
            (intent for intent, keywords in rules if any(word in lowered for word in keywords)),
            AssistantIntent.UNKNOWN,
        )

    def _extract_parameters(
        self,
        intent: AssistantIntent,
        message: str,
    ) -> dict[str, JsonValue]:
        parameters: dict[str, JsonValue] = {}
        product_id = self._first_match(
            r"\b(?:PRODUCT|PROD|SP)[-_]?(?=[A-Z0-9_-]*\d)[A-Z0-9][A-Z0-9_-]*\b",
            message,
        )
        order_id = self._first_match(r"\bORD[A-Z0-9_-]*\d[A-Z0-9_-]*\b", message)
        session_id = self._first_match(r"\bSES[A-Z0-9_-]*\d[A-Z0-9_-]*\b", message)
        shop_id = self._first_match(r"\bSHOP[A-Z0-9_-]*\d[A-Z0-9_-]*\b", message)
        uuid_match = _UUID_PATTERN.search(message)

        if intent is AssistantIntent.SELECTION_ANALYSIS:
            site = self._extract_site(message)
            if site:
                parameters["site"] = site
            category_id = extract_category_external_id(message)
            if category_id:
                parameters["category_id"] = category_id
        elif intent is AssistantIntent.REVIEW_ANALYSIS and product_id:
            parameters["product_id"] = product_id
        elif intent is AssistantIntent.PRODUCT_IMPROVEMENT:
            if product_id:
                parameters["product_id"] = product_id
            elif uuid_match:
                parameters["analysis_id"] = uuid_match.group(0).lower()
        elif intent is AssistantIntent.CONTENT_GENERATION:
            if product_id:
                parameters["product_id"] = product_id
            language = self._extract_language(message)
            if language:
                parameters["target_language"] = language
        elif intent is AssistantIntent.INVENTORY_REPLENISHMENT:
            if shop_id:
                parameters["shop_external_id"] = shop_id
        elif intent is AssistantIntent.LOW_STOCK_CHECK:
            if shop_id:
                parameters["shop_id"] = shop_id
        elif intent is AssistantIntent.ORDER_QUERY:
            if order_id:
                parameters["order_id"] = order_id
            if shop_id:
                parameters["shop_id"] = shop_id
            status = self._extract_order_status(message)
            if status:
                parameters["status"] = status
        elif intent is AssistantIntent.LOGISTICS_QUERY and order_id:
            parameters["order_id"] = order_id
        elif intent is AssistantIntent.KNOWLEDGE_QUERY:
            parameters["query"] = message
        elif intent is AssistantIntent.CUSTOMER_SERVICE_REPLY and session_id:
            parameters["session_id"] = session_id
            parameters["buyer_message"] = message
            if "模拟发送" in message or "mock send" in message.casefold():
                parameters["simulate_send"] = True
        return parameters

    @staticmethod
    def _first_match(pattern: str, message: str) -> str | None:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        return match.group(0).upper() if match else None

    @staticmethod
    def _extract_site(message: str) -> str | None:
        lowered = message.casefold()
        aliases = (
            ("新加坡", "sg"),
            ("singapore", "sg"),
            ("马来西亚", "my"),
            ("malaysia", "my"),
            ("菲律宾", "ph"),
            ("philippines", "ph"),
            ("泰国", "th"),
            ("thailand", "th"),
            ("越南", "vn"),
            ("vietnam", "vn"),
            ("印度尼西亚", "id"),
            ("indonesia", "id"),
            ("台湾", "tw"),
            ("taiwan", "tw"),
            ("巴西", "br"),
            ("brazil", "br"),
        )
        for alias, value in aliases:
            if alias in lowered:
                return value
        match = re.search(r"(?:站点|site)\s*[:=]?\s*(sg|my|ph|th|vn|id|tw|br)\b", lowered)
        return match.group(1) if match else None

    @staticmethod
    def _extract_language(message: str) -> str | None:
        lowered = message.casefold()
        aliases = (
            ("简体中文", "zh-CN"),
            ("英语", "en"),
            ("英文", "en"),
            ("english", "en"),
            ("马来语", "ms"),
            ("印尼语", "id"),
            ("泰语", "th"),
            ("越南语", "vi"),
            ("菲律宾语", "tl"),
            ("葡萄牙语", "pt-BR"),
            ("繁体中文", "zh-TW"),
        )
        return next((value for alias, value in aliases if alias in lowered), None)

    @staticmethod
    def _extract_order_status(message: str) -> str | None:
        lowered = message.casefold()
        aliases = (
            ("待支付", "pending"),
            ("已支付", "paid"),
            ("处理中", "processing"),
            ("已发货", "shipped"),
            ("已完成", "completed"),
            ("已取消", "cancelled"),
            ("已退款", "refunded"),
        )
        return next((value for alias, value in aliases if alias in lowered), None)

    @staticmethod
    def _select_tools(
        capability: AssistantCapabilityDefinition,
        parameters: dict[str, JsonValue],
    ) -> tuple[str, ...]:
        if capability.intent is AssistantIntent.ORDER_QUERY:
            return ("get_order",) if parameters.get("order_id") else ("list_orders",)
        if capability.intent is AssistantIntent.CUSTOMER_SERVICE_REPLY and not parameters.get(
            "simulate_send"
        ):
            return tuple(
                name for name in capability.tool_names if name != "mock_send_customer_reply"
            )
        return capability.tool_names

    def _build_steps(
        self,
        capability: AssistantCapabilityDefinition,
        selected_tools: tuple[str, ...],
    ) -> list[AssistantPlanStep]:
        if capability.workflow_name:
            workflow = self.registry.workflows.get(
                capability.workflow_name,
                required_version=capability.workflow_version,
            )
            return [
                AssistantPlanStep(
                    order=index,
                    kind="tool" if node.node_type is WorkflowNodeType.TOOL else "workflow",
                    name=node.tool_name or node.name,
                    summary=(
                        self.registry.tools.get(node.tool_name).description
                        if node.tool_name
                        else workflow.description
                    ),
                )
                for index, node in enumerate(workflow.nodes, start=1)
            ]
        if selected_tools:
            return [
                AssistantPlanStep(
                    order=index,
                    kind="tool",
                    name=tool_name,
                    summary=self.registry.tools.get(tool_name).description,
                )
                for index, tool_name in enumerate(selected_tools, start=1)
            ]
        return [
            AssistantPlanStep(
                order=1,
                kind="capability",
                name=capability.capability_key,
                summary=capability.unavailable_reason or "Capability contract is not executable.",
            )
        ]

    @staticmethod
    def _risk_summary(risk_level: ToolRiskLevel) -> str:
        if risk_level is ToolRiskLevel.READ:
            return "只读计划；当前阶段不会执行工具或修改业务数据。"
        return "该能力包含写入或高风险工具，实际执行前必须进入统一确认流程。"

    @staticmethod
    def _unknown_plan() -> AssistantPlanResponse:
        return AssistantPlanResponse(
            detected_intent=AssistantIntent.UNKNOWN,
            extracted_parameters={},
            missing_parameters=[],
            selected_capability=None,
            selected_workflow=None,
            tool_names=[],
            steps=[],
            risk_summary="未匹配受控能力，不会调用任何工具。",
            requires_confirmation=False,
            availability=AssistantAvailability.UNAVAILABLE,
            unavailable_reason="未识别到已冻结的 Assistant 能力，请改用常用任务入口。",
            can_execute=False,
            target_path=None,
            mock_notice=(
                "当前为 Mock 计划模式：仅生成确定性执行计划，不创建任务、不调用工具，"
                "也不会连接真实 Shopee。"
            ),
        )


def build_assistant_capability_registry(
    workflows: WorkflowRegistry,
    tools: ToolRegistry,
) -> AssistantCapabilityRegistry:
    registry = AssistantCapabilityRegistry(workflows, tools)
    definitions = (
        AssistantCapabilityDefinition(
            capability_key="selection_analysis",
            display_name="智能选品分析",
            intent=AssistantIntent.SELECTION_ANALYSIS,
            workflow_name="selection",
            workflow_version="1.0.0",
            required_parameters=("site",),
            optional_parameters=("category_id", "min_price", "max_price", "risk_preference"),
            tool_names=("search_market_products", "score_product_opportunity"),
            availability=AssistantAvailability.AVAILABLE,
            example_message="分析新加坡站的选品机会",
            target_path="/market/selection",
        ),
        AssistantCapabilityDefinition(
            capability_key="review_analysis",
            display_name="商品评论分析",
            intent=AssistantIntent.REVIEW_ANALYSIS,
            workflow_name="review_analysis",
            workflow_version="1.0.0",
            required_parameters=("product_id",),
            optional_parameters=("site", "languages", "min_rating", "max_rating"),
            tool_names=("analyze_product_reviews",),
            availability=AssistantAvailability.AVAILABLE,
            example_message="分析商品 PROD-001 的用户评论",
            target_path="/market/reviews",
        ),
        AssistantCapabilityDefinition(
            capability_key="product_improvement",
            display_name="产品改良建议",
            intent=AssistantIntent.PRODUCT_IMPROVEMENT,
            workflow_name="product_improvement",
            workflow_version="1.0.0",
            required_parameters=(),
            optional_parameters=("product_id", "analysis_id"),
            tool_names=("analyze_product_reviews", "generate_product_improvement_plan"),
            availability=AssistantAvailability.AVAILABLE,
            example_message="根据商品 PROD-001 的评论生成产品改良建议",
            target_path="/market/reviews/improvement",
        ),
        AssistantCapabilityDefinition(
            capability_key="content_generation",
            display_name="多语言内容生成",
            intent=AssistantIntent.CONTENT_GENERATION,
            workflow_name="content_generation",
            workflow_version="1.0.0",
            required_parameters=("product_id", "target_language"),
            optional_parameters=("site", "audience", "selling_points", "keywords"),
            tool_names=("generate_localized_listing", "check_listing_compliance"),
            availability=AssistantAvailability.AVAILABLE,
            example_message="为商品 PROD-001 生成英文商品文案",
            target_path="/products/content",
        ),
        AssistantCapabilityDefinition(
            capability_key="inventory_replenishment",
            display_name="库存补货建议",
            intent=AssistantIntent.INVENTORY_REPLENISHMENT,
            workflow_name="inventory_replenishment",
            workflow_version="1.0.0",
            required_parameters=("shop_external_id",),
            optional_parameters=(
                "analysis_days",
                "lead_time_days",
                "safety_factor",
                "only_replenishment",
            ),
            tool_names=("analyze_inventory_replenishment",),
            availability=AssistantAvailability.AVAILABLE,
            example_message="分析 SHOP001 的库存补货建议",
            target_path="/products/listing-inventory",
        ),
        AssistantCapabilityDefinition(
            capability_key="low_stock_check",
            display_name="低库存检查",
            intent=AssistantIntent.LOW_STOCK_CHECK,
            workflow_name="low_stock_check",
            workflow_version="1.0.0",
            optional_parameters=("shop_id", "limit"),
            tool_names=("list_low_stock",),
            availability=AssistantAvailability.AVAILABLE,
            example_message="检查当前店铺的低库存商品",
            target_path="/products/listing-inventory",
        ),
        AssistantCapabilityDefinition(
            capability_key="order_query",
            display_name="订单查询",
            intent=AssistantIntent.ORDER_QUERY,
            workflow_name="order_query",
            workflow_version="1.0.0",
            optional_parameters=("order_id", "status", "shop_id", "limit"),
            tool_names=("list_orders", "get_order"),
            availability=AssistantAvailability.AVAILABLE,
            example_message="查询已发货订单",
            target_path="/orders",
        ),
        AssistantCapabilityDefinition(
            capability_key="logistics_query",
            display_name="物流查询",
            intent=AssistantIntent.LOGISTICS_QUERY,
            workflow_name="logistics_query",
            workflow_version="1.0.0",
            required_parameters=("order_id",),
            tool_names=("get_order_logistics",),
            availability=AssistantAvailability.AVAILABLE,
            example_message="查询订单 ORD000001 的物流",
            target_path="/orders",
        ),
        AssistantCapabilityDefinition(
            capability_key="knowledge_query",
            display_name="知识库检索",
            intent=AssistantIntent.KNOWLEDGE_QUERY,
            workflow_name="knowledge_query",
            workflow_version="1.0.0",
            required_parameters=("query",),
            optional_parameters=("category", "top_k"),
            tool_names=("search_knowledge",),
            availability=AssistantAvailability.AVAILABLE,
            example_message="在知识库中检索退货政策",
            target_path="/customer-service/knowledge",
        ),
        AssistantCapabilityDefinition(
            capability_key="customer_service_reply",
            display_name="客服回复建议",
            intent=AssistantIntent.CUSTOMER_SERVICE_REPLY,
            workflow_name="customer_service_reply",
            workflow_version="1.0.0",
            required_parameters=("session_id",),
            optional_parameters=("buyer_message", "simulate_send"),
            tool_names=(
                "get_customer_conversation",
                "classify_customer_request",
                "search_knowledge",
                "get_order",
                "get_order_logistics",
                "get_product",
                "draft_customer_reply",
                "mock_send_customer_reply",
            ),
            availability=AssistantAvailability.AVAILABLE,
            example_message="为会话 SES00001 生成客服回复建议",
            target_path="/customer-service/conversations",
        ),
    )
    for definition in definitions:
        registry.register(definition)
    registry.validate_references()
    return registry
