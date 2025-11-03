"""Helper functions for executing modalities."""
from typing import Any

from features.tool_calling.logic import call_tool
from utils.logging import logger


async def get_context_for_modality(
    modality: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute a modality and return its result.
    
    Maps modality types to tool names and executes them.
    Returns a context JSON object.
    """
    modality_type = modality.get("type")
    
    if modality_type == "chat_with_web_search":
        # Execute web search tool
        search_query = modality.get("search_query", "")
        try:
            result = await call_tool("chat_with_web_search", {"search_query": search_query})
            return {
                "type": "web_search",
                "content": {
                    "search_query": search_query,
                    "results": result,
                },
            }
        except Exception as e:
            logger.error(f"Error executing web search modality: {e}", exc_info=True)
            return {
                "type": "web_search",
                "content": {
                    "search_query": search_query,
                    "error": str(e),
                },
            }
    
    elif modality_type == "get_stock_price":
        symbol = modality.get("symbol", "")
        period = modality.get("period", "1d")
        try:
            result = await call_tool("get_stock_price", {"symbol": symbol, "period": period})
            return {
                "type": "stock_price",
                "content": {
                    "symbol": symbol,
                    "period": period,
                    "result": result,
                },
            }
        except Exception as e:
            logger.error(f"Error executing stock price modality: {e}", exc_info=True)
            return {
                "type": "stock_price",
                "content": {
                    "symbol": symbol,
                    "error": str(e),
                },
            }
    
    elif modality_type == "get_macro_data":
        metric = modality.get("metric", "")
        try:
            result = await call_tool("get_macro_data", {"metric": metric})
            return {
                "type": "macro_data",
                "content": {
                    "metric": metric,
                    "result": result,
                },
            }
        except Exception as e:
            logger.error(f"Error executing macro data modality: {e}", exc_info=True)
            return {
                "type": "macro_data",
                "content": {
                    "metric": metric,
                    "error": str(e),
                },
            }
    
    elif modality_type == "get_finance_news":
        topic = modality.get("topic", "")
        try:
            result = await call_tool("get_finance_news", {"topic": topic})
            return {
                "type": "finance_news",
                "content": {
                    "topic": topic,
                    "result": result,
                },
            }
        except Exception as e:
            logger.error(f"Error executing finance news modality: {e}", exc_info=True)
            return {
                "type": "finance_news",
                "content": {
                    "topic": topic,
                    "error": str(e),
                },
            }
    
    elif modality_type == "self_knowledge":
        try:
            result = await call_tool("self_knowledge", {})
            return {
                "type": "self_knowledge",
                "content": {
                    "result": result,
                },
            }
        except Exception as e:
            logger.error(f"Error executing self_knowledge modality: {e}", exc_info=True)
            return {
                "type": "self_knowledge",
                "content": {
                    "error": str(e),
                },
            }
    
    else:
        logger.warning(f"Unknown modality type: {modality_type}")
        return {
            "type": "unknown",
            "content": {
                "error": f"Unknown modality type: {modality_type}",
            },
        }

