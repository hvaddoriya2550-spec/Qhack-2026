import json
from dataclasses import dataclass

from app.agents.base.agent import BaseAgent
from app.agents.base.llm import chat_completion
from app.agents.base.types import (
    AgentContext,
    AgentMessage,
    MessageRole,
)
from app.agents.sales.schemas import (
    CompetitorInfo,
    SalesData,
    SalesPhase,
)
from app.core.config import settings

SYSTEM_PROMPT = """\
You are the Cleo, Cloover's AI Sales Coach — a research assistant helping an \
energy installer prepare for a customer visit. You speak directly to \
the installer (not the customer).

Given the customer and property data, research the local energy market.

Use the `web_search` tool to find:
1. Regional subsidies and incentive programs (KfW, BAFA, local programs) \
for the customer's postal code area
2. Current energy prices and outlook in Germany
3. Competitor pricing for relevant products
4. Market trends in residential solar/heat pump/battery adoption

After searching, use `store_research` to save your findings.

IMPORTANT INTERACTION RULES:
- Do NOT ask the installer what to search. You already have the data — \
just do the research proactively.
- After completing your research, present a clear summary of findings.
- End with ONE meaningful question like: "I found that this customer \
could qualify for up to 70% subsidy on a heat pump. Before I build the \
strategy — is there anything specific about this customer's situation \
that the data doesn't show? For example, have they mentioned any concerns \
or preferences in previous calls?"
- If the installer provides context, incorporate it and call \
`mark_research_complete` to move on.
- If they say "looks good", "no", "go ahead", or similar — call \
`mark_research_complete` immediately.
- Keep the conversation moving. Don't make the installer repeat themselves."""

SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the internet for energy incentives, pricing, and market data",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query",
            }
        },
        "required": ["query"],
    },
}

STORE_RESEARCH_TOOL = {
    "name": "store_research",
    "description": "Store research findings",
    "input_schema": {
        "type": "object",
        "properties": {
            "regional_incentives": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Subsidies, tax credits, programs",
            },
            "energy_price_outlook": {
                "type": "string",
                "description": "Current and projected energy prices",
            },
            "market_trends": {
                "type": "array",
                "items": {"type": "string"},
            },
            "insights": {
                "type": "array",
                "items": {"type": "string"},
            },
            "competitor_name": {"type": "string"},
            "competitor_description": {"type": "string"},
            "competitor_strengths": {
                "type": "array",
                "items": {"type": "string"},
            },
            "competitor_weaknesses": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    },
}

MARK_RESEARCH_COMPLETE_TOOL = {
    "name": "mark_research_complete",
    "description": "Mark research as complete and advance to strategy phase. Only call this when the installer explicitly says to proceed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Brief summary of research findings",
            }
        },
        "required": ["summary"],
    },
}

ALL_TOOLS = [SEARCH_TOOL, STORE_RESEARCH_TOOL, MARK_RESEARCH_COMPLETE_TOOL]


def _get_sales_data(context: AgentContext) -> SalesData:
    raw = context.shared_state.get("sales_data")
    if isinstance(raw, dict):
        return SalesData(**raw)
    if isinstance(raw, SalesData):
        return raw
    return SalesData()


def _save(context: AgentContext, data: SalesData) -> None:
    context.shared_state["sales_data"] = data.model_dump()


