from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    project_id: str | None = None
    message: str
    agent_id: str | None = None  # Target specific agent, or let orchestrator decide


class AgentAction(BaseModel):
    agent_name: str
    action: str
    input_data: dict | None = None
    output: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    agent_actions: list[AgentAction] = []
    metadata: dict = {}


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
