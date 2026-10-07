from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.application import Application
from app.models.job import Job
from app.models.resume import Resume
from app.models.scheduled_application import ScheduledApplication
from app.models.user import User
from app.services.job_discovery import DiscoveredJob, JobDiscoveryService
from app.services.scheduler import SchedulerService
from app.services.adobe_application import ApplicationAutomationService, SubmissionResult


def test_form_field_mapping_uses_resume_values_and_leaves_unknowns_unanswered() -> None:
    profile = {
        "name": "Jamie Student",
        "email": "jamie@example.com",
        "phone": "+1 555 010 1111",
        "location": "Seattle, WA",
    }

    assert ApplicationAutomationService.value_for_field("Given Name", profile) == "Jamie"
    assert ApplicationAutomationService.value_for_field("Email Address", profile) == "jamie@example.com"
    assert ApplicationAutomationService.value_for_field("City", profile) == "Seattle"
    assert ApplicationAutomationService.value_for_field("Country", profile) is None


@pytest.mark.asyncio
async def test_application_automation_refuses_without_schedule_authorization() -> None:
    result = await ApplicationAutomationService().submit(
        "https://careers.example.com/jobs/123",
        resume_path="missing.pdf",
        profile={},
        auto_submit_authorized=False,
    )

    assert result.submitted is False
    assert "not authorized" in result.message


