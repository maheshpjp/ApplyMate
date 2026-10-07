from __future__ import annotations

import asyncio
import json
import logging
import smtplib
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.database import AsyncSessionLocal
from app.models.application import Application
from app.models.job import Job
from app.models.resume import Resume
from app.models.scheduled_application import ScheduledApplication
from app.models.user import User
from app.services.adobe_application import ApplicationAutomationService
from app.services.job_discovery import JobDiscoveryService
from app.services.notifications import EmailNotificationService

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self._lock = asyncio.Lock()
        self._running = False
        self.last_run_at: datetime | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        async with self._lock:
            if self.is_running:
                return

            self.scheduler.add_job(
                self.run,
                trigger=IntervalTrigger(seconds=settings.job_check_interval_seconds),
                id="applymate-monitoring-job",
                name="ApplyMate job monitoring",
                replace_existing=True,
            )
            self.scheduler.start()
            self._running = True

    async def stop(self) -> None:
        async with self._lock:
            if not self.is_running:
                return

            self.scheduler.shutdown(wait=False)
            self._running = False

    async def run(
        self,
        db: AsyncSession | None = None,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        if db is None:
            async with AsyncSessionLocal() as db:
                return await self._run(db, user_id=user_id)

        return await self._run(db, user_id=user_id)

    async def _run(self, db: AsyncSession, *, user_id: str | None = None) -> dict[str, Any]:
        jobs_query = select(Job).where(Job.user_id.is_not(None))
        schedules_query = select(ScheduledApplication).where(
            ScheduledApplication.status == "scheduled",
            ScheduledApplication.scheduled_at <= datetime.now(timezone.utc),
        )
        if user_id is not None:
            jobs_query = jobs_query.where(Job.user_id == user_id)
            schedules_query = schedules_query.where(ScheduledApplication.user_id == user_id)

        result = await db.execute(jobs_query)
        jobs = list(result.scalars().all())

        for job in jobs:
            job.last_run_at = datetime.now(timezone.utc)
            job.status = "monitoring"

        await db.commit()

        schedules_result = await db.execute(schedules_query)
        due_schedules = list(schedules_result.scalars().all())
        await self._process_due_schedules(db, due_schedules)

        self.last_run_at = datetime.now(timezone.utc)
        return {
            "status": "completed",
            "jobs_processed": len(jobs),
            "scheduled_applications_processed": len(due_schedules),
        }

    async def _process_due_schedules(
        self,
        db: AsyncSession,
        schedules: list[ScheduledApplication],
    ) -> None:
        discovery = JobDiscoveryService()
        for schedule in schedules:
            schedule.status = "checking"
            await db.commit()
            try:
                discovered_jobs = await discovery.discover_url(schedule.careers_url)
            except Exception as exc:
                await self._mark_needs_attention(
                    db,
                    schedule,
                    f"Could not check careers page: {exc}",
                )
                continue

            target_title = " ".join(schedule.role_title.casefold().split())
            match = next(
                (
                    job for job in discovered_jobs
                    if target_title in " ".join(job.title.casefold().split())
                    or " ".join(job.title.casefold().split()) in target_title
                ),
                None,
            )
            if match is None:
                await self._mark_needs_attention(
                    db,
                    schedule,
                    "No matching role was found. Check the careers page or schedule another check.",
                )
                continue

            job = await db.scalar(
                select(Job).where(Job.user_id == schedule.user_id, Job.job_url == match.url)
            )
            if job is None:
                job = Job(
                    user_id=schedule.user_id,
                    company_name=schedule.company_name,
                    job_title=match.title,
                    job_url=match.url,
                    source="scheduled-careers-check",
                )
                db.add(job)
                await db.flush()

            application = await db.scalar(
                select(Application).where(
                    Application.user_id == schedule.user_id,
                    Application.job_id == job.id,
                    Application.resume_id == schedule.resume_id,
                )
            )
            if application is None:
                application = Application(
                    user_id=schedule.user_id,
                    job_id=job.id,
                    resume_id=schedule.resume_id,
                    status="draft",
                    notes="Created from a scheduled careers-page check. Review before applying.",
                )
                db.add(application)

            schedule.matched_job_id = job.id
            if schedule.auto_submit_authorized:
                resume = await db.get(Resume, schedule.resume_id)
                user = await db.get(User, schedule.user_id)
                try:
                    profile = json.loads(resume.metadata_json or "{}") if resume else {}
                except json.JSONDecodeError:
                    profile = {}
                if user:
                    profile.setdefault("name", user.name)
                    profile.setdefault("email", user.email)

                try:
                    resume_text = await self._resume_text(resume) if resume else ""
                except Exception:
                    logger.exception(
                        "Could not read resume for scheduled application",
                        extra={"schedule_id": schedule.id, "user_id": schedule.user_id},
                    )
                    await self._mark_needs_attention(
                        db,
                        schedule,
                        "The selected resume could not be read. Upload a readable PDF or DOCX and review this application.",
                    )
                    continue

                submission = await ApplicationAutomationService().submit(
                    job.job_url,
                    resume_path=resume.storage_path if resume else "",
                    profile=profile,
                    resume_text=resume_text,
                    auto_submit_authorized=schedule.auto_submit_authorized,
                )
                if submission.submitted:
                    schedule.status = "submitted"
                    schedule.result_message = submission.message
                    application.status = "submitted"
                    application.submitted_at = datetime.now(timezone.utc)
                    await db.commit()
                else:
                    await self._mark_needs_attention(db, schedule, submission.message)
            else:
                schedule.status = "application_ready"
                schedule.result_message = "Matching role found. A draft using the selected resume is ready for review."
                await db.commit()

    @staticmethod
    async def _mark_needs_attention(
        db: AsyncSession,
        schedule: ScheduledApplication,
        message: str,
    ) -> None:
        schedule.status = "needs_attention"
        schedule.result_message = message
        await db.commit()

        user = await db.get(User, schedule.user_id)
        if user is None:
            logger.error(
                "Could not notify about a scheduled application because its user is missing",
                extra={"schedule_id": schedule.id, "user_id": schedule.user_id},
            )
            return

        try:
            sent = await EmailNotificationService().notify_schedule_needs_attention(schedule, user)
        except (OSError, ValueError, smtplib.SMTPException):
            logger.exception(
                "Could not send scheduled application attention email",
                extra={"schedule_id": schedule.id, "user_id": schedule.user_id},
            )
            schedule.result_message = (
                f"{message} Email notification could not be sent; review this schedule in ApplyMate."
            )
            await db.commit()
            return

        if not sent:
            schedule.result_message = (
                f"{message} Email notification is not configured; review this schedule in ApplyMate."
            )
            await db.commit()

    @staticmethod
    async def _resume_text(resume: Resume) -> str:
        from app.services.resume_parser.factory import ResumeParserFactory

        parser = ResumeParserFactory.create(resume.content_type)
        text, _ = parser.parse(resume.storage_path)
        return text
