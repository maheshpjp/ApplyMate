from datetime import datetime

from pydantic import BaseModel, Field


class ResumeMetadata(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    work_authorization: str | None = None


class ResumeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    is_default: bool = False


class ResumeRead(BaseModel):
    id: str
    name: str
    file_name: str
    content_type: str
    is_default: bool
    metadata_json: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=25)


class ResumeSearchResult(BaseModel):
    id: str
    content: str
    score: float
    section: str | None = None
    metadata: dict[str, object]
    resume_id: str
    user_id: str

    model_config = {"from_attributes": True}
