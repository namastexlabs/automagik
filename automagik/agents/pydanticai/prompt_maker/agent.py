"""Enhanced Prompt Maker Agent using framework patterns."""
from typing import Dict

from automagik.agents.pydanticai.simple.agent import SimpleAgent as BaseSimpleAgent
from .prompts.prompt import AGENT_PROMPT


class PromptMakerAgent(BaseSimpleAgent):
    """Enhanced Prompt Maker Agent for creating high-quality prompts."""
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize PromptMaker Agent with automatic setup."""
        super().__init__(config)
        
        # Set the prompt text
        self._code_prompt_text = AGENT_PROMPT


def create_agent(config: Dict[str, str]) -> PromptMakerAgent:
    """Factory function to create enhanced Prompt Maker agent."""
    try:
        return PromptMakerAgent(config)
    except Exception:
        from automagik.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)