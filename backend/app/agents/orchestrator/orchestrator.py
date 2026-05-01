from typing import AsyncIterator

from app.agents.base.agent import BaseAgent
from app.agents.base.types import AgentContext, AgentMessage, MessageRole
from app.agents.registry import registry
from app.core.logging import logger


class AgentOrchestrator:
    """Routes messages to appropriate agents and manages multi-agent conversations.

    The orchestrator is responsible for:
    1. Determining which agent(s) should handle a given message
    2. Managing handoffs between agents
    3. Maintaining shared context across agent interactions
    4. Enforcing execution limits and timeouts
    """

    async def route(self, context: AgentContext, message: AgentMessage) -> BaseAgent:
        """Select the best agent to handle the current message."""
        agents = registry.list_agents()
        if not agents:
            raise RuntimeError("No agents registered")

        best_agent = agents[0]
        best_score = 0.0

        for agent in agents:
            score = await agent.can_handle(message)
            if score > best_score:
                best_score = score
                best_agent = agent

        logger.info(f"Routed to agent '{best_agent.name}' (score={best_score:.2f})")
        return best_agent

    async def execute(self, context: AgentContext, message: AgentMessage) -> AgentMessage:
        """Execute a single turn: route message -> agent execution -> response."""
        agent = await self.route(context, message)
        context.current_step += 1
        response = await agent.execute(context, message)
        context.history.append(message)
        context.history.append(response)
        return response

    async def stream(
        self, context: AgentContext, message: AgentMessage
    ) -> AsyncIterator[dict]:
        """Stream agent execution events for real-time UI updates."""
        agent = await self.route(context, message)
        yield {"type": "agent_selected", "agent": agent.name}

        context.current_step += 1
        response = await agent.execute(context, message)

        yield {"type": "message", "content": response.content, "agent": agent.name}
        yield {"type": "done"}
