"""Self knowledge tool handler - returns the self-knowledge document."""
import os
from pathlib import Path

from utils.logging import logger


def read_self_knowledge_doc() -> str:
    """Read the self-knowledge document."""
    # Get the project root (finsense directory)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent.parent
    
    # Path to self-knowledge doc
    doc_path = project_root / "documents" / "self-knowledge-v1.md"
    
    try:
        if doc_path.exists():
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"Successfully loaded self-knowledge doc from {doc_path}")
            return content
        else:
            logger.warning(f"Self-knowledge doc not found at {doc_path}, using fallback")
            return get_fallback_self_knowledge()
    except Exception as e:
        logger.error(f"Error reading self-knowledge doc: {e}", exc_info=True)
        return get_fallback_self_knowledge()


def get_fallback_self_knowledge() -> str:
    """Return a minimal fallback self-knowledge doc if the file can't be read."""
    return """# FinSense Self-Knowledge

FinSense is a financial research assistant with the following capabilities:

## Tools/Modalities Available:
1. chat_with_web_search - Search the web for current information
2. get_stock_price - Get stock price data and historical information
3. get_macro_data - Get macroeconomic indicators (CPI, GDP, FEDFUNDS, UNRATE, etc.)
4. get_finance_news - Get recent finance news articles

## How I Work:
- I'm a multi-step agent that can perform 1-25+ steps per query
- I use modalities (structured JSON) to execute research workflows
- I can run operations in parallel or sequentially
- I include self-critique in each step to catch mistakes

## Use Cases:
- Stock analysis and price queries
- Market research and trends
- Economic indicator analysis
- Finance news research
- Complex multi-step financial research
"""


async def self_knowledge(**kwargs) -> str:
    """Return the self-knowledge document."""
    return read_self_knowledge_doc()