@dataclass
class ResearchAgent(BaseAgent):
    name: str = "research"
    description: str = (
        "Researches energy incentives, pricing, and market data"
    )
    system_prompt: str = SYSTEM_PROMPT

    def __post_init__(self) -> None:
        from app.agents.tools.web_search import WebSearchTool
        self._search_tool = WebSearchTool()

    def _has_research(self, sales_data: SalesData) -> bool:
        return bool(sales_data.regional_incentives or sales_data.market_trends or sales_data.energy_price_outlook)

    async def execute(
        self,
        context: AgentContext,
        message: AgentMessage,
    ) -> AgentMessage:
        sales_data = _get_sales_data(context)

        known = {
            "customer": sales_data.customer_name,
            "postal_code": sales_data.postal_code,
            "city": sales_data.city,
            "product_interest": sales_data.product_interest,
            "house_type": sales_data.house_type,
            "build_year": sales_data.build_year,
            "heating_type": sales_data.heating_type,
            "electricity_kwh_year": sales_data.electricity_kwh_year,
            "monthly_bill": sales_data.monthly_energy_bill_eur,
            "existing_assets": sales_data.existing_assets,
        }

        # Follow-up message (research already done) — handle user input
        if self._has_research(sales_data):
            return await self._handle_followup(context, message, sales_data, known)

        # Step 1: Run web searches proactively
        product = sales_data.product_interest or "solar"
        postal = sales_data.postal_code or ""
        city = sales_data.city or "Germany"

        queries = [
            f"KfW BAFA subsidies {product} Germany 2025 2026",
            f"energy prices Germany residential electricity gas 2025 outlook",
            f"{product} installer prices cost Germany {city}",
            f"residential {product} market trends Germany adoption rate",
        ]

        search_results = []
        for q in queries:
            try:
                result = await self._search_tool.execute(query=q)
                search_results.append({"query": q, "results": result.output})
            except Exception:
                search_results.append({"query": q, "results": "Search failed"})

        # Step 2: Synthesize with LLM
        # Include uploaded documents if available
        doc_context = ""
        uploaded_docs = context.shared_state.get("uploaded_docs", [])
        if uploaded_docs:
            doc_texts = []
            for doc in uploaded_docs:
                doc_texts.append(f"--- {doc['filename']} ---\n{doc['text'][:3000]}")
            doc_context = (
                f"\n\nUploaded documents provided by the installer:\n"
                + "\n\n".join(doc_texts)
                + "\n\nUse these documents as additional context for your research. "
                "Reference specific data from them when relevant.\n"
            )

        synthesis_prompt = (
            f"You are the Cleo, Cloover's AI Sales Coach researching for an installer.\n\n"
            f"Customer data:\n{json.dumps(known, indent=2)}\n\n"
            f"Web search results:\n{json.dumps(search_results, indent=2)}\n"
            f"{doc_context}\n"
            f"Based on these search results{' and the uploaded documents' if uploaded_docs else ''}, "
            f"provide a clear research briefing for the installer. Structure your response as:\n\n"
            f"**Regional Incentives & Subsidies**\n"
            f"- List specific programs (KfW, BAFA, local) with amounts\n\n"
            f"**Energy Price Context**\n"
            f"- Current prices, trends, projections\n\n"
            f"**Market & Competitor Landscape**\n"
            f"- Market trends, typical pricing\n\n"
            f"**Key Takeaways for This Customer**\n"
            f"- What matters most for this specific situation\n\n"
            f"End with ONE specific, useful question based on your findings. "
            f"Example: 'I found X subsidy could save them Y. Before I build "
            f"the pitch — anything from your calls with them I should know?'\n\n"
            f"Also call `store_research` to save the structured findings."
        )

        response = await chat_completion(
            model=self.model,
            max_tokens=8192,
            system=self.system_prompt + f"\n\nCustomer data:\n{json.dumps(known, indent=2)}",
            messages=[{"role": "user", "content": synthesis_prompt}],
            tools=[STORE_RESEARCH_TOOL, MARK_RESEARCH_COMPLETE_TOOL],
        )

        # Handle any tool calls from the synthesis
        for tc in response.tool_calls:
            await self._handle_tool(tc.name, tc.input, sales_data)

        _save(context, sales_data)

        reply = response.text
        if not reply.strip():
            reply = self._build_summary(sales_data)

        return AgentMessage(
            role=MessageRole.ASSISTANT,
            content=reply,
            agent_name=self.name,
            metadata={"phase": sales_data.phase.value},
        )

    async def _handle_followup(
        self,
        context: AgentContext,
        message: AgentMessage,
        sales_data: SalesData,
        known: dict,
    ) -> AgentMessage:
        """Handle follow-up messages after research is done."""
        existing = self._build_summary(sales_data)
        system = (
            self.system_prompt
            + f"\n\nCustomer data:\n{json.dumps(known, indent=2)}"
            + f"\n\nResearch already gathered:\n{existing}"
        )
        response = await chat_completion(
            model=self.model,
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": message.content}],
            tools=[STORE_RESEARCH_TOOL, MARK_RESEARCH_COMPLETE_TOOL],
        )

        for tc in response.tool_calls:
            await self._handle_tool(tc.name, tc.input, sales_data)

        _save(context, sales_data)

        reply = response.text
        if not reply.strip():
            if sales_data.phase == SalesPhase.STRATEGY:
                reply = "Great, let's move to building your sales strategy!"
            else:
                reply = "Understood. Anything else you'd like me to research, or shall we move to strategy?"

        return AgentMessage(
            role=MessageRole.ASSISTANT,
            content=reply,
            agent_name=self.name,
            metadata={"phase": sales_data.phase.value},
        )

    def _build_summary(self, sales_data: SalesData) -> str:
        parts = ["Here's what I found:\n"]
        if sales_data.regional_incentives:
            parts.append("**Regional Incentives:**")
            for i in sales_data.regional_incentives:
                parts.append(f"- {i}")
        if sales_data.energy_price_outlook:
            parts.append(
                f"\n**Energy Prices:** "
                f"{sales_data.energy_price_outlook}"
            )
        if sales_data.market_trends:
            parts.append("\n**Market Trends:**")
            for t in sales_data.market_trends:
                parts.append(f"- {t}")
        if sales_data.competitors:
            parts.append("\n**Competitors:**")
            for c in sales_data.competitors:
                parts.append(f"- {c.name}: {c.description}")
        parts.append(
            "\nResearch complete — moving to strategy."
        )
        return "\n".join(parts)

    async def _handle_tool(
        self,
        tool_name: str,
        tool_input: dict,
        sales_data: SalesData,
    ) -> str:
        if tool_name == "web_search":
            query = tool_input.get("query", "")
            result = await self._search_tool.execute(
                query=query
            )
            return result.output

        if tool_name == "store_research":
            for inc in tool_input.get(
                "regional_incentives", []
            ):
                if inc not in sales_data.regional_incentives:
                    sales_data.regional_incentives.append(inc)
            if tool_input.get("energy_price_outlook"):
                sales_data.energy_price_outlook = (
                    tool_input["energy_price_outlook"]
                )
            for trend in tool_input.get("market_trends", []):
                if trend not in sales_data.market_trends:
                    sales_data.market_trends.append(trend)
            for ins in tool_input.get("insights", []):
                if ins not in sales_data.industry_insights:
                    sales_data.industry_insights.append(ins)
            if tool_input.get("competitor_name"):
                comp = CompetitorInfo(
                    name=tool_input["competitor_name"],
                    description=tool_input.get(
                        "competitor_description", ""
                    ),
                    strengths=tool_input.get(
                        "competitor_strengths", []
                    ),
                    weaknesses=tool_input.get(
                        "competitor_weaknesses", []
                    ),
                )
                names = {
                    c.name for c in sales_data.competitors
                }
                if comp.name not in names:
                    sales_data.competitors.append(comp)
            return "Research stored"

        if tool_name == "mark_research_complete":
            sales_data.phase = SalesPhase.ANALYSIS
            return "Research complete — advancing to analysis phase."

        return "Unknown tool"

    async def plan(
        self, context: AgentContext, task: str
    ) -> list[str]:
        return [
            "Search for regional energy incentives",
            "Research energy prices and outlook",
            "Find competitor pricing",
            "Summarize findings",
        ]

    async def can_handle(
        self, message: AgentMessage
    ) -> float:
        return 0.2
