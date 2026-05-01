from typing import AsyncIterator

from app.agents.base.agent import BaseAgent
from app.agents.base.types import AgentContext, AgentMessage, MessageRole
from app.agents.orchestrator.orchestrator import AgentOrchestrator
from app.agents.registry import registry
from app.agents.sales.schemas import SalesData, SalesPhase
from app.core.logging import logger

# Maps each phase to the agent name that handles it
PHASE_AGENT_MAP: dict[SalesPhase, str] = {
    SalesPhase.DATA_GATHERING: "data_gathering",
    SalesPhase.RESEARCH: "research",
    SalesPhase.ANALYSIS: "analysis",
    SalesPhase.FINANCIAL: "financial",
    SalesPhase.STRATEGY: "strategy",
    SalesPhase.DELIVERABLE: "pitch_deck",
    SalesPhase.COMPLETE: "strategy",  # Q&A after pipeline is done
}

# Handoff prompts — only used for automatic silent transitions.
# A phase that has a handoff prompt will auto-run after the previous
# phase finishes (chained, in a single user turn). A phase that does
# NOT have one is a "manual gate" — the supervisor stops there and
# waits for the next user message.
#
# Today the manual gate is STRATEGY: research → analysis → financial
# all chain automatically, then we wait for the installer to review
# the briefing before kicking off the strategy conversation.
HANDOFF_PROMPTS: dict[SalesPhase, str] = {
    SalesPhase.RESEARCH: (
        "Customer data is complete. Research regional energy incentives, "
        "pricing, and market data for this customer's area. Present your "
        "findings to the installer and ask if they have any additional "
        "context or priorities before moving to strategy."
    ),
    SalesPhase.ANALYSIS: (
        "Market research is complete. Run the data analysis: geocode the "
        "customer, pull PVGIS solar yield, fetch SMARD wholesale prices, "
        "and infer house type, heating costs, and 3 bundle tiers "
        "(Starter / Recommended / Full Independence)."
    ),
    SalesPhase.FINANCIAL: (
        "Analysis is complete with solar yield, retail price, and bundle "
        "tiers inferred. Now run the financial pipeline: apply KfW/BEG/BAFA "
        "subsidies per component, build cash / subsidy+cash / "
        "subsidy+financing scenarios for each tier, and flag age-based "
        "suitability alerts."
    ),
    SalesPhase.DELIVERABLE: (
        "The sales strategy has been finalized. "
        "Generate the personalized pitch deck for the customer."
    ),
}

# Safety cap on how many auto-handoffs can chain in a single user turn.
# data → research → analysis → financial → strategy → deliverable = 6.
MAX_AUTO_HANDOFFS = 6


def _get_sales_data(context: AgentContext) -> SalesData:
    raw = context.shared_state.get("sales_data")
    if isinstance(raw, SalesData):
        return raw
    if isinstance(raw, dict):
        return SalesData(**raw)
    return SalesData()


def _save_sales_data(
    context: AgentContext, data: SalesData
) -> None:
    context.shared_state["sales_data"] = data.model_dump()


