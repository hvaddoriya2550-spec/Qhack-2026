from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class MemoryEntry:
    key: str
    content: str
    metadata: dict[str, Any] | None = None
    score: float = 0.0


class BaseMemory(ABC):
    """Base class for agent memory backends (short-term, long-term, episodic)."""

    @abstractmethod
    async def store(self, key: str, content: str, metadata: dict | None = None) -> None:
        ...

    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 5) -> list[MemoryEntry]:
        ...

    @abstractmethod
    async def clear(self) -> None:
        ...


class ConversationMemory(BaseMemory):
    """In-memory conversation buffer. Replace with Redis/vector DB for production."""

    def __init__(self) -> None:
        self._store: list[MemoryEntry] = []

    async def store(self, key: str, content: str, metadata: dict | None = None) -> None:
        self._store.append(MemoryEntry(key=key, content=content, metadata=metadata))

    async def retrieve(self, query: str, top_k: int = 5) -> list[MemoryEntry]:
        # Simple recency-based retrieval; swap for semantic search in production
        return self._store[-top_k:]

    async def clear(self) -> None:
        self._store.clear()
