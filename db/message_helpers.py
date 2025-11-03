"""Helper functions for working with ChatMessage model."""
from typing import Any

from db.models import ChatMessage, ChatWithContext
from llm.domain.enums import ChatDataType, ChatRole


def create_user_message(
    chat: ChatWithContext,
    content: str,
    parent_message: ChatMessage | None = None,
    context_collected: bool = False,
    context_data: dict[str, Any] | None = None,
    file_ids: list[str] | None = None,
) -> ChatMessage:
    """Create a user message and add it to the chat."""
    latest = chat.get_latest_message() if hasattr(chat, 'get_latest_message') else None
    root = chat.root_message if latest else None  # Access root_message synchronously (OK in sync context)
    
    message = ChatMessage.objects.create(
        chat=chat,
        role=ChatRole.USER.value,
        content_type=ChatDataType.TEXT.value,
        content=content,
        parent_message=parent_message or latest,
        root_message=root,
        context_collected=context_collected,
        context_data=context_data or {},
        file_ids=file_ids or [],
    )
    
    return message


def create_assistant_message(
    chat: ChatWithContext,
    content: str,
    parent_message: ChatMessage | None = None,
    content_type: str = ChatDataType.TEXT.value,
    step_number: int | None = None,
    modality_type: str | None = None,
    is_final: bool = False,
    questions_asked: int = 0,
    metadata: dict[str, Any] | None = None,
) -> ChatMessage:
    """Create an assistant message and add it to the chat."""
    latest = chat.get_latest_message() if hasattr(chat, 'get_latest_message') else None
    root = chat.root_message if latest else None  # Access root_message synchronously (OK in sync context)
    
    message = ChatMessage.objects.create(
        chat=chat,
        role=ChatRole.ASSISTANT.value,
        content_type=content_type,
        content=content,
        parent_message=parent_message or latest,
        root_message=root,
        step_number=step_number,
        modality_type=modality_type,
        is_final=is_final,
        questions_asked=questions_asked,
        metadata=metadata or {},
    )
    
    return message


def create_tool_message(
    chat: ChatWithContext,
    content: str,
    parent_message: ChatMessage | None = None,
    tool_name: str | None = None,
    tool_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ChatMessage:
    """Create a tool message and add it to the chat."""
    latest = chat.get_latest_message() if hasattr(chat, 'get_latest_message') else None
    root = chat.root_message if latest else None  # Access root_message synchronously (OK in sync context)
    
    tool_metadata = {
        "tool_name": tool_name,
        "tool_id": tool_id,
        **(metadata or {}),
    }
    
    message = ChatMessage.objects.create(
        chat=chat,
        role=ChatRole.TOOL.value,
        content_type=ChatDataType.TOOL_RESULT.value,
        content=content,
        parent_message=parent_message or latest,
        root_message=root,
        metadata=tool_metadata,
    )
    
    return message


def messages_to_api_format(messages: list[ChatMessage]) -> list[list[str]]:
    """Convert ChatMessage list to format expected by LLM API.
    
    Returns: List of [role, content_data...] pairs for LLM API.
    """
    import json
    api_format = []
    for msg in messages:
        # Build message blocks: [role, content_type:content]
        blocks = [msg.role]
        
        # Add main content
        blocks.append(f"{msg.content_type}:{msg.content}")
        
        # Add file_ids if present
        if msg.file_ids:
            blocks.append(f"{ChatDataType.FILE_IDS.value}:{json.dumps(msg.file_ids)}")
        
        # For tool results, include metadata in content if needed
        if msg.role == ChatRole.TOOL.value and msg.metadata:
            # Tool results are formatted as JSON strings
            tool_result = {
                "result": msg.content,
                "tool_id": msg.metadata.get("tool_id"),
                "func_name": msg.metadata.get("tool_name") or msg.metadata.get("func_name"),
            }
            blocks = [msg.role, f"{msg.content_type}:{json.dumps(tool_result)}"]
        
        api_format.append(blocks)
    
    return api_format


def messages_to_legacy_format(messages: list[ChatMessage]) -> list[list[str]]:
    """Convert ChatMessage list to legacy format for backwards compatibility.
    
    This is used by the traces API to maintain the same response format.
    Returns: List of [role, content_data...] pairs compatible with legacy format.
    """
    import json
    legacy_format = []
    for msg in messages:
        # Build message blocks: [role, content_type:content, ...]
        blocks = [msg.role]
        
        # Add main content
        blocks.append(f"{msg.content_type}:{msg.content}")
        
        # Add file_ids if present
        if msg.file_ids:
            blocks.append(f"{ChatDataType.FILE_IDS.value}:{json.dumps(msg.file_ids)}")
        
        # For tool results, format as JSON
        if msg.role == ChatRole.TOOL.value and msg.metadata:
            tool_result = {
                "result": msg.content,
                "tool_id": msg.metadata.get("tool_id"),
                "func_name": msg.metadata.get("tool_name") or msg.metadata.get("func_name"),
            }
            blocks = [msg.role, f"{msg.content_type}:{json.dumps(tool_result)}"]
        
        legacy_format.append(blocks)
    
    return legacy_format
