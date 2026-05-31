from fastapi import APIRouter

from api.dependencies import run_manager
from services.validation import (
    PlatformReadiness,
    SmokeRunResult,
    check_platform_readiness,
    run_backend_smoke_suite,
)

router = APIRouter(prefix="/api/validation", tags=["validation"])


@router.post("/e2e-smoke", response_model=SmokeRunResult)
async def run_e2e_smoke(force_feedback_demo: bool = False) -> SmokeRunResult:
    return await run_backend_smoke_suite(
        run_manager,
        force_feedback_demo=force_feedback_demo,
    )


@router.get("/platform-readiness", response_model=PlatformReadiness)
async def platform_readiness() -> PlatformReadiness:
    return await check_platform_readiness()
