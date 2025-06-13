"""Enhanced Simple Agent using new framework patterns with multimodal support."""
from typing import Dict

from src.agents.common.specialized_agents import MultimodalAgent
from .prompts.prompt import AGENT_PROMPT

# Export commonly used functions for backward compatibility with tests


class SimpleAgent(MultimodalAgent):
    """Enhanced Simple Agent with multimodal capabilities.
    
    Features:
    - Image analysis and description
    - Document reading and summarization  
    - Audio transcription (when supported)
    - Automatic model switching to vision-capable models
    - Built-in multimodal analysis tools
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize with automatic multimodal setup."""
        super().__init__(
            config=config,
            prompt=AGENT_PROMPT,
            vision_model="openai:gpt-4.1",  # Auto-switch to vision model when media present
            supported_media=['image', 'audio', 'document'],  # Support all media types
            auto_enhance_prompts=True  # Enable automatic prompt enhancement
        )
        
        # Register Evolution tools for backward compatibility with tests
        self.tool_registry.register_evolution_tools(self.context)


def create_agent(config: Dict[str, str]) -> SimpleAgent:
    """Factory function to create enhanced simple agent with multimodal support."""
    try:
        return SimpleAgent(config)
    except Exception:
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)