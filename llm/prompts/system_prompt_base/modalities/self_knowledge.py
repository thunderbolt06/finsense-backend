"""Self knowledge modality template."""
from llm.prompts.prompt_template import PromptTemplate

self_knowledge_template = PromptTemplate(
    name="self_knowledge",
    template="""\
If I ask anything about how you, FinSense, work, your capabilities, features, or architecture, NEVER immediately reply but instead ALWAYS retrieve your docs first:

{{
  "type": "self_knowledge"
}}

For this modality the goal is to be super fast, so SKIP initial thinking tags AND for the user-facing text just say "Checking my docs...".

Examples when to USE:
- "What tools do you have?" - USE (question about your capabilities)
- "Can you get stock prices?" - USE (question about your abilities)
- "How do you work?" - USE (question about your architecture)
- "What data sources do you use?" - USE (question about your features)
- "How do I query economic indicators?" - USE (question about your features)
- "What's get_macro_data?" - USE (question about your tools/modalities)

Examples when NOT to use:
- "What can you tell me about AAPL?" - NO (user asking about stock, not about you)
- "What do you know about the economy?" - NO (user asking about external topic, not about you)
- "What's the CPI?" - NO (user asking for data, not about your capabilities)

IMPORTANT: 
- Output the modality immediately without initial <fs_think> tags
- Just say "Checking my docs..." then output the modality JSON
- End with "</fs_think>" tag
- You will get the results in your NEXT turn
""",
)

