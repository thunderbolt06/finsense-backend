"""Functions for parsing modalities from thinking blocks."""
import json
from typing import Any

from llm.constants import END_TAG_THINKING, START_TAG_THINKING
from utils.logging import logger
from utils.strings import extract_content_between_tags, extract_json_object


class RoutingInfo(dict):
    """Routing information extracted from thinking blocks."""
    pass


def extract_routing_info_from_block_text(block_text: str) -> tuple[RoutingInfo | None, Exception | None]:
    """Extract routing information from the block text that contains JSON.
    
    The JSON in thinking blocks uses double curly braces {{ }} but we need to extract
    the actual JSON object with single braces { }.
    
    Returns:
        Tuple of (routing_info, error)
    """
    try:
        # Extract JSON from between tags if present
        if START_TAG_THINKING in block_text and END_TAG_THINKING in block_text:
            content = extract_content_between_tags(block_text, START_TAG_THINKING, END_TAG_THINKING)
            if content:
                # The content might have double braces {{ }} which we need to convert to single braces
                # Also might have Qx prefix before the JSON
                # Look for JSON object in the content
                modalities_dict = extract_json_object(content)
            else:
                return None, None
        else:
            # Try to extract JSON directly
            modalities_dict = extract_json_object(block_text)
        
        # Validate routing info
        if modalities_dict and modalities_dict.get("first_modality"):
            routing_info = RoutingInfo({
                "routing_info": modalities_dict,
                "analysis": "",
            })
            return routing_info, None
        return None, None
    except ValueError as e:
        if str(e) == "No JSON object found":
            return None, None
        return None, e
    except Exception as e:
        logger.error(f"Error extracting routing info: {e}", exc_info=True)
        return None, e


def extract_modalities(routing_info: RoutingInfo | None) -> list[dict[str, Any]]:
    """Return a list of modalities (first + parallel) from the routing info."""
    if not routing_info:
        return []
    
    routing_info_inner = routing_info.get("routing_info", {})
    first_modality = routing_info_inner.get("first_modality")
    parallel_modalities = routing_info_inner.get("additional_parallel_modalities", [])
    
    # Combine first modality and parallel modalities
    modalities = ([first_modality] if first_modality else []) + parallel_modalities
    
    return [m for m in modalities if m and m.get("type") is not None]


def parse_thinking_blocks_from_message(
    message_content: str,
) -> tuple[RoutingInfo | None, Exception | None]:
    """
    Parse thinking blocks from a message and extract routing information.
    
    Looks for the last <fs_think> block and extracts JSON from it.
    """
    # Find all thinking blocks
    start_idx = message_content.rfind(START_TAG_THINKING)
    if start_idx == -1:
        return None, None
    
    end_idx = message_content.find(END_TAG_THINKING, start_idx)
    if end_idx == -1:
        return None, None
    
    # Extract the last thinking block
    thinking_block = message_content[start_idx:end_idx + len(END_TAG_THINKING)]
    
    # Extract routing info from the block
    return extract_routing_info_from_block_text(thinking_block)

