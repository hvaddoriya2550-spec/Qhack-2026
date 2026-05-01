from fastapi import APIRouter, HTTPException

from app.agents.registry import registry
from app.schemas.agent import AgentInfo

router = APIRouter()


def _agent_to_info(agent) -> AgentInfo:
    return AgentInfo(
        id=agent.name,
        name=agent.name,
        description=agent.description,
        capabilities=[t["name"] for t in agent.tools] if agent.tools else [],
        model=agent.model,
    )


@router.get("/", response_model=list[AgentInfo])
async def list_agents() -> list[AgentInfo]:
    """List all available agents and their capabilities."""
    return [_agent_to_info(a) for a in registry.list_agents()]


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str) -> AgentInfo:
    """Get details about a specific agent."""
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_to_info(agent)
