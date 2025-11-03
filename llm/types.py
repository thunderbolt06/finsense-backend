"""Types for LLM configuration."""
from typing import Any

from google.genai import types as genai_types
from pydantic import BaseModel


class LLMConfig(BaseModel):
    """Configuration for LLM calls."""
    thinking_config: genai_types.ThinkingConfig | None = None
    response_mime_type: str | None = None
    max_completion_tokens: int | None = None
    response_schema: dict[str, Any] | None = None
    integration_tools: list[genai_types.Tool] | None = None

