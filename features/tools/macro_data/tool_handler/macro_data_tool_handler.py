"""Macro economic data tool handler with FRED API support."""
import json
from datetime import datetime, timedelta

from finsense.settings import settings
from utils.logging import logger

# Mock data for common metrics (used when FRED_API_KEY is not set)
MOCK_MACRO_DATA = {
    "CPI": {
        "latest_value": 305.0,
        "unit": "Index 1982-84=100",
        "description": "Consumer Price Index for All Urban Consumers: All Items",
        "latest_date": "2025-01",
    },
    "CPIAUCSL": {
        "latest_value": 305.0,
        "unit": "Index 1982-84=100",
        "description": "Consumer Price Index for All Urban Consumers: All Items",
        "latest_date": "2025-01",
    },
    "GDP": {
        "latest_value": 28.5,
        "unit": "Billions of Dollars",
        "description": "Gross Domestic Product",
        "latest_date": "2025-Q1",
    },
    "FEDFUNDS": {
        "latest_value": 5.25,
        "unit": "Percent",
        "description": "Effective Federal Funds Rate",
        "latest_date": "2025-01",
    },
    "UNRATE": {
        "latest_value": 3.7,
        "unit": "Percent",
        "description": "Unemployment Rate",
        "latest_date": "2025-01",
    },
}


async def get_macro_data(metric: str) -> str:
    """Get macroeconomic data for a given metric.

    Args:
        metric: Economic metric name (e.g., CPI, GDP, FEDFUNDS, UNRATE)

    Returns:
        JSON string with macroeconomic data
    """
    logger.info(
        f"Fetching macro economic data: metric={metric}"
    )
    
    try:
        # Check if FRED API key is set
        if settings.FRED_API_KEY:
            logger.info(
                f"Using FRED API for metric {metric}"
            )
            try:
                from fredapi import Fred
                
                fred = Fred(api_key=settings.FRED_API_KEY)
                
                # Get the series data
                data = fred.get_series(metric, observation_start=(datetime.now() - timedelta(days=365*2)).strftime("%Y-%m-%d"))
                
                if data.empty:
                    logger.warning(
                        f"Metric '{metric}' not found in FRED database"
                    )
                    return json.dumps({
                        "error": f"Metric '{metric}' not found in FRED database",
                        "metric": metric,
                        "hint": "Try common metrics: CPI, GDP, FEDFUNDS, UNRATE",
                    }, indent=2)
                
                latest_value = float(data.iloc[-1])
                latest_date = data.index[-1].strftime("%Y-%m-%d")
                
                # Get series info
                try:
                    series_info = fred.get_series_info(metric)
                    description = series_info.get("title", "Economic Indicator")
                    unit = series_info.get("units", "")
                except Exception:
                    description = f"{metric} Economic Indicator"
                    unit = ""
                
                # Get recent data points (last 12 months)
                recent_data = []
                for idx, value in data.tail(12).items():
                    recent_data.append({
                        "date": idx.strftime("%Y-%m-%d"),
                        "value": round(float(value), 2),
                    })
                
                result = {
                    "metric": metric,
                    "latest_value": round(latest_value, 2),
                    "latest_date": latest_date,
                    "unit": unit,
                    "description": description,
                    "source": "FRED (Federal Reserve Economic Data)",
                    "recent_data": recent_data,
                }
                
                logger.info(
                    f"Macro data retrieved from FRED API: {metric} (value={result['latest_value']}, date={result['latest_date']}, points={len(recent_data)})"
                )
                
                return json.dumps(result, indent=2)
                
            except ImportError:
                logger.warning(
                    f"fredapi not installed, falling back to mock data for metric {metric}"
                )
            except Exception as e:
                logger.error(
                    f"Error fetching from FRED API for metric {metric}: {e}",
                    exc_info=True,
                )
                return json.dumps({
                    "error": f"FRED API error: {str(e)}",
                    "metric": metric,
                    "note": "Falling back to mock data",
                }, indent=2)
        
        # Use mock data if FRED_API_KEY is not set or API fails
        metric_upper = metric.upper()
        logger.info(
            f"Using mock data for {metric_upper} (FRED_API_KEY not set or API failed)"
        )
        
        if metric_upper in MOCK_MACRO_DATA:
            mock = MOCK_MACRO_DATA[metric_upper]
            result = {
                "metric": metric,
                "latest_value": mock["latest_value"],
                "latest_date": mock["latest_date"],
                "unit": mock["unit"],
                "description": mock["description"],
                "source": "Mock Data (placeholder)",
                "note": "Set FRED_API_KEY environment variable for real data from FRED",
                "recent_data": [
                    {"date": mock["latest_date"], "value": mock["latest_value"]},
                ],
            }
            
            logger.info(
                f"Macro data retrieved (mock): {metric} (value={result['latest_value']}, date={result['latest_date']})"
            )
            
            return json.dumps(result, indent=2)
        else:
            logger.warning(
                f"Metric '{metric}' not found in mock data. Available: {list(MOCK_MACRO_DATA.keys())}"
            )
            return json.dumps({
                "error": f"Metric '{metric}' not found. Available mock metrics: {', '.join(MOCK_MACRO_DATA.keys())}",
                "metric": metric,
                "note": "Set FRED_API_KEY for access to all FRED metrics",
            }, indent=2)
            
    except Exception as e:
        logger.error(
            f"Error fetching macro data for {metric}: {e}",
            exc_info=True,
        )
        return json.dumps({
            "error": str(e),
            "metric": metric,
        }, indent=2)

