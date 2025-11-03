# FinSense Self-Knowledge Feature Guide

## Overview

The **self-knowledge** modality allows FinSense to retrieve its own documentation to answer questions about its capabilities, features, architecture, and how it works. This ensures accurate, up-to-date answers about the system itself.

## What is Self-Knowledge?

Self-knowledge is a special modality that serves as a "docs lookup" mechanism. When users ask questions about:
- Your capabilities and tools
- How you work
- Your features and architecture
- How to use specific functionalities

...instead of relying on potentially outdated training data, you retrieve your own documentation (`self-knowledge-v1.md`) to provide accurate answers.

## Use Cases

### 1. **Capability Questions**
- **User**: "What tools do you have?"
- **Response**: FinSense uses `self_knowledge` modality to retrieve the tools section from documentation
- **Answer**: Lists all 5 modalities: web_search, stock_price, macro_data, finance_news, self_knowledge

### 2. **Feature Questions**
- **User**: "How do I get stock price information?"
- **Response**: Retrieves the "Stock Price Analysis" section
- **Answer**: Explains how to query stock prices, supported periods, and what data is provided

### 3. **Architecture Questions**
- **User**: "How do you work?"
- **Response**: Retrieves the "How FinSense Works" section
- **Answer**: Explains modality-based architecture, multi-step research, parallel processing

### 4. **Technical Questions**
- **User**: "What data sources do you use?"
- **Response**: Retrieves the "Data Sources" section
- **Answer**: Lists Yahoo Finance, FRED, SERPAPI, RSS feeds

### 5. **Usage Questions**
- **User**: "Can you compare multiple stocks?"
- **Response**: Retrieves relevant section about parallel queries
- **Answer**: Explains how parallel modalities work for stock comparisons

### 6. **Limitation Questions**
- **User**: "Can you execute trades?"
- **Response**: Retrieves the "Limitations & Constraints" section
- **Answer**: Clarifies what FinSense can and cannot do

## How It Works

### For Modalities-Based Agent (v7h_modalities)

1. **User asks**: "What tools do you have?"
2. **Agent recognizes**: Question is about its own capabilities
3. **Agent outputs**: 
   ```
   Checking my docs...<fs_think>{"first_modality": {"type": "self_knowledge"}}</fs_think>
   ```
4. **System executes**: `self_knowledge()` tool handler
5. **Tool handler reads**: `documents/self-knowledge-v1.md`
6. **Agent receives**: Full self-knowledge document
7. **Agent responds**: Uses the document to answer the question accurately

### For Tool-Calling Agent (v7i_tools)

1. **User asks**: "What tools do you have?"
2. **Agent recognizes**: Question is about its own capabilities  
3. **Agent calls**: `self_knowledge()` tool (bypasses normal response structure)
4. **Tool handler reads**: `documents/self-knowledge-v1.md`
5. **Agent receives**: Full self-knowledge document
6. **Agent responds**: Uses the document to answer accurately

## Key Characteristics

### Speed Optimization
- **For modalities**: Skip initial `<fs_think>` tags
- **User-facing text**: Just "Checking my docs..."
- **Goal**: Minimize latency when retrieving documentation

### When to Use
✅ **USE** for:
- Questions about your capabilities: "What can you do?"
- Questions about your tools: "What's get_macro_data?"
- Questions about your architecture: "How do you work?"
- Questions about your features: "How do I query economic indicators?"

❌ **DON'T USE** for:
- Questions about external topics: "What's the CPI?" (user wants data, not explanation)
- Questions about stocks: "What can you tell me about AAPL?" (user asking about stock, not you)
- Questions about economy: "What do you know about inflation?" (user asking about topic, not capabilities)

## Integration Points

### 1. Modality Template
- **Location**: `llm/prompts/system_prompt_base/modalities/self_knowledge.py`
- **Purpose**: Instructs agent when and how to use self_knowledge modality

### 2. Tool Definition
- **Location**: `features/tools/self_knowledge/tool_def/self_knowledge_tool_def.py`
- **Purpose**: Defines the tool for Gemini function calling

### 3. Tool Handler
- **Location**: `features/tools/self_knowledge/tool_handler/self_knowledge_tool_handler.py`
- **Purpose**: Reads and returns the self-knowledge document

