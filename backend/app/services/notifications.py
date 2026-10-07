from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.models.scheduled_application import ScheduledApplication
from app.models.user import User

logger = logging.getLogger(__name__)


class EmailNotificationService:
    async def notify_schedule_needs_attention(
        self,
        schedule: ScheduledApplication,
        user: User,
    ) -> bool:
        if not settings.smtp_host or not settings.smtp_from_address:
            logger.warning(
                "Schedule needs attention but SMTP is not configured",
                extra={"schedule_id": schedule.id, "user_id": user.id},
            )
            return False

        if bool(settings.smtp_username) != bool(settings.smtp_password):
            raise ValueError("Configure both SMTP_USERNAME and SMTP_PASSWORD, or neither")

        message = EmailMessage()
        message["Subject"] = f"ApplyMate needs your help: {schedule.role_title}"
        message["From"] = settings.smtp_from_address
        message["To"] = user.email
        message.set_content(
            f"ApplyMate could not complete the scheduled application check for "
            f"{schedule.role_title} at {schedule.company_name}.\n\n"
            f"Reason: {schedule.result_message or 'The application needs your attention.'}\n\n"
            f"Careers page: {schedule.careers_url}\n\n"
            "Open ApplyMate to review the schedule and complete any required steps. "
            "ApplyMate does not solve CAPTCHAs or answer personal questions for you."
        )

        await asyncio.to_thread(self._send, message)
        return True

    @staticmethod
    def _send(message: EmailMessage) -> None:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.request_timeout_seconds,
        ) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
