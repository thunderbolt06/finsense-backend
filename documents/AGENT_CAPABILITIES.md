# FinSense Agent Capabilities - Complete Guide

## End-to-End Understanding of Agent Capabilities

This document provides a comprehensive guide to understanding and using FinSense's agent capabilities, including use cases, workflows, and best practices.

## Table of Contents
1. [Agent Architecture](#agent-architecture)
2. [Available Tools & Modalities](#available-tools--modalities)
3. [Multi-Step Research](#multi-step-research)
4. [Use Cases by Scenario](#use-cases-by-scenario)
5. [How to Use the Agent](#how-to-use-the-agent)
6. [Response Format Understanding](#response-format-understanding)
7. [Best Practices](#best-practices)
8. [Limitations](#limitations)

---

## Agent Architecture

### Two Agent Types

#### 1. **Tool-Calling Agent (v7i_tools)**
- Uses Gemini function calling directly
- Simpler, single-turn focused
- Good for: Quick queries, simple fact-finding

#### 2. **Modalities-Based Agent (v7h_modalities)**
- Uses modality JSON in `<lb_think>` tags
- Multi-turn autonomous execution
- Good for: Complex research, multi-step analysis

### Core Components

1. **Modalities**: Structured JSON specifications for tool execution
2. **Multi-Step Execution**: Agent performs 1-25+ steps automatically
3. **Parallel Processing**: Execute multiple independent operations simultaneously
4. **Sequential Planning**: Plan dependent operations using `likely_subsequent_modalities`
5. **Self-Critique**: Each step includes self-review and error correction

---

## Available Tools & Modalities

### 1. **chat_with_web_search**
**Purpose**: Search the web for current information

**Use When**:
- Current events that may have changed
- Information not in structured financial data
- General financial questions requiring web research
- CEO changes, company announcements, market news

**Example Queries**:
- "Who is the current CEO of Apple?"
- "What's the latest news about the Federal Reserve?"
- "Find information about the tech sector rally"

**Parameters**:
- `search_query`: String - A concise search query

**Returns**:
- Search results with links to sources
- Always includes source URLs in response

---

### 2. **get_stock_price**
**Purpose**: Get real-time stock price data and historical information

**Use When**:
- Stock price queries
- Price history analysis
- Market performance questions
- Stock valuation research

**Example Queries**:
- "What's the stock price of AAPL?"
- "Show me GOOGL's price over the last month"
- "Compare AAPL and MSFT stock prices"

**Parameters**:
- `symbol`: String - Stock ticker symbol (e.g., AAPL, GOOGL, MSFT)
- `period`: String - Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

**Returns**:
- Current price
- Period high/low
- Volume
- Price history for requested period

---

### 3. **get_macro_data**
**Purpose**: Get macroeconomic indicators

**Use When**:
- Economic indicator queries
- Inflation data
- Interest rate information
- GDP, unemployment, etc.

**Example Queries**:
- "What's the latest CPI data?"
- "What's the current Federal Funds Rate?"
- "Show me unemployment rate trends"

**Parameters**:
- `metric`: String - Economic metric name (CPI, GDP, FEDFUNDS, UNRATE, CPIAUCSL)

**Returns**:
- Latest value
- Historical data points

**Common Metrics**:
- CPI/CPIAUCSL: Consumer Price Index (inflation)
- GDP: Gross Domestic Product
- FEDFUNDS: Federal Funds Rate
- UNRATE: Unemployment Rate

---

### 4. **get_finance_news**
**Purpose**: Get recent finance news articles

**Use When**:
- Finance news queries
- Market updates
- Financial analysis articles
- Company-specific news

**Example Queries**:
- "What's the latest finance news?"
- "Find news about AAPL"
- "What are analysts saying about the market?"

**Parameters**:
- `topic`: String - Topic or keyword (e.g., 'stock market', 'Federal Reserve', 'inflation', 'AAPL')

**Returns**:
- Article titles
- Links
- Publication dates
- Summaries

---

### 5. **self_knowledge**
**Purpose**: Lookup agent's own documentation

**Use When**:
- Questions about agent capabilities
- Questions about features
- Questions about how the agent works
- Technical documentation queries

**Example Queries**:
- "What tools do you have?"
- "How do you work?"
- "What's get_macro_data?"
- "Can you execute trades?"

**Parameters**: None

**Returns**:
- Full self-knowledge documentation
- Comprehensive information about capabilities, features, architecture

---

## Multi-Step Research

### Understanding Step Types

#### Simple Queries (1-3 steps)
- Quick fact-finding
- Single data source needed
- **Example**: "What's the stock price of AAPL?"
  - Step 1: Get AAPL price → Return answer

#### Moderate Research (4-10 steps)
- Multiple data sources
- Some analysis required
- **Example**: "Should I invest in AAPL?"
  - Step 1: Get AAPL stock price
  - Step 2: Get recent finance news about AAPL
  - Step 3: Web search for analyst opinions
  - Step 4: Synthesize and provide recommendation

#### Deep Research (10-25 steps)
- Comprehensive analysis
- Multiple stocks/indicators
- Extensive web research
- **Example**: "Analyze all S&P 500 tech stocks that gained 20% this year"
  - Step 1: Create research plan (todo list)
  - Steps 2-15: Execute research items (get prices, search news, analyze trends)
  - Step 16: Synthesize final answer

### Research Eagerness

**Current Setting**: 9% (prioritizing speed)

- **Low (0-20%)**: Quick answers, fewer steps
- **Medium (20-60%)**: Balanced thoroughness and speed
- **High (60-100%)**: Comprehensive research, many steps

### Planning Research

When agent determines research is needed:

1. **Initial Analysis**: Adds "RESEARCH" tag (e.g., `<lb_think>M10 RESEARCH</lb_think>`)
2. **Research Plan**: Creates todo list of research items
3. **Execution**: Addresses each item in separate steps
4. **Adaptation**: Modifies plan based on findings
5. **Synthesis**: Final answer combines all findings

---

## Use Cases by Scenario

### Scenario 1: Quick Stock Price Query
**User**: "What's the stock price of AAPL?"

**Agent Flow**:
1. Recognizes simple query
2. Calls `get_stock_price` with symbol="AAPL", period="1d"
3. Returns current price immediately

**Result**: Fast, single-step response

---

### Scenario 2: Stock Comparison
**User**: "Compare AAPL and GOOGL stock prices"

**Agent Flow**:
1. Recognizes parallel query opportunity
2. Calls both `get_stock_price` simultaneously:
   - First: AAPL
   - Parallel: GOOGL
3. Compares results
4. Returns comparison

**Result**: Efficient parallel processing

---

### Scenario 3: Investment Analysis
**User**: "Should I invest in AAPL?"

**Agent Flow**:
1. Recognizes complex query needing research
2. **Step 1**: Get AAPL stock price
3. **Step 2**: Get finance news about AAPL
4. **Step 3**: Web search for analyst opinions
5. **Step 4**: Synthesize recommendation

**Result**: Multi-step comprehensive analysis

---

### Scenario 4: Economic Indicator Query
**User**: "What's the current inflation rate?"

**Agent Flow**:
1. Recognizes economic indicator query
2. Calls `get_macro_data` with metric="CPI"
3. Returns latest CPI data with context

**Result**: Direct data access, fast response

---

### Scenario 5: Market Research
**User**: "What's happening in the stock market today?"

**Agent Flow**:
1. Recognizes broad research query
2. **Step 1**: Web search for "stock market today"
3. **Step 2**: Get finance news
4. **Step 3**: Synthesize market update

**Result**: Multi-source market overview

---

### Scenario 6: Deep Research
**User**: "Analyze all S&P 500 tech stocks that gained 20% this year"

**Agent Flow**:
1. Recognizes deep research query (adds "RESEARCH" tag)
2. Creates research plan:
   - Identify S&P 500 tech stocks
   - Get prices for each
   - Calculate year-to-date gains
   - Filter those with >20% gains
   - Analyze each stock
   - Synthesize findings
3. Executes plan step-by-step (10-25 steps)
4. Final synthesis with comprehensive answer

**Result**: Thorough, comprehensive research

---

### Scenario 7: Capability Question
**User**: "What tools do you have?"

**Agent Flow**:
1. Recognizes question about own capabilities
2. Calls `self_knowledge` modality
3. Retrieves documentation
4. Answers based on docs

**Result**: Accurate, up-to-date capability information

---

## How to Use the Agent

### API Endpoint

**POST** `/api/query`

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
- `tool_call`: Tool invocation notification
- `tool_execution_start`: Tool execution beginning
- `tool_execution_complete`: Tool execution finished
- `done`: Stream complete (includes `chat_id`)

### Example Client Code

```python
import requests

response = requests.post(
    "http://localhost:8000/api/query",
    json={"question": "What's the stock price of AAPL?"},
    stream=True
)

for line in response.iter_lines():
    if line.startswith(b"data: "):
        data = json.loads(line[6:])
        if data.get("event") == "token":
            print(data["text"], end="", flush=True)
```

### Asking Effective Questions

#### 1. Be Specific
❌ **Bad**: "Tell me about stocks"
✅ **Good**: "What's the stock price of AAPL?"

#### 2. Specify Timeframes
❌ **Bad**: "AAPL price"
✅ **Good**: "AAPL price over the last month"

#### 3. Request Comparisons
❌ **Bad**: "Tell me about AAPL and GOOGL"
✅ **Good**: "Compare AAPL and GOOGL stock prices"

#### 4. Ask for Analysis
❌ **Bad**: "AAPL"
✅ **Good**: "Should I invest in AAPL?"

#### 5. Specify Scope
❌ **Bad**: "Tech stocks"
✅ **Good**: "Analyze tech stocks in the S&P 500 that gained 20% this year"

---

## Response Format Understanding

### Message Structure

Each agent message has three parts:

#### 1. Initial Analysis
Hidden in `<lb_think>` tags at the start:
- Format: `E0`, `N1`, `M10`, etc.
- **E** = Enough info (final answer)
- **N** = Not enough (1-3 steps needed)
- **M** = Multi-step (4+ steps needed)
- Number = estimated remaining steps

**Special Tags**:
- `RESEARCH`: Starting deep research
- `CONDENSED_NON_FINAL`: Intermediate step (condensed style)
- `FINAL`: Final answer (normal style)

#### 2. User-Facing Text
What you see in the conversation:
- Natural language explanation
- May be condensed for intermediate steps
- Full synthesis for final answer

#### 3. Final Internal Portion
Hidden in `<lb_think>` tags at the end:
- `Qx`: Number of questions asked (if >0, stops)
- Self-critique (1-7 words, actionable flaws only)
- Optional modality JSON for next step

### Example Response

```
<lb_think>N2</lb_think>
Let me check the stock prices for AAPL and GOOGL...

<lb_think>Q0 Need both prices{{"first_modality":{"type":"get_stock_price","symbol":"AAPL","period":"1d"},"additional_parallel_modalities":[{"type":"get_stock_price","symbol":"GOOGL","period":"1d"}]}}</lb_think>
```

**Breakdown**:
- `N2`: Not enough info, expect 2 more steps
- User-facing text explains what's happening
- `Q0`: No questions asked
- Modality JSON specifies parallel stock price queries

---

## Best Practices

### For Users

1. **Be Specific**: Clear, specific questions get better results
2. **Specify Timeframes**: Include time periods when relevant
3. **Use Comparisons**: Ask for comparisons when comparing multiple items
4. **Allow Time**: Complex research takes time (10-25 steps)
5. **Read Final Answer**: Skip intermediate updates, read final synthesis

### For Developers

1. **Handle Streaming**: Process SSE events properly
2. **Store chat_id**: Returned in `done` event for conversation continuity
3. **Handle Tool Calls**: Display tool execution notifications
4. **Error Handling**: Handle API errors gracefully
5. **Timeout Handling**: Complex queries may take time

---

## Limitations

### What FinSense CAN Do
✅ Research stocks, markets, and economic indicators
✅ Search the web for current financial information
✅ Get finance news articles
✅ Perform multi-step research workflows
✅ Compare multiple stocks or indicators
✅ Analyze trends and patterns

### What FinSense CANNOT Do
❌ Execute trades or place orders
❌ Access personal investment accounts
❌ Provide personalized investment advice (provides information, not advice)
❌ Set reminders or calendar events
❌ Create or upload files
❌ Access private user data or context

---

## Conclusion

FinSense is a powerful financial research assistant that can perform both simple queries and complex multi-step research. Understanding its capabilities, tools, and response format will help you get the most out of the agent.

For specific tool capabilities, see:
- Stock Price Analysis: `get_stock_price` modality
- Economic Indicators: `get_macro_data` modality
- Finance News: `get_finance_news` modality
- Web Research: `chat_with_web_search` modality
- Agent Capabilities: `self_knowledge` modality

For agent capabilities and features, ask: "What tools do you have?" or "How do you work?"

