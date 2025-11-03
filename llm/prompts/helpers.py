"""Helper functions for prompts."""
from llm.prompts.prompt_template import PromptTemplate
from llm.prompts.system_prompt_base.modalities.chat_with_web_search import chat_with_web_search_template
from llm.prompts.system_prompt_base.modalities.get_finance_news import get_finance_news_template
from llm.prompts.system_prompt_base.modalities.get_macro_data import get_macro_data_template
from llm.prompts.system_prompt_base.modalities.get_stock_price import get_stock_price_template
from llm.prompts.system_prompt_base.modalities.self_knowledge import self_knowledge_template

modality_defn_template = PromptTemplate(name="modality_defn", template="#### {i}. {key}\n{defn}")

# Default modality templates for FinSense
DEFAULT_MODALITY_TEMPLATES = {
    "chat_with_web_search": chat_with_web_search_template,
    "get_stock_price": get_stock_price_template,
    "get_macro_data": get_macro_data_template,
    "get_finance_news": get_finance_news_template,
    "self_knowledge": self_knowledge_template,
}


async def get_modality_prompt_template_strings(**kwargs) -> tuple[str, str]:
    """Generate a string of modality names and a string of their definitions for use in the system message preamble.

    Returns:
        Tuple of (modality_names_string, modality_definitions_string)
    """
    templates = DEFAULT_MODALITY_TEMPLATES
    
    present_templates = {k: v for k, v in templates.items() if v}
    names = " | ".join([f'"{key}"' for key in present_templates])
    
    defn_parts = []
    for i, (key, template) in enumerate(present_templates.items(), start=1):
        formatted = modality_defn_template.format(i=str(i), key=key, defn=template.template)
        defn_parts.append(str(formatted))
    
    defs = "\n\n".join(defn_parts)
    
    return names, defs

