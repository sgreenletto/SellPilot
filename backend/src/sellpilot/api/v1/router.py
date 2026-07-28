from fastapi import APIRouter

from sellpilot.api.v1.endpoints import (
    auth,
    commerce,
    confirmations,
    content_generation,
    health,
    platform,
    product_improvement,
    review_analysis,
    selection,
    tasks,
    tool_calls,
    tools,
)

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(platform.router, prefix="/platform", tags=["platform"])
router.include_router(commerce.router, prefix="/commerce", tags=["commerce"])
router.include_router(
    content_generation.router,
    prefix="/content-generation",
    tags=["content-generation"],
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
