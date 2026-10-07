from datetime import datetime

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.job import Job
from app.models.user import User
from app.services.scheduler import SchedulerService


@pytest.mark.asyncio
async def test_scheduler_service_runs_user_jobs(db_session) -> None:
    user = User(
        email="scheduler@example.com",
        name="Scheduler User",
        hashed_password=hash_password("secret123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    job = Job(
        user_id=user.id,
        company_name="Example",
        job_title="Engineer",
        job_url="https://example.com/jobs/engineer",
        source="company-careers",
        status="monitoring",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    service = SchedulerService()
    await service.run(db_session)

    updated_job = await db_session.scalar(select(Job).where(Job.id == job.id))
    assert updated_job is not None
    assert updated_job.last_run_at is not None
    assert updated_job.status == "monitoring"
    assert service.last_run_at is not None


@pytest.mark.asyncio
async def test_scheduler_service_is_idempotent(db_session) -> None:
    service = SchedulerService()
    await service.start()
    await service.start()
    assert service.is_running is True
    assert len(service.scheduler.get_jobs()) == 1

    await service.stop()
    assert service.is_running is False
