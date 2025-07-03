"""Flashinho Agent - Basic educational assistant for Brazilian students.

This is a client-specific agent with self-contained tools.
"""
import logging
import os
from typing import Dict

from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.response import AgentResponse
from automagik.agents.models.dependencies import AutomagikAgentsDependencies
from automagik.memory.message_history import MessageHistory

# Import tools from local tools directory
from .tools.flashed.tool import (
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy
)
from .prompts.prompt import AGENT_PROMPT

logger = logging.getLogger(__name__)


class FlashinhoAgent(AutomagikAgent):
    """Flashinho Agent - Basic educational assistant for Brazilian students.
    
    This is a client-specific agent with self-contained tools.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Flashinho Agent with configuration."""
        if config is None:
            config = {}

        # Default model
        self.default_model = "openai:gpt-4o-mini"
        config.setdefault("supported_media", ["image", "audio", "document"])
        
        super().__init__(config)

        self._code_prompt_text = AGENT_PROMPT

        # Setup dependencies
        self.dependencies = AutomagikAgentsDependencies(
            model_name=self.default_model,
            model_settings={
                "temperature": 0.7,
                "max_tokens": 2048
            },
            api_keys={
                "openai_api_key": os.environ.get("OPENAI_API_KEY", "")
            },
            tool_config={}
        )
        
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
            
        self.tool_registry.register_default_tools(self.context)
        
        # Register Flashed API tools
        self._register_flashed_tools()
        
        logger.info("Flashinho Agent initialized")
    
    def _register_flashed_tools(self) -> None:
        """Register all Flashed API tools."""
        self.tool_registry.register_tool(get_user_data)
        self.tool_registry.register_tool(get_user_score)
        self.tool_registry.register_tool(get_user_roadmap)
        self.tool_registry.register_tool(get_user_objectives)
        self.tool_registry.register_tool(get_last_card_round)
        self.tool_registry.register_tool(get_user_energy)
        logger.debug("Flashed tools registered")


def create_agent(config: Dict[str, str]) -> FlashinhoAgent:
    """Factory function to create enhanced Flashinho agent."""
    try:
        return FlashinhoAgent(config)
    except Exception as e:
        logger.error(f"Failed to create Enhanced Flashinho Agent: {e}")
        from automagik.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)