@pytest.mark.asyncio
async def test_job_and_application_tracking(authenticated_client, db_session) -> None:
    user = await db_session.scalar(select(User).where(User.email == "test@example.com"))
    assert user is not None

    resume = Resume(
        user_id=user.id,
        name="Product Resume",
        file_name="resume.pdf",
        content_type="application/pdf",
        storage_path="/tmp/resume.pdf",
        metadata_json="{}",
    )
    db_session.add(resume)
    await db_session.commit()
    await db_session.refresh(resume)

    response = await authenticated_client.post(
        "/api/jobs",
        json={
            "company_name": "OpenAI",
            "job_title": "Product Manager",
            "job_url": "https://example.com/jobs/product-manager",
            "source": "company-careers",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["company_name"] == "OpenAI"
    assert payload["status"] == "monitoring"
    assert payload["user_id"] == user.id

    job_id = payload["id"]
    application_response = await authenticated_client.post(
        f"/api/jobs/{job_id}/applications",
        json={
            "resume_id": resume.id,
            "cover_letter": "I am excited to apply.",
            "notes": "Strong match",
        },
    )

    assert application_response.status_code == 201
    application = application_response.json()
    assert application["job_id"] == job_id
    assert application["status"] == "draft"
    assert application["user_id"] == user.id

    jobs_response = await authenticated_client.get("/api/jobs")
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 1
    assert jobs[0]["app_count"] == 1

    scheduler_response = await authenticated_client.post("/api/scheduler/run")
    assert scheduler_response.status_code == 200
    assert scheduler_response.json()["status"] == "completed"
    assert scheduler_response.json()["jobs_processed"] == 1

    stored_job = await db_session.get(Job, job_id)
    assert stored_job is not None
    assert stored_job.last_run_at is not None

    application_record = await db_session.scalar(select(Application).where(Application.job_id == job_id))
    assert application_record is not None
    assert application_record.status == "draft"


@pytest.mark.asyncio
async def test_scheduler_rejects_missing_resume_id(authenticated_client) -> None:
    job_response = await authenticated_client.post(
        "/api/jobs",
        json={
            "company_name": "Example",
            "job_title": "Engineer",
            "job_url": "https://example.com/jobs/engineer",
            "source": "company-careers",
        },
    )
    job_id = job_response.json()["id"]

    response = await authenticated_client.post(
        f"/api/jobs/{job_id}/applications",
        json={"cover_letter": "I am excited to apply."},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_scheduler_prepares_application_for_due_matching_role(db_session, monkeypatch) -> None:
    user = User(email="scheduled@example.com", name="Scheduled User", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()
    resume = Resume(
        user_id=user.id,
        name="Engineering Resume",
        file_name="engineering.pdf",
        content_type="application/pdf",
        storage_path="/tmp/engineering.pdf",
        metadata_json="{}",
    )
    db_session.add(resume)
    await db_session.flush()
    schedule = ScheduledApplication(
        user_id=user.id,
        company_name="Example Co",
        role_title="Software Engineer Intern",
        careers_url="https://example.com/careers",
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        resume_id=resume.id,
    )
    db_session.add(schedule)
    await db_session.commit()

    async def discover_url(self, url: str):
        return [DiscoveredJob(title="Software Engineer Intern", url="https://example.com/jobs/123")]

    monkeypatch.setattr(JobDiscoveryService, "discover_url", discover_url)
    result = await SchedulerService().run(db_session)

    assert result["scheduled_applications_processed"] == 1
    assert schedule.status == "application_ready"
    application = await db_session.scalar(select(Application).where(Application.job_id == schedule.matched_job_id))
    assert application is not None
    assert application.resume_id == resume.id
    assert application.status == "draft"


@pytest.mark.asyncio
async def test_scheduler_marks_authorized_submission_after_portal_confirmation(db_session, monkeypatch) -> None:
    user = User(email="autopilot@example.com", name="Jamie Student", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()
    resume = Resume(
        user_id=user.id,
        name="Selected Resume",
        file_name="selected.pdf",
        content_type="application/pdf",
        storage_path="/tmp/selected.pdf",
        metadata_json='{"name":"Jamie Student","email":"jamie@example.com"}',
    )
    db_session.add(resume)
    await db_session.flush()
    schedule = ScheduledApplication(
        user_id=user.id,
        company_name="Example Co",
        role_title="Backend Engineer",
        careers_url="https://careers.example.com/jobs",
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        resume_id=resume.id,
        auto_submit_authorized=True,
    )
    db_session.add(schedule)
    await db_session.commit()

    async def discover_url(self, url: str):
        return [DiscoveredJob(title="Backend Engineer", url="https://careers.example.com/job/42")]

    async def resume_text(resume: Resume) -> str:
        return "Backend engineer with Python experience."

    async def submit(
        self,
        job_url: str,
        *,
        resume_path: str,
        profile: dict,
        resume_text: str,
        auto_submit_authorized: bool,
    ):
        assert job_url == "https://careers.example.com/job/42"
        assert resume_path == resume.storage_path
        assert profile["email"] == "jamie@example.com"
        assert "Python" in resume_text
        assert auto_submit_authorized is True
        return SubmissionResult(True, "Portal confirmed submission")

    monkeypatch.setattr(JobDiscoveryService, "discover_url", discover_url)
    monkeypatch.setattr(SchedulerService, "_resume_text", staticmethod(resume_text))
    monkeypatch.setattr(ApplicationAutomationService, "submit", submit)
    await SchedulerService().run(db_session)

    assert schedule.status == "submitted"
    application = await db_session.scalar(select(Application).where(Application.job_id == schedule.matched_job_id))
    assert application is not None
    assert application.status == "submitted"
    assert application.submitted_at is not None


@pytest.mark.asyncio
async def test_manual_scheduler_run_only_processes_authenticated_users_jobs(
    authenticated_client,
    db_session,
    monkeypatch,
) -> None:
    other_user = User(
        email="another-user@example.com",
        name="Another User",
        hashed_password="hashed",
    )
    db_session.add(other_user)
    await db_session.flush()
    other_job = Job(
        user_id=other_user.id,
        company_name="Other Company",
        job_title="Engineer",
        job_url="https://other.example.com/jobs/engineer",
        source="company-careers",
    )
    db_session.add(other_job)
    other_resume = Resume(
        user_id=other_user.id,
        name="Other Resume",
        file_name="other.pdf",
        content_type="application/pdf",
        storage_path="/tmp/other.pdf",
        metadata_json="{}",
    )
    db_session.add(other_resume)
    await db_session.flush()
    other_schedule = ScheduledApplication(
        user_id=other_user.id,
        company_name="Other Company",
        role_title="Data Analyst",
        careers_url="https://other.example.com/careers",
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        resume_id=other_resume.id,
    )
    db_session.add(other_schedule)
    await db_session.commit()

    async def discover_url(self, url: str):
        return []

    monkeypatch.setattr(JobDiscoveryService, "discover_url", discover_url)
    response = await authenticated_client.post("/api/scheduler/run")

    assert response.status_code == 200
    assert response.json()["jobs_processed"] == 0
    await db_session.refresh(other_job)
    await db_session.refresh(other_schedule)
    assert other_job.last_run_at is None
    assert other_schedule.status == "scheduled"


@pytest.mark.asyncio
async def test_scheduler_emails_user_when_a_due_role_needs_attention(
    db_session,
    monkeypatch,
) -> None:
    user = User(email="attention@example.com", name="Student", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()
    resume = Resume(
        user_id=user.id,
        name="Student Resume",
        file_name="resume.pdf",
        content_type="application/pdf",
        storage_path="/tmp/resume.pdf",
        metadata_json="{}",
    )
    db_session.add(resume)
    await db_session.flush()
    schedule = ScheduledApplication(
        user_id=user.id,
        company_name="Example Co",
        role_title="Data Analyst",
        careers_url="https://example.com/careers",
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        resume_id=resume.id,
    )
    db_session.add(schedule)
    await db_session.commit()
    notified: list[tuple[str, str]] = []

    async def discover_url(self, url: str):
        return []

    async def notify(self, target_schedule: ScheduledApplication, target_user: User) -> bool:
        notified.append((target_schedule.id, target_user.email))
        return True

    monkeypatch.setattr(JobDiscoveryService, "discover_url", discover_url)
    monkeypatch.setattr(
        "app.services.scheduler.EmailNotificationService.notify_schedule_needs_attention",
        notify,
    )

    await SchedulerService().run(db_session)

    assert schedule.status == "needs_attention"
    assert notified == [(schedule.id, user.email)]
