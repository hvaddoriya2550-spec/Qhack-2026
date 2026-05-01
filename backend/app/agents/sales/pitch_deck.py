import json
from dataclasses import dataclass

from app.agents.base.agent import BaseAgent
from app.agents.base.llm import chat_completion
from app.agents.base.types import AgentContext, AgentMessage, MessageRole
from app.agents.sales.schemas import SalesData, SalesPhase

SYSTEM_PROMPT = """\
You are an expert at creating personalized energy sales pitch decks. \
Given customer data, market research, and a sales strategy, generate a \
professional pitch deck report in Markdown that the installer can present \
to the customer.

The report MUST include these sections:
1. **Customer Overview** — Name, location, property summary
2. **Current Energy Situation** — Heating type, consumption, monthly costs
3. **Recommended Solution** — What product(s) and why they fit this customer
4. **Financial Benefits** — Savings estimate, payback period, ROI
5. **Available Incentives** — Regional subsidies, tax credits, programs
6. **Market Context** — Energy price trends, why now is a good time
7. **Financing Options** — Based on the customer's profile
8. **Common Questions & Answers** — Objection handling
9. **Next Steps** — Clear action items for the customer

Make it professional, personalized, and compelling. Use the customer's \
name and specific data throughout. Use tables for financial comparisons. \
This should be a document the installer can hand to the customer."""


@dataclass
class PitchDeckAgent(BaseAgent):
    name: str = "pitch_deck"
    description: str = (
        "Generates a personalized energy pitch deck"
    )
    system_prompt: str = SYSTEM_PROMPT

    async def execute(
        self,
        context: AgentContext,
        message: AgentMessage,
    ) -> AgentMessage:
        raw = context.shared_state.get("sales_data")
        if isinstance(raw, dict):
            sales_data = SalesData(**raw)
        elif isinstance(raw, SalesData):
            sales_data = raw
        else:
            sales_data = SalesData()

        data_dump = json.dumps(
            sales_data.model_dump(), indent=2
        )

        response = await chat_completion(
            model=self.model,
            max_tokens=8192,
            system=self.system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Generate the pitch deck for this "
                        "customer:\n\n"
                        f"```json\n{data_dump}\n```\n\n"
                        f"Installer notes: {message.content}"
                    ),
                }
            ],
        )

        report_text = response.text

        sales_data.phase = SalesPhase.COMPLETE
        context.shared_state["sales_data"] = (
            sales_data.model_dump()
        )
        context.shared_state["deliverable"] = report_text

        return AgentMessage(
            role=MessageRole.ASSISTANT,
            content=report_text,
            agent_name=self.name,
            metadata={
                "phase": SalesPhase.COMPLETE.value,
                "deliverable_ready": True,
            },
        )

    async def plan(
        self, context: AgentContext, task: str
    ) -> list[str]:
        return [
            "Generate personalized pitch deck from "
            "customer data and strategy"
        ]

    async def can_handle(
        self, message: AgentMessage
    ) -> float:
        return 0.1
