from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Return a vector embedding for the supplied text."""


class EmbeddingFailure(RuntimeError):
    pass
