"""Simplified web search core - only SerpAPI."""
import asyncio

from llm.tools.web_search.providers.serpapi import get_web_search_context_with_serpapi
from utils.logging import logger


async def get_web_search_context(search_query: str) -> dict:
    """Get web search context for a query - simplified version (SerpAPI only, no user).

    Args:
        search_query: The search query to execute

    Returns:
        Dictionary with search results
    """
    try:
        result = await asyncio.wait_for(
            get_web_search_context_with_serpapi(search_query), 
            timeout=20
        )
        return {
            "type": "list_response_with_search_query",
            "search_query": search_query,
            "results": result["results"],
        }
    except Exception as e:
        logger.error(f"Error in web search: {e}")
        return {
            "type": "failed_web_search_response",
            "search_query": search_query,
            "error": str(e),
        }

