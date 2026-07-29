from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.services.confirmation import ConfirmationService
from sellpilot.tools.commerce import register_commerce_read_tools
from sellpilot.tools.content_generation import register_content_generation_tools
from sellpilot.tools.executor import TOOL_CONFIRMATION_OPERATION, ToolExecutor
from sellpilot.tools.product_improvement import register_product_improvement_tools
from sellpilot.tools.registry import ToolRegistry
from sellpilot.tools.review_analysis import register_review_analysis_tools
from sellpilot.tools.selection import register_selection_tools
from sellpilot.tools.system import build_system_health_tool


def build_tool_registry(settings: Settings) -> ToolRegistry:
    registry = ToolRegistry(settings)
    registry.register(build_system_health_tool(settings))
    register_commerce_read_tools(registry)
    register_selection_tools(registry)
    register_review_analysis_tools(registry)
    register_product_improvement_tools(registry)
    register_content_generation_tools(registry)
    return registry


def build_tool_executor(
    registry: ToolRegistry,
    session: AsyncSession,
    settings: Settings,
) -> ToolExecutor:
    return ToolExecutor(registry, session, settings)


def build_confirmation_service(
    registry: ToolRegistry,
    session: AsyncSession,
    settings: Settings,
) -> ConfirmationService:
    service = ConfirmationService(session)
    executor = build_tool_executor(registry, session, settings)
    service.register_executor(TOOL_CONFIRMATION_OPERATION, executor.execute_confirmation)
    return service
