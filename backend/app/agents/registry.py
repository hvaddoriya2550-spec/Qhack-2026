from app.agents.base.agent import BaseAgent
from app.core.logging import logger


class AgentRegistry:
    """Central registry for all available agents."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        logger.info(f"Registering agent: {agent.name}")
        self._agents[agent.name] = agent

    def get(self, name: str) -> BaseAgent | None:
        return self._agents.get(name)

    def list_agents(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def unregister(self, name: str) -> None:
        self._agents.pop(name, None)


# Global singleton
registry = AgentRegistry()
