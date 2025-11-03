"""Tool calling logic - simplified version."""
from typing import Any

from features.tool_calling.tool_translators import format_tool_definition_for_gemini_api
from features.tools.web_search.tool_def.web_search_tool_def import WEB_SEARCH_TOOL
from features.tools.web_search.tool_handler.web_search_tool_handler import chat_with_web_search
from llm.domain.enums import AIModelsProvider
from utils.logging import logger


# Tool definitions
TOOL_DEFINITIONS = [
    WEB_SEARCH_TOOL,
]

TOOL_FUNCTIONS_DICT = {
    "chat_with_web_search": chat_with_web_search,
}

# Format tools for Gemini
CORE_TOOLS_DICT: dict[str, Any] = {}

for tool in TOOL_DEFINITIONS:
    tool.provider_format[AIModelsProvider.GEMINI] = format_tool_definition_for_gemini_api(tool)
    CORE_TOOLS_DICT[tool.name] = tool


async def call_tool(tool_name: str | None, args: dict) -> str:
    """Call a tool by name with the provided arguments."""
    try:
        # Remove 'user' and 'agent_config' from args if present (not needed for simplified version)
        args_clean = {k: v for k, v in args.items() if k not in ["user", "agent_config"]}
        return str(await TOOL_FUNCTIONS_DICT[tool_name](**args_clean))  # type: ignore
    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {e}")
        return f"An error happened when calling the tool {tool_name}, the error is:\n{type(e).__name__}: {e}"

