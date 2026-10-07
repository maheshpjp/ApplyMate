from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.resume import Resume
from app.models.scheduled_application import ScheduledApplication
from app.models.user import User


@pytest.mark.asyncio
async def test_create_list_and_cancel_schedule(authenticated_client, db_session) -> None:
    user = await db_session.scalar(select(User).where(User.email == "test@example.com"))
    assert user is not None
    resume = Resume(
        user_id=user.id,
        name="Software Resume",
        file_name="resume.pdf",
        content_type="application/pdf",
        storage_path="/tmp/resume.pdf",
        metadata_json="{}",
    )
    db_session.add(resume)
    await db_session.commit()
    await db_session.refresh(resume)

    response = await authenticated_client.post(
        "/api/schedules",
        json={
            "company_name": "Adobe",
            "role_title": "Software Engineer",
            "careers_url": "https://careers.adobe.com/jobs",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "resume_id": resume.id,
        },
    )

    assert response.status_code == 201, response.text
    schedule_id = response.json()["id"]
    assert response.json()["status"] == "scheduled"
    assert response.json()["resume_id"] == resume.id

    listed = await authenticated_client.get("/api/schedules")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [schedule_id]

    cancelled = await authenticated_client.delete(f"/api/schedules/{schedule_id}")
    assert cancelled.status_code == 204
    assert await db_session.get(ScheduledApplication, schedule_id) is None