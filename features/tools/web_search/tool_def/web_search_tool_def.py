"""Web search tool definition."""
from llm.domain.enums import ToolPropertyType
from llm.domain.models import ToolDefinition, ToolParameter

CHAT_WITH_WEB_SEARCH_DESCRIPTION = """\
Search the web for current information.

IMPORTANT: When using chat_with_web_search, always provide links to sources! For example: "This [Medium article](https://medium.com/@user/article-title) says..."
IMPORTANT: If you are asked about recent/current events, they may be outside of your knowledge cutoff date, so do a search. 
IMPORTANT: If you are asked about current state of affairs then it's DEFINITELY outside your knowledge cutoff, so DEFINITELY do a search! 

Examples:
- "Who is the current <blank>?" - MUST search (something could have happened since your knowledge cutoff date)
- "Who was the first ruler of ancient <blank>?" - MUST NOT search (nothing could have happened since your knowledge cutoff date)
- "What is now the tallest <blank> in the world?" - "As of my last update, the tallest <blank> is <blank>, but let me double-check with a web search in case something changed"
- "Who is the CEO of <blank>?" - MUST search (something could have happened since your knowledge cutoff date)\
"""

WEB_SEARCH_TOOL = ToolDefinition(
    description=CHAT_WITH_WEB_SEARCH_DESCRIPTION,
    name="chat_with_web_search",
    parameters={
        "search_query": ToolParameter(
            description="A single, concise query",
            type=ToolPropertyType.STRING,
            is_required=True,
        ),
    },
)

