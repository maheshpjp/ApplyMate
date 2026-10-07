import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.database.database import Base, engine
from app.main import app
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User


@pytest.mark.asyncio
async def test_application_draft_flow(authenticated_client: AsyncClient, db_session) -> None:
    user = await db_session.scalar(select(User).where(User.email == "test@example.com"))
    assert user is not None

    resume = Resume(
        user_id=user.id,
        name="Draft Resume",
        file_name="resume.pdf",
        content_type="application/pdf",
        storage_path="/tmp/resume.pdf",
        metadata_json="{}",
    )
    job = Job(
        user_id=user.id,
        company_name="Example Corp",
        job_title="Product Engineer",
        job_url="https://example.com/jobs/product-engineer",
        source="company-careers",
    )
    db_session.add_all([resume, job])
    await db_session.commit()
    await db_session.refresh(resume)
    await db_session.refresh(job)

    create_response = await authenticated_client.post(
        f"/api/jobs/{job.id}/applications",
        json={
            "resume_id": resume.id,
            "cover_letter": "I am excited to apply.",
            "notes": "Review before submitting.",
        },
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["status"] == "draft"

    list_response = await authenticated_client.get("/api/applications")
    assert list_response.status_code == 200
    drafts = list_response.json()
    assert len(drafts) == 1
    assert drafts[0]["job_id"] == job.id
    assert drafts[0]["status"] == "draft"

    detail_response = await authenticated_client.get(f"/api/applications/{payload['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["cover_letter"] == "I am excited to apply."

    submit_response = await authenticated_client.post(f"/api/applications/{payload['id']}/submit")
    assert submit_response.status_code == 403
    assert "human review" in submit_response.json()["detail"].lower()
