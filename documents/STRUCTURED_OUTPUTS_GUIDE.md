# FinSense Structured Outputs Agent Guide

## Overview

The **structured outputs agent** (v7h_structured) is an evolution of the modalities-based agent that uses Gemini's structured outputs feature instead of parsing JSON from text. This provides more reliable, type-safe responses and eliminates the need for regex/JSON extraction.

## Key Differences from v7h_modalities

| Feature | v7h_modalities | v7h_structured |
|---------|----------------|----------------|
| Output Format | JSON in `<lb_think>` tags | Structured schema |
| Parsing | Text parsing + JSON extraction | Direct structured object |
| Reliability | Can fail on malformed JSON | Guaranteed structure |
| Type Safety | Runtime validation | Schema-enforced |
| Implementation | Manual parsing | Native Gemini feature |

## Architecture

### Response Schema

The agent response follows this structured schema:

```json
{
  "initial_analysis": {
    "status": "E" | "N" | "M",
    "estimated_steps": 0-25,
    "simple_date": "YYYY-MM-DD",
    "tags": ["RESEARCH", "CONDENSED_NON_FINAL", "FINAL", "JAILBREAK", "A"],
    "has_links": boolean,
    "no_results": boolean
  },
  "user_facing_text": "string",
  "final_internal": {
    "questions_count": 0-25,
    "self_critique": "string (1-7 words)",
    "routing_info": {
      "first_modality": { /* modality object */ },
      "additional_parallel_modalities": [ /* array of modalities */ ],
      "likely_subsequent_modalities": [ /* array of modality types */ ]
    }
  }
}
```

### Schema Elements

#### 1. Initial Analysis
- **status**: E (enough), N (not enough, 1-3 steps), M (multistep, 4+ steps)
- **estimated_steps**: Number of remaining steps
- **simple_date**: Current date (required)
- **tags**: Optional metadata tags
- **has_links**: Whether response includes source links
- **no_results**: Whether search returned no results

#### 2. User-Facing Text
- Natural language response visible to user
- May be condensed for intermediate steps
- Full synthesis for final answers

#### 3. Final Internal
- **questions_count**: Stops execution if >0
- **self_critique**: Actionable flaws only (1-7 words)
- **routing_info**: Modality specifications for next step

## Modality Specifications

Each modality can have these fields based on type:

### chat_with_web_search
```json
{
  "type": "chat_with_web_search",
  "search_query": "string"
}
```

### get_stock_price
```json
{
  "type": "get_stock_price",
  "symbol": "AAPL",
  "period": "1d" | "5d" | "1mo" | "3mo" | "6mo" | "1y" | "2y" | "5y" | "10y" | "ytd" | "max"
}
```

### get_macro_data
```json
{
  "type": "get_macro_data",
  "metric": "CPI" | "GDP" | "FEDFUNDS" | "UNRATE" | "CPIAUCSL"
}
```

### get_finance_news
```json
{
  "type": "get_finance_news",
  "topic": "string"
}
```

### self_knowledge
```json
{
  "type": "self_knowledge"
}
```

## Integration

### 1. Import Agent

```python
from llm.prompts.system_prompt_base.preamble_self_route_v7h_structured import (
    PREAMBLE_SPEC_V7H_STRUCTURED,
    get_agent_response_schema,
)
```

### 2. Setup LLM Config

```python
from llm.types import LLMConfig

response_schema = get_agent_response_schema()
llm_config = LLMConfig(
    response_schema=response_schema,
    response_mime_type="application/json",
)
```

### 3. Call Gemini

```python
from llm.call_gemini import call_gemini_raw
from llm.prompts.system_prompt_base.structured_response_parser import (
    extract_structured_response_from_gemini,
)

response = await call_gemini_raw(
    system_prompt=str(system_prompt),
    messages=messages,
    model="gemini-2.5-pro",
    tools=None,  # No function calling with structured outputs
    llm_config=llm_config,
)

structured_response = extract_structured_response_from_gemini(response)
```

### 4. Process Response

```python
# Get user-facing text
user_text = structured_response.user_facing_text

# Check if continuing
if structured_response.is_continuing:
    modalities = structured_response.to_modalities_list()
    # Execute modalities...
    
# Check if final
if structured_response.is_final:
    # Final answer, no more steps
    pass
```

