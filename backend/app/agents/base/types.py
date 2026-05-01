from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class AgentMessage:
    role: MessageRole
    content: str
    agent_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentContext:
    """Shared context passed between agents during orchestration."""

    conversation_id: str
    history: list[AgentMessage] = field(default_factory=list)
    shared_state: dict[str, Any] = field(default_factory=dict)
    max_steps: int = 25
    current_step: int = 0
