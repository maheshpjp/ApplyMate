import re
from pathlib import Path

import fitz

from app.schemas.resume import ResumeMetadata


class PDFParser:
    def parse(self, path: Path) -> tuple[str, ResumeMetadata]:
        document = fitz.open(path)
        text_blocks: list[str] = []
        for page in document:
            text_blocks.append(page.get_text("text"))
        document.close()

        text = "\n".join(text_blocks)
        metadata = ResumeMetadata(
            name=self._extract_name(text),
            email=self._extract_email(text),
            phone=self._extract_phone(text),
            location=self._extract_location(text),
            linkedin=self._extract_link(text, "linkedin.com"),
            github=self._extract_link(text, "github.com"),
            portfolio=self._extract_link(text, "portfolio"),
            skills=self._extract_skills(text),
            education=self._extract_sections(text, ["education", "academic background"]),
            experience=self._extract_sections(text, ["experience", "professional experience", "work history"]),
            projects=self._extract_sections(text, ["projects", "selected projects"]),
            certifications=self._extract_sections(text, ["certifications", "licenses"]),
            work_authorization=self._extract_work_authorization(text),
        )
        return text, metadata

    def _extract_email(self, text: str) -> str | None:
        match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
        return match.group(0).lower() if match else None

    def _extract_name(self, text: str) -> str | None:
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), None)
        return first_line if first_line and len(first_line.split()) <= 6 else None

    def _extract_phone(self, text: str) -> str | None:
        match = re.search(r"\+?\d[\d\s().-]{7,}\d", text)
        return match.group(0).strip() if match else None

    def _extract_location(self, text: str) -> str | None:
        patterns = [
            r"(?:Location|City|Address)[:\s]+([^\n]+)",
            r"([^\n]*,\s*[A-Z]{2,})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if location:
                    return location
        return None

    def _extract_link(self, text: str, domain: str) -> str | None:
        match = re.search(rf"https?://(?:www\.)?{re.escape(domain)}[^\s]+", text, re.IGNORECASE)
        return match.group(0) if match else None

    def _extract_skills(self, text: str) -> list[str]:
        match = re.search(r"(?:skills?|technical skills?)\s*[:\-]\s*([^\n]+(?:\n(?!\s*(?:education|experience|projects|certifications|work authorization)\b)[^\n]+)*)", text, flags=re.IGNORECASE)
        if not match:
            return []
        return [item.strip() for item in re.split(r"[,;\n]+", match.group(1)) if item.strip()]

    def _extract_sections(self, text: str, headings: list[str]) -> list[str]:
        normalized = text.replace("\r", "")
        blocks: list[str] = []
        for heading in headings:
            pattern = rf"(?im)^{re.escape(heading)}\s*[:\-]?\s*\n?(.*?)(?=\n\s*(?:[A-Z][A-Za-z ]+\s*[:\-]?\s*\n|$))"
            for match in re.finditer(pattern, normalized):
                blocks.append(re.sub(r"\s+", " ", match.group(1)).strip())
        return blocks

    def _extract_work_authorization(self, text: str) -> str | None:
        match = re.search(r"(?:work authorization|authorized to work)[^\n]*[:\s]+([^\n]+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else None
