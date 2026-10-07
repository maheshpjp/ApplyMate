from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database.database import get_db
from app.models.resume import Resume
from app.models.scheduled_application import ScheduledApplication
from app.schemas.schedule import ScheduleCreate, ScheduleRead

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleRead])
async def list_schedules(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[ScheduledApplication]:
    result = await db.execute(
        select(ScheduledApplication)
        .where(ScheduledApplication.user_id == user_id)
        .order_by(ScheduledApplication.scheduled_at)
    )
    return list(result.scalars().all())


@router.post("", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: ScheduleCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ScheduledApplication:
    if payload.scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Choose a future date and time")

    resume = await db.get(Resume, payload.resume_id)
    if resume is None or resume.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    schedule = ScheduledApplication(
        user_id=user_id,
        company_name=payload.company_name,
        role_title=payload.role_title,
        careers_url=str(payload.careers_url),
        scheduled_at=payload.scheduled_at.astimezone(timezone.utc),
        resume_id=resume.id,
        auto_submit_authorized=payload.auto_submit_authorized,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_schedule(
    schedule_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    schedule = await db.get(ScheduledApplication, schedule_id)
    if schedule is None or schedule.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled application not found")
    await db.delete(schedule)
    await db.commit()