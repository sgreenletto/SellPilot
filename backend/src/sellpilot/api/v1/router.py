from fastapi import APIRouter

from sellpilot.api.v1.endpoints import auth, commerce, confirmations, health, platform, tasks

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(platform.router, prefix="/platform", tags=["platform"])
router.include_router(commerce.router, prefix="/commerce", tags=["commerce"])
router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
router.include_router(confirmations.router, prefix="/confirmations", tags=["confirmations"])
