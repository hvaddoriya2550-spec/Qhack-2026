"""Multi-provider LLM client for all agents.

Supports Gemini, Anthropic, and OpenAI. The active provider is set via
LLM_PROVIDER in config/.env. All agents call `chat_completion()` and get
back a normalized `LLMResponse` regardless of which provider is used.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings


@dataclass
class ToolCall:
    """A tool call extracted from an LLM response."""
    name: str
    id: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    """Normalized response from any provider."""
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"


# ── public entry point ──────────────────────────────────────────────

async def chat_completion(
    *,
    model: str,
    system: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    max_tokens: int = 2048,
) -> LLMResponse:
    """Route to the configured provider and return a normalized response."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "gemini":
        return await _gemini_completion(
            model=model, system=system, messages=messages,
            tools=tools, max_tokens=max_tokens,
        )
    elif provider == "anthropic":
        return await _anthropic_completion(
            model=model, system=system, messages=messages,
            tools=tools, max_tokens=max_tokens,
        )
    elif provider == "openai":
        return await _openai_completion(
            model=model, system=system, messages=messages,
            tools=tools, max_tokens=max_tokens,
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


# ── Gemini ──────────────────────────────────────────────────────────

def _gemini_model(model: str) -> str:
    """Map generic model name to a Gemini model."""
    mapping = {
        "gemini-2.0-flash": "gemini-2.5-flash",
        "gemini-2.5-flash": "gemini-2.5-flash",
        "gemini-2.5-pro": "gemini-2.5-pro",
    }
    return mapping.get(model, "gemini-2.5-flash")


async def _gemini_completion(
    *, model: str, system: str, messages: list[dict],
    tools: list[dict] | None, max_tokens: int,
) -> LLMResponse:
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Convert tool definitions
    gem_tools = None
    if tools:
        declarations = []
        for t in tools:
            schema = t.get("input_schema", {})
            props = {
                k: {kk: vv for kk, vv in v.items()
                     if kk in ("type", "description", "items", "enum")}
                for k, v in schema.get("properties", {}).items()
            }
            declarations.append(genai_types.FunctionDeclaration(
                name=t["name"],
                description=t.get("description", ""),
                parameters={
                    "type": "OBJECT",
                    "properties": props,
                    "required": schema.get("required", []),
                } if props else None,
            ))
        gem_tools = [genai_types.Tool(function_declarations=declarations)]

    # Convert messages
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        content = msg.get("content", "")
        if isinstance(content, str):
            contents.append(genai_types.Content(
                role=role,
                parts=[genai_types.Part.from_text(text=content)],
            ))

    config = genai_types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
        tools=gem_tools,
    )

    response = await client.aio.models.generate_content(
        model=_gemini_model(model),
        contents=contents,
        config=config,
    )

    # Parse response
    result = LLMResponse()
    if not response.candidates:
        return result
    candidate = response.candidates[0]
    if not candidate.content or not candidate.content.parts:
        return result
    for part in candidate.content.parts:
        if part.text:
            result.text += part.text
        elif part.function_call:
            fc = part.function_call
            result.tool_calls.append(ToolCall(
                name=fc.name,
                id=fc.name,
                input=dict(fc.args) if fc.args else {},
            ))
    if result.tool_calls:
        result.stop_reason = "tool_use"
    return result


# ── Anthropic ───────────────────────────────────────────────────────

def _anthropic_model(model: str) -> str:
    mapping = {
        "gemini-2.0-flash": "claude-sonnet-4-20250514",
        "gemini-2.5-flash": "claude-sonnet-4-20250514",
        "gemini-2.5-pro": "claude-opus-4-20250514",
    }
    return mapping.get(model, model)


async def _anthropic_completion(
    *, model: str, system: str, messages: list[dict],
    tools: list[dict] | None, max_tokens: int,
) -> LLMResponse:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    kwargs: dict[str, Any] = {
        "model": _anthropic_model(model),
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    response = await client.messages.create(**kwargs)

    result = LLMResponse()
    for block in response.content:
        if block.type == "text":
            result.text += block.text
        elif block.type == "tool_use":
            result.tool_calls.append(ToolCall(
                name=block.name,
                id=block.id,
                input=block.input,
            ))
    if result.tool_calls:
        result.stop_reason = "tool_use"
    elif response.stop_reason == "end_turn":
        result.stop_reason = "end_turn"
    return result


# ── OpenAI ──────────────────────────────────────────────────────────

def _openai_model(model: str) -> str:
    mapping = {
        "gemini-2.0-flash": "gpt-4o-mini",
        "gemini-2.5-flash": "gpt-4o",
        "gemini-2.5-pro": "gpt-4o",
    }
    return mapping.get(model, model)


def _tools_to_openai(tools: list[dict]) -> list[dict]:
    """Convert our tool definitions to OpenAI function-calling format."""
    result = []
    for t in tools:
        schema = t.get("input_schema", {})
        result.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": schema,
            },
        })
    return result


async def _openai_completion(
    *, model: str, system: str, messages: list[dict],
    tools: list[dict] | None, max_tokens: int,
) -> LLMResponse:
    import openai

    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # Build OpenAI messages
    oai_messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
    ]
    for msg in messages:
        oai_messages.append({
            "role": msg["role"],
            "content": msg.get("content", ""),
        })

    kwargs: dict[str, Any] = {
        "model": _openai_model(model),
        "max_tokens": max_tokens,
        "messages": oai_messages,
    }
    if tools:
        kwargs["tools"] = _tools_to_openai(tools)

    response = await client.chat.completions.create(**kwargs)

    result = LLMResponse()
    choice = response.choices[0]
    if choice.message.content:
        result.text = choice.message.content
    if choice.message.tool_calls:
        import json
        for tc in choice.message.tool_calls:
            result.tool_calls.append(ToolCall(
                name=tc.function.name,
                id=tc.id,
                input=json.loads(tc.function.arguments),
            ))
        result.stop_reason = "tool_use"
    return result
