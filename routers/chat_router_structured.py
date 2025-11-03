"""Chat router with structured outputs support for v7h_structured agent."""
import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db.models import ChatWithContext
from features.tool_calling.logic import call_tool
from llm.call_gemini import DEFAULT_GEMINI_PRO_MODEL, call_gemini_raw, stream_gemini
from llm.domain.enums import AIModelsProvider, ChatDataType, ChatRole
from llm.domain.models import ToolResult
from llm.prompts.system_prompt_base.preamble_self_route_v7h_structured import (
    PREAMBLE_SPEC_V7H_STRUCTURED,
    get_agent_response_schema,
)
from llm.prompts.system_prompt_base.structured_response_parser import (
    StructuredAgentResponse,
    extract_structured_response_from_gemini,
    parse_structured_response,
)
from llm.types import LLMConfig
from llm.helpers import format_chat_history_for_gemini_api
from utils.logging import logger

router = APIRouter(prefix="/api")


class QueryRequest(BaseModel):
    """Request model for /api/query endpoint."""
    question: str
    chat_id: str | None = None


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


def parse_chat_history_from_string(chat_history_str: str) -> list[list[str]]:
    """Parse chat history from JSON string."""
    try:
        return json.loads(chat_history_str)
    except (json.JSONDecodeError, TypeError):
        return []


def format_chat_history_for_saving(chat_history: list[list[str]]) -> str:
    """Format chat history as JSON string for saving to DB."""
    return json.dumps(chat_history)


async def execute_modalities(modalities: list[dict[str, Any]], chat_history: list[list[str]]) -> None:
    """Execute modalities and add results to chat history."""
    if not modalities:
        return
    
    tool_results = []
    for modality in modalities:
        try:
            modality_type = modality.get("type")
            if not modality_type:
                continue
            
            # Map modality type to tool name
            tool_name = modality_type
            
            # Extract parameters based on modality type
            args = {}
            if modality_type == "chat_with_web_search":
                args["search_query"] = modality.get("search_query", "")
            elif modality_type == "get_stock_price":
                args["symbol"] = modality.get("symbol", "")
                args["period"] = modality.get("period", "1d")
            elif modality_type == "get_macro_data":
                args["metric"] = modality.get("metric", "")
            elif modality_type == "get_finance_news":
                args["topic"] = modality.get("topic", "")
            elif modality_type == "self_knowledge":
                args = {}
            
            logger.info(f"Executing modality: {tool_name} with args: {args}")
            result = await call_tool(tool_name, args)
            
            tool_results.append({
                "tool_name": tool_name,
                "result": result,
            })
            
        except Exception as e:
            logger.error(f"Error executing modality {modality.get('type')}: {e}", exc_info=True)
            tool_results.append({
                "tool_name": modality.get("type", "unknown"),
                "result": f"Error: {e}",
            })
    
    # Add tool results to chat history
    if tool_results:
        chat_history.append([ChatRole.TOOL.value])
        for tool_result in tool_results:
            tool_result_obj = ToolResult(
                tool_id=None,
                result=tool_result["result"],
                func_name=tool_result["tool_name"],
            )
            chat_history[-1].append(f"{ChatDataType.TOOL_RESULT}:{tool_result_obj.model_dump_json()}")


async def process_chat_stream_structured(
    chat: ChatWithContext, question: str
) -> AsyncGenerator[str, None]:
    """Process chat request with structured outputs and stream responses."""
    # Get or parse chat history
    chat_history = parse_chat_history_from_string(chat.chat_history)
    
    # Add user message
    chat_history.append([ChatRole.USER.value, f"{ChatDataType.TEXT}:{question}"])
    
    # Determine if this is step 0
    is_step_0 = len(chat_history) <= 1
    
    # Get system prompt
    preamble_func = PREAMBLE_SPEC_V7H_STRUCTURED["step_0" if is_step_0 else "not_step_0"]
    system_prompt = await preamble_func()
    
    # Get response schema
    response_schema = get_agent_response_schema()
    
    # Create LLM config with structured outputs
    llm_config = LLMConfig(
        response_schema=response_schema,
        response_mime_type="application/json",
    )
    
    max_iterations = 10  # Prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        logger.info(
            f"Starting LLM call iteration {iteration} (chat_id={chat.id}, history_length={len(chat_history)})"
        )
        
        # Call Gemini with structured outputs
        try:
            messages = await format_chat_history_for_gemini_api(chat_history)
            response = await call_gemini_raw(
                system_prompt=str(system_prompt),
                messages=messages,
                model=DEFAULT_GEMINI_PRO_MODEL,
                tools=None,  # No function calling, using structured outputs
                llm_config=llm_config,
            )
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
            break
        
        # Parse structured response
        structured_response = extract_structured_response_from_gemini(response)
        if not structured_response:
            logger.error("Failed to extract structured response from Gemini")
            yield f"data: {json.dumps({'event': 'error', 'message': 'Failed to parse structured response'})}\n\n"
            break
        
        # Stream user-facing text
        if structured_response.user_facing_text:
            # Yield text in chunks for streaming effect
            text_chunks = structured_response.user_facing_text.split(" ")
            for chunk in text_chunks:
                yield f"data: {json.dumps({'text': chunk + ' ', 'event': 'token'})}\n\n"
            
            # Add assistant response to chat history
            chat_history.append([
                ChatRole.ASSISTANT.value,
                f"{ChatDataType.TEXT}:{structured_response.user_facing_text}"
            ])
        
        # Check if final
        if structured_response.is_final:
            logger.info("Agent marked response as final")
            break
        
        # Check if agent asked questions
        if structured_response.questions_count > 0:
            logger.info(f"Agent asked {structured_response.questions_count} question(s), stopping")
            break
        
        # Execute modalities if continuing
        if structured_response.is_continuing:
            modalities = structured_response.to_modalities_list()
            if modalities:
                logger.info(f"Executing {len(modalities)} modality(ies) in iteration {iteration}")
                yield f"data: {json.dumps({'event': 'modality_execution_start', 'count': len(modalities)})}\n\n"
                
                await execute_modalities(modalities, chat_history)
                
                yield f"data: {json.dumps({'event': 'modality_execution_complete', 'count': len(modalities)})}\n\n"
                
                # Update system prompt (not step_0 anymore)
                system_prompt = await PREAMBLE_SPEC_V7H_STRUCTURED["not_step_0"]()
            else:
                logger.warning("Agent marked as continuing but no modalities specified")
                break
        else:
            logger.info("Agent not continuing, ending conversation")
            break
    
    # Save updated chat history
    chat.chat_history = format_chat_history_for_saving(chat_history)
    chat.finished = True
    
    import asyncio
    try:
        await chat.asave()
    except AttributeError:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: chat.save())
    
    # Send done event
    yield f"data: {json.dumps({'event': 'done', 'chat_id': str(chat.id)})}\n\n"


@router.post("/query-structured")
async def query_structured(request: QueryRequest):
    """Chat endpoint with structured outputs support.
    
    Returns streaming response with chat_id in the final 'done' event.
    Uses structured outputs from Gemini instead of parsing JSON from text.
    """
    try:
        # Get or create chat
        chat = await get_or_create_chat(request.chat_id)
        
        # Return streaming response
        return StreamingResponse(
            process_chat_stream_structured(chat, request.question),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        logger.error(f"Error in /api/query-structured: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})

