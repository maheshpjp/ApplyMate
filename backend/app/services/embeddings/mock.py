import math

from app.services.embeddings.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    def embed(self, text: str) -> list[float]:
        normalized = text.lower().strip()
        if not normalized:
            return [0.0] * 8

        vector = [0.0] * 8
        for index, token in enumerate(["python", "react", "backend", "data", "experience", "projects", "skills", "resume"]):
            if token in normalized:
                vector[index] = 1.0
        return vector
