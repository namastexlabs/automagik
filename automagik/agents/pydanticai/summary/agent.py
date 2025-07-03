"""Enhanced Summary Agent using framework patterns."""
from typing import Dict

from automagik.agents.pydanticai.simple.agent import SimpleAgent as BaseSimpleAgent
from .prompts.prompt import AGENT_PROMPT


class SummaryAgent(BaseSimpleAgent):
    """Enhanced Summary Agent with Claude Sonnet-4 model."""
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Summary Agent with automatic setup."""
        super().__init__(config)
        
        # Set the prompt text
        self._code_prompt_text = AGENT_PROMPT
        
        # Override to use Claude Sonnet-4
        if hasattr(self.dependencies, 'model_name'):
            self.dependencies.model_name = "anthropic:claude-3-5-sonnet-20241022"


def create_agent(config: Dict[str, str]) -> SummaryAgent:
    """Factory function to create enhanced Summary agent."""
    try:
        return SummaryAgent(config)
    except Exception:
        from automagik.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)