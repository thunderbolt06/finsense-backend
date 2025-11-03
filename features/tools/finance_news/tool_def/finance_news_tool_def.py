"""Finance news tool definition."""
from llm.domain.enums import ToolPropertyType
from llm.domain.models import ToolDefinition, ToolParameter

GET_FINANCE_NEWS_DESCRIPTION = """\
Get recent finance news articles about a specific topic.

Searches finance RSS feeds for articles matching the topic keyword.
Returns article titles, links, publication dates, and summaries.
Use this to find current finance news, market updates, or financial analysis.
"""

FINANCE_NEWS_TOOL = ToolDefinition(
    description=GET_FINANCE_NEWS_DESCRIPTION,
    name="get_finance_news",
    parameters={
        "topic": ToolParameter(
            description="Topic or keyword to search for in finance news (e.g., 'stock market', 'Federal Reserve', 'inflation', 'AAPL')",
            type=ToolPropertyType.STRING,
            is_required=True,
        ),
    },
)


