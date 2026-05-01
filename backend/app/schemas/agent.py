from pydantic import BaseModel


class AgentInfo(BaseModel):
    id: str
    name: str
    description: str
    capabilities: list[str]
    model: str
    is_active: bool = True
