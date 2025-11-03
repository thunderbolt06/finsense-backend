"""Simple prompt template."""
from typing import Any


class Prompt(str):
    """A prompt is just a string."""
    pass


class PromptTemplate:
    """Simple prompt template."""
    
    def __init__(self, name: str, template: str):
        self.name = name
        self.template = template
    
    def format(self, **kwargs: Any) -> Prompt:
        """Format the template with the given kwargs."""
        return Prompt(self.template.format(**kwargs))

