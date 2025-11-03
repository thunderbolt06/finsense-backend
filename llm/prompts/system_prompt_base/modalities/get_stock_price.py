"""Stock price modality template."""
from llm.prompts.prompt_template import PromptTemplate

get_stock_price_template = PromptTemplate(
    name="get_stock_price",
    template="""\
Get stock price data and historical information for a given stock symbol:
{{
  "type": "get_stock_price",
  "symbol": "Stock ticker symbol (e.g., AAPL, GOOGL, MSFT, TSLA)",
  "period": "Time period for historical data. Options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"
}}

Returns current price, period high/low, volume, and price history.
Use this to answer questions about stock prices, market performance, or stock valuations.
""",
)

