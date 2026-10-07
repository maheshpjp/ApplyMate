from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database.database import get_db
from app.models.application import Application
from app.models.job import Job
from app.schemas.job import JobApplicationRead
from app.services.browser_automation import BrowserAutomationService

router = APIRouter(prefix="/applications", tags=["applications"])


def get_browser_service(request: Request) -> BrowserAutomationService:
    if not hasattr(request.app.state, "browser_service"):
        request.app.state.browser_service = BrowserAutomationService()
    return request.app.state.browser_service


@router.get("", response_model=list[JobApplicationRead])
async def list_applications(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[Application]:
    result = await db.execute(
        select(Application)
        .where(Application.user_id == user_id)
        .order_by(Application.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{application_id}", response_model=JobApplicationRead)
async def get_application(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Application:
    application = await db.get(Application, application_id)
    if not application or application.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


@router.post("/{application_id}/submit", status_code=status.HTTP_403_FORBIDDEN)
async def submit_application(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    application = await db.get(Application, application_id)
    if not application or application.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Application submission requires explicit human review and approval.",
    )


@router.post("/{application_id}/inspect", response_model=dict[str, str])
async def inspect_application_job(
    application_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    application = await db.get(Application, application_id)
    if not application or application.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    job = await db.get(Job, application.job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    detail = await get_browser_service(request).inspect(job.job_url, company_name=job.company_name)
    return {
        "job_title": detail.job_title,
        "company_name": detail.company_name,
        "description": detail.description,
        "requirements": detail.requirements,
        "source_url": detail.source_url,
        "extracted_at": detail.extracted_at,
    }
