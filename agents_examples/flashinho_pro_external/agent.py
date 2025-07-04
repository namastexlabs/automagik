"""Flashinho Pro External Agent - Refactored with BaseExternalAgent.

This is the same as flashinho_pro but demonstrates external agent pattern.
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
    # Flashed tools
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy,
    get_user_by_pretty_id,
    FlashedProvider,
    UserStatusChecker, preserve_authentication_state, restore_authentication_state,
    identify_user_comprehensive, UserIdentificationResult,
    ensure_user_uuid_matches_flashed_id, make_session_persistent,
    analyze_student_problem,
    generate_math_processing_message, generate_pro_feature_message,
    generate_error_message,
    # Evolution tools
    send_text_message
)
from .prompts.prompt import AGENT_PROMPT, AGENT_FREE

logger = logging.getLogger(__name__)


class FlashinhoProExternalRefactored(BaseExternalAgent):
    """Flashinho Pro External with simplified initialization."""
    
    # Configuration
    DEFAULT_MODEL = "google:gemini-2.5-pro"
    EXTERNAL_API_KEYS = [
        ("FLASHED_API_KEY", "Flashed API authentication key"),
        ("GEMINI_API_KEY", "Google Gemini API key"),
    ]
    EXTERNAL_URLS = [
        ("FLASHED_API_URL", "Flashed API base URL"),
        ("EVOLUTION_API_URL", "Evolution API URL"),
    ]
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize with Pro/Free model setup."""
        # Set up model defaults BEFORE calling super().__init__
        self.pro_model = "google:gemini-2.5-pro"
        self.free_model = "google:gemini-2.5-flash"
        
        # Initialize state flags
        self._user_status_checked = False
        self._is_pro_user = False
        
        # Call parent initialization
        super().__init__(config)
    
    def _initialize_agent(self) -> None:
        """Initialize agent-specific functionality."""
        # Set initial prompt (will be updated based on Pro status)
        self._code_prompt_text = AGENT_PROMPT
        
        # Initialize providers
        self.flashed_provider = FlashedProvider()
        self.user_status_checker = UserStatusChecker()
        
        # Register Flashed tools
        flashed_tools = [
            get_user_data, get_user_score, get_user_roadmap,
            get_user_objectives, get_last_card_round, get_user_energy,
            get_user_by_pretty_id
        ]
        for tool in flashed_tools:
            self.tool_registry.register_tool(tool)
        
        # Register multimodal tools
        self._register_multimodal_tools()
        
        logger.info("Flashinho Pro External initialized with dynamic model selection")
    
    def _register_multimodal_tools(self):
        """Register multimodal analysis tools using common helper."""
        from automagik.agents.common.multimodal_helper import register_multimodal_tools
        register_multimodal_tools(self.tool_registry, self.dependencies)
    
    # Note: For full functionality like flashinho_pro, you would copy all the
    # async methods from flashinho_pro/agent.py here.
    # This is just the initialization part to show the pattern.


def create_agent(config: Dict[str, str]) -> FlashinhoProExternalRefactored:
    """Factory function using the simplified factory."""
    return create_external_agent(FlashinhoProExternalRefactored, config)