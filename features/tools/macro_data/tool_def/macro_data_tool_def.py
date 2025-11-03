"""Macro economic data tool definition."""
from llm.domain.enums import ToolPropertyType
from llm.domain.models import ToolDefinition, ToolParameter

GET_MACRO_DATA_DESCRIPTION = """\
Get macroeconomic data for economic indicators.

Common metrics:
- CPI or CPIAUCSL: Consumer Price Index
- GDP: Gross Domestic Product
- FEDFUNDS: Federal Funds Rate
- UNRATE: Unemployment Rate

Returns the latest value and historical data points.
Set FRED_API_KEY environment variable for real data from Federal Reserve Economic Data (FRED).
If not set, returns mock placeholder data.
"""

MACRO_DATA_TOOL = ToolDefinition(
    description=GET_MACRO_DATA_DESCRIPTION,
    name="get_macro_data",
    parameters={
        "metric": ToolParameter(
            description="Economic metric name (e.g., CPI, GDP, FEDFUNDS, UNRATE, CPIAUCSL)",
            type=ToolPropertyType.STRING,
            is_required=True,
        ),
    },
)


