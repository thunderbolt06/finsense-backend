"""Web search tool handler - simplified version (no user)."""
import json

from llm.tools.web_search.web_search_core import get_web_search_context


async def chat_with_web_search(search_query: str) -> str:
    """Perform a web search and return formatted results.

    Args:
        search_query: The search query to execute

    Returns:
        JSON string containing search results with sources
    """
    result = await get_web_search_context(search_query)
    
    # Extract just the results part
    if "results" in result:
        return json.dumps(result, indent=2)
    else:
        # Error case
        return json.dumps({"error": result.get("error", "Unknown error"), "search_query": search_query}, indent=2)

