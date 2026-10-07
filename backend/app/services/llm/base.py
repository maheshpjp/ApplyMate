from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, *, system_prompt: str | None = None) -> str:
        """Return a provider-neutral text response."""

    @abstractmethod
    def generate_structured(self, prompt: str, schema: type[object], *, system_prompt: str | None = None) -> dict[str, Any]:
        """Return validated structured data."""


class LLMFailure(RuntimeError):
    pass