class SalesSupervisor(AgentOrchestrator):
    """Phase-based orchestrator for Cleo, Cloover's AI Sales Coach.

    Key behaviors:
    - If lead data is already complete, skip data gathering → research.
    - Research / Analysis / Financial chain automatically in one turn
      (each has a handoff prompt). The chain stops at STRATEGY because
      strategy is the manual gate where the installer reviews the
      briefing and gives input.
    - Strategy → Deliverable auto-advances after strategy is marked
      complete.
    """

    def _maybe_fast_forward(self, context: AgentContext) -> bool:
        """On first interaction, if data is already complete, advance past gathering."""
        sd = _get_sales_data(context)
        if sd.is_gathering_complete() and sd.phase in (
            SalesPhase.DATA_GATHERING, SalesPhase.RESEARCH
        ):
            if sd.phase == SalesPhase.DATA_GATHERING:
                sd.phase = SalesPhase.RESEARCH
                _save_sales_data(context, sd)
            # Only fast-forward if no research has been done yet
            if not sd.regional_incentives and not sd.market_trends:
                logger.info("Lead data complete, no research yet — fast-forwarding to research")
                return True
        return False

    async def route(
        self, context: AgentContext, message: AgentMessage
    ) -> BaseAgent:
        sales_data = _get_sales_data(context)
        phase = sales_data.phase

        agent_name = PHASE_AGENT_MAP.get(phase)
        if agent_name:
            agent = registry.get(agent_name)
            if agent:
                logger.info(
                    f"Supervisor routing to '{agent_name}' "
                    f"(phase={phase.value})"
                )
                return agent

        logger.warning(
            f"No agent for phase '{phase.value}', "
            f"falling back to score-based routing"
        )
        return await super().route(context, message)

    def _detect_phase_change(
        self, context: AgentContext, phase_before: SalesPhase
    ) -> SalesPhase | None:
        """Return the new phase if it changed, else None."""
        sales_data = _get_sales_data(context)
        if sales_data.phase != phase_before:
            # The agent advanced the phase itself (e.g. research →
            # analysis via mark_research_complete, analysis → financial
            # via is_analysis_complete, financial → strategy via
            # is_financial_complete, etc.). Trust it.
            return sales_data.phase

        # Safety nets — auto-advance based on data conditions if the
        # agent forgot to set the phase.
        if (
            sales_data.phase == SalesPhase.DATA_GATHERING
            and sales_data.is_gathering_complete()
        ):
            return SalesPhase.RESEARCH
        if (
            sales_data.phase == SalesPhase.RESEARCH
            and sales_data.is_research_complete()
        ):
            return SalesPhase.ANALYSIS
        if (
            sales_data.phase == SalesPhase.ANALYSIS
            and sales_data.is_analysis_complete()
        ):
            return SalesPhase.FINANCIAL
        if (
            sales_data.phase == SalesPhase.FINANCIAL
            and sales_data.is_financial_complete()
        ):
            return SalesPhase.STRATEGY
        # Strategy → Deliverable is NOT auto-advanced here.
        # Only the strategy agent's mark_strategy_complete tool advances it.

        return None

    async def _run_agent(
        self,
        context: AgentContext,
        message: AgentMessage,
    ) -> AgentMessage:
        agent = await self.route(context, message)
        context.current_step += 1
        response = await agent.execute(context, message)
        context.history.append(message)
        context.history.append(response)
        return response

    async def _run_chain(
        self,
        context: AgentContext,
        first_message: AgentMessage,
    ) -> AgentMessage:
        """Run the routed agent + chain auto-handoffs until none triggers.

        Each iteration:
          1. Runs the current-phase agent
          2. Detects whether the phase changed
          3. If the new phase has a handoff prompt, builds a fake user
             message with that prompt and loops to run the next agent
          4. Otherwise stops — the user is now the gate
        """
        pieces: list[str] = []
        last_response: AgentMessage | None = None
        current_msg = first_message

        for _ in range(MAX_AUTO_HANDOFFS):
            phase_before = _get_sales_data(context).phase
            response = await self._run_agent(context, current_msg)
            pieces.append(response.content)
            last_response = response

            new_phase = self._detect_phase_change(context, phase_before)
            if not new_phase or new_phase == phase_before:
                break

            sd = _get_sales_data(context)
            sd.phase = new_phase
            _save_sales_data(context, sd)

            handoff_prompt = HANDOFF_PROMPTS.get(new_phase)
            if not handoff_prompt:
                # Phase changed but no auto-handoff for this phase →
                # this is the manual gate. Stop and return to the user.
                break

            logger.info(
                f"Auto-handoff: {phase_before.value} -> {new_phase.value}"
            )
            current_msg = AgentMessage(
                role=MessageRole.USER,
                content=handoff_prompt,
            )

        if last_response is None:
            # Should never happen — keeps mypy happy.
            return AgentMessage(
                role=MessageRole.ASSISTANT,
                content="(no response)",
                agent_name=None,
            )

        return AgentMessage(
            role=MessageRole.ASSISTANT,
            content="\n\n---\n\n".join(pieces),
            agent_name=last_response.agent_name,
            metadata=last_response.metadata,
        )

    async def _is_question(self, text: str) -> bool:
        """Detect if the user message is a question or general conversation
        rather than a phase-advancing command."""
        t = text.strip().lower()
        # Short affirmative responses → not a question, let phase advance
        affirmatives = [
            "ok", "okay", "yes", "yep", "yeah", "sure", "go ahead",
            "proceed", "continue", "next", "looks good", "good", "fine",
            "move", "ready", "let's go", "do it", "perfect", "great",
            "no changes", "all good", "approved", "confirm", "hi", "hello",
            "hey", "start", "begin",
        ]
        if t in affirmatives or len(t) < 4:
            return False
        # If it contains a question mark → likely a question
        if "?" in text:
            return True
        # If it starts with question words
        q_words = ["what", "why", "how", "which", "when", "where", "who",
                    "can", "could", "would", "should", "is", "are", "do",
                    "does", "tell", "explain", "show", "compare", "clarify"]
        first_word = t.split()[0] if t.split() else ""
        if first_word in q_words:
            return True
        # Longer messages that aren't commands are likely questions/discussion
        if len(t) > 60:
            return True
        return False

    async def _answer_question(
        self, context: AgentContext, message: AgentMessage
    ) -> AgentMessage:
        """Answer a user question using all accumulated data without advancing the phase."""
        from app.agents.base.llm import chat_completion
        import json

        sd = _get_sales_data(context)
        data_dump = sd.model_dump(exclude_none=True, exclude_defaults=True)
        data_dump.pop("phase", None)

        # Build conversation history
        history_lines = []
        for msg in context.history[-10:]:  # last 10 messages
            role = "Installer" if msg.role == MessageRole.USER else "Cleo"
            history_lines.append(f"{role}: {msg.content[:300]}")
        history = "\n".join(history_lines)

        system = (
            "You are Cleo, Cloover's AI Sales Coach. The installer asked a question "
            "during the sales coaching session. Answer it using ALL the data you have "
            "— customer info, research findings, analysis, and strategy. Be helpful, "
            "specific, and reference actual numbers/data when possible.\n\n"
            "DO NOT advance the pipeline or change the topic. Just answer the question "
            "and ask if they need anything else before continuing."
        )

        response = await chat_completion(
            model="gemini-2.5-flash",
            system=system,
            messages=[
                {"role": "user", "content": (
                    f"Customer & pipeline data:\n{json.dumps(data_dump, indent=2, default=str)}\n\n"
                    f"Recent conversation:\n{history}\n\n"
                    f"Installer's question: {message.content}"
                )},
            ],
            max_tokens=4096,
        )

        return AgentMessage(
            role=MessageRole.ASSISTANT,
            content=response.text,
            agent_name="strategy",
            metadata={"phase": sd.phase.value},
        )

    async def execute(
        self, context: AgentContext, message: AgentMessage
    ) -> AgentMessage:
        # If pipeline is done, respond without running any agent
        sd = _get_sales_data(context)
        if sd.phase == SalesPhase.COMPLETE:
            return AgentMessage(
                role=MessageRole.ASSISTANT,
                content=(
                    "Your sales briefing is ready! Click **Generate Report** "
                    "to download the full pitch deck with packages, "
                    "financing options, and pitch guidance."
                ),
                agent_name="strategy",
                metadata={"phase": "complete"},
            )

        # If the user is asking a question, answer it without advancing the phase
        if len(context.history) > 0 and await self._is_question(message.content):
            logger.info("Detected question — answering without advancing phase")
            return await self._answer_question(context, message)

        # Fast-forward on first message if data is complete
        fast_forwarded = self._maybe_fast_forward(context)

        if fast_forwarded:
            sd = _get_sales_data(context)
            intro = (
                f"I already have the details for {sd.customer_name or 'this customer'} "
                f"in {sd.city or 'their area'}. Let me research the market, "
                f"run the analysis, and build the financing scenarios.\n\n"
                f"*Please hold on while I look into this...*"
            )

            handoff_msg = AgentMessage(
                role=MessageRole.USER,
                content=HANDOFF_PROMPTS.get(SalesPhase.RESEARCH, "Research this customer."),
            )
            chain_response = await self._run_chain(context, handoff_msg)

            return AgentMessage(
                role=MessageRole.ASSISTANT,
                content=intro + "\n\n---\n\n" + chain_response.content,
                agent_name=chain_response.agent_name,
                metadata=chain_response.metadata,
            )

        return await self._run_chain(context, message)

    async def stream(
        self, context: AgentContext, message: AgentMessage
    ) -> AsyncIterator[dict]:
        fast_forwarded = self._maybe_fast_forward(context)

        if fast_forwarded:
            sd = _get_sales_data(context)
            intro = (
                f"I already have the details for {sd.customer_name or 'this customer'} "
                f"in {sd.city or 'their area'}. Let me research the market, "
                f"run the analysis, and build the financing scenarios.\n\n"
                f"*Please hold on while I look into this...*"
            )
            yield {"type": "phase_changed", "phase": "research"}

            handoff_msg = AgentMessage(
                role=MessageRole.USER,
                content=HANDOFF_PROMPTS.get(SalesPhase.RESEARCH, "Research."),
            )
            current_msg = handoff_msg
            chained_pieces: list[str] = [intro]

            for _ in range(MAX_AUTO_HANDOFFS):
                phase_before = _get_sales_data(context).phase
                agent = await self.route(context, current_msg)
                yield {"type": "agent_selected", "agent": agent.name}
                context.current_step += 1
                response = await agent.execute(context, current_msg)
                context.history.append(current_msg)
                context.history.append(response)
                chained_pieces.append(response.content)
                yield {
                    "type": "message",
                    "content": response.content,
                    "agent": agent.name,
                }

                new_phase = self._detect_phase_change(context, phase_before)
                if not new_phase or new_phase == phase_before:
                    break

                sd2 = _get_sales_data(context)
                sd2.phase = new_phase
                _save_sales_data(context, sd2)
                yield {"type": "phase_changed", "phase": new_phase.value}

                handoff_prompt = HANDOFF_PROMPTS.get(new_phase)
                if not handoff_prompt:
                    break

                current_msg = AgentMessage(
                    role=MessageRole.USER,
                    content=handoff_prompt,
                )

            yield {"type": "done"}
            return

        # Normal path: run the routed agent and chain handoffs
        current_msg = message
        for _ in range(MAX_AUTO_HANDOFFS):
            phase_before = _get_sales_data(context).phase
            agent = await self.route(context, current_msg)
            yield {"type": "agent_selected", "agent": agent.name}
            context.current_step += 1
            response = await agent.execute(context, current_msg)
            context.history.append(current_msg)
            context.history.append(response)
            yield {
                "type": "message",
                "content": response.content,
                "agent": agent.name,
            }

            new_phase = self._detect_phase_change(context, phase_before)
            if not new_phase or new_phase == phase_before:
                break

            sd = _get_sales_data(context)
            sd.phase = new_phase
            _save_sales_data(context, sd)
            yield {"type": "phase_changed", "phase": new_phase.value}

            handoff_prompt = HANDOFF_PROMPTS.get(new_phase)
            if not handoff_prompt:
                break

            current_msg = AgentMessage(
                role=MessageRole.USER,
                content=handoff_prompt,
            )

        yield {"type": "done"}
