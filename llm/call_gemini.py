"""
Simplified Gemini LLM integration - no observability/telemetry.
"""
import json
import os
from functools import cache
from typing import Any, AsyncIterator

import anyio
import google.genai as genai
from google.genai import types

from llm.domain.models import ChatResponse, ToolData
from llm.helpers import format_chat_history_for_gemini_api
from llm.types import LLMConfig
from utils.logging import logger

GEMINI_FLASH_LITE_MODEL = "gemini-2.5-flash-lite"
DEFAULT_GEMINI_FLASH_MODEL = "gemini-2.5-flash-preview-09-2025"
DEFAULT_GEMINI_PRO_MODEL = "gemini-2.5-pro"
GEMINI_API_KEY_ENV = os.environ.get("GEMINI_API_KEY")
TEMPERATURE_CHAT_LLM = 0.7

if not GEMINI_API_KEY_ENV:
    logger.warning("GEMINI_API_KEY environment variable not set")


@cache
def gemini_client():
    """Get Gemini client instance."""
    if not GEMINI_API_KEY_ENV:
        raise ValueError("GEMINI_API_KEY environment variable must be set")
    return genai.Client(api_key=GEMINI_API_KEY_ENV)


async def call_gemini_raw(
    system_prompt: str | None,
    messages: list[types.ContentUnion],
    *,
    model: str = DEFAULT_GEMINI_FLASH_MODEL,
    tools: list[dict] | None = None,
    temperature: float = TEMPERATURE_CHAT_LLM,
    llm_config: LLMConfig | None = None,
) -> types.GenerateContentResponse:
    """Call Gemini API without observability."""
    llm_config = llm_config or LLMConfig()
    params: dict[str, Any] = {}
    
    # Set thinking budget for 2.5 Pro models
    default_thinking_budget = 128 if model.startswith("gemini-2.5-pro") else 0
    if not (model.startswith("gemini-1.5") or model.startswith("gemini-2.0")):
        params["thinking_config"] = llm_config.thinking_config or types.ThinkingConfig(
            thinking_budget=default_thinking_budget
        )
    
    if llm_config.response_mime_type:
        params["response_mime_type"] = llm_config.response_mime_type
    if llm_config.max_completion_tokens:
        params["max_output_tokens"] = llm_config.max_completion_tokens
    if llm_config.response_schema:
        params["response_schema"] = llm_config.response_schema

    if llm_config.integration_tools or tools:
        params["tools"] = [types.Tool(function_declarations=tools)] if tools else []  # type: ignore[arg-type]
        if llm_config.integration_tools:
            params["tools"].extend(llm_config.integration_tools)  # type: ignore[arg-type]

    response = await gemini_client().aio.models.generate_content(
        model=model,
        contents=messages,
        config=types.GenerateContentConfig(temperature=temperature, system_instruction=system_prompt or "", **params),  # type: ignore[arg-type]
    )

    return response


async def call_gemini(
    system_prompt: str | None,
    message_chain: list[list[str]],
    *,
    model: str = DEFAULT_GEMINI_FLASH_MODEL,
    tools: list[dict] | None = None,
    temperature: float = TEMPERATURE_CHAT_LLM,
    llm_config: LLMConfig | None = None,
) -> ChatResponse:
    """Call Gemini API (non-streaming)."""
    response = await call_gemini_raw(
        system_prompt=system_prompt,
        messages=await format_chat_history_for_gemini_api(message_chain),
        model=model,
        temperature=temperature,
        llm_config=llm_config,
        tools=tools,
    )

    if response.prompt_feedback and response.prompt_feedback.block_reason:
        return ChatResponse(text="blocked")
    return ChatResponse(text=response.text or "")


async def stream_gemini(
    system_prompt: str | None,
    message_chain: list[list[str]],
    *,
    model: str = DEFAULT_GEMINI_FLASH_MODEL,
    tools: list[dict] | None = None,
    temperature: float = TEMPERATURE_CHAT_LLM,
    llm_config: LLMConfig | None = None,
) -> AsyncIterator[ChatResponse]:
    """Stream responses from Gemini API."""
    messages = await format_chat_history_for_gemini_api(message_chain)
    params: dict[str, Any] = {}

    # Set thinking budget for 2.5 Pro models
    default_thinking_budget = 128 if model.startswith("gemini-2.5-pro") else 0
    if not model.startswith(("gemini-1.5", "gemini-2.0")):
        params["thinking_config"] = (
            llm_config.thinking_config
            if llm_config and llm_config.thinking_config
            else types.ThinkingConfig(thinking_budget=default_thinking_budget, include_thoughts=True)
        )
    if tools:
        params["tools"] = [types.Tool(function_declarations=tools)]  # type: ignore[arg-type]

    last_chunk = None
    response = await gemini_client().aio.models.generate_content_stream(
        model=model,
        contents=messages,
        config=types.GenerateContentConfig(temperature=temperature, system_instruction=system_prompt, **params),  # type: ignore[arg-type]
    )
    
    try:
        async for chunk in response:
            if chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                yield ChatResponse(finish_reason=f"blocked:{chunk.prompt_feedback.block_reason}")
                break

            if not chunk.candidates:
                logger.error("Gemini API chunk contains no candidates", prompt_feedback=chunk.prompt_feedback)
                yield ChatResponse(
                    finish_reason="error:Gemini API chunk contains no candidates, "
                    f"prompt feedback: {chunk.prompt_feedback}"
                )
                break

            candidate = chunk.candidates[0]
            if not candidate.content or not candidate.content.parts:
                logger.warning("Gemini API chunk contains no content or the content has no parts.")
                continue

            for part in candidate.content.parts:
                if part.thought:
                    yield ChatResponse(text=part.text or "", metadata={"thought": True})
                if part.function_call:
                    function_call = part.function_call
                    yield ChatResponse(
                        tool=ToolData(
                            index="0",
                            tool_id=function_call.id,
                            func_name=function_call.name,
                            func_args=json.dumps(function_call.args),
                        )
                    )
            if chunk.text:
                last_chunk = chunk
                yield ChatResponse(text=chunk.text)

    except anyio.get_cancelled_exc_class():
        logger.warning(f"Gemini stream cancelled for model {model}")
        raise

