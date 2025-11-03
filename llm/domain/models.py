"""Domain models for LLM integration."""
from typing import Any

from pydantic import BaseModel, Field

from llm.domain.enums import AIModelsProvider, ToolPropertyType


class ToolParameter(BaseModel):
    type: ToolPropertyType
    items: "ToolParameter | None" = None
    properties: dict[str, "ToolParameter"] | None = None
    description: str = ""
    enum: list[str] | None = None
    is_required: bool = True


class ToolDefinition(BaseModel):
    description: str
    name: str  # This must be the function name, e.g. "chat_with_web_search"
    parameters: dict[str, ToolParameter]
    provider_format: dict[AIModelsProvider, dict] = Field(default_factory=dict)


class ToolData(BaseModel):
    index: str
    tool_id: str | None = None
    func_name: str | None = None
    func_args: str = ""


class ChatResponse(BaseModel):
    text: str = ""
    tool: ToolData | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    finish_reason: str | None = None
    model: str | None = None


class ToolResult(BaseModel):
    tool_id: str | None  # Usually None for Gemini
    result: str
    func_name: str | None

