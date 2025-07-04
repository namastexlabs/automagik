"""Flashinho The First Agent - Refactored with BaseExternalAgent.

This is flashinho_v2 refactored to use the base class pattern.
"""
import logging
import sys
import os
from typing import Dict, Optional
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from base_external_agent import BaseExternalAgent
from external_agent_factory import create_external_agent
from tools import (
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy,
    get_user_by_pretty_id,
    FlashedProvider,
    UserStatusChecker,
    build_external_key,
    attach_user_by_external_key,
    attach_user_by_flashed_id_lookup,
    find_user_by_whatsapp_id,
    user_has_conversation_code,
    identify_user_comprehensive,
    UserIdentificationResult,
    ensure_user_uuid_matches_flashed_id
)
from .prompts import AGENT_PROMPT_DEFAULT, AGENT_PROMPT_PRO

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for model selection based on user status."""
    model_name: str
    vision_model: str
    system_message: str


class FlashinhoTheFirstRefactored(BaseExternalAgent):
    """Flashinho The First (V2) with simplified initialization."""
    
    # Configuration
    DEFAULT_MODEL = "google:gemini-2.5-pro"  # This will be the Pro model
    SUPPORTED_MEDIA = ["image", "audio", "document"]
    EXTERNAL_API_KEYS = [
        ("FLASHED_API_KEY", "Flashed API authentication key"),
        ("GEMINI_API_KEY", "Google Gemini API key"),
    ]
    EXTERNAL_URLS = [
        ("FLASHED_API_URL", "Flashed API base URL"),
    ]
    
    # Model constants
    PRO_MODEL = "google:gemini-2.5-pro"
    FREE_MODEL = "google:gemini-2.5-flash"
    
    def _initialize_agent(self) -> None:
        """Initialize agent-specific functionality."""
        # Set default prompt
        self._code_prompt_text = AGENT_PROMPT_DEFAULT
        
        # Initialize user status tracking
        self._user_status_checked = False
        self._is_pro_user = False
        self.flashed_provider = FlashedProvider()
        
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
        
        logger.debug(f"Registered {len(flashed_tools)} Flashed API tools")
    
    def _register_multimodal_tools(self):
        """Register multimodal analysis tools using common helper."""
        from automagik.agents.common.multimodal_helper import register_multimodal_tools
        register_multimodal_tools(self.tool_registry, self.dependencies)
    
    async def _check_user_pro_status(self, user_id: Optional[str] = None) -> bool:
        """Check if user has Pro subscription status."""
        if not user_id:
            logger.warning("No user ID available to check Pro status, defaulting to non-Pro")
            return False
        
        try:
            return await self.flashed_provider.check_user_pro_status(user_id)
        except Exception as e:
            logger.error(f"Error checking Pro status for user {user_id}: {str(e)}")
            return False
    
    def _create_model_config(self, is_pro_user: bool) -> ModelConfig:
        """Create model configuration based on user status."""
        if is_pro_user:
            return ModelConfig(
                model_name=self.PRO_MODEL,
                vision_model=self.PRO_MODEL,
                system_message=AGENT_PROMPT_PRO
            )
        else:
            return ModelConfig(
                model_name=self.FREE_MODEL,
                vision_model=self.FREE_MODEL,
                system_message=AGENT_PROMPT_DEFAULT
            )
    
    # Note: For full functionality, you would copy all the async methods
    # from the original agent.py here, similar to flashinho_pro_refactored.py


def create_agent(config: Dict[str, str]) -> FlashinhoTheFirstRefactored:
    """Factory function using the simplified factory."""
    return create_external_agent(FlashinhoTheFirstRefactored, config)