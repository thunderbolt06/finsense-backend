"""
Simplified helpers for LLM integration.
Only includes format_chat_history_for_gemini_api.
"""
import json

from google.genai import types

from llm.domain.enums import ChatDataType, CHAT_DATA_TYPES_EXCLUDE_FROM_LLM_APIS, CHAT_DATA_TYPES_FOR_LLM_APIS
from llm.domain.models import ToolData, ToolResult
from utils.logging import logger

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
        message_blocks = message[1:]

        current_turn_parts: list[types.Part] = []
        tool_results: list[types.Content] = []
        tool_calls: list[types.Part] = []

        # Handle tool role messages (tool results)
        if role_str == "tool":
            for block in message_blocks:
                if ":" not in block:
                    continue
                data_type, data = block.split(":", 1)
                
                if data_type == ChatDataType.TOOL_RESULT:
                    try:
                        result = ToolResult.model_validate_json(data)
                        # Parse the result string - tool handlers return JSON strings
                        parsed_result = None
                        result_str = result.result if result.result else ""
                        
                        try:
                            # Try to parse as JSON
                            if result_str.strip().startswith("{") or result_str.strip().startswith("["):
                                parsed_result = json.loads(result_str)
                            else:
                                # Not JSON, keep as string but wrap in dict
                                parsed_result = {"result": result_str}
                        except (json.JSONDecodeError, ValueError, AttributeError) as parse_error:
                            # If parsing fails, wrap the string in a dict
                            logger.debug(f"Could not parse tool result as JSON, using as string: {parse_error}")
                            parsed_result = {"result": result_str}
                        
                        # Ensure parsed_result is a dict (Gemini expects dict/object for function responses)
                        if not isinstance(parsed_result, dict):
                            parsed_result = {"result": parsed_result}
                        
                        # Create a separate Content for each tool result
                        # Gemini expects the response to match the function call by name
                        tool_results.append(
                            types.Content(
                                role="tool",
                                parts=[
                                    types.Part.from_function_response(
                                        name=result.func_name or "unknown_function",
                                        response=parsed_result
                                    )
                                ],
                            )
                        )
                        logger.debug(f"Formatted tool result for {result.func_name}: {list(parsed_result.keys())[:3]}...")
                    except Exception as e:
                        # Skip invalid tool results but log the error
                        logger.error(f"Error parsing tool result: {e}", exc_info=True)
                        continue
            
            # Add all tool results for this message
            if tool_results:
                gemini_contents.extend(tool_results)
            continue  # Move to next message

        # Handle user/assistant messages
        role = "model" if role_str == "assistant" else "user"

        for block in message_blocks:
            if ":" not in block:
                continue
            data_type, data = block.split(":", 1)
            
            if data_type in CHAT_DATA_TYPES_EXCLUDE_FROM_LLM_APIS:
                pass  # Ignore add-on items like "sources:", "agent:", etc.
            elif data_type == ChatDataType.TEXT:
                current_turn_parts.append(types.Part.from_text(text=data or EMPTY_MESSAGE_PLACEHOLDER))
            elif data_type == ChatDataType.TOOL_USE:
                try:
                    tool_data = ToolData.model_validate_json(data)
                    tool_calls.append(
                        types.Part.from_function_call(
                            name=tool_data.func_name or "", 
                            args=json.loads(tool_data.func_args) if tool_data.func_args else {}
                        )
                    )
                except Exception as e:
                    # Skip invalid tool data
                    continue
            # Note: TOOL_RESULT is handled above for "tool" role messages

        # Add tool calls (if any) - these come from assistant messages
        if tool_calls:
            gemini_contents.append(types.Content(role=role, parts=tool_calls))
        # Otherwise add text parts
        elif current_turn_parts:
            gemini_contents.append(types.Content(role=role, parts=current_turn_parts))

    return gemini_contents

