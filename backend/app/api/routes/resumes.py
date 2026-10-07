from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database.database import get_db
from app.models.resume import Resume, ResumeChunk
from app.schemas.resume import ResumeCreate, ResumeRead, ResumeSearchRequest, ResumeSearchResult
from app.services.embeddings.mock import MockEmbeddingProvider
from app.services.rag.retriever import SemanticRetriever
from app.services.resume_parser.factory import ResumeProcessingError
from app.services.resume_parser.service import ResumeProcessingService

router = APIRouter(prefix="/resumes", tags=["resumes"])

SUPPORTED_RESUME_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def normalize_resume_content_type(filename: str, content_type: str | None = None) -> str | None:
    extension_type = SUPPORTED_RESUME_EXTENSIONS.get(Path(filename).suffix.lower())
    if extension_type:
        return extension_type
    if content_type in SUPPORTED_RESUME_EXTENSIONS.values():
        return content_type
    return None


@router.get("", response_model=list[ResumeRead])
async def list_resumes(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[Resume]:
    result = await db.execute(select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def create_resume(
    name: str = Form(...),
    is_default: bool = Form(False),
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Resume:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A file is required")

    content_type = normalize_resume_content_type(file.filename, file.content_type)
    if content_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file '{file.filename}'. Choose a PDF or DOCX resume.",
        )

    upload_dir = Path("storage/resumes")
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4()}-{file.filename}"
    storage_path = upload_dir / stored_name
    contents = await file.read()
    storage_path.write_bytes(contents)

    resume = Resume(
        user_id=user_id,
        name=name,
        file_name=file.filename,
        content_type=content_type,
        storage_path=str(storage_path),
        is_default=is_default,
        metadata_json="{}",
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    try:
        await ResumeProcessingService(db).process(resume)
    except ResumeProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return resume


@router.post("/search", response_model=list[ResumeSearchResult])
async def search_resumes(
    request: ResumeSearchRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[ResumeSearchResult]:
    query_vector = MockEmbeddingProvider().embed(request.query)
    select_columns = (
        ResumeChunk.id,
        ResumeChunk.content,
        ResumeChunk.embedding,
        ResumeChunk.section,
        ResumeChunk.resume_id,
        Resume.user_id.label("user_id"),
    )
    result = await db.execute(
        select(*select_columns)
        .join(Resume, Resume.id == ResumeChunk.resume_id)
        .where(Resume.user_id == user_id)
        .limit(500)
    )
    chunks = [
        {
            "id": str(chunk_id),
            "content": content,
            "embedding": embedding,
            "section": section,
            "resume_id": str(resume_id),
            "user_id": str(user_id),
        }
        for chunk_id, content, embedding, section, resume_id, user_id in result.all()
    ]
    retrieved = SemanticRetriever(top_k=request.top_k).retrieve(query_vector, chunks, user_id=user_id)
    return [
        ResumeSearchResult(
            id=item.id,
            content=item.content,
            score=item.score,
            section=item.section,
            metadata=item.metadata,
            resume_id=item.resume_id,
            user_id=item.user_id,
        )
        for item in retrieved
    ]


@router.get("/{resume_id}", response_model=ResumeRead)
async def get_resume(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Resume:
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    await db.delete(resume)
    await db.commit()
