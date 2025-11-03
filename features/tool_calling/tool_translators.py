"""Tool definition translators for different LLM providers."""
from typing import Any

from llm.domain.enums import ToolPropertyType
from llm.domain.models import ToolDefinition, ToolParameter


def validate_tool_parameter(tool_param: ToolParameter):
    """Validate a tool parameter."""
    if tool_param.type != ToolPropertyType.ARRAY and tool_param.items:
        raise ValueError("The type must be array if `items` is non-empty.")
    if tool_param.type != ToolPropertyType.OBJECT and tool_param.properties:
        raise ValueError("The type must be object if `properties` is non-empty.")
    if tool_param.type == ToolPropertyType.ARRAY and not tool_param.items:
        raise ValueError("If type is array, `items` cannot be empty.")
    if tool_param.type == ToolPropertyType.OBJECT and not tool_param.properties:
        raise ValueError("If type is object, `properties` cannot be empty.")


def format_common_properties(tool_param: ToolParameter) -> dict[str, Any]:
    """Format common properties for a tool parameter."""
    data = {"type": tool_param.type.value}
    if tool_param.description:
        data["description"] = tool_param.description
    if tool_param.enum:
        data["enum"] = tool_param.enum
    return data


def format_nested_property_for_gemini_api(tool_param: ToolParameter) -> dict[str, Any]:
    """Recursively format a ToolParameter into the Gemini API's required schema."""
    validate_tool_parameter(tool_param)
    data = format_common_properties(tool_param)
    if tool_param.type == ToolPropertyType.ARRAY:
        data["items"] = format_nested_property_for_gemini_api(tool_param.items)  # type: ignore[arg-type]

    elif tool_param.type == ToolPropertyType.OBJECT:
        data["properties"] = {k: format_nested_property_for_gemini_api(v) for k, v in tool_param.properties.items()}  # type: ignore[union-attr]
        # The 'required' list contains names of mandatory nested properties.
        required_properties = [k for k, v in tool_param.properties.items() if v.is_required]  # type: ignore[union-attr]
        if required_properties:
            data["required"] = required_properties

    return data


def format_tool_definition_for_gemini_api(tool: ToolDefinition) -> dict[str, Any]:
    """Format a ToolDefinition into the full function declaration schema required by the Google Gemini API.
    Reference: https://ai.google.dev/gemini-api/docs/function-calling#function_declarations
    """
    # The top-level parameters object is always of type 'object'.
    parameters_schema = {
        "type": ToolPropertyType.OBJECT.value,
        "properties": {k: format_nested_property_for_gemini_api(v) for k, v in tool.parameters.items()},
    }

    # The top-level 'required' list contains names of mandatory direct parameters.
    required_params = [k for k, v in tool.parameters.items() if v.is_required]
    if required_params:
        parameters_schema["required"] = required_params
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": parameters_schema,
    }

