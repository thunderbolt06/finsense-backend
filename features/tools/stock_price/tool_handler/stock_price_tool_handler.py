"""Stock price tool handler using yfinance."""
import json
from datetime import datetime

import yfinance as yf

from utils.logging import logger


async def get_stock_price(symbol: str, period: str = "1mo") -> str:
    """Get stock price data for a given symbol and period.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, GOOGL)
        period: Time period (e.g., 1d, 5d, 1mo, 3mo, 1y, max)

    Returns:
        JSON string with stock price data
    """
    logger.info(
        f"Fetching stock price data: symbol={symbol}, period={period}"
    )
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            logger.warning(
                f"No stock data found for symbol {symbol}, period={period}"
            )
            return json.dumps({
                "error": f"No data found for symbol {symbol}",
                "symbol": symbol,
                "period": period,
            }, indent=2)
        
        info = ticker.info
        
        # Get current price (last close or current price)
        current_price = float(hist["Close"].iloc[-1]) if len(hist) > 0 else None
        period_high = float(hist["High"].max())
        period_low = float(hist["Low"].min())
        volume = int(hist["Volume"].sum())
        
        # Date range
        start_date = hist.index[0].strftime("%Y-%m-%d")
        end_date = hist.index[-1].strftime("%Y-%m-%d")
        
        # Company name
        company_name = info.get("longName") or info.get("shortName") or symbol
        
        result = {
            "symbol": symbol,
            "company_name": company_name,
            "period": period,
            "current_price": round(current_price, 2) if current_price else None,
            "period_high": round(period_high, 2),
            "period_low": round(period_low, 2),
            "volume": volume,
            "date_range": {
                "start": start_date,
                "end": end_date,
            },
            "currency": info.get("currency", "USD"),
        }
        
        # Add recent price history (last 5 days)
        if len(hist) > 0:
            recent_prices = []
            for idx, row in hist.tail(5).iterrows():
                recent_prices.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })
            result["recent_prices"] = recent_prices
        
        # Log successful response
        logger.info(
            f"Stock price data retrieved successfully: {symbol} (price={result['current_price']}, high={result['period_high']}, low={result['period_low']}, range={result['date_range']}, points={len(hist)})"
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(
            f"Error fetching stock price for {symbol}, period={period}: {e}",
            exc_info=True,
        )
        return json.dumps({
            "error": str(e),
            "symbol": symbol,
            "period": period,
        }, indent=2)

