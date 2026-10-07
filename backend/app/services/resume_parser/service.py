import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume, ResumeChunk
from app.schemas.resume import ResumeMetadata
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.mock import MockEmbeddingProvider
from app.services.rag.chunking import TextChunker
from app.services.resume_parser.factory import ResumeParserFactory, ResumeProcessingError

logger = logging.getLogger(__name__)


class ResumeProcessingService:
    def __init__(self, session: AsyncSession, *, embedding_provider: EmbeddingProvider | None = None):
        self.session = session
        self.embedding_provider = embedding_provider or MockEmbeddingProvider()
        self.chunker = TextChunker(chunk_size=500, chunk_overlap=80)

    async def process(self, resume: Resume) -> Resume:
        path = Path(resume.storage_path)
        if not path.exists():
            raise ResumeProcessingError("Stored resume file does not exist")

        parser = ResumeParserFactory.create(resume.content_type)
        try:
            text, metadata = parser.parse(path)
        except Exception as exc:
            raise ResumeProcessingError(f"Failed to parse resume: {exc}") from exc

        if not text.strip():
            raise ResumeProcessingError("The uploaded file did not contain any readable text")

        resume.metadata_json = json.dumps(metadata.model_dump(exclude_none=True), ensure_ascii=False)
        await self.session.commit()
        await self.session.refresh(resume)
        await self.store_chunks(resume, text)
        logger.info("Resume parsed", extra={"resume_id": resume.id, "user_id": resume.user_id})
        return resume

    async def store_chunks(self, resume: Resume, text: str) -> list[ResumeChunk]:
        chunks = self.chunker.chunk(text, section="resume")
        created: list[ResumeChunk] = []

        for index, chunk in enumerate(chunks):
            embedding = self.embedding_provider.embed(chunk.content)
            record = ResumeChunk(
                resume_id=resume.id,
                content=chunk.content,
                embedding=embedding,
                section=chunk.section,
                document_type="resume",
                metadata_json=json.dumps({
                    "source": chunk.metadata.get("source"),
                    "chunk_index": index,
                    "chunk_size": len(chunk.content),
                }, ensure_ascii=False),
            )
            self.session.add(record)
            created.append(record)

        await self.session.commit()
        for record in created:
            await self.session.refresh(record)
        return created
