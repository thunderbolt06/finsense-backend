"""Stock price tool definition."""
from llm.domain.enums import ToolPropertyType
from llm.domain.models import ToolDefinition, ToolParameter

GET_STOCK_PRICE_DESCRIPTION = """\
Get stock price data and historical information for a given stock symbol.

Period options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

Returns current price, period high/low, volume, and price history.
Use this to answer questions about stock prices, market performance, or stock valuations.
"""

STOCK_PRICE_TOOL = ToolDefinition(
    description=GET_STOCK_PRICE_DESCRIPTION,
    name="get_stock_price",
    parameters={
        "symbol": ToolParameter(
            description="Stock ticker symbol (e.g., AAPL, GOOGL, MSFT, TSLA)",
            type=ToolPropertyType.STRING,
            is_required=True,
        ),
        "period": ToolParameter(
            description="Time period for historical data. Options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max",
            type=ToolPropertyType.STRING,
            is_required=True,
        ),
    },
)


