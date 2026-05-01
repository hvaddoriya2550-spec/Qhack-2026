from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    output: str
    success: bool = True
    metadata: dict[str, Any] | None = None


@dataclass
class BaseTool(ABC):
    """Base class for tools that agents can use."""

    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given parameters."""
        ...

    def get_schema(self) -> dict:
        """Return the tool's JSON schema for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._parameter_schema(),
        }

    @abstractmethod
    def _parameter_schema(self) -> dict:
        """Define the tool's parameter schema."""
        ...
