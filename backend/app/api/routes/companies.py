from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database.database import get_db
from app.models.job import Job
from app.schemas.job import JobDiscoveryResponse
from app.services.job_discovery import JobDiscoveryService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("/discover-careers", response_model=JobDiscoveryResponse, status_code=status.HTTP_201_CREATED)
async def discover_careers(
    company_url: Annotated[str, Query(min_length=1, max_length=2048)],
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> JobDiscoveryResponse:
    parsed = urlparse(company_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Company URL must be an absolute HTTP or HTTPS URL")

    service = JobDiscoveryService()
    try:
        jobs = await service.discover_url(company_url)
    except Exception as exc:
        reason = str(exc).strip() or "The browser-based careers-page check failed without returning details."
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not check the company careers page. {reason}",
        ) from exc

    if not jobs:
        return JobDiscoveryResponse(
            company_url=company_url,
            company_name=parsed.netloc,
            discovered_jobs=0,
            created_jobs=0,
            jobs=[],
            message=(
                "No job listings were detected on this page or its linked search pages. "
                "Try the company's direct job-search/results URL; some career portals "
                "may require a location/search selection or may not expose public listings."
            ),
        )

    company_name = parsed.netloc.replace("www.", "").split(":")[0].title()
    created_jobs: list[Job] = []

    for discovered_job in jobs:
        existing = await db.scalar(select(Job).where(Job.user_id == user_id, Job.job_url == discovered_job.url))
        if existing is not None:
            continue

        job = Job(
            user_id=user_id,
            company_name=company_name,
            job_title=discovered_job.title,
            job_url=discovered_job.url,
            source="company-careers",
        )
        db.add(job)
        created_jobs.append(job)

    await db.commit()

    for job in created_jobs:
        await db.refresh(job)

    return JobDiscoveryResponse(
        company_url=company_url,
        company_name=company_name,
        discovered_jobs=len(jobs),
        created_jobs=len(created_jobs),
        jobs=[
            {
                "job_title": job.job_title,
                "job_url": job.job_url,
                "company_name": job.company_name,
                "source": job.source,
            }
            for job in created_jobs
        ],
    )
