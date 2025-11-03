"""
Simplified chat router with /api/query endpoint.
Tool calling pattern: Gemini function calls → execute tool → add tool_result → continue stream.
Now uses ChatMessage model for persistence.
"""
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llm.prompts.system_prompt_base.preamble_self_route_v7h_modalities import PREAMBLE_SPEC_V7H_MODALITIES

from db.message_helpers import (
    create_assistant_message,
    create_tool_message,
    create_user_message,
    messages_to_api_format,
)
from db.models import ChatMessage, ChatWithContext
from features.tool_calling.logic import CORE_TOOLS_DICT, call_tool
from llm.call_gemini import DEFAULT_GEMINI_PRO_MODEL, stream_gemini
from llm.domain.enums import AIModelsProvider, ChatDataType, ChatRole
from llm.domain.models import ToolData
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
            # Use async ORM if available, otherwise wrap in executor
            try:
                chat = await ChatWithContext.objects.aget(id=chat_id)
                return chat
            except AttributeError:
                # Fallback to sync ORM in executor
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
        # Fallback to sync ORM in executor
        chat = await loop.run_in_executor(
            None,
            lambda: ChatWithContext.objects.create(
                title="New Chat",
                finished=False,
            )
        )
    return chat


async def handle_tool_calls(
    tools_dict: dict[str, ToolData],
    chat: ChatWithContext,
    parent_message: ChatMessage,
) -> ChatMessage | None:
    """Execute tool calls and create tool messages."""
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
            result_preview = result[:200] if len(result) > 200 else result
            logger.info(
                f"Tool call completed: {td.func_name} (tool_id={td.tool_id}, result_length={len(result)}, preview={result_preview[:100]}...)"
            )
            
            # Create tool message
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
                f"Error calling tool {td.func_name} (tool_id={td.tool_id}): {e}",
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


async def process_chat_stream(
    chat: ChatWithContext, question: str, file_ids: list[str] | None = None
) -> AsyncGenerator[str, None]:
    """Process chat request and stream responses using ChatMessage model."""
    import asyncio
    loop = asyncio.get_event_loop()
    
    # Get message chain (sync operation, run in executor)
    message_chain = await loop.run_in_executor(
        None,
        lambda: chat.get_message_chain() if hasattr(chat, 'get_message_chain') else []
    )
    
    # Create user message
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
    # Convert messages to API format for LLM
    api_history = messages_to_api_format(message_chain + [user_msg])
    
    # Get system prompt
    system_prompt = await PREAMBLE_SPEC_V7H_MODALITIES["not_step_0"]()
    
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
        # If tool call detected, collect it
        if response.tool:
            # Use a unique key for each tool call (index or func_name+args hash)
            tool_key = response.tool.index or f"{response.tool.func_name}_{hash(json.dumps(response.tool.func_args or ''))}"
            tools_dict[tool_key] = response.tool
            logger.info(
                f"Tool call detected during streaming: {response.tool.func_name} (tool_id={response.tool.tool_id}, key={tool_key})"
            )
            # Yield tool call event to client
            yield f"data: {json.dumps({'event': 'tool_call', 'tool_name': response.tool.func_name, 'tool_id': response.tool.tool_id})}\n\n"
        
        # Stream text
        if response.text:
            had_initial_response = True
            accumulated_text += response.text
            if response.metadata.get("thought"):
                pass
                # yield f"data: {json.dumps({'text': response.text, 'event': 'thought'})}\n\n"
            else:
                yield f"data: {json.dumps({'text': response.text, 'event': 'token'})}\n\n"
    
    logger.info(
        f"Initial stream completed. Tool calls: {len(tools_dict)}, Had text: {had_initial_response}, Text length: {len(accumulated_text)}"
    )
    
    # Create assistant message if there was any text
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
    
    # Handle tool calls if any
    if tools_dict:
        logger.info(
            f"Executing {len(tools_dict)} tool call(s): {[tool_data.func_name for tool_data in tools_dict.values()]}"
        )
        
        # Yield tool execution start event
        yield f"data: {json.dumps({'event': 'tool_execution_start', 'tool_count': len(tools_dict), 'tools': [td.func_name for td in tools_dict.values()]})}\n\n"
        
        last_tool_msg = await handle_tool_calls(tools_dict, chat, assistant_msg or user_msg)
        
        # Yield tool execution complete event
        yield f"data: {json.dumps({'event': 'tool_execution_complete', 'tool_count': len(tools_dict)})}\n\n"
        
        # Stream again after tool calls
        # Get updated system prompt (not step_0 anymore)
        system_prompt = await PREAMBLE_SPEC_V7I_TOOLS["not_step_0"]()
        
        # Handle recursive tool calls - keep looping until we get a text response
        max_iterations = 20  # Prevent infinite loops
        iteration = 0
        current_accumulated_text = accumulated_text
        
        while iteration < max_iterations:
            iteration += 1
            
            # Get updated message chain (sync operation, run in executor)
            updated_chain = await loop.run_in_executor(
                None,
                lambda: chat.get_message_chain() if hasattr(chat, 'get_message_chain') else []
            )
            api_history = messages_to_api_format(updated_chain)
            
            logger.info(
                f"Starting LLM stream iteration {iteration} after tool calls (chat_id={chat.id}, message_count={len(updated_chain)})"
            )
            
            # Collect tool calls from this iteration
            iteration_tools_dict: dict[str, ToolData] = {}
            iteration_accumulated_text = ""
            response_count = 0
            
            async for response in stream_gemini(
                system_prompt=str(system_prompt),
                message_chain=api_history,
                model=DEFAULT_GEMINI_PRO_MODEL,
                tools=tools,
                llm_config=LLMConfig(),
            ):
                response_count += 1
                
                # Handle tool calls - recursive tool calling
                if response.tool:
                    # Use a unique key for each tool call (index or func_name+args hash)
                    tool_key = response.tool.index or f"{response.tool.func_name}_{hash(json.dumps(response.tool.func_args or ''))}"
                    logger.info(
                        f"Tool call in iteration {iteration}: {response.tool.func_name} (tool_id={response.tool.tool_id}, key={tool_key})"
                    )
                    iteration_tools_dict[tool_key] = response.tool
                    yield f"data: {json.dumps({'event': 'tool_call', 'tool_name': response.tool.func_name, 'tool_id': response.tool.tool_id})}\n\n"
                
                # Stream text (skip thought metadata)
                if response.text and not response.metadata.get("thought"):
                    iteration_accumulated_text += response.text
                    current_accumulated_text += response.text
                    yield f"data: {json.dumps({'text': response.text, 'event': 'token'})}\n\n"
            
            logger.info(
                f"Stream iteration {iteration} completed. Responses: {response_count}, Text length: {len(iteration_accumulated_text)}, Tool calls: {len(iteration_tools_dict)}"
            )
            
            # If we got text, create/update assistant message and break
            if iteration_accumulated_text:
                if assistant_msg:
                    # Update existing message
                    assistant_msg.content = current_accumulated_text
                    await loop.run_in_executor(None, lambda: assistant_msg.save())
                else:
                    # Create new message
                    assistant_msg = await loop.run_in_executor(
                        None,
                        lambda: create_assistant_message(
                            chat=chat,
                            content=current_accumulated_text,
                            parent_message=last_tool_msg or user_msg,
                        )
                    )
                break
            
            # If we got tool calls, execute them and continue
            if iteration_tools_dict:
                logger.info(
                    f"Executing {len(iteration_tools_dict)} tool call(s) in iteration {iteration}: {[tool_data.func_name for tool_data in iteration_tools_dict.values()]}"
                )
                yield f"data: {json.dumps({'event': 'tool_execution_start', 'tool_count': len(iteration_tools_dict), 'tools': [td.func_name for td in iteration_tools_dict.values()]})}\n\n"
                
                last_tool_msg = await handle_tool_calls(iteration_tools_dict, chat, assistant_msg or last_tool_msg or user_msg)
                
                yield f"data: {json.dumps({'event': 'tool_execution_complete', 'tool_count': len(iteration_tools_dict)})}\n\n"
                # Continue to next iteration
            else:
                # No tool calls and no text - break to avoid infinite loop
                logger.warning(f"No text or tool calls in iteration {iteration}, breaking")
                break
        
        # Create final assistant message if we have text but no message yet
        if current_accumulated_text and not assistant_msg:
            assistant_msg = await loop.run_in_executor(
                None,
                lambda: create_assistant_message(
                    chat=chat,
                    content=current_accumulated_text,
                    parent_message=last_tool_msg or user_msg,
                )
            )
        elif not had_initial_response and not assistant_msg:
            # If we had no response at all, add a placeholder message
            logger.warning("No text response received in any stream")
            placeholder = "I've executed the requested tools. Please check the results above."
            assistant_msg = await loop.run_in_executor(
                None,
                lambda: create_assistant_message(
                    chat=chat,
                    content=placeholder,
                    parent_message=last_tool_msg or user_msg,
                )
            )
            yield f"data: {json.dumps({'text': placeholder, 'event': 'token'})}\n\n"
            
    
    # Mark chat as finished
    chat.finished = True
    try:
        await chat.asave()
    except AttributeError:
        await loop.run_in_executor(None, lambda: chat.save())
    
    # Send done event with chat_id
    yield f"data: {json.dumps({'event': 'done', 'chat_id': str(chat.id)})}\n\n"


