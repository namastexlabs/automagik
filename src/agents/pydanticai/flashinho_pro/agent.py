"""Flashinho Pro Agent - Advanced multimodal Brazilian educational assistant.

This agent combines the authentic Brazilian educational coaching personality of Flashinho
with advanced multimodal capabilities powered by Google Gemini 2.5 Pro model.
"""
import logging
from typing import Dict, Optional

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.response import AgentResponse
from src.memory.message_history import MessageHistory
from src.tools.flashed.tool import (
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy
)
from src.tools.flashed.provider import FlashedProvider
from .prompts.prompt import AGENT_PROMPT, AGENT_FREE
from .memory_manager import update_flashinho_pro_memories, initialize_flashinho_pro_memories

logger = logging.getLogger(__name__)


class FlashinhoPro(AutomagikAgent):
    """Advanced multimodal Brazilian educational assistant powered by Google Gemini 2.5 Pro.
    
    Features:
    - Authentic Brazilian Generation Z Portuguese coaching style
    - Multimodal processing: images, audio, documents for educational content
    - Complete Flashed API integration for educational gaming
    - WhatsApp/Evolution channel integration for media handling
    - Cultural authenticity for Brazilian high school students
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Flashinho Pro with multimodal and Gemini configuration."""
        if config is None:
            config = {}

        # default/fallback models
        self.pro_model = "google-gla:gemini-2.5-pro-preview-05-06"
        self.free_model = "google-gla:gemini-2.5-flash-preview-05-20"

        config.setdefault("model", self.pro_model)
        config.setdefault("vision_model", self.pro_model)
        config.setdefault("supported_media", ["image", "audio", "document"])
        config.setdefault("auto_enhance_prompts", True)
        config.setdefault("enable_multi_prompt", True)

        super().__init__(config)

        self._code_prompt_text = AGENT_PROMPT

        # setup dependencies
        self.dependencies = self.create_default_dependencies()
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        self.tool_registry.register_default_tools(self.context)
        
        # Register Flashed API tools for educational context
        self._register_flashed_tools()
        
        # Flag to track if we've checked user status
        self._user_status_checked = False
        # Default to non-pro until verified
        self._is_pro_user = False
        
        # Initialize provider
        self.flashed_provider = FlashedProvider()
        
        logger.info("Flashinho Pro initialized with dynamic model selection based on user status")
    
    def _register_flashed_tools(self) -> None:
        """Register all 6 Flashed API tools for educational gaming functionality."""
        # Register tools using the tool registry (same method used by MultimodalAgent)
        self.tool_registry.register_tool(get_user_data)
        self.tool_registry.register_tool(get_user_score)
        self.tool_registry.register_tool(get_user_roadmap)
        self.tool_registry.register_tool(get_user_objectives)
        self.tool_registry.register_tool(get_last_card_round)
        self.tool_registry.register_tool(get_user_energy)
        
        logger.debug("Registered 6 Flashed API tools")
    
    async def _check_user_pro_status(self, user_id: Optional[str] = None) -> bool:
        """Check if user has Pro subscription status.
        
        Args:
            user_id: User ID to check
            
        Returns:
            Boolean indicating if user has Pro status
        """
        try:
            if not user_id:
                logger.warning("No user ID available to check Pro status, defaulting to non-Pro")
                return False
                
            # Use the Flashed API to check user subscription status
            return await self.flashed_provider.check_user_pro_status(user_id)
                
        except Exception as e:
            logger.error(f"Error checking Pro status for user {user_id}: {str(e)}")
            # Default to non-Pro on errors
            return False
    
    async def _update_model_and_prompt_based_on_status(self, user_id: Optional[str] = None) -> None:
        """Update model and prompt based on user's Pro status.
        
        Args:
            user_id: User ID to check
        """
        # Skip if we've already checked this session
        if self._user_status_checked:
            return
            
        # Check user Pro status
        self._is_pro_user = await self._check_user_pro_status(user_id)
        self._user_status_checked = True
        
        # Update model and prompt based on status
        if self._is_pro_user:
            # Pro user - use Pro model and prompt
            self.model_name = self.pro_model
            self.system_message = AGENT_PROMPT
            # Update vision model
            self.vision_model = self.pro_model
            # Ensure the model is properly set for the LLM client
            if hasattr(self, 'llm_client') and hasattr(self.llm_client, 'model'):
                self.llm_client.model = self.pro_model
            # Update dependencies if they exist
            if hasattr(self, 'dependencies'):
                if hasattr(self.dependencies, 'model_name'):
                    self.dependencies.model_name = self.pro_model
                if hasattr(self.dependencies, 'llm_client') and hasattr(self.dependencies.llm_client, 'model'):
                    self.dependencies.llm_client.model = self.pro_model
                # Ensure the prompt is set in dependencies if applicable
                if hasattr(self.dependencies, 'prompt'):
                    self.dependencies.prompt = AGENT_PROMPT
            logger.info(f"User {user_id} is a Pro user. Using model: {self.pro_model}")
        else:
            # Free user - use Free model and prompt
            self.model_name = self.free_model
            self.system_message = AGENT_FREE
            # Update vision model for multimodal content
            self.vision_model = self.free_model
            # Ensure the model is properly set for the LLM client
            if hasattr(self, 'llm_client') and hasattr(self.llm_client, 'model'):
                self.llm_client.model = self.free_model
            # Update dependencies if they exist
            if hasattr(self, 'dependencies'):
                if hasattr(self.dependencies, 'model_name'):
                    self.dependencies.model_name = self.free_model
                if hasattr(self.dependencies, 'llm_client') and hasattr(self.dependencies.llm_client, 'model'):
                    self.dependencies.llm_client.model = self.free_model
                # Ensure the prompt is set in dependencies if applicable
                if hasattr(self.dependencies, 'prompt'):
                    self.dependencies.prompt = AGENT_FREE
            logger.info(f"User {user_id} is a Free user. Using model: {self.free_model}")
    
    async def _ensure_user_memories_ready(self, user_id: Optional[str] = None) -> None:
        """Ensure user memories are initialized and updated for prompt variables.
        
        Args:
            user_id: User ID for user-specific memories
        """
        try:
            if not self.db_id:
                logger.warning("No agent database ID available, skipping memory initialization")
                return
                
            # Initialize default memories if they don't exist
            await initialize_flashinho_pro_memories(self.db_id, user_id)
            
            # Update memories with current user data from Flashed API
            success = await update_flashinho_pro_memories(self.db_id, user_id, self.context)
            
            if success:
                logger.info(f"Successfully updated Flashinho Pro memories for user {user_id}")
            else:
                logger.warning(f"Failed to update some Flashinho Pro memories for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error ensuring user memories ready: {str(e)}")
            # Continue with default memories - the framework will handle missing variables
    
    async def run(
        self, 
        input_text: str, 
        *, 
        multimodal_content=None, 
        system_message=None, 
        message_history_obj: Optional[MessageHistory] = None,
        channel_payload: Optional[dict] = None,
        message_limit: Optional[int] = 20
    ) -> AgentResponse:
        """Enhanced run method with user identification and memory-based personalization."""
        
        try:
            # Extract user information from context (populated by Evolution handler)
            user_id = self.context.get("user_id") or self.context.get("flashed_user_id")
            whatsapp_phone = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
            whatsapp_name = self.context.get("whatsapp_user_name") or self.context.get("user_name")
            
            logger.info(f"Flashinho Pro processing message from {whatsapp_name} ({whatsapp_phone})")
            
            # Check user Pro status and update model/prompt accordingly
            await self._update_model_and_prompt_based_on_status(user_id)
            
            # Ensure user memories are ready
            await self._ensure_user_memories_ready(user_id)
            
            # Use the enhanced framework to handle execution
            return await self._run_agent(
                input_text=input_text,
                system_prompt=system_message,  # Framework will use appropriate prompt with memory substitution
                message_history=message_history_obj.get_formatted_pydantic_messages(limit=message_limit) if message_history_obj else [],
                multimodal_content=multimodal_content,
                channel_payload=channel_payload,
                message_limit=message_limit
            )
            
        except Exception as e:
            logger.error(f"Error in Flashinho Pro run method: {str(e)}")
            # Fallback to basic execution - framework will still handle memory substitution
            return await self._run_agent(
                input_text=input_text,
                system_prompt=system_message,
                message_history=message_history_obj.get_formatted_pydantic_messages(limit=message_limit) if message_history_obj else [],
                multimodal_content=multimodal_content,
                channel_payload=channel_payload,
                message_limit=message_limit
            )


def create_agent(config: Dict[str, str]) -> FlashinhoPro:
    """Factory function to create Flashinho Pro agent instance."""
    try:
        return FlashinhoPro(config)
    except Exception as e:
        logger.error(f"Failed to create Flashinho Pro Agent: {e}")
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)