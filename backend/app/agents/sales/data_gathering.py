import json
from dataclasses import dataclass

from app.agents.base.agent import BaseAgent
from app.agents.base.llm import chat_completion
from app.agents.base.types import AgentContext, AgentMessage, MessageRole
from app.agents.sales.schemas import SalesData, SalesPhase
from app.core.config import settings

SYSTEM_PROMPT = """\
You are the Cleo, Cloover's AI Sales Coach — helping energy installers prepare \
winning pitches for residential customers (solar panels, heat pumps, \
wallboxes, batteries). You speak directly to the installer.

Your job right now is to gather key information about the customer and \
their property so you can build a personalized pitch together.

You must collect the following (ask naturally, one or two questions at a time):
1. Customer name
2. Location (postal code / city)
3. Product interest (Solar, Heat pump, Wallbox, Battery, or combo)
4. House type and build year
5. Current heating system
6. Electricity consumption (kWh/year) or monthly energy bill
7. Household size
8. Roof orientation (if solar)
9. Existing assets (e.g. already has solar, planning EV)
10. Financial situation / openness to financing
11. Any special notes or concerns

When the user provides information, call `extract_customer_data` to structure it.
When you have enough data (at minimum: name, product interest, house type, and \
heating type), call `mark_gathering_complete`.

If customer data was pre-loaded from a lead, DO NOT re-ask for information you \
already have. Start by briefly acknowledging what you know (e.g. "I see you're \
interested in solar panels for your home in Munich…") and then ONLY ask about \
the specific missing fields. Never repeat questions for data already collected.

When most key fields are filled, call `mark_gathering_complete` right away \
instead of asking more questions.

Be conversational and professional. Do NOT ask all questions at once."""

EXTRACT_TOOL = {
    "name": "extract_customer_data",
    "description": "Extract and store structured customer/property data from the conversation",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_name": {"type": "string"},
            "date_of_birth": {
                "type": "string",
                "description": (
                    "Customer date of birth in ISO format YYYY-MM-DD. "
                    "Used downstream to flag age-vs-financing-tenor risk."
                ),
            },
            "postal_code": {"type": "string"},
            "city": {"type": "string"},
            "product_interest": {"type": "string", "description": "Solar, Heat pump, Wallbox, Battery, or combo"},
            "household_size": {"type": "integer"},
            "house_type": {"type": "string"},
            "build_year": {"type": "integer"},
            "roof_orientation": {"type": "string"},
            "electricity_kwh_year": {"type": "integer"},
            "heating_type": {"type": "string"},
            "monthly_energy_bill_eur": {"type": "integer"},
            "existing_assets": {"type": "string"},
            "financial_profile": {"type": "string"},
            "notes": {"type": "string"},
        },
    },
}

COMPLETE_TOOL = {
    "name": "mark_gathering_complete",
    "description": "Mark data gathering as complete when sufficient customer info has been collected",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Brief summary of what was collected",
            }
        },
        "required": ["summary"],
    },
}


def _get_sales_data(context: AgentContext) -> SalesData:
    raw = context.shared_state.get("sales_data")
    if isinstance(raw, SalesData):
        return raw
    if isinstance(raw, dict):
        return SalesData(**raw)
    return SalesData()


def _save_sales_data(context: AgentContext, data: SalesData) -> None:
    context.shared_state["sales_data"] = data.model_dump()


def _build_messages(context: AgentContext) -> list[dict]:
    messages = []
    for msg in context.history:
        if msg.role in (MessageRole.USER, MessageRole.ASSISTANT):
            messages.append({"role": msg.role.value, "content": msg.content})
    return messages


def _apply_extraction(sales_data: SalesData, tool_input: dict) -> SalesData:
    for field in [
        "customer_name", "date_of_birth", "postal_code", "city",
        "product_interest", "house_type", "roof_orientation", "heating_type",
        "existing_assets", "financial_profile", "notes",
    ]:
        if tool_input.get(field):
            setattr(sales_data, field, tool_input[field])
    for field in ["household_size", "build_year", "electricity_kwh_year", "monthly_energy_bill_eur"]:
        if tool_input.get(field) is not None:
            setattr(sales_data, field, tool_input[field])
    return sales_data


@dataclass
class DataGatheringAgent(BaseAgent):
    name: str = "data_gathering"
    description: str = "Collects customer and property info for energy sales pitch"
    system_prompt: str = SYSTEM_PROMPT

    async def execute(self, context: AgentContext, message: AgentMessage) -> AgentMessage:
        sales_data = _get_sales_data(context)

        messages = _build_messages(context)
        messages.append({"role": "user", "content": message.content})

        system = self.system_prompt
        known = sales_data.model_dump(exclude_none=True, exclude_defaults=True)
        known.pop("phase", None)
        if known:
            system += f"\n\nCustomer data already known:\n{json.dumps(known, indent=2)}"

        response = await chat_completion(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=[EXTRACT_TOOL, COMPLETE_TOOL],
        )

        reply_text = response.text
        for tc in response.tool_calls:
            if tc.name == "extract_customer_data":
                sales_data = _apply_extraction(sales_data, tc.input)
            elif tc.name == "mark_gathering_complete":
                sales_data.phase = SalesPhase.RESEARCH

        _save_sales_data(context, sales_data)

        if not reply_text.strip():
            if sales_data.phase == SalesPhase.RESEARCH:
                reply_text = (
                    f"I've captured the key details about {sales_data.customer_name or 'the customer'}. "
                    "Now I'll research incentives and market data for your area."
                )
            else:
                reply_text = "Got it, I've noted that. What else can you tell me?"

        return AgentMessage(
            role=MessageRole.ASSISTANT,
            content=reply_text,
            agent_name=self.name,
            metadata={"phase": sales_data.phase.value, "sales_data": sales_data.model_dump()},
        )

    async def plan(self, context: AgentContext, task: str) -> list[str]:
        return [
            "Collect customer name and location",
            "Identify product interest and property details",
            "Gather energy consumption and financial info",
            "Confirm and summarize gathered data",
        ]

    async def can_handle(self, message: AgentMessage) -> float:
        return 0.3