@router.post("/query")
async def query(request: QueryRequest):
    """Main chat endpoint with tool calling support using ChatMessage model.
    
    Returns streaming response with chat_id in the final 'done' event.
    Client should store the chat_id and send it in subsequent requests to continue the conversation.
    """
    try:
        # Get or create chat
        chat = await get_or_create_chat(request.chat_id)
        
        # Return streaming response
        return StreamingResponse(
            process_chat_stream(chat, request.question, request.file_ids),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        logger.error(f"Error in /api/query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/traces")
async def get_traces():
    """Get all chat histories from all chats using ChatMessage model.
    
    Returns a list of all chats with their histories.
    Useful for debugging and viewing all conversation traces.
    """
    try:
        from db.message_helpers import messages_to_legacy_format
        
        import asyncio
        
        # Get all chats using async ORM
        loop = asyncio.get_event_loop()
        
        # Get all chats (sync operation, run in executor)
        all_chats = await loop.run_in_executor(
            None,
            lambda: list(ChatWithContext.objects.all().order_by('-created_at'))
        )
        
        # Format response
        traces = []
        for chat in all_chats:
            # Get message chain from ChatMessage model (sync operation)
            message_chain = await loop.run_in_executor(
                None,
                lambda c=chat: c.get_message_chain() if hasattr(c, 'get_message_chain') else []
            )
            
            # Convert to legacy format for backwards compatibility
            chat_history = await loop.run_in_executor(
                None,
                lambda m=message_chain: messages_to_legacy_format(m) if m else []
            )
            
            traces.append({
                "chat_id": str(chat.id),
                "title": chat.title,
                "finished": chat.finished,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
                "chat_history": chat_history,
            })
        
        return {
            "status": "ok",
            "count": len(traces),
            "traces": traces,
        }
    except Exception as e:
        logger.error(f"Error in /api/traces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})

