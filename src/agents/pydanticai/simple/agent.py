"""Enhanced Simple Agent using new framework patterns with multimodal support."""
from typing import Dict, List

from src.agents.models.automagik_agent import AutomagikAgent
from .prompts.prompt import AGENT_PROMPT

# Export commonly used functions for backward compatibility with tests
from src.agents.common.message_parser import (
    extract_all_messages,
    extract_tool_calls,
    extract_tool_outputs,
)


class SimpleAgent(AutomagikAgent):
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
        # inject multimodal defaults
        if config is None:
            config = {}
        config.setdefault("vision_model", "openai:gpt-4o")
        config.setdefault("supported_media", ["image", "audio", "document"])
        config.setdefault("auto_enhance_prompts", True)

        super().__init__(config)

        self._code_prompt_text = AGENT_PROMPT

        # dependencies setup
        self.dependencies = self.create_default_dependencies()
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)

        # Register default tools
        self.tool_registry.register_default_tools(self.context)

        # Register Evolution WhatsApp helpers for parity with Sofia
        self.tool_registry.register_evolution_tools(self.context)

        # Register multimodal tools using common helper
        self._register_multimodal_tools()

    def _register_multimodal_tools(self):
        """Register multimodal analysis tools using common helper."""
        from src.agents.common.multimodal_helper import register_multimodal_tools
        register_multimodal_tools(self.tool_registry, self.dependencies)


def create_agent(config: Dict[str, str]) -> SimpleAgent:
    """Factory function to create enhanced simple agent with multimodal support."""
    try:
        return SimpleAgent(config)
    except Exception:
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)