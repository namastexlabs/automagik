"""Enhanced Summary Agent using framework patterns."""
from typing import Dict

from src.agents.pydanticai.simple.agent import SimpleAgent as BaseSimpleAgent
from .prompts.prompt import AGENT_PROMPT


class SummaryAgent(BaseSimpleAgent):
    """Enhanced Summary Agent with Claude Sonnet-4 model."""
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize with automatic setup via ChannelHandler system."""
        # Use Claude Sonnet-4 for summary tasks
        super().__init__(config, AGENT_PROMPT)
        
        # Override to use Claude Sonnet-4
        if hasattr(self.dependencies, 'model_name'):
            self.dependencies.model_name = "anthropic:claude-3-5-sonnet-20241022"


def create_agent(config: Dict[str, str]) -> SummaryAgent:
    """Factory function to create enhanced Summary agent."""
    try:
        return SummaryAgent(config)
    except Exception:
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)