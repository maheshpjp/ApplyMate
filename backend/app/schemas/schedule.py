from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ScheduleCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    role_title: str = Field(min_length=1, max_length=255)
    careers_url: HttpUrl
    scheduled_at: datetime
    resume_id: str = Field(min_length=1, max_length=36)
    auto_submit_authorized: bool = False

    @field_validator("scheduled_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Choose a date and time with a timezone")
        return value


class ScheduleRead(BaseModel):
    id: str
    user_id: str
    company_name: str
    role_title: str
    careers_url: str
    scheduled_at: datetime
    resume_id: str
    auto_submit_authorized: bool
    status: str
    result_message: str | None = None
    matched_job_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}