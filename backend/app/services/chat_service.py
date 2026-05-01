import uuid
from typing import Any, AsyncIterator

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base.types import (
    AgentContext,
    AgentMessage,
    MessageRole,
)
from app.agents.sales.schemas import SalesData, SalesPhase
from app.agents.sales.supervisor import SalesSupervisor
from app.models.conversation import Conversation, Message
from app.models.deliverable import Deliverable
from app.models.project import Project
from app.schemas.chat import ChatRequest, ChatResponse


class ChatService:
    """Service layer for chat operations.

    Handles two flows:
    1. Project chat: project exists → load its data into context,
       continue conversation, deliverables save to that project.
    2. No-project chat: start fresh → gather data → auto-create
       a project once gathering completes → deliverables attach to it.
    """

    # In-memory context store keyed by conversation_id.
    _contexts: dict[str, AgentContext] = {}

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.orchestrator = SalesSupervisor()
        self.db = db

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------

    def _get_or_create_context(
        self, conversation_id: str
    ) -> AgentContext:
        if conversation_id not in self._contexts:
            self._contexts[conversation_id] = AgentContext(
                conversation_id=conversation_id
            )
        return self._contexts[conversation_id]

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _ensure_conversation(
        self,
        conversation_id: str,
        project_id: str | None = None,
    ) -> None:
        """Create conversation row if it doesn't exist."""
        if not self.db:
            return
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            self.db.add(
                Conversation(
                    id=conversation_id,
                    project_id=project_id,
                )
            )
            await self.db.commit()
        elif project_id and not conv.project_id:
            # Link an existing conversation to a project
            conv.project_id = project_id
            await self.db.commit()

    async def _persist_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        agent_name: str | None = None,
    ) -> None:
        if not self.db:
            return
        self.db.add(
            Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                agent_name=agent_name,
            )
        )
        await self.db.commit()

    # ------------------------------------------------------------------
    # Project ↔ Context loading / syncing
    # ------------------------------------------------------------------

    async def _load_project_into_context(
        self, project_id: str, context: AgentContext
    ) -> None:
        """Load an existing project's data into shared_state."""
        if not self.db:
            return
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return

        sales_data = SalesData(
            customer_name=project.customer_name,
            date_of_birth=project.date_of_birth,
            postal_code=project.postal_code,
            city=project.city,
            product_interest=project.product_interest,
            household_size=project.household_size,
            house_type=project.house_type,
            build_year=project.build_year,
            roof_orientation=project.roof_orientation,
            electricity_kwh_year=project.electricity_kwh_year,
            heating_type=project.heating_type,
            monthly_energy_bill_eur=project.monthly_energy_bill_eur,
            existing_assets=project.existing_assets,
            financial_profile=project.financial_profile,
            notes=project.notes,
            recommendations=project.recommendations or [],
            competitors=project.competitors or [],
        )

        # Restore research / strategy data if present
        rd = project.research_data or {}
        sales_data.market_trends = rd.get("market_trends", [])
        sales_data.regional_incentives = rd.get(
            "regional_incentives", []
        )
        sales_data.energy_price_outlook = rd.get(
            "energy_price_outlook"
        )
        sales_data.industry_insights = rd.get(
            "industry_insights", []
        )

        sn = project.strategy_notes or {}
        sales_data.positioning = sn.get("positioning")
        sales_data.value_proposition = sn.get("value_proposition")
        sales_data.key_messages = sn.get("key_messages", [])
        sales_data.objections = sn.get("objections", [])
        sales_data.savings_estimate = sn.get("savings_estimate")
        sales_data.payback_period = sn.get("payback_period")
        sales_data.financing_options = sn.get(
            "financing_options", []
        )

        # Resume at the right phase
        phase_map = {
            "data_gathering": SalesPhase.DATA_GATHERING,
            "research": SalesPhase.RESEARCH,
            "strategy": SalesPhase.STRATEGY,
            "deliverable": SalesPhase.DELIVERABLE,
            "complete": SalesPhase.COMPLETE,
        }
        sales_data.phase = phase_map.get(
            project.status or "data_gathering",
            SalesPhase.DATA_GATHERING,
        )
        if (
            sales_data.phase == SalesPhase.DATA_GATHERING
            and sales_data.is_gathering_complete()
        ):
            sales_data.phase = SalesPhase.RESEARCH
            # Also update the project row so the frontend sees the correct phase
            project.status = "research"
            await self.db.commit()

        context.shared_state["sales_data"] = (
            sales_data.model_dump()
        )
        context.shared_state["project_id"] = project_id

        # Load uploaded documents for RAG
        if project.documents:
            context.shared_state["uploaded_docs"] = project.documents

    async def _auto_create_project(
        self, context: AgentContext
    ) -> str | None:
        """Create a Project from SalesData gathered in a no-project chat.
        Returns the new project_id or None.
        """
        if not self.db:
            return None

        raw = context.shared_state.get("sales_data", {})
        sd = SalesData(**raw) if isinstance(raw, dict) else raw

        project = Project(
            name=sd.customer_name or "Untitled Project",
            customer_name=sd.customer_name,
            postal_code=sd.postal_code,
            city=sd.city,
            product_interest=sd.product_interest,
            household_size=sd.household_size,
            house_type=sd.house_type,
            build_year=sd.build_year,
            roof_orientation=sd.roof_orientation,
            electricity_kwh_year=sd.electricity_kwh_year,
            heating_type=sd.heating_type,
            monthly_energy_bill_eur=sd.monthly_energy_bill_eur,
            existing_assets=sd.existing_assets,
            financial_profile=sd.financial_profile,
            notes=sd.notes,
            status=sd.phase.value,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)

        context.shared_state["project_id"] = project.id
        return project.id

    async def _persist_project_data(
        self, context: AgentContext
    ) -> None:
        """Sync shared_state sales_data back to the Project row."""
        project_id = context.shared_state.get("project_id")
        if not self.db or not project_id:
            return

        raw = context.shared_state.get("sales_data", {})
        sd = SalesData(**raw) if isinstance(raw, dict) else raw

        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return

        project.customer_name = sd.customer_name
        project.postal_code = sd.postal_code
        project.city = sd.city
        project.product_interest = sd.product_interest
        project.household_size = sd.household_size
        project.house_type = sd.house_type
        project.build_year = sd.build_year
        project.roof_orientation = sd.roof_orientation
        project.electricity_kwh_year = sd.electricity_kwh_year
        project.heating_type = sd.heating_type
        project.monthly_energy_bill_eur = sd.monthly_energy_bill_eur
        project.existing_assets = sd.existing_assets
        project.financial_profile = sd.financial_profile
        project.notes = sd.notes
        project.recommendations = [
            r.model_dump() if hasattr(r, "model_dump") else r
            for r in sd.recommendations
        ]
        project.competitors = [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in sd.competitors
        ]
        project.research_data = {
            "market_trends": sd.market_trends,
            "regional_incentives": sd.regional_incentives,
            "energy_price_outlook": sd.energy_price_outlook,
            "industry_insights": sd.industry_insights,
        }
        project.strategy_notes = {
            "positioning": sd.positioning,
            "value_proposition": sd.value_proposition,
            "key_messages": sd.key_messages,
            "objections": [
                o.model_dump() if hasattr(o, "model_dump") else o
                for o in sd.objections
            ],
            "savings_estimate": sd.savings_estimate,
            "payback_period": sd.payback_period,
            "financing_options": sd.financing_options,
        }
        project.status = sd.phase.value
        await self.db.commit()

    async def _persist_deliverable(
        self, context: AgentContext
    ) -> str | None:
        """Save the generated deliverable to DB.
        Returns the deliverable_id or None.
        """
        deliverable_text = context.shared_state.get("deliverable")
        project_id = context.shared_state.get("project_id")
        if not self.db or not deliverable_text or not project_id:
            return None

        # Avoid duplicate writes for the same report
        if context.shared_state.get("deliverable_persisted"):
            return context.shared_state.get("deliverable_id")

        deliverable = Deliverable(
            project_id=project_id,
            title=(
                context.shared_state.get("sales_data", {}).get(
                    "customer_name", ""
                )
                or "Customer"
            )
            + " — Pitch Deck",
            content_markdown=deliverable_text,
        )
        self.db.add(deliverable)
        await self.db.commit()
        await self.db.refresh(deliverable)

        context.shared_state["deliverable_id"] = deliverable.id
        context.shared_state["deliverable_persisted"] = True
        return deliverable.id

    # ------------------------------------------------------------------
    # Post-turn hook: auto-create project, persist deliverable
    # ------------------------------------------------------------------

    async def _post_turn(
        self,
        context: AgentContext,
        conversation_id: str,
    ) -> dict[str, Any]:
        """Run after every agent turn. Returns extra metadata."""
        extra: dict[str, Any] = {}

        raw = context.shared_state.get("sales_data", {})
        sd = SalesData(**raw) if isinstance(raw, dict) else raw

        # Auto-create project when data gathering finishes
        # and we don't have a project yet
        if (
            not context.shared_state.get("project_id")
            and sd.is_gathering_complete()
        ):
            project_id = await self._auto_create_project(context)
            if project_id:
                # Link the conversation to the new project
                await self._ensure_conversation(
                    conversation_id, project_id
                )
                extra["project_id"] = project_id
                extra["project_created"] = True

        # Sync data to project
        await self._persist_project_data(context)

        # Persist deliverable if pitch deck was generated
        if context.shared_state.get("deliverable"):
            did = await self._persist_deliverable(context)
            if did:
                extra["deliverable_id"] = did
                extra["deliverable_ready"] = True

        return extra

    # ------------------------------------------------------------------
    # Main entry points
    # ------------------------------------------------------------------

    async def process_message(
        self, request: ChatRequest
    ) -> ChatResponse:
        conversation_id = (
            request.conversation_id or str(uuid.uuid4())
        )
        context = self._get_or_create_context(conversation_id)

        # First message: load project or init blank SalesData
        if (
            request.project_id
            and "project_id" not in context.shared_state
        ):
            await self._load_project_into_context(
                request.project_id, context
            )
            await self._ensure_conversation(
                conversation_id, request.project_id
            )
        else:
            await self._ensure_conversation(conversation_id)

        if "sales_data" not in context.shared_state:
            context.shared_state["sales_data"] = (
                SalesData().model_dump()
            )

        message = AgentMessage(
            role=MessageRole.USER,
            content=request.message,
        )
        await self._persist_message(
            conversation_id, "user", request.message
        )

        response = await self.orchestrator.execute(
            context, message
        )

        await self._persist_message(
            conversation_id,
            "assistant",
            response.content,
            response.agent_name,
        )

        # Post-turn: auto-create project, save deliverable, sync
        extra = await self._post_turn(context, conversation_id)
        metadata = {**response.metadata, **extra}

        return ChatResponse(
            conversation_id=conversation_id,
            message=response.content,
            agent_actions=[],
            metadata=metadata,
        )

    async def stream_response(
        self,
        conversation_id: str,
        websocket: WebSocket,
    ) -> AsyncIterator[dict[str, Any]]:
        data = await websocket.receive_json()
        context = self._get_or_create_context(conversation_id)

        project_id = data.get("project_id")
        if (
            project_id
            and "project_id" not in context.shared_state
        ):
            await self._load_project_into_context(
                project_id, context
            )
            await self._ensure_conversation(
                conversation_id, project_id
            )
        else:
            await self._ensure_conversation(conversation_id)

        if "sales_data" not in context.shared_state:
            context.shared_state["sales_data"] = (
                SalesData().model_dump()
            )

        message = AgentMessage(
            role=MessageRole.USER,
            content=data["message"],
        )
        await self._persist_message(
            conversation_id, "user", data["message"]
        )

        full_response = ""
        agent_name = None

        async for event in self.orchestrator.stream(
            context, message
        ):
            if event.get("type") == "agent_selected":
                agent_name = event.get("agent")
            if event.get("type") == "message":
                full_response += event.get("content", "")
            yield event

        if full_response:
            await self._persist_message(
                conversation_id,
                "assistant",
                full_response,
                agent_name,
            )

        # Post-turn: auto-create project, save deliverable, sync
        extra = await self._post_turn(context, conversation_id)

        # Emit extra events for project creation / deliverable
        if extra.get("project_created"):
            yield {
                "type": "project_created",
                "project_id": extra["project_id"],
            }
        if extra.get("deliverable_ready"):
            yield {
                "type": "deliverable_ready",
                "deliverable_id": extra["deliverable_id"],
            }

    # ------------------------------------------------------------------
    # Conversation lookup for project
    # ------------------------------------------------------------------

    async def get_project_conversation(
        self, project_id: str
    ) -> str | None:
        """Find an existing conversation for a project, if any."""
        if not self.db:
            return None
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.project_id == project_id)
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
        conv = result.scalar_one_or_none()
        return conv.id if conv else None
