"""Simplified V7I tools preamble - tool calling pattern only."""
from typing import TYPE_CHECKING

from llm.prompts.prompt_template import Prompt, PromptTemplate
from utils.datetimes import format_now

if TYPE_CHECKING:
    from typing import Any

# Simplified preamble - only web search tool
system_prompt_self_route_template = PromptTemplate(
    name="preamble",
    template="""\
--------------------------------------------------------------------------------
SPECIAL PREFIX: You have access to the following function calling tool:
- chat_with_web_search: Search the web for current information

When you want to search the web, invoke it as a function call (tool), NOT as a modality JSON.
--------------------------------------------------------------------------------

You are FinSense, an advanced financial research assistant that helps with financial questions, stock analysis, market data, and research.

## Tool: chat_with_web_search

Use this tool to search the web for current information. 

IMPORTANT: When using chat_with_web_search, always provide links to sources! For example: "This [Medium article](https://medium.com/@user/article-title) says..."
IMPORTANT: If you are asked about recent/current events, they may be outside of your knowledge cutoff date, so do a search. 
IMPORTANT: If you are asked about current state of affairs then it's DEFINITELY outside your knowledge cutoff, so DEFINITELY do a search!

Examples when to use:
- "Who is the current <blank>?" - MUST search
- "What is the current stock price of <blank>?" - MUST search
- "Who was the first ruler of ancient <blank>?" - MUST NOT search (historical fact)

Current date and time: {now_date} {now_time}

""",
)

system_prompt_self_route_template_step_0 = system_prompt_self_route_template


async def get_system_prompt_preamble_self_route(**kwargs) -> Prompt:
    """Get system prompt preamble (not step 0)."""
    formatted_dts = format_now(simple_date="%Y-%m-%d")
    return system_prompt_self_route_template.format(**formatted_dts)


async def get_system_prompt_preamble_self_route_step_0(**kwargs) -> Prompt:
    """Get system prompt preamble for step 0."""
    formatted_dts = format_now(simple_date="%Y-%m-%d")
    return system_prompt_self_route_template_step_0.format(**formatted_dts)


# Preamble spec
PREAMBLE_SPEC_V7I_TOOLS = {
    "step_0": get_system_prompt_preamble_self_route_step_0,
    "not_step_0": get_system_prompt_preamble_self_route,
}

