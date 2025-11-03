"""
Simplified helpers for LLM integration.
Only includes format_chat_history_for_gemini_api.
"""
import json

from google.genai import types

from llm.domain.enums import ChatDataType, CHAT_DATA_TYPES_EXCLUDE_FROM_LLM_APIS, CHAT_DATA_TYPES_FOR_LLM_APIS
from llm.domain.models import ToolData, ToolResult

EMPTY_MESSAGE_PLACEHOLDER = "<empty message>"


async def format_chat_history_for_gemini_api(chat_history: list[list[str]]) -> list[types.ContentUnion]:
    """Format the chat history for the Gemini API.

    Args:
        chat_history: Lists with prefixes (e.g. "text:..." or "tool_use:...").

    Returns:
        The formatted chat history suitable for the Gemini API.
    """
    gemini_contents: list[types.ContentUnion] = []

    for message in chat_history:
        # First element is role (user, assistant, tool)
        if not message:
            continue
            
        role_str = message[0]
        role = "model" if role_str == "assistant" else "user"
        message_blocks = message[1:]

        current_turn_parts: list[types.Part] = []
        tool_results: list[types.Content] = []
        tool_calls: list[types.Part] = []

        for block in message_blocks:
            if ":" not in block:
                continue
            data_type, data = block.split(":", 1)
            
            if data_type in CHAT_DATA_TYPES_EXCLUDE_FROM_LLM_APIS:
                pass  # Ignore add-on items like "sources:", "agent:", etc.
            elif data_type == ChatDataType.TEXT:
                current_turn_parts.append(types.Part.from_text(text=data or EMPTY_MESSAGE_PLACEHOLDER))
            elif data_type == ChatDataType.TOOL_USE:
                tool_data = ToolData.model_validate_json(data)
                tool_calls.append(
                    types.Part.from_function_call(
                        name=tool_data.func_name or "", 
                        args=json.loads(tool_data.func_args) if tool_data.func_args else {}
                    )
                )
            elif data_type == ChatDataType.TOOL_RESULT:
                result = ToolResult.model_validate_json(data)
                tool_results.append(
                    types.Content(
                        role="tool",
                        parts=[
                            types.Part.from_function_response(
                                name=result.func_name or "unknown_function", 
                                response={"result": result.result}
                            )
                        ],
                    )
                )
            else:
                # Unknown type - skip it
                continue

        # Add tool results first (if any)
        if tool_results:
            gemini_contents.extend(tool_results)
        # Then add tool calls (if any)
        elif tool_calls:
            gemini_contents.append(types.Content(role=role, parts=tool_calls))
        # Otherwise add text parts
        elif current_turn_parts:
            gemini_contents.append(types.Content(role=role, parts=current_turn_parts))

    return gemini_contents

