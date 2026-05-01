from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.agents.base.types import AgentMessage, AgentContext


@dataclass
class BaseAgent(ABC):
    """Base class for all agents in the system."""

    name: str
    description: str
    model: str = "claude-sonnet-4-20250514"
    system_prompt: str = ""
    tools: list[Any] = field(default_factory=list)

    @abstractmethod
    async def execute(self, context: AgentContext, message: AgentMessage) -> AgentMessage:
        """Execute the agent's logic given context and an input message."""
        ...

    @abstractmethod
    async def plan(self, context: AgentContext, task: str) -> list[str]:
        """Break down a task into steps (used by orchestrator for routing)."""
        ...

    async def can_handle(self, message: AgentMessage) -> float:
        """Return confidence score (0-1) that this agent can handle the message."""
        return 0.0
