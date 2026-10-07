from dataclasses import dataclass
import re
from typing import Iterable


@dataclass(frozen=True)
class Chunk:
    content: str
    section: str | None = None
    metadata: dict[str, str | int | float | bool | None] | None = None


class TextChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be between 0 and chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, *, section: str | None = None) -> list[Chunk]:
        normalized = re.sub(r"\r\n?", "\n", text).strip()
        if not normalized:
            return []

        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", normalized) if paragraph.strip()]
        chunks: list[Chunk] = []

        for paragraph in paragraphs:
            chunks.extend(self._chunk_paragraph(paragraph, section=section))

        return self._merge_overlaps(chunks)

    def _chunk_paragraph(self, paragraph: str, *, section: str | None) -> list[Chunk]:
        if len(paragraph) <= self.chunk_size:
            return [self._build_chunk(paragraph, section=section)]

        chunks: list[Chunk] = []
        start = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(paragraph):
            end = min(start + self.chunk_size, len(paragraph))
            chunk = paragraph[start:end]
            chunks.append(self._build_chunk(chunk, section=section))
            if end == len(paragraph):
                break
            start += step

        return chunks

    def _build_chunk(self, content: str, *, section: str | None) -> Chunk:
        return Chunk(content=content.strip(), section=section, metadata={"source": "resume"})

    def _merge_overlaps(self, chunks: list[Chunk]) -> list[Chunk]:
        if len(chunks) < 2:
            return chunks

        merged: list[Chunk] = [chunks[0]]
        for chunk in chunks[1:]:
            previous = merged[-1]
            candidate = (previous.content + "\n\n" + chunk.content).strip()
            if len(candidate) <= self.chunk_size:
                merged[-1] = Chunk(
                    content=candidate,
                    section=previous.section,
                    metadata=previous.metadata,
                )
                continue
            merged.append(chunk)
        return merged
