"""
Multi-step agentic chat router with modality support.
Based on Little-Bird-Backend's handle_chat_v4_request pattern.
Uses ChatMessage model for persistence.
"""
import asyncio
import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db.message_helpers import (
    create_assistant_message,
    create_user_message,
    messages_to_api_format,
)
from db.models import ChatMessage, ChatWithContext
from llm.call_gemini import DEFAULT_GEMINI_PRO_MODEL, stream_gemini
from llm.constants import END_TAG_THINKING, START_TAG_THINKING
from llm.modality_helpers import get_context_for_modality
from llm.modality_parsing import (
    RoutingInfo,
    extract_modalities,
    extract_routing_info_from_block_text,
    parse_thinking_blocks_from_message,
)
from llm.prompts.system_prompt_base.preamble_self_route_v7h_modalities import PREAMBLE_SPEC_V7H_MODALITIES
from llm.types import LLMConfig
from utils.logging import logger

router = APIRouter(prefix="/api")

# Maximum number of agentic steps
MAX_AGENTIC_STEPS = 20

# Message to insert between agent steps
MESSAGE_BETWEEN_STEPS = "This is an auto-generated message. Assistant, after your previous message the system message was dynamically updated with any new context found, instructions, etc. based on this very state of the chat, in order to allow you to continue responding."


class QueryRequest(BaseModel):
    """Request model for /api/query endpoint."""
    question: str
    chat_id: str | None = None
    file_ids: list[str] | None = None


async def get_or_create_chat(chat_id: str | None) -> ChatWithContext:
    """Get existing chat or create a new one."""
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


def append_between_step_message(
    chat: ChatWithContext,
    routing_info: RoutingInfo | None,
    parent_message: ChatMessage,
) -> ChatMessage:
    """Insert a 'fake' user message between consecutive agent steps.
    
    This is needed because some LLMs don't allow consecutive assistant messages.
    """
    message = MESSAGE_BETWEEN_STEPS
    
    # If routing_info has modality identifiers, include them
    if routing_info:
        inner = routing_info.get("routing_info", {})
        all_modalities = [inner.get("first_modality")] + inner.get("additional_parallel_modalities", [])
        identifiers = []
        for modality in all_modalities:
            if modality and modality.get("type"):
                # Extract identifier if available (for future use)
                modality_type = modality.get("type")
                identifiers.append(modality_type)
        
        if identifiers:
            message = f"Here are the modalities invoked in the last step: {', '.join(identifiers)}"
    
    return create_user_message(
        chat=chat,
        content=f"<system>{message}</system>",
        parent_message=parent_message,
    )


async def construct_context_and_system_prompt(
    chat: ChatWithContext,
    message_chain: list[ChatMessage],
    step: int,
    routing_info: RoutingInfo | None,
) -> tuple[list[dict[str, Any]], str]:
    """
    Construct context and system prompt for chat interaction based on routing information.
    
    Returns:
        Tuple of (context_json, system_prompt_text)
    """
    context_json: list[dict[str, Any]] = []
    
    # If we have routing info from previous step, execute modalities
    if routing_info and step > 0:
        inner = routing_info.get("routing_info", {})
        first_modality = inner.get("first_modality")
        parallel_modalities = inner.get("additional_parallel_modalities", [])
        
        # Combine all modalities to execute
        all_modalities = ([first_modality] if first_modality else []) + parallel_modalities
        
        # Execute all modalities in parallel
        logger.info(f"Executing {len(all_modalities)} modalities in parallel for step {step}")
        modality_results = await asyncio.gather(
            *[get_context_for_modality(modality) for modality in all_modalities if modality],
            return_exceptions=True,
        )
        
        # Add results to context_json
        for result in modality_results:
            if isinstance(result, Exception):
                logger.error(f"Modality execution error: {result}", exc_info=True)
                continue
            if result:
                context_json.append(result)
                logger.info(f"Added context from modality: {result.get('type', 'unknown')}")
    
    # Get system prompt based on step
    if step == 0:
        system_prompt = await PREAMBLE_SPEC_V7H_MODALITIES["step_0"]()
    else:
        system_prompt = await PREAMBLE_SPEC_V7H_MODALITIES["not_step_0"]()
    
    system_prompt_text = str(system_prompt)
    
    # Add context to system prompt if we have any
    # Format context in a way that's useful for the LLM
    if context_json:
        context_parts = []
        for ctx in context_json:
            ctx_type = ctx.get("type", "unknown")
            ctx_content = ctx.get("content", {})
            
            if ctx_type == "web_search":
                context_parts.append(f"## Web Search Results\nQuery: {ctx_content.get('search_query', 'N/A')}\nResults: {ctx_content.get('results', 'No results')}")
            elif ctx_type == "stock_price":
                context_parts.append(f"## Stock Price Data\nSymbol: {ctx_content.get('symbol', 'N/A')}\nPeriod: {ctx_content.get('period', 'N/A')}\nData: {ctx_content.get('result', 'No data')}")
            elif ctx_type == "macro_data":
                context_parts.append(f"## Macroeconomic Data\nMetric: {ctx_content.get('metric', 'N/A')}\nData: {ctx_content.get('result', 'No data')}")
            elif ctx_type == "finance_news":
                context_parts.append(f"## Finance News\nTopic: {ctx_content.get('topic', 'N/A')}\nArticles: {ctx_content.get('result', 'No articles')}")
            elif ctx_type == "self_knowledge":
                context_parts.append(f"## Self-Knowledge Documentation\n{ctx_content.get('result', 'No documentation')}")
        
        if context_parts:
            context_str = "\n\n".join(context_parts)
            system_prompt_text += f"\n\n---\n## Context from Previous Step\n\n{context_str}\n\n---\n"
            logger.info(f"Added {len(context_json)} context items to system prompt")
    
    return context_json, system_prompt_text


