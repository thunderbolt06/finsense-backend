"""Macro economic data modality template."""
from llm.prompts.prompt_template import PromptTemplate

get_macro_data_template = PromptTemplate(
    name="get_macro_data",
    template="""\
Get macroeconomic data for economic indicators:
{{
  "type": "get_macro_data",
  "metric": "Economic metric name (e.g., CPI, GDP, FEDFUNDS, UNRATE, CPIAUCSL)"
}}

Common metrics:
- CPI or CPIAUCSL: Consumer Price Index
- GDP: Gross Domestic Product
- FEDFUNDS: Federal Funds Rate
- UNRATE: Unemployment Rate

Returns the latest value and historical data points.
Use this to answer questions about economic indicators, inflation, interest rates, or macroeconomic trends.
""",
)

