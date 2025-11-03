"""Tool calling logic - simplified version."""
from typing import Any

from features.tool_calling.tool_translators import format_tool_definition_for_gemini_api
from features.tools.finance_news.tool_def.finance_news_tool_def import FINANCE_NEWS_TOOL
from features.tools.finance_news.tool_handler.finance_news_tool_handler import get_finance_news
from features.tools.macro_data.tool_def.macro_data_tool_def import MACRO_DATA_TOOL
from features.tools.macro_data.tool_handler.macro_data_tool_handler import get_macro_data
from features.tools.self_knowledge.tool_def.self_knowledge_tool_def import SELF_KNOWLEDGE_TOOL
from features.tools.self_knowledge.tool_handler.self_knowledge_tool_handler import self_knowledge
from features.tools.stock_price.tool_def.stock_price_tool_def import STOCK_PRICE_TOOL
from features.tools.stock_price.tool_handler.stock_price_tool_handler import get_stock_price
from features.tools.web_search.tool_def.web_search_tool_def import WEB_SEARCH_TOOL
from features.tools.web_search.tool_handler.web_search_tool_handler import chat_with_web_search
from llm.domain.enums import AIModelsProvider
from utils.logging import logger


# Tool definitions
TOOL_DEFINITIONS = [
    WEB_SEARCH_TOOL,
    STOCK_PRICE_TOOL,
    MACRO_DATA_TOOL,
    FINANCE_NEWS_TOOL,
    SELF_KNOWLEDGE_TOOL,
]

TOOL_FUNCTIONS_DICT = {
    "chat_with_web_search": chat_with_web_search,
    "get_stock_price": get_stock_price,
    "get_macro_data": get_macro_data,
    "get_finance_news": get_finance_news,
    "self_knowledge": self_knowledge,
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
        
        # Log tool call initiation
        logger.info(
            f"Tool call initiated: {tool_name} (args={args_clean})"
        )
        
        # Call the tool
        result = str(await TOOL_FUNCTIONS_DICT[tool_name](**args_clean))  # type: ignore
        
        # Log successful tool call with response summary
        result_preview = result[:500] if len(result) > 500 else result
        logger.info(
            f"Tool call completed: {tool_name} (args={args_clean}, result_length={len(result)}, preview={result_preview[:200]}...)"
        )
        
        return result
        
    except Exception as e:
        args_repr = args_clean if 'args_clean' in locals() else args
        logger.error(
            f"Error calling tool {tool_name} (args={args_repr}): {e}",
            exc_info=True,
        )
        return f"An error happened when calling the tool {tool_name}, the error is:\n{type(e).__name__}: {e}"