async def run_agentic_step(
    chat: ChatWithContext,
    message_chain: list[ChatMessage],
    step: int,
    routing_info: RoutingInfo | None,
    use_streaming: bool = True,
) -> AsyncGenerator[tuple[str, RoutingInfo | None, bool], None]:
    """
    Run a single agentic step.
    
    Args:
        chat: The chat object
        message_chain: Current message chain
        step: Current step number
        routing_info: Routing info from previous step (if any)
        use_streaming: Whether to stream responses
    
    Yields:
        Tuples of (event_data, new_routing_info, is_done)
        - event_data: JSON string for SSE event
        - new_routing_info: Routing info extracted from this step's response
        - is_done: Whether this is the final step
    """
    loop = asyncio.get_event_loop()
    
    # Construct context and system prompt
    context_json, system_prompt = await construct_context_and_system_prompt(
        chat=chat,
        message_chain=message_chain,
        step=step,
        routing_info=routing_info,
    )
    
    # Convert message chain to API format
    api_history = messages_to_api_format(message_chain)
    
    logger.info(f"Starting agentic step {step} (chat_id={chat.id}, history_length={len(api_history)})")
    
    # Stream LLM response
    accumulated_text = ""
    assistant_msg: ChatMessage | None = None
    parent_message = message_chain[-1] if message_chain else None
    
    async for response in stream_gemini(
        system_prompt=system_prompt,
        message_chain=api_history,
        model=DEFAULT_GEMINI_PRO_MODEL,
        tools=None,  # Using modalities, not tools
        llm_config=LLMConfig(),
    ):
        if response.text:
            accumulated_text += response.text
            is_thought = response.metadata.get("thought", False)
            event_type = "thought" if is_thought else "token"
            yield json.dumps({"text": response.text, "event": event_type}), None, False
    
    logger.info(f"Step {step} LLM stream completed. Text length: {len(accumulated_text)}")
    
    # Create assistant message
    if accumulated_text:
        assistant_msg = await loop.run_in_executor(
            None,
            lambda: create_assistant_message(
                chat=chat,
                content=accumulated_text,
                parent_message=parent_message,
                step_number=step,
            )
        )
    
    # Parse thinking blocks to extract routing info
    # This matches Little-Bird-Backend's parse_thinking_blocks logic
    new_routing_info: RoutingInfo | None = None
    is_modality_called = False
    is_tool_called = False  # We don't use tools in this agent, but keeping for consistency
    
    if accumulated_text and assistant_msg:
        # Parse thinking blocks from the message
        routing_info, error = await loop.run_in_executor(
            None,
            lambda: parse_thinking_blocks_from_message(assistant_msg.content)
        )
        
        if error:
            logger.warning(f"Error parsing thinking blocks: {error}")
        
        if routing_info:
            new_routing_info = routing_info
            is_modality_called = True
            
            # Extract and yield modalities info
            modalities = extract_modalities(routing_info)
            if modalities:
                modalities_str = json.dumps(modalities)
                yield json.dumps({"modalities": modalities_str, "event": "progress_message"}), new_routing_info, False
                logger.info(f"Step {step}: Modalities called: {[m.get('type') for m in modalities]}")
        else:
            # No modality called
            is_modality_called = False
            logger.info(f"Step {step}: No modality called")
    else:
        # No text response - this shouldn't happen but handle gracefully
        logger.warning(f"Step {step}: No text response received")
        is_modality_called = False
    
    # Handle max steps or manual interrupt (similar to Little-Bird-Backend line 1609)
    if step >= MAX_AGENTIC_STEPS - 1:
        is_modality_called = False  # Force completion
        logger.info(f"Step {step}: Max steps reached ({MAX_AGENTIC_STEPS})")
    
    # Insert between-step message if modality was called (matches Little-Bird-Backend line 1616-1617)
    if is_modality_called and assistant_msg:
        between_msg = await loop.run_in_executor(
            None,
            lambda: append_between_step_message(chat, new_routing_info, assistant_msg)
        )
        logger.info(f"Step {step}: Inserted between-step message, continuing to step {step + 1}")
    
    # Determine event type (matches Little-Bird-Backend line 1635-1645)
    if is_modality_called or is_tool_called:
        # Continue to next step
        event = "finish_one_assistant_message"
        is_done = False
    else:
        # Done - no more modalities or tools
        event = "done"
        is_done = True
        # Mark chat as finished
        chat.finished = True
        try:
            await chat.asave()
        except AttributeError:
            await loop.run_in_executor(None, lambda: chat.save())
    
    logger.info(f"Step {step}: Sending event={event}, is_modality_called={is_modality_called}, is_done={is_done}")
    
    yield json.dumps({"event": event, "chat_id": str(chat.id)}), new_routing_info, is_done


