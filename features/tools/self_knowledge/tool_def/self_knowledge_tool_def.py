"""Self knowledge tool definition."""
from llm.domain.models import ToolDefinition

SELF_KNOWLEDGE_DESCRIPTION = """\
This tool is the equivalent of docs lookup. You don't currently have enough information how you yourself work, so if the question requires understanding your own features, abilities, architecture, basically if it's the kind of question where the answer is "in the docs", then call this tool WITHOUT producing any other text. This is a special case where the normal response structure is bypassed for speed: SKIP initial thinking tags, any user-facing text, or final thinking tag and ONLY call the tool.

Examples:
- "What tools do you have?" - USE (call this tool immediately without outputting anything else)
- "Can you get stock prices?" - USE
- "How do you work?" - USE
- "What's get_macro_data?" - USE (get_macro_data, get_stock_price, get_finance_news, and chat_with_web_search are your modalities)
- "What can you tell me about AAPL?" - NO (user is asking about a stock, not about you)
- "What's the CPI?" - NO (user is asking for data, not about your capabilities)

Example of what NOT to output:
- DON'T: "<fs_think>..." (don't output these tags, for self_knowledge must ONLY call tool)
"""

SELF_KNOWLEDGE_TOOL = ToolDefinition(
    description=SELF_KNOWLEDGE_DESCRIPTION,
    name="self_knowledge",
    parameters={},
)

