"""Flashinho Old Make Agent - Refactored with BaseExternalAgent.

This shows how to use the base class to reduce boilerplate.
"""
import logging
import sys
import os
from typing import Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from base_external_agent import BaseExternalAgent
from external_agent_factory import create_external_agent
from tools import (
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy
)
from .prompts.prompt import AGENT_PROMPT

logger = logging.getLogger(__name__)


class FlashinhoOldMakeAgentRefactored(BaseExternalAgent):
    """Flashinho Old Make Agent - Simplified with base class."""
    
    # Configuration - just override class attributes
    DEFAULT_MODEL = "openai:gpt-4o-mini"
    EXTERNAL_API_KEYS = [
        ("FLASHED_API_KEY", "Flashed API authentication key"),
    ]
    EXTERNAL_URLS = [
        ("FLASHED_API_URL", "Flashed API base URL"),
    ]
    
    def _initialize_agent(self) -> None:
        """Initialize agent-specific functionality."""
        # Set the prompt
        self._code_prompt_text = AGENT_PROMPT
        
        # Register tools
        tools = [
            get_user_data, get_user_score, get_user_roadmap,
            get_user_objectives, get_last_card_round, get_user_energy
        ]
        
        for tool in tools:
            self.tool_registry.register_tool(tool)
        
        logger.debug(f"Registered {len(tools)} Flashed tools")


def create_agent(config: Dict[str, str]) -> FlashinhoOldMakeAgentRefactored:
    """Factory function using the simplified factory."""
    return create_external_agent(FlashinhoOldMakeAgentRefactored, config)