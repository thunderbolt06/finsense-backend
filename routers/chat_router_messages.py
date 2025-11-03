"""Chat router using ChatMessage model instead of JSON string."""
import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db.message_helpers import (
    create_assistant_message,
    create_tool_message,
    create_user_message,
    messages_to_api_format,
)
from db.models import ChatMessage, ChatWithContext
from features.tool_calling.logic import call_tool
from llm.call_gemini import DEFAULT_GEMINI_PRO_MODEL, stream_gemini
from llm.domain.enums import AIModelsProvider, ChatDataType, ChatRole
from llm.domain.models import ToolData, ToolResult
from llm.helpers import format_chat_history_for_gemini_api
from llm.prompts.system_prompt_base.preamble_self_route_v7i_tools import PREAMBLE_SPEC_V7I_TOOLS
from llm.types import LLMConfig
from utils.logging import logger

router = APIRouter(prefix="/api")


class QueryRequest(BaseModel):
    """Request model for /api/query endpoint."""
    question: str
    chat_id: str | None = None
    file_ids: list[str] | None = None


async def get_or_create_chat(chat_id: str | None) -> ChatWithContext:
    """Get existing chat or create a new one."""
    import asyncio
    
    loop = asyncio.get_event_loop()
    
    if chat_id:
        try:
            try:
                chat = await ChatWithContext.objects.aget(id=chat_id)
                return chat
            except AttributeError:
                chat = await loop.run_in_executor(
                    None,
                    lambda: ChatWithContext.objects.get(id=chat_id)
                )
                return chat
        except ChatWithContext.DoesNotExist:
            pass
    
    # Create new chat
    try:
        chat = await ChatWithContext.objects.acreate(
            title="New Chat",
            finished=False,
        )
    except AttributeError:
        chat = await loop.run_in_executor(
            None,
            lambda: ChatWithContext.objects.create(
                title="New Chat",
                finished=False,
            )
        )
    return chat




async def handle_tool_calls_from_messages(
    tools_dict: dict[str, ToolData],
    chat: ChatWithContext,
    parent_message: ChatMessage,
) -> ChatMessage | None:
    """Execute tool calls and create tool messages."""
    if not tools_dict:
        return None
    
    import asyncio
    loop = asyncio.get_event_loop()
    
    last_tool_message = None
    
    for td in tools_dict.values():
        try:
            args = json.loads(td.func_args) if td.func_args else {}
            logger.info(
                f"Executing tool call: {td.func_name} (tool_id={td.tool_id}, args={args})"
            )
            
            result = await call_tool(td.func_name, args)
            
            # Create tool message using helper
            tool_msg = await loop.run_in_executor(
                None,
                lambda: create_tool_message(
                    chat=chat,
                    content=result,
                    parent_message=parent_message if not last_tool_message else last_tool_message,
                    tool_name=td.func_name,
                    tool_id=td.tool_id,
                )
            )
            last_tool_message = tool_msg
            
        except Exception as e:
            logger.error(
                f"Error calling tool {td.func_name}: {e}",
                exc_info=True,
            )
            tool_msg = await loop.run_in_executor(
                None,
                lambda: create_tool_message(
                    chat=chat,
                    content=f"Error: {e}",
                    parent_message=parent_message if not last_tool_message else last_tool_message,
                    tool_name=td.func_name,
                    tool_id=td.tool_id,
                )
            )
            last_tool_message = tool_msg
    
    return last_tool_message




async def process_chat_stream_with_messages(
    chat: ChatWithContext, question: str, file_ids: list[str] | None = None
) -> AsyncGenerator[str, None]:
    """Process chat request using ChatMessage model."""
    import asyncio
    loop = asyncio.get_event_loop()
    
    # Get message chain (sync operation, run in executor)
    message_chain = await loop.run_in_executor(
        None,
        lambda: chat.get_message_chain() if hasattr(chat, 'get_message_chain') else []
    )
    
    # Create user message with file_ids
    user_msg = await loop.run_in_executor(
        None,
        lambda: create_user_message(
            chat=chat,
            content=question,
            parent_message=chat.get_latest_message() if hasattr(chat, 'get_latest_message') else None,
            file_ids=file_ids or [],
        )
    )
    
    # Determine if this is step 0
    is_step_0 = len(message_chain) == 0
    
    # Get system prompt
    from features.tool_calling.logic import CORE_TOOLS_DICT
    
    preamble_func = PREAMBLE_SPEC_V7I_TOOLS["step_0" if is_step_0 else "not_step_0"]
    system_prompt = await preamble_func()
    
    # Convert messages to API format for LLM
    api_history = messages_to_api_format(message_chain + [user_msg])
    
    # Prepare tools
    tools = [tool.provider_format[AIModelsProvider.GEMINI] for tool in CORE_TOOLS_DICT.values()]
    
    # Stream responses
    tools_dict: dict[str, ToolData] = {}
    accumulated_text = ""
    had_initial_response = False
    
    logger.info(
        f"Starting initial LLM stream for question: {question[:100]} (chat_id={chat.id}, length={len(question)})"
    )
    
    async for response in stream_gemini(
        system_prompt=str(system_prompt),
        message_chain=api_history,
        model=DEFAULT_GEMINI_PRO_MODEL,
        tools=tools,
        llm_config=LLMConfig(),
    ):
        if response.tool:
            tool_key = response.tool.index or f"{response.tool.func_name}_{hash(json.dumps(response.tool.func_args or ''))}"
            tools_dict[tool_key] = response.tool
            logger.info(
                f"Tool call detected: {response.tool.func_name} (tool_id={response.tool.tool_id})"
            )
            yield f"data: {json.dumps({'event': 'tool_call', 'tool_name': response.tool.func_name, 'tool_id': response.tool.tool_id})}\n\n"
        
        if response.text:
            had_initial_response = True
            accumulated_text += response.text
            yield f"data: {json.dumps({'text': response.text, 'event': 'token'})}\n\n"
    
    logger.info(
        f"Initial stream completed. Tool calls: {len(tools_dict)}, Text length: {len(accumulated_text)}"
    )
    
    # Create assistant message
    assistant_msg = None
    if accumulated_text:
        assistant_msg = await loop.run_in_executor(
            None,
            lambda: create_assistant_message(
                chat=chat,
                content=accumulated_text,
                parent_message=user_msg,
            )
        )
    
    # Handle tool calls
    if tools_dict:
        logger.info(f"Executing {len(tools_dict)} tool call(s)")
        yield f"data: {json.dumps({'event': 'tool_execution_start', 'tool_count': len(tools_dict)})}\n\n"
        
        last_tool_msg = await handle_tool_calls_from_messages(
            tools_dict,
            chat,
            assistant_msg or user_msg,
        )
        
        yield f"data: {json.dumps({'event': 'tool_execution_complete', 'tool_count': len(tools_dict)})}\n\n"
        
        # Continue processing if needed (similar to original router)
        if last_tool_msg:
            # Get updated system prompt
            system_prompt = await PREAMBLE_SPEC_V7I_TOOLS["not_step_0"]()
            
            # Continue processing (simplified - you may want to add full multi-step logic)
            max_iterations = 5
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"Processing iteration {iteration} after tool calls")
                
                # Get updated message chain (sync operation, run in executor)
                updated_chain = await loop.run_in_executor(
                    None,
                    lambda: chat.get_message_chain() if hasattr(chat, 'get_message_chain') else []
                )
                api_history = messages_to_api_format(updated_chain)
                
                iteration_tools_dict: dict[str, ToolData] = {}
                iteration_text = ""
                
                async for response in stream_gemini(
                    system_prompt=str(system_prompt),
                    message_chain=api_history,
                    model=DEFAULT_GEMINI_PRO_MODEL,
                    tools=tools,
                    llm_config=LLMConfig(),
                ):
                    if response.tool:
                        tool_key = response.tool.index or f"{response.tool.func_name}_{hash(json.dumps(response.tool.func_args or ''))}"
                        iteration_tools_dict[tool_key] = response.tool
                    
                    if response.text and not response.metadata.get("thought"):
                        iteration_text += response.text
                        accumulated_text += response.text
                        yield f"data: {json.dumps({'text': response.text, 'event': 'token'})}\n\n"
                
                if iteration_text:
                    # Update or create assistant message
                    if assistant_msg:
                        assistant_msg.content = accumulated_text
                        await loop.run_in_executor(None, lambda: assistant_msg.save())
                    else:
                        assistant_msg = await loop.run_in_executor(
                            None,
                            lambda: create_assistant_message(
                                chat=chat,
                                content=accumulated_text,
                                parent_message=last_tool_msg,
                            )
                        )
                    break
                
                if iteration_tools_dict:
                    await handle_tool_calls_from_messages(
                        iteration_tools_dict,
                        chat,
                        assistant_msg or last_tool_msg,
                    )
                else:
                    break
    
    # Mark chat as finished
    chat.finished = True
    await loop.run_in_executor(None, lambda: chat.save())
    
    # Send done event
    yield f"data: {json.dumps({'event': 'done', 'chat_id': str(chat.id)})}\n\n"


@router.post("/query-messages")
async def query_messages(request: QueryRequest):
    """Chat endpoint using ChatMessage model.
    
    Returns streaming response with chat_id in the final 'done' event.
    Uses ChatMessage table instead of JSON string for chat history.
    """
    try:
        chat = await get_or_create_chat(request.chat_id)
        
        return StreamingResponse(
            process_chat_stream_with_messages(chat, request.question, request.file_ids),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        logger.error(f"Error in /api/query-messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})

