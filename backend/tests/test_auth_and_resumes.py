from pathlib import Path

from io import BytesIO

import fitz
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes.resumes import normalize_resume_content_type
from app.main import app


@pytest.mark.asyncio
async def test_initialize_database_creates_required_tables() -> None:
    from app.database.database import Base, engine, initialize_database

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await initialize_database()

    assert {"users", "resumes", "jobs", "applications"}.issubset(Base.metadata.tables)


@pytest.mark.asyncio
async def test_register_and_login() -> None:
    from app.database.database import Base, engine

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/register",
            json={"email": "new-user@example.com", "name": "New User", "password": "StrongPass123"},
        )
        assert response.status_code == 201
        token_response = await client.post(
            "/api/auth/login",
            json={"email": "new-user@example.com", "password": "StrongPass123"},
        )
        assert token_response.status_code == 200
        assert token_response.json()["access_token"]


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_resume(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get("/api/resumes/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upload_resume_accepts_multipart_form(authenticated_client: AsyncClient) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Resume with readable work experience")
    resume_bytes = document.tobytes()
    document.close()

    response = await authenticated_client.post(
        "/api/resumes",
        data={"name": "Test resume", "is_default": "false"},
        files={"file": ("resume.pdf", resume_bytes, "application/pdf")},
    )

    assert response.status_code == 201, response.text


def test_normalize_resume_content_type_accepts_supported_extensions() -> None:
    assert normalize_resume_content_type("test.pdf") == "application/pdf"
    assert normalize_resume_content_type("resume.DOCX") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert normalize_resume_content_type("resume", "application/pdf") == "application/pdf"
    assert normalize_resume_content_type("resume", "application/vnd.openxmlformats-officedocument.wordprocessingml.document") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert normalize_resume_content_type("notes.txt") is None
