from pathlib import Path

from app.services.resume_parser.docx_parser import DOCXParser
from app.services.resume_parser.pdf_parser import PDFParser


class ResumeParserFactory:
    @staticmethod
    def create(content_type: str):
        if content_type == "application/pdf":
            return PDFParser()
        if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return DOCXParser()
        raise ValueError(f"Unsupported resume content type: {content_type}")


class ResumeProcessingError(RuntimeError):
    pass
