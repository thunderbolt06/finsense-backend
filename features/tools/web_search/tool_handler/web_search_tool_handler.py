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
    from utils.logging import logger
    
    logger.info(
        f"Performing web search: query={search_query}"
    )
    
    result = await get_web_search_context(search_query)
    
    # Extract just the results part
    if "results" in result:
        result_count = len(result.get("results", []))
        sample_results = [r.get("title", "")[:100] for r in result.get("results", [])[:3]]
        logger.info(
            f"Web search completed successfully: {search_query} (results={result_count}, samples={sample_results})"
        )
        return json.dumps(result, indent=2)
    else:
        # Error case
        error_msg = result.get("error", "Unknown error")
        logger.error(
            f"Web search failed: {search_query} (error={error_msg})"
        )
        return json.dumps({"error": error_msg, "search_query": search_query}, indent=2)