async def handle_chat_request(
    chat: ChatWithContext,
    question: str,
    file_ids: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Handle chat request with multi-step agentic loop.
    
    This is the main entry point that manages the agentic loop.
    Pattern copied from Little-Bird-Backend's handle_chat_v4_request.
    """
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
    
    # Start agentic loop
    routing_info: RoutingInfo | None = None
    
    for step in range(MAX_AGENTIC_STEPS):
        logger.info(f"Starting agentic step {step} (chat_id={chat.id})")
        
        # Update message chain for this step (includes any between-step messages)
        message_chain = await loop.run_in_executor(
            None,
            lambda: chat.get_message_chain() if hasattr(chat, 'get_message_chain') else []
        )
        
        async for event_data, new_routing_info, is_done in run_agentic_step(
            chat=chat,
            message_chain=message_chain,
            step=step,
            routing_info=routing_info,
        ):
            yield f"data: {event_data}\n\n"
            
            # Check if event is "done" (matches Little-Bird-Backend line 1440-1442)
            try:
                event_dict = json.loads(event_data)
                if event_dict.get("event") == "done":
                    logger.info(f"Got done event, returning", final_step=step)
                    return
            except (json.JSONDecodeError, KeyError):
                # If parsing fails, fall back to is_done flag
                if is_done:
                    logger.info(f"Agentic loop completed at step {step} (via is_done flag)")
                    return
            
            # Update routing_info for next iteration
            if new_routing_info:
                routing_info = new_routing_info
    
    # Max steps reached - mark as done
    logger.warning(f"Max agentic steps ({MAX_AGENTIC_STEPS}) reached")
    chat.finished = True
    try:
        await chat.asave()
    except AttributeError:
        await loop.run_in_executor(None, lambda: chat.save())
    
    yield f"data: {json.dumps({'event': 'done', 'chat_id': str(chat.id)})}\n\n"


@router.post("/query-agentic")
async def query_agentic(request: QueryRequest):
    """Multi-step agentic chat endpoint with modality support.
    
    Returns streaming response with chat_id in the final 'done' event.
    """
    try:
        # Get or create chat
        chat = await get_or_create_chat(request.chat_id)
        
        # Return streaming response
        return StreamingResponse(
            handle_chat_request(chat, request.question, request.file_ids),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        logger.error(f"Error in /api/query-agentic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})

