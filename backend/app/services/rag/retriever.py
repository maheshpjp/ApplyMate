from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import math
from typing import Any

import numpy as np


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    content: str
    score: float
    section: str | None
    metadata: dict[str, object]
    resume_id: str
    user_id: str


class SemanticRetriever:
    def __init__(self, *, top_k: int = 5) -> None:
        self.top_k = top_k

    def retrieve(self, query_vector: Sequence[float], chunks: Sequence[dict[str, object]], *, user_id: str) -> list[RetrievedChunk]:
        normalized_query = self._normalize_vector(query_vector)
        results: list[RetrievedChunk] = []
        for chunk in chunks:
            if chunk.get("user_id") != user_id:
                continue
            candidate = chunk.get("embedding")
            if candidate is None:
                continue
            try:
                normalized_candidate = self._normalize_vector(candidate)
            except (TypeError, ValueError):
                continue
            score = self._cosine_similarity(normalized_query, normalized_candidate)
            results.append(
                RetrievedChunk(
                    id=str(chunk["id"]),
                    content=str(chunk["content"]),
                    score=score,
                    section=chunk.get("section"),
                    metadata={"resume_id": chunk.get("resume_id")},
                    resume_id=str(chunk["resume_id"]),
                    user_id=str(user_id),
                )
            )

        return sorted(results, key=lambda item: item.score, reverse=True)[: self.top_k]

    @staticmethod
    def _normalize_vector(values: Sequence[Any] | Any) -> list[float]:
        if isinstance(values, str):
            cleaned = values.strip()
            if cleaned.startswith("[") and cleaned.endswith("]"):
                cleaned = cleaned[1:-1]
            if not cleaned:
                return []
            values = [part.strip() for part in cleaned.split(",")]

        if isinstance(values, (list, tuple)):
            return [float(value) for value in values]

        if isinstance(values, np.ndarray):
            return [float(value) for value in values.tolist()]

        if hasattr(values, "tolist"):
            return [float(value) for value in values.tolist()]

        return [float(values)]

    def _cosine_similarity(self, left: Sequence[float], right: Sequence[float]) -> float:
        if len(left) != len(right):
            return 0.0

        dot = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)
