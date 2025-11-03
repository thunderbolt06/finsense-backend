"""String utility functions."""
import json
import re

from utils.logging import logger


def extract_json(text: str):
    """Extract a single JSON object or array from a string.

    Determines the first occurrence of '{' or '[', and the last occurrence of '}' or ']', then
    extracts the JSON structure accordingly. Returns a dictionary or list on
    success, throws on parse errors, including a bracket mismatch.
    """
    length = len(text)
    first_curly_brace = text.find("{")
    last_curly_brace = text.rfind("}")
    first_square_brace = text.find("[")
    last_square_brace = text.rfind("]")

    assert first_curly_brace + first_square_brace > -2, "No opening curly or square bracket found"

    if first_curly_brace == -1:
        first_curly_brace = length
    elif first_square_brace == -1:
        first_square_brace = length

    assert (first_curly_brace < first_square_brace) == (last_curly_brace > last_square_brace), (
        "Mismatched curly and square brackets"
    )

    first = min(first_curly_brace, first_square_brace)
    last = max(last_curly_brace, last_square_brace)

    assert first < last, "No closing bracket found"

    json_text = text[first : last + 1]

    # Remove any invalid commas before a closing curly or square bracket (LLMs occasionally produce them by mistake)
    json_text = re.sub(r",\s*([\]}])", r"\1", json_text)

    # Handle double braces (LLMs sometimes copy {{ and }} from prompt templates)
    json_text = json_text.strip()
    if json_text.startswith("{{") and json_text.endswith("}}"):
        json_text = "{" + json_text[2:-2] + "}"

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing JSON: {e}, text: {json_text}")


def extract_json_object(text: str) -> dict:
    """Extract a single JSON object from a string.

    Determines the first occurrence of '{' and the last occurrence of '}', then
    extracts the JSON structure accordingly. Returns a dictionary on
    success, throws on parse errors, including a bracket mismatch.
    """
    first_curly_brace = text.find("{")
    last_curly_brace = text.rfind("}")

    if first_curly_brace == -1 or last_curly_brace == -1:
        raise ValueError("No JSON object found")

    if first_curly_brace > last_curly_brace:
        raise ValueError("Mismatched curly brackets")

    json_text = text[first_curly_brace : last_curly_brace + 1]

    # Remove any invalid commas before a closing curly or square bracket (LLMs occasionally produce them by mistake)
    json_text = re.sub(r",\s*([\]}])", r"\1", json_text)

    # Handle double braces (LLMs sometimes copy {{ and }} from prompt templates)
    json_text = json_text.strip()
    if json_text.startswith("{{") and json_text.endswith("}}"):
        json_text = "{" + json_text[2:-2] + "}"

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing JSON: JSONDecodeError: {e}")


def extract_json_str(text: str, is_object=True) -> str:
    """Extract a JSON object or array from a string, and return it as a string.

    If is_object is True, extract a JSON object. Otherwise, extract a JSON array. The JSON string
    is formatted with 2 spaces for readability.
    """
    return json.dumps(extract_json_object(text) if is_object else extract_json(text), indent=2)


def extract_content_between_tags(text: str, start_tag: str, end_tag: str) -> str | None:
    """Extract content between specified start and end tags.

    Returns None if no start or end tag is found. Uses the first occurrence of the start tag and the
    first occurrence of the end tag that is after the start tag.
    """
    start_pos = text.find(start_tag)
    if start_pos == -1:
        return None

    content_start = start_pos + len(start_tag)
    end_pos = text.find(end_tag, content_start)
    if end_pos == -1:
        return None

    return text[content_start:end_pos]


def remove_content_between_tags(text: str, start_tag: str, end_tag: str) -> str:
    """Remove content between specified start and end tags.

    Example: "blah<fs_think>...</fs_think>blah<fs_think>...</fs_think>blah" -> "blahblahblah"

    NOTE: Wouldn't work with nested tags.
    """
    logger.info(f"Removing content between tags: {start_tag} and {end_tag}")
    return re.sub(f"{re.escape(start_tag)}.*?{re.escape(end_tag)}", "", text, flags=re.DOTALL)


def remove_content_with_tags(text: str, start_tag: str, end_tag: str) -> str:
    """Remove content between specified start and end tags and return the text.
    If only start_tag is found in the text then return only the text before the start_tag. 
    And if only end_tag is found in the text then return only the text after the end_tag.

    Example: "blah<fs_think>...</fs_think>blah<fs_think>...</fs_think>blah" -> "blahblahblah"
    Example: "blah<fs_think>....." -> "blah"
    Example: "<fs_think>...</fs_think>blah" -> "blah"
    Example: "blah<fs_think>...</fs_think>" -> ""
    Example: "<fs_think>...</fs_think>" -> ""
    Example: "blah" -> "blah"
    Example: "" -> ""
    Example: None -> None
    Example: "" -> ""
    Example: "" -> ""

    NOTE: Wouldn't work with nested tags.
    """
    if start_tag in text and end_tag in text:
        return re.sub(f"{re.escape(start_tag)}.*?{re.escape(end_tag)}", "", text, flags=re.DOTALL)
    elif start_tag in text:
        return text.split(start_tag)[0]
    elif end_tag in text:
        return text.split(end_tag)[1]
    else:
        return text

def format_exception(e: Exception) -> str:
    """Format an exception to a string showing both the exception type and message."""
    return f"{type(e).__name__}: {str(e)}"