## API Endpoint

### POST `/api/query-structured`

**Request**:
```json
{
  "question": "What's the stock price of AAPL?",
  "chat_id": "optional-chat-id"
}
```

**Response**: Streaming SSE (Server-Sent Events)

**Events**:
- `token`: Text chunk from agent
- `modality_execution_start`: Modality execution beginning
- `modality_execution_complete`: Modality execution finished
- `done`: Stream complete (includes `chat_id`)

**Example Client Code**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/query-structured",
    json={"question": "What's the stock price of AAPL?"},
    stream=True
)

for line in response.iter_lines():
    if line.startswith(b"data: "):
        data = json.loads(line[6:])
        if data.get("event") == "token":
            print(data["text"], end="", flush=True)
```

## Response Parser

The `StructuredAgentResponse` class provides:

### Properties
- `status`: E, N, or M
- `estimated_steps`: Number of remaining steps
- `tags`: List of tags
- `is_final`: True if final answer
- `is_continuing`: True if continuing to next step
- `routing_info`: Modality specifications
- `questions_count`: Number of questions asked
- `self_critique`: Self-critique text

### Methods
- `to_modalities_list()`: Extract modalities as list for execution
- `format_for_display()`: Format with lb_think tags for compatibility

## Example Response

### Simple Query
```json
{
  "initial_analysis": {
    "status": "E",
    "estimated_steps": 0,
    "simple_date": "2025-01-20",
    "tags": ["FINAL"]
  },
  "user_facing_text": "The current stock price of AAPL is $175.43, up 2.3% from yesterday.",
  "final_internal": {
    "questions_count": 0,
    "self_critique": "Good"
  }
}
```

### Continuing Query
```json
{
  "initial_analysis": {
    "status": "N",
    "estimated_steps": 2,
    "simple_date": "2025-01-20",
    "tags": ["CONDENSED_NON_FINAL"]
  },
  "user_facing_text": "Let me check the stock prices for AAPL and GOOGL.",
  "final_internal": {
    "questions_count": 0,
    "self_critique": "Need both prices",
    "routing_info": {
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
      "likely_subsequent_modalities": []
    }
  }
}
```

### Deep Research
```json
{
  "initial_analysis": {
    "status": "M",
    "estimated_steps": 10,
    "simple_date": "2025-01-20",
    "tags": ["RESEARCH"]
  },
  "user_facing_text": "I'll analyze all S&P 500 tech stocks that gained 20% this year. This will take several steps.",
  "final_internal": {
    "questions_count": 0,
    "self_critique": "Research plan: 1) Get list, 2) Fetch prices, 3) Calculate gains",
    "routing_info": {
      "first_modality": {
        "type": "chat_with_web_search",
        "search_query": "S&P 500 technology stocks list 2024"
      },
      "additional_parallel_modalities": [],
      "likely_subsequent_modalities": [
        {"type": "get_stock_price"},
        {"type": "get_finance_news"}
      ]
    }
  }
}
```

## Benefits

1. **Reliability**: No JSON parsing errors
2. **Type Safety**: Schema-enforced structure
3. **Validation**: Gemini validates output matches schema
4. **Easier Integration**: Direct object access
5. **Better Errors**: Clear schema violation messages

## Migration from v7h_modalities

To migrate from v7h_modalities to v7h_structured:

1. Replace `PREAMBLE_SPEC_V7H_MODALITIES` with `PREAMBLE_SPEC_V7H_STRUCTURED`
2. Remove JSON parsing logic from `<lb_think>` tags
3. Use `extract_structured_response_from_gemini()` instead of text parsing
4. Use `StructuredAgentResponse` properties instead of parsed dicts
5. Update router to use `/api/query-structured` endpoint

## Troubleshooting

### Schema Validation Errors
- Check that all required fields are provided
- Ensure enum values match exactly
- Verify date format is YYYY-MM-DD

### Missing Routing Info
- Check `questions_count == 0` and `estimated_steps > 0`
- Verify `routing_info` is included when continuing

### Modality Execution Errors
- Verify modality type matches enum
- Check required parameters for each modality type
- Ensure parallel modalities are independent

## Status

✅ Agent definition complete
✅ Response schema defined
✅ Parser implementation complete
✅ Router integration complete
✅ Ready for use

