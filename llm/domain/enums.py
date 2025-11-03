"""Domain enums for LLM integration."""
from enum import Enum


class ToolPropertyType(str, Enum):
    NUMBER = "number"
    STRING = "string"
    OBJECT = "object"
    ARRAY = "array"
    BOOLEAN = "boolean"


class AIModelsProvider(str, Enum):
    GEMINI = "gemini"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

    def __str__(self):
        return self.value


CHAT_ROLES = (ChatRole.USER, ChatRole.ASSISTANT, ChatRole.TOOL)


class ChatDataType(str, Enum):
    TEXT = "text"
    THOUGHT = "thought"
    SOURCES = "sources"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    ID = "id"
    FILE_IDS = "file_ids"

    def __str__(self):
        return self.value


CHAT_DATA_TYPES = (
    ChatDataType.TEXT,
    ChatDataType.TOOL_USE,
    ChatDataType.TOOL_RESULT,
    ChatDataType.THOUGHT,
    ChatDataType.SOURCES,
    ChatDataType.ID,
    ChatDataType.FILE_IDS,
)

CHAT_DATA_TYPES_FOR_LLM_APIS = (
    ChatDataType.TEXT,
    ChatDataType.TOOL_USE,
    ChatDataType.TOOL_RESULT,
)

CHAT_DATA_TYPES_EXCLUDE_FROM_LLM_APIS = tuple(x for x in CHAT_DATA_TYPES if x not in CHAT_DATA_TYPES_FOR_LLM_APIS)

