"""
Simplified chat router with /api/query endpoint.
Tool calling pattern: Gemini function calls → execute tool → add tool_result → continue stream.
"""
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db.models import ChatWithContext
from features.tool_calling.logic import CORE_TOOLS_DICT, call_tool
from llm.call_gemini import DEFAULT_GEMINI_PRO_MODEL, stream_gemini
from llm.domain.enums import AIModelsProvider, ChatDataType, ChatRole
from llm.domain.models import ToolData, ToolResult
from llm.prompts.system_prompt_base.preamble_self_route_v7i_tools import PREAMBLE_SPEC_V7I_TOOLS
from llm.types import LLMConfig
from utils.logging import logger

router = APIRouter(prefix="/api")


class QueryRequest(BaseModel):
    """Request model for /api/query endpoint."""
    question: str
    chat_id: str | None = None


async def get_or_create_chat(chat_id: str | None) -> ChatWithContext:
    """Get existing chat or create a new one."""
    if chat_id:
        try:
            chat = ChatWithContext.objects.get(id=chat_id)
            return chat
        except ChatWithContext.DoesNotExist:
            pass
    
    # Create new chat
    chat = ChatWithContext.objects.create(
        title="New Chat",
        chat_history="[]",
        finished=False,
    )
    return chat


def format_chat_history_for_saving(chat_history: list[list[str]]) -> str:
    """Format chat history as JSON string for saving to DB."""
    return json.dumps(chat_history)


def parse_chat_history_from_string(chat_history_str: str) -> list[list[str]]:
    """Parse chat history from JSON string."""
    try:
        return json.loads(chat_history_str)
    except (json.JSONDecodeError, TypeError):
        return []


async def handle_tool_calls(
    tools_dict: dict[str, ToolData], chat_history: list[list[str]]
) -> None:
    """Execute tool calls and add results to chat history."""
    tools_results: list[dict] = []
    for td in tools_dict.values():
        try:
            args = json.loads(td.func_args) if td.func_args else {}
            # Call the tool (user and agent_config removed in simplified version)
            result = await call_tool(td.func_name, args)
            tools_results.append({"tool_id": td.tool_id, "func_name": td.func_name, "result": result})
        except Exception as e:
            logger.error(f"Error calling tool {td.func_name}: {e}")
            tools_results.append({"tool_id": td.tool_id, "func_name": td.func_name, "result": f"Error: {e}"})

    # Add tool results to chat history
    chat_history.append([ChatRole.TOOL.value])
    for tool_result in tools_results:
        tool_result_obj = ToolResult(
            tool_id=tool_result.get("tool_id"),
            result=tool_result["result"],
            func_name=tool_result["func_name"],
        )
        chat_history[-1].append(f"{ChatDataType.TOOL_RESULT}:{tool_result_obj.model_dump_json()}")


async def process_chat_stream(
    chat: ChatWithContext, question: str
) -> AsyncGenerator[str, None]:
    """Process chat request and stream responses."""
    # Get or parse chat history
    chat_history = parse_chat_history_from_string(chat.chat_history)
    
    # Add user message
    chat_history.append([ChatRole.USER.value, f"{ChatDataType.TEXT}:{question}"])
    
    # Determine if this is step 0
    is_step_0 = len(chat_history) <= 1
    
    # Get system prompt
    preamble_func = PREAMBLE_SPEC_V7I_TOOLS["step_0" if is_step_0 else "not_step_0"]
    system_prompt = await preamble_func()
    
    # Prepare tools
    tools = [tool.provider_format[AIModelsProvider.GEMINI] for tool in CORE_TOOLS_DICT.values()]
    
    # Stream responses
    tools_dict: dict[str, ToolData] = {}
    accumulated_text = ""
    
    async for response in stream_gemini(
        system_prompt=str(system_prompt),
        message_chain=chat_history,
        model=DEFAULT_GEMINI_PRO_MODEL,
        tools=tools,
        llm_config=LLMConfig(),
    ):
        # If tool call detected, collect it
        if response.tool:
            tools_dict[response.tool.index] = response.tool
        
        # Stream text
        if response.text:
            accumulated_text += response.text
            yield f"data: {json.dumps({'text': response.text, 'event': 'token'})}\n\n"
    
    # Add assistant response to chat history
    if accumulated_text:
        chat_history.append([ChatRole.ASSISTANT.value, f"{ChatDataType.TEXT}:{accumulated_text}"])
    
    # Handle tool calls if any
    if tools_dict:
        await handle_tool_calls(tools_dict, chat_history)
        
        # Stream again after tool calls
        # Get updated system prompt (not step 0 anymore)
        system_prompt = await PREAMBLE_SPEC_V7I_TOOLS["not_step_0"]()
        
        accumulated_text = ""
        async for response in stream_gemini(
            system_prompt=str(system_prompt),
            message_chain=chat_history,
            model=DEFAULT_GEMINI_PRO_MODEL,
            tools=tools,
            llm_config=LLMConfig(),
        ):
            if response.text:
                accumulated_text += response.text
                yield f"data: {json.dumps({'text': response.text, 'event': 'token'})}\n\n"
        
        # Add final assistant response
        if accumulated_text:
            chat_history.append([ChatRole.ASSISTANT.value, f"{ChatDataType.TEXT}:{accumulated_text}"])
    
    # Save updated chat history
    chat.chat_history = format_chat_history_for_saving(chat_history)
    chat.finished = True
    chat.save()
    
    # Send done event
    yield f"data: {json.dumps({'event': 'done'})}\n\n"


@router.post("/query")
async def query(request: QueryRequest):
    """Main chat endpoint with tool calling support."""
    try:
        # Get or create chat
        chat = await get_or_create_chat(request.chat_id)
        
        # Return streaming response
        return StreamingResponse(
            process_chat_stream(chat, request.question),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        logger.error(f"Error in /api/query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})

