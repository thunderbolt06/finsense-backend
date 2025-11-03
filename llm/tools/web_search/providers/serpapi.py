"""SerpAPI web search provider - simplified version."""
from typing import TypedDict

from finsense.settings import settings
from utils.http_client import get_async_client
from utils.logging import logger


class WebResponse(TypedDict):
    """Web search response."""
    results: list[dict[str, str]]


async def _call_serpapi(search_query: str, engine: str = "google_light") -> dict:
    """Call SerpAPI with the given search query."""
    params = {
        "engine": engine,
        "q": search_query,
        "hl": "en",
        "gl": "us",
        "api_key": settings.SERPAPI_API_KEY,
    }

    async with get_async_client() as client:
        response = await client.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        return await response.json()


async def get_web_search_context_with_serpapi(search_query: str, engine: str = "google_light") -> WebResponse:
    """Get web search results using SerpAPI."""
    try:
        data = await _call_serpapi(search_query, engine)
        organic_results = data.get("organic_results", [])

        results: WebResponse = {
            "results": [
                {"title": result.get("title", ""), "url": result.get("link", ""), "content": result.get("snippet", "")}
                for result in organic_results
            ]
        }

        return results

    except Exception as e:
        logger.error(f"Error calling SerpAPI: {e}", exc_info=True)
        raise RuntimeError(f"Failed to get response from SerpAPI: {str(e)}") from e

