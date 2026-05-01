from dataclasses import dataclass, field

import httpx

from app.agents.tools.base_tool import BaseTool, ToolResult
from app.core.config import settings


@dataclass
class WebSearchTool(BaseTool):
    """Search the web using Tavily API for market research."""

    name: str = "web_search"
    description: str = (
        "Search the internet for competitive analysis, "
        "market data, and industry trends"
    )
    _client: httpx.AsyncClient = field(
        default_factory=httpx.AsyncClient, repr=False
    )

    async def execute(  # type: ignore[override]
        self,
        query: str = "",
        num_results: int = 5,
        **kwargs: object,
    ) -> ToolResult:
        if not settings.SEARCH_API_KEY:
            return ToolResult(
                output=(
                    f"[Search API key not configured. "
                    f"Query was: '{query}'. "
                    f"Set SEARCH_API_KEY in .env to enable live search.]"
                ),
                success=False,
            )

        try:
            if settings.SEARCH_PROVIDER == "tavily":
                return await self._tavily_search(query, num_results)
            return ToolResult(
                output=f"Unknown search provider: {settings.SEARCH_PROVIDER}",
                success=False,
            )
        except Exception as e:
            return ToolResult(
                output=f"Search failed: {e}",
                success=False,
            )

    async def _tavily_search(
        self, query: str, num_results: int
    ) -> ToolResult:
        response = await self._client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.SEARCH_API_KEY,
                "query": query,
                "max_results": num_results,
                "include_answer": True,
                "search_depth": "advanced",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        # Format results
        parts = []
        if data.get("answer"):
            parts.append(f"**Summary:** {data['answer']}\n")

        for i, result in enumerate(data.get("results", []), 1):
            title = result.get("title", "")
            content = result.get("content", "")
            url = result.get("url", "")
            parts.append(f"{i}. **{title}**\n   {content}\n   Source: {url}")

        output = "\n\n".join(parts) if parts else "No results found."
        return ToolResult(
            output=output,
            success=True,
            metadata={"query": query, "result_count": len(data.get("results", []))},
        )

    def _parameter_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results",
                    "default": 5,
                },
            },
            "required": ["query"],
        }
