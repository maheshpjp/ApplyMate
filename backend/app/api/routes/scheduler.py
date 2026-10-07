from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database.database import get_db
from app.services.scheduler import SchedulerService

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def get_scheduler_service(request: Request) -> SchedulerService:
    if not hasattr(request.app.state, "scheduler"):
        request.app.state.scheduler = SchedulerService()
    return request.app.state.scheduler


@router.get("/health")
async def scheduler_health(request: Request) -> dict[str, str]:
    scheduler_service = get_scheduler_service(request)
    return {"status": "running" if scheduler_service.is_running else "stopped"}


@router.post("/run")
async def trigger_run(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    scheduler_service: SchedulerService = get_scheduler_service(request)
    result = await scheduler_service.run(db, user_id=user_id)
    return {
        "status": str(result["status"]),
        "jobs_processed": int(result["jobs_processed"]),
        "scheduled_applications_processed": int(result["scheduled_applications_processed"]),
    }
