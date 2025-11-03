# FinSense Multi-Turn Agent with Modalities (V7H Modalities)

This document describes the multi-turn agent implementation based on `preamble_self_route_v7h` adapted for FinSense with modality-based tool calling.

## Overview

The `preamble_self_route_v7h_modalities` agent is a multi-turn autonomous agent that performs multiple steps per query to fully answer user requests. Unlike the tool-calling approach in `v7i_tools`, this agent uses **modalities** - a structured JSON format embedded in `<fs_think>` tags that allows the agent to plan and execute multiple sequential or parallel operations.

## Key Features

1. **Multi-Step Execution**: The agent can perform 1-25+ steps per query, automatically deciding when to continue or stop
2. **Modality-Based Tools**: Uses JSON modality specifications instead of direct tool calls
3. **Parallel & Sequential Planning**: Supports parallel modality execution and subsequent dependent modalities
4. **Self-Critique**: Each step includes self-critique to catch mistakes and adjust plans
5. **Research Capabilities**: Can perform deep research (10-25 steps) or quick queries (1-3 steps)

## Architecture

### Files Created

```
finsense/llm/prompts/system_prompt_base/
├── preamble_self_route_v7h_modalities.py  # Main agent definition
├── modalities/
│   ├── __init__.py
│   ├── chat_with_web_search.py           # Web search modality
│   ├── get_stock_price.py                 # Stock price modality
│   ├── get_macro_data.py                  # Macro economic data modality
│   └── get_finance_news.py                # Finance news modality
└── helpers.py                             # Modality template generation
```

### Modalities Available

1. **chat_with_web_search**
   - Type: `"chat_with_web_search"`
   - Fields: `search_query` (string)
   - Use: General web searches for current information

2. **get_stock_price**
   - Type: `"get_stock_price"`
   - Fields: `symbol` (string), `period` (string)
   - Use: Stock price data and historical information

3. **get_macro_data**
   - Type: `"get_macro_data"`
   - Fields: `metric` (string)
   - Use: Macroeconomic indicators (CPI, GDP, FEDFUNDS, UNRATE, etc.)

4. **get_finance_news**
   - Type: `"get_finance_news"`
   - Fields: `topic` (string)
   - Use: Recent finance news articles about specific topics

## Usage

### Import and Use

```python
from llm.prompts.system_prompt_base.preamble_self_route_v7h_modalities import PREAMBLE_SPEC_V7H_MODALITIES

# Determine if this is step 0
is_step_0 = len(chat_history) <= 1

# Get system prompt
preamble_func = PREAMBLE_SPEC_V7H_MODALITIES["step_0" if is_step_0 else "not_step_0"]
system_prompt = await preamble_func()
```

### Modality JSON Format

The agent outputs modality JSON in this format:

```json
{
  "first_modality": {
    "type": "get_stock_price",
    "symbol": "AAPL",
    "period": "1d"
  },
  "additional_parallel_modalities": [
    {
      "type": "get_stock_price",
      "symbol": "GOOGL",
      "period": "1d"
    }
  ],
  "likely_subsequent_modalities": [
    {
      "type": "chat_with_web_search"
    },
    {
      "type": "get_finance_news"
    }
  ]
}
```

### Agent Response Format

Each agent message has three parts:

1. **Initial Analysis** (in `<fs_think>` tags):
   - Format: `E0`, `N1`, `M10`, etc.
   - E = Enough info, N = Not enough (1-3 steps), M = Multi-step (4+ steps)
   - Number = estimated remaining steps

2. **User-Facing Text**: 
   - Natural language response
   - Explains what the agent is doing

3. **Final Internal Portion** (in `<fs_think>` tags):
   - `Qx` = number of questions asked (if >0, stops and waits for user)
   - Self-critique (1-7 words, only actionable flaws)
   - Optional modality JSON if continuing to next step

Example:
```
<fs_think>N2</fs_think>
Let me check the stock prices for AAPL and GOOGL...
<fs_think>Q0 Need both prices{{"first_modality":{"type":"get_stock_price","symbol":"AAPL","period":"1d"},"additional_parallel_modalities":[{"type":"get_stock_price","symbol":"GOOGL","period":"1d"}]}}</fs_think>
```

## Key Differences from V7H

1. **Removed User Context**: All references to `chat_with_user_context`, user names, and personal data removed
3. **Financial Tools Only**: Examples and modalities focus on financial tools (stocks, macro data, finance news, web search)
4. **Simplified Helpers**: Helper function doesn't require user or agent_config parameters

## Processing Modalities

The chat router needs to:
1. Parse `<fs_think>` tags to extract modality JSON
2. Execute the modalities (call corresponding tools)
3. Format results and add to conversation context
4. Continue streaming to get next agent response

## Research Eagerness

The agent has a dynamic "research eagerness" setting (currently 9%):
- 0% = Always prioritize speed
- 100% = Always prioritize thoroughness
- Controls how many steps the agent will perform for research tasks

For regular research: 5-10 steps
For deep research: 10-25 steps

## Example Workflows

### Simple Query
User: "What's the stock price of AAPL?"
- Step 1: Get stock price → Return result
- Total: 1 step

### Parallel Queries
User: "Compare AAPL and GOOGL stock prices"
- Step 1: Get both prices in parallel → Compare and return
- Total: 1 step (parallel modalities)

### Sequential Research
User: "Should I invest in AAPL?"
- Step 1: Get stock price
- Step 2: Get recent finance news about AAPL
- Step 3: Web search for analyst opinions
- Step 4: Synthesize and provide recommendation
- Total: 4+ steps

### Deep Research
User: "Analyze all S&P 500 tech stocks that gained 20% this year"
- Step 1: Research plan (todo list)
- Steps 2-15: Execute each research item
- Step 16: Synthesize final answer
- Total: 16+ steps

## Integration Notes

To integrate this agent into the chat router:

1. Replace `PREAMBLE_SPEC_V7I_TOOLS` with `PREAMBLE_SPEC_V7H_MODALITIES`
2. Remove tool calling logic (Gemini function calls)
3. Add modality JSON parsing from `<fs_think>` tags
4. Execute modalities → call corresponding tools
5. Add modality results to conversation context
6. Continue streaming for multi-step responses

## Status

✅ Agent definition complete
✅ All 4 modalities defined
✅ User context removed
✅ Examples updated for financial domain
✅ Ready for integration with chat router

