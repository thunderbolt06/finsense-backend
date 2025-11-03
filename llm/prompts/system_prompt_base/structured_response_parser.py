"""Parser for structured agent responses."""
import json
from typing import Any

from utils.logging import logger
from utils.strings import extract_json_object


class StructuredAgentResponse:
    """Parsed structured agent response."""
    
    def __init__(self, data: dict[str, Any]):
        self.initial_analysis = data.get("initial_analysis", {})
        self.user_facing_text = data.get("user_facing_text", "")
        self.final_internal = data.get("final_internal", {})
    
    @property
    def status(self) -> str:
        """Get status (E, N, M)."""
        return self.initial_analysis.get("status", "E")
    
    @property
    def estimated_steps(self) -> int:
        """Get estimated remaining steps."""
        return self.initial_analysis.get("estimated_steps", 0)
    
    @property
    def tags(self) -> list[str]:
        """Get tags."""
        return self.initial_analysis.get("tags", [])
    
    @property
    def is_final(self) -> bool:
        """Check if this is a final answer."""
        return self.status == "E" and self.estimated_steps == 0
    
    @property
    def is_continuing(self) -> bool:
        """Check if agent is continuing to next step."""
        return self.estimated_steps > 0 and self.final_internal.get("questions_count", 0) == 0
    
    @property
    def routing_info(self) -> dict[str, Any] | None:
        """Get routing info if continuing."""
        return self.final_internal.get("routing_info")
    
    @property
    def questions_count(self) -> int:
        """Get number of questions asked."""
        return self.final_internal.get("questions_count", 0)
    
    @property
    def self_critique(self) -> str:
        """Get self-critique."""
        return self.final_internal.get("self_critique", "")
    
    def format_for_display(self) -> str:
        """Format response for display (reconstructing fs_think tags for compatibility)."""
        # Build initial analysis string
        status_str = self.status
        steps_str = str(self.estimated_steps)
        tags_str = " ".join(self.tags) if self.tags else ""
        initial_analysis = f"{status_str}{steps_str}"
        if tags_str:
            initial_analysis += f" {tags_str}"
        
        # Add date and flags if present
        if self.initial_analysis.get("simple_date"):
            initial_analysis += f" {self.initial_analysis['simple_date']}"
        if self.initial_analysis.get("has_links"):
            initial_analysis += " L"
        if self.initial_analysis.get("no_results"):
            initial_analysis += " 0R"
        
        # Build final internal portion
        final_parts = [f"Q{self.questions_count}"]
        if self.self_critique:
            final_parts.append(self.self_critique)
        
        # Add routing info if continuing
        if self.routing_info:
            routing_json = json.dumps(self.routing_info, separators=(",", ":"))
            final_parts.append(routing_json)
        
        final_internal = " ".join(final_parts)
        
        # Reconstruct with fs_think tags for compatibility
        return f"<fs_think>{initial_analysis}</fs_think>{self.user_facing_text}<fs_think>{final_internal}</fs_think>"
    
    def to_modalities_list(self) -> list[dict[str, Any]]:
        """Extract modalities as a list for execution."""
        if not self.routing_info:
            return []
        
        modalities = []
        
        # Add first modality
        if first_modality := self.routing_info.get("first_modality"):
            modalities.append(self._clean_modality(first_modality))
        
        # Add parallel modalities
        if parallel := self.routing_info.get("additional_parallel_modalities"):
            modalities.extend([self._clean_modality(m) for m in parallel])
        
        return modalities
    
    def _clean_modality(self, modality: dict[str, Any]) -> dict[str, Any]:
        """Clean modality dict, removing None values."""
        cleaned = {}
        for key, value in modality.items():
            if value is not None:
                cleaned[key] = value
        return cleaned


def parse_structured_response(response_text: str) -> StructuredAgentResponse:
    """Parse structured response from Gemini.
    
    Uses extract_json_object to handle edge cases like double braces {{ }} that
    LLMs sometimes produce when copying from prompt templates.
    """
    try:
        # Use extract_json_object to handle edge cases (double braces, trailing commas, etc.)
        data = extract_json_object(response_text)
        return StructuredAgentResponse(data)
    except ValueError as e:
        logger.error(f"Failed to parse structured response: {e}")
        logger.error(f"Response text: {response_text[:500]}")
        # Return a default response
        return StructuredAgentResponse({
            "initial_analysis": {
                "status": "E",
                "estimated_steps": 0,
                "simple_date": "",
            },
            "user_facing_text": response_text or "Error parsing structured response",
            "final_internal": {
                "questions_count": 0,
                "self_critique": "Parse error",
            }
        })


def extract_structured_response_from_gemini(response: Any) -> StructuredAgentResponse | None:
    """Extract structured response from Gemini API response object."""
    try:
        # Check if response has structured output
        if hasattr(response, "text"):
            text = response.text
            if text:
                return parse_structured_response(text)
        
        # Check candidates for structured content
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content:
                if hasattr(candidate.content, "parts") and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "text") and part.text:
                            return parse_structured_response(part.text)
        
        return None
    except Exception as e:
        logger.error(f"Error extracting structured response: {e}", exc_info=True)
        return None

