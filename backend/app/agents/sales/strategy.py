import json
from dataclasses import dataclass

from app.agents.base.agent import BaseAgent
from app.agents.base.llm import chat_completion
from app.agents.base.types import AgentContext, AgentMessage, MessageRole
from app.agents.sales.schemas import ObjectionResponse, SalesData, SalesPhase
from app.core.config import settings

SYSTEM_PROMPT = """\
You are Cleo, Cloover's AI Sales Coach — a strategy partner for energy installers. \
You're helping an installer prepare a winning pitch for a residential customer. \
You have the customer's data, market research, and analysis findings.

You speak directly to the installer, as a knowledgeable colleague. Be confident \
and proactive — present your full strategy upfront, then ask for feedback.

HOW TO STRUCTURE YOUR RESPONSE:

Present ALL of these in ONE message (don't ask for approval on each):

1. **Value Proposition** — Why this product makes sense for THIS customer
2. **Savings & Payback** — Annual savings, payback period, key numbers
3. **Key Talking Points** — 3-5 messages for the in-person meeting
4. **Financing Recommendation** — Best payment path with KfW/BAFA subsidies
5. **Objection Handling** — 2-3 likely pushbacks with suggested responses

Call `store_strategy` with all the data at once.

After presenting everything, ask ONE focused question:
"This is my recommended approach. Is there anything about this customer \
that I should factor in — maybe something from your previous conversations \
with them, or a specific concern they raised?"

If the installer provides feedback, adjust the strategy and call \
`store_strategy` again with updates. If they say it looks good or \
want to proceed, call `mark_strategy_complete`.

Do NOT ask for step-by-step approval. Present the full strategy, \
get one round of feedback, then move on."""

STORE_STRATEGY_TOOL = {
    "name": "store_strategy",
    "description": "Store the COMPLETE sales strategy in ONE call. Include ALL fields at once — value proposition, savings, messages, financing, and objections. Never call this multiple times.",
    "input_schema": {
        "type": "object",
        "properties": {
            "value_proposition": {"type": "string", "description": "Full value proposition"},
            "savings_estimate": {"type": "string", "description": "Annual savings estimate"},
            "payback_period": {"type": "string", "description": "Payback period"},
            "key_messages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 talking points for the meeting",
            },
            "financing_options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Recommended financing paths",
            },
            "objections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "objection": {"type": "string"},
                        "response": {"type": "string"},
                    },
                },
                "description": "2-3 likely objections with responses",
            },
        },
        "required": ["value_proposition", "savings_estimate", "key_messages"],
    },
}

COMPLETE_TOOL = {
    "name": "mark_strategy_complete",
    "description": (
        "Mark strategy as finalized. ONLY call when the "
        "installer confirms they want the pitch deck."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
        },
        "required": ["summary"],
    },
}


def _get_sales_data(context: AgentContext) -> SalesData:
    raw = context.shared_state.get("sales_data")
    if isinstance(raw, dict):
        return SalesData(**raw)
    if isinstance(raw, SalesData):
        return raw
    return SalesData()


def _save_sales_data(
    context: AgentContext, data: SalesData
) -> None:
    context.shared_state["sales_data"] = data.model_dump()


@dataclass
class StrategyAgent(BaseAgent):
    name: str = "strategy"
    description: str = (
        "Develops personalized energy sales strategy "
        "through multi-turn collaboration"
    )
    system_prompt: str = SYSTEM_PROMPT

    async def execute(
        self,
        context: AgentContext,
        message: AgentMessage,
    ) -> AgentMessage:
        sales_data = _get_sales_data(context)

        known = json.dumps(
            sales_data.model_dump(
                exclude_none=True, exclude_defaults=True
            ),
            indent=2,
        )
        system = (
            self.system_prompt
            + f"\n\nAll collected data:\n{known}"
        )

        stored = []
        if sales_data.value_proposition:
            stored.append(
                f"Value prop: {sales_data.value_proposition}"
            )
        if sales_data.savings_estimate:
            stored.append(
                f"Savings: {sales_data.savings_estimate}"
            )
        if sales_data.key_messages:
            stored.append(
                f"Key messages: {sales_data.key_messages}"
            )
        if sales_data.financing_options:
            stored.append(
                f"Financing: {sales_data.financing_options}"
            )
        if sales_data.objections:
            stored.append(
                f"Objections: {len(sales_data.objections)} stored"
            )

        if stored:
            system += (
                "\n\nStrategy elements already approved:\n"
                + "\n".join(f"- {s}" for s in stored)
                + "\n\nContinue with the next unapproved element."
            )

        messages = []
        for msg in context.history:
            if msg.role in (
                MessageRole.USER,
                MessageRole.ASSISTANT,
            ):
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })
        messages.append({
            "role": "user",
            "content": message.content,
        })

        response = await chat_completion(
            model=self.model,
            max_tokens=8192,
            system=system,
            messages=messages,
            tools=[
                STORE_STRATEGY_TOOL,
                COMPLETE_TOOL,
            ],
        )

        reply_text = response.text
        for tc in response.tool_calls:
            self._handle_tool(
                tc.name, tc.input, sales_data
            )

        _save_sales_data(context, sales_data)

        if not reply_text.strip():
            if sales_data.phase == SalesPhase.DELIVERABLE:
                reply_text = (
                    "Strategy locked in. "
                    "Generating your pitch deck now."
                )
            else:
                reply_text = (
                    "Saved. Let's move to the next element."
                )

        return AgentMessage(
            role=MessageRole.ASSISTANT,
            content=reply_text,
            agent_name=self.name,
            metadata={"phase": sales_data.phase.value},
        )

    def _handle_tool(
        self,
        tool_name: str,
        tool_input: dict,
        sales_data: SalesData,
    ) -> None:
        if tool_name == "store_strategy":
            if tool_input.get("value_proposition"):
                sales_data.value_proposition = (
                    tool_input["value_proposition"]
                )
            if tool_input.get("savings_estimate"):
                sales_data.savings_estimate = (
                    tool_input["savings_estimate"]
                )
            if tool_input.get("payback_period"):
                sales_data.payback_period = (
                    tool_input["payback_period"]
                )
            if tool_input.get("key_messages"):
                sales_data.key_messages = (
                    tool_input["key_messages"]
                )
            if tool_input.get("financing_options"):
                sales_data.financing_options = (
                    tool_input["financing_options"]
                )
            # Objections included in the same tool call
            if tool_input.get("objections"):
                for obj in tool_input["objections"]:
                    if isinstance(obj, dict) and obj.get("objection"):
                        sales_data.objections.append(
                            ObjectionResponse(
                                objection=obj["objection"],
                                response=obj.get("response", ""),
                            )
                        )

        elif tool_name == "mark_strategy_complete":
            sales_data.phase = SalesPhase.DELIVERABLE

    async def plan(
        self, context: AgentContext, task: str
    ) -> list[str]:
        return [
            "Propose value proposition",
            "Estimate savings and payback",
            "Define key sales messages",
            "Suggest financing options",
            "Prepare objection handling",
            "Get installer approval to proceed",
        ]

    async def can_handle(
        self, message: AgentMessage
    ) -> float:
        return 0.2
