from fastapi import APIRouter

from sellpilot.api.v1.endpoints import (
    ai_management,
    assistant,
    auth,
    commerce,
    confirmations,
    content_generation,
    health,
    knowledge_base,
    platform,
    product_improvement,
    product_translation,
    review_analysis,
    selection,
    tasks,
    tool_calls,
    tools,
)

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
router.include_router(ai_management.router, prefix="/ai-management", tags=["ai-management"])
router.include_router(knowledge_base.router, prefix="/knowledge", tags=["knowledge"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(platform.router, prefix="/platform", tags=["platform"])
router.include_router(commerce.router, prefix="/commerce", tags=["commerce"])
router.include_router(
    content_generation.router,
    prefix="/content-generation",
    tags=["content-generation"],
)
router.include_router(
    product_translation.router,
    prefix="/product-translations",
    tags=["product-translations"],
)
router.include_router(selection.router, prefix="/selection", tags=["selection"])
router.include_router(
    product_improvement.router,
    prefix="/product-improvement",
    tags=["product-improvement"],
)
router.include_router(
    review_analysis.router,
    prefix="/review-analysis",
    tags=["review-analysis"],
)
router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
router.include_router(confirmations.router, prefix="/confirmations", tags=["confirmations"])
router.include_router(tools.router, prefix="/tools", tags=["tools"])
router.include_router(tool_calls.router, prefix="/tool-calls", tags=["tool-calls"])
