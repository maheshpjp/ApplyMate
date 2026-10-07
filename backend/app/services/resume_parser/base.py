from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas.resume import ResumeMetadata


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, path: Path) -> tuple[str, ResumeMetadata]:
        """Extract text and structured metadata from a supported document."""


class ResumeParseResult(tuple[str, ResumeMetadata]):
    def __new__(cls, text: str, metadata: ResumeMetadata) -> "ResumeParseResult":
        return super().__new__(cls, (text, metadata))
