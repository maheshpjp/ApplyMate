import math

import numpy as np
import pytest
from sqlalchemy import select

from app.models.resume import Resume, ResumeChunk
from app.services.embeddings.mock import MockEmbeddingProvider
from app.services.rag.chunking import TextChunker
from app.services.rag.retriever import SemanticRetriever
from app.services.resume_parser.service import ResumeProcessingService


def test_chunker_produces_reasonable_boundaries() -> None:
    text = "Section one\n\n" + ("word " * 100) + "\n\nSection two"
    chunks = TextChunker(chunk_size=200, chunk_overlap=20).chunk(text)

    assert len(chunks) >= 2
    assert all(len(chunk.content) <= 200 for chunk in chunks)
    assert chunks[0].content.startswith("Section one")


def test_retriever_ranks_relevant_resume_chunks() -> None:
    query_vector = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    chunks = [
        {"id": "a", "content": "Python projects and backend experience", "embedding": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "user_id": "user-1", "section": "experience", "resume_id": "resume-1"},
        {"id": "b", "content": "React design work", "embedding": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "user_id": "user-1", "section": "skills", "resume_id": "resume-1"},
    ]

    results = SemanticRetriever(top_k=1).retrieve(query_vector, chunks, user_id="user-1")

    assert results[0].id == "a"
    assert results[0].score == 1.0


def test_retriever_excludes_other_users() -> None:
    query_vector = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    chunks = [
        {"id": "a", "content": "User one Python experience", "embedding": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "user_id": "user-1", "section": "experience", "resume_id": "resume-1"},
        {"id": "b", "content": "User two Python experience", "embedding": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "user_id": "user-2", "section": "experience", "resume_id": "resume-2"},
    ]

    results = SemanticRetriever(top_k=10).retrieve(query_vector, chunks, user_id="user-1")

    assert [result.id for result in results] == ["a"]


def test_retriever_accepts_numpy_vector_values() -> None:
    query_vector = [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0]
    chunks = [
        {"id": "a", "content": "Python backend experience", "embedding": np.array(query_vector, dtype=np.float32), "user_id": "user-1", "section": "experience", "resume_id": "resume-1"},
    ]

    results = SemanticRetriever(top_k=5).retrieve(query_vector, chunks, user_id="user-1")

    assert [result.id for result in results] == ["a"]
    assert math.isclose(results[0].score, 1.0, rel_tol=1e-12, abs_tol=1e-12)


def test_retriever_accepts_stringified_vectors() -> None:
    query_vector = [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0]
    chunks = [
        {"id": "a", "content": "Python backend experience", "embedding": "[1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0]", "user_id": "user-1", "section": "experience", "resume_id": "resume-1"},
    ]

    results = SemanticRetriever(top_k=5).retrieve(query_vector, chunks, user_id="user-1")

    assert [result.id for result in results] == ["a"]
    assert math.isclose(results[0].score, 1.0, rel_tol=1e-12, abs_tol=1e-12)


def test_mock_embedding_provider_extracts_keywords() -> None:
    embedding = MockEmbeddingProvider().embed("Python, React, and backend experience")

    assert embedding[0] == 1.0
    assert embedding[1] == 1.0
    assert embedding[2] == 1.0


@pytest.mark.asyncio
async def test_resume_processing_persists_user_scoped_embeddings(db_session) -> None:
    from app.models.user import User

    user = User(
        email="rag@example.com",
        name="RAG User",
        hashed_password="hashed-password",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    resume = Resume(
        user_id=user.id,
        name="Sample Resume",
        file_name="resume.txt",
        content_type="text/plain",
        storage_path="not-used",
        metadata_json="{}",
    )
    db_session.add(resume)
    await db_session.commit()
    await db_session.refresh(resume)

    service = ResumeProcessingService(db_session, embedding_provider=MockEmbeddingProvider())
    await service.store_chunks(resume, "Python backend experience\n\nReact projects")

    result = await db_session.execute(
        select(ResumeChunk).where(ResumeChunk.resume_id == resume.id)
    )
    chunks = list(result.scalars().all())
    stored_embedding = [float(value) for value in chunks[0].embedding]

    assert len(chunks) == 1
    assert chunks[0].content.startswith("Python backend experience")
    assert stored_embedding == [1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0]
    assert chunks[0].metadata_json is not None


@pytest.mark.asyncio
async def test_resume_search_returns_only_user_chunks(authenticated_client: object, db_session) -> None:
    from app.models.user import User
    from app.models.resume import Resume, ResumeChunk

    user = await db_session.scalar(select(User).where(User.email == "test@example.com"))
    assert user is not None

    other_user = User(
        email="other@example.com",
        name="Other User",
        hashed_password="hashed-password",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    resume = Resume(
        user_id=user.id,
        name="Search Resume",
        file_name="resume.txt",
        content_type="text/plain",
        storage_path="not-used",
        metadata_json="{}",
    )
    other_resume = Resume(
        user_id=other_user.id,
        name="Other Resume",
        file_name="resume.txt",
        content_type="text/plain",
        storage_path="not-used",
        metadata_json="{}",
    )
    db_session.add_all([resume, other_resume])
    await db_session.commit()
    await db_session.refresh(resume)
    await db_session.refresh(other_resume)

    for target_resume in (resume, other_resume):
        text = "Python backend experience" if target_resume.user_id == user.id else "React design work"
        chunk = ResumeChunk(
            resume_id=target_resume.id,
            content=text,
            embedding=MockEmbeddingProvider().embed(text),
            section="experience",
            document_type="resume",
            metadata_json="{}",
        )
        db_session.add(chunk)
    await db_session.commit()

    response = await authenticated_client.post(
        "/api/resumes/search",
        json={"query": "Python backend experience", "top_k": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["resume_id"] == resume.id
    assert payload[0]["content"].startswith("Python backend experience")
    assert payload[0]["score"] > 0.0
    assert payload[0]["user_id"] == user.id
