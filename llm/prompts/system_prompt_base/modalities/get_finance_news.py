"""Finance news modality template."""
from llm.prompts.prompt_template import PromptTemplate

get_finance_news_template = PromptTemplate(
    name="get_finance_news",
    template="""\
Get recent finance news articles about a specific topic:
{{
  "type": "get_finance_news",
  "topic": "Topic or keyword to search for in finance news (e.g., 'stock market', 'Federal Reserve', 'inflation', 'AAPL')"
}}

Searches finance RSS feeds for articles matching the topic keyword.
Returns article titles, links, publication dates, and summaries.
Use this to find current finance news, market updates, or financial analysis.
""",
)

