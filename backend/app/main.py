from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.registry import registry
from app.agents.sales.analysis import AnalysisAgent
from app.agents.sales.data_gathering import DataGatheringAgent
from app.agents.sales.financial import FinancialAgent
from app.agents.sales.research import ResearchAgent
from app.agents.sales.strategy import StrategyAgent
from app.agents.sales.pitch_deck import PitchDeckAgent
from app.api.routes import router as api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

# Ensure all models are imported so Base.metadata knows about them
import app.models.project  # noqa: F401
import app.models.conversation  # noqa: F401
import app.models.deliverable  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Register sales agents
    registry.register(DataGatheringAgent())
    registry.register(ResearchAgent())
    registry.register(AnalysisAgent())
    registry.register(FinancialAgent())
    registry.register(StrategyAgent())
    registry.register(PitchDeckAgent())
    yield
    # Shutdown: cleanup resources


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