### 4. Documentation
- **Location**: `documents/self-knowledge-v1.md`
- **Purpose**: Comprehensive documentation about FinSense

### 5. Tool Registration
- **Location**: `features/tool_calling/logic.py`
- **Purpose**: Registers self_knowledge in TOOL_DEFINITIONS and TOOL_FUNCTIONS_DICT

## Example Workflows

### Example 1: User Asks About Capabilities
```
User: "What tools do you have?"

Agent (v7h_modalities):
  Checking my docs...<fs_think>{"first_modality": {"type": "self_knowledge"}}</fs_think>

System: Executes self_knowledge → Returns full document

Agent: 
  I have access to 5 modalities:
  1. chat_with_web_search - Search the web for current information
  2. get_stock_price - Get stock price data and historical information
  3. get_macro_data - Get macroeconomic indicators
  4. get_finance_news - Get recent finance news articles
  5. self_knowledge - Lookup my own documentation
  
  [Detailed explanation from docs...]
```

### Example 2: User Asks About Features
```
User: "How do I query economic indicators?"

Agent (v7h_modalities):
  Checking my docs...<fs_think>{"first_modality": {"type": "self_knowledge"}}</fs_think>

System: Returns self-knowledge document

Agent:
  To query economic indicators, you can ask questions like:
  - "What's the latest CPI data?"
  - "What's the current Federal Funds Rate?"
  
  I'll fetch the latest value and historical data points from FRED.
  
  Supported indicators include:
  - CPI or CPIAUCSL: Consumer Price Index
  - GDP: Gross Domestic Product
  - FEDFUNDS: Federal Funds Rate
  - UNRATE: Unemployment Rate
  [More details from docs...]
```

### Example 3: User Asks About Architecture
```
User: "How do you work?"

Agent:
  Checking my docs...<fs_think>{"first_modality": {"type": "self_knowledge"}}</fs_think>

System: Returns documentation

Agent:
  I work using a modality-based architecture:
  
  - I'm a multi-step agent that can perform 1-25+ steps per query
  - I use modalities (structured JSON) to execute research workflows
  - I can run operations in parallel or sequentially
  - Each step includes self-critique to catch mistakes
  
  [Architecture details from docs...]
```

## Benefits

1. **Accuracy**: Always provides up-to-date information about capabilities
2. **Consistency**: Same documentation source ensures consistent answers
3. **Maintainability**: Update documentation in one place, all agents benefit
4. **Transparency**: Users get accurate information about what FinSense can do
5. **Completeness**: Comprehensive documentation covers all aspects of the system

## Maintenance

### Updating Documentation
1. Edit `documents/self-knowledge-v1.md`
2. Changes automatically reflected in next query
3. No code changes needed

### Adding New Sections
1. Add section to `self-knowledge-v1.md`
2. Agent will automatically retrieve and use new content
3. Consider updating modality template examples if needed

### Testing
- Test with various capability questions
- Verify agent uses self_knowledge appropriately
- Ensure documentation is comprehensive and accurate

## Best Practices

1. **Keep Documentation Updated**: Regularly update `self-knowledge-v1.md` as features change
2. **Be Comprehensive**: Cover all aspects: capabilities, limitations, usage, technical details
3. **Organize Well**: Use clear sections and formatting for easy retrieval
4. **Include Examples**: Provide concrete examples in documentation
5. **Maintain Accuracy**: Ensure documentation matches actual implementation

## Troubleshooting

### Issue: Agent doesn't use self_knowledge
- **Check**: Modality template is included in DEFAULT_MODALITY_TEMPLATES
- **Check**: Tool is registered in TOOL_DEFINITIONS and TOOL_FUNCTIONS_DICT
- **Check**: Agent prompt includes self_knowledge in modality_names

### Issue: Documentation not found
- **Check**: `documents/self-knowledge-v1.md` exists
- **Check**: File path resolution in tool handler
- **Check**: File permissions

### Issue: Agent answers without using self_knowledge
- **Check**: Modality template examples are clear
- **Check**: Agent prompt emphasizes using self_knowledge for capability questions
- **Check**: Examples in template match common user questions

## Conclusion

The self-knowledge feature ensures FinSense can accurately answer questions about itself, maintaining transparency and providing users with reliable information about capabilities, features, and usage. By retrieving its own documentation, the agent stays accurate even as the system evolves.

