from datetime import datetime

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    job_title: str = Field(min_length=1, max_length=255)
    job_url: str = Field(min_length=1, max_length=5000)
    source: str = Field(default="company-careers", min_length=1, max_length=128)


class JobRead(BaseModel):
    id: str
    user_id: str
    company_name: str
    job_title: str
    job_url: str
    source: str
    status: str
    match_score: float | None = None
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    app_count: int = 0

    model_config = {"from_attributes": True}


class JobApplicationCreate(BaseModel):
    resume_id: str = Field(min_length=1, max_length=36)
    cover_letter: str | None = None
    notes: str | None = None


class JobApplicationRead(BaseModel):
    id: str
    user_id: str
    job_id: str
    resume_id: str
    status: str
    cover_letter: str | None = None
    notes: str | None = None
    submitted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiscoveredJobResponse(BaseModel):
    job_title: str
    job_url: str
    company_name: str
    source: str


class JobDiscoveryResponse(BaseModel):
    company_url: str
    company_name: str
    discovered_jobs: int
    created_jobs: int
    jobs: list[DiscoveredJobResponse]
    message: str | None = None
    model_config = {"from_attributes": True}
