from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.models.scheduled_application import ScheduledApplication
from app.models.user import User
from app.services.notifications import EmailNotificationService


@pytest.mark.asyncio
async def test_attention_email_uses_account_email_and_schedule_details(monkeypatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_from_address", "alerts@example.com")
    monkeypatch.setattr(settings, "smtp_username", "smtp-user")
    monkeypatch.setattr(settings, "smtp_password", "smtp-password")
    sent_messages = []
    monkeypatch.setattr(EmailNotificationService, "_send", staticmethod(sent_messages.append))
    schedule = ScheduledApplication(
        id="schedule-id",
        user_id="user-id",
        company_name="Example Co",
        role_title="Software Engineer",
        careers_url="https://example.com/careers",
        scheduled_at=datetime.now(timezone.utc),
        resume_id="resume-id",
        status="needs_attention",
        result_message="The careers site presented a CAPTCHA.",
    )
    user = User(id="user-id", email="student@example.com", name="Student", hashed_password="hashed")

    sent = await EmailNotificationService().notify_schedule_needs_attention(schedule, user)

    assert sent is True
    assert len(sent_messages) == 1
    assert sent_messages[0]["To"] == "student@example.com"
    assert "Software Engineer" in sent_messages[0]["Subject"]
    assert "CAPTCHA" in sent_messages[0].get_content()
