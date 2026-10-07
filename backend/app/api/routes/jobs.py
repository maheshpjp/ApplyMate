from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database.database import get_db
from app.models.application import Application
from app.models.job import Job
from app.models.resume import Resume
from app.schemas.job import JobApplicationCreate, JobApplicationRead, JobCreate, JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
async def list_jobs(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[JobRead]:
    result = await db.execute(
        select(
            Job,
            func.count(Application.id).label("app_count"),
        )
        .outerjoin(Application, Application.job_id == Job.id)
        .where(Job.user_id == user_id)
        .group_by(Job.id)
        .order_by(Job.created_at.desc())
    )
    jobs: list[JobRead] = []
    for job, app_count in result.all():
        jobs.append(
            JobRead(
                id=job.id,
                user_id=job.user_id,
                company_name=job.company_name,
                job_title=job.job_title,
                job_url=job.job_url,
                source=job.source,
                status=job.status,
                match_score=job.match_score,
                last_run_at=job.last_run_at,
                created_at=job.created_at,
                updated_at=job.updated_at,
                app_count=int(app_count),
            )
        )
    return jobs


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    job = Job(
        user_id=user_id,
        company_name=payload.company_name,
        job_title=payload.job_title,
        job_url=payload.job_url,
        source=payload.source,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    return JobRead(
        id=job.id,
        user_id=job.user_id,
        company_name=job.company_name,
        job_title=job.job_title,
        job_url=job.job_url,
        source=job.source,
        status=job.status,
        match_score=job.match_score,
        last_run_at=job.last_run_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
        app_count=0,
    )


@router.post("/{job_id}/applications", response_model=JobApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application(
    job_id: str,
    payload: JobApplicationCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> JobApplicationRead:
    job = await db.get(Job, job_id)
    if job is None or job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    resume = await db.get(Resume, payload.resume_id)
    if resume is None or resume.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    application = Application(
        user_id=user_id,
        job_id=job.id,
        resume_id=resume.id,
        cover_letter=payload.cover_letter,
        notes=payload.notes,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    return JobApplicationRead(
        id=application.id,
        user_id=application.user_id,
        job_id=application.job_id,
        resume_id=application.resume_id,
        status=application.status,
        cover_letter=application.cover_letter,
        notes=application.notes,
        submitted_at=application.submitted_at,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )
