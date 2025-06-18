"""Flashinho V2 Agent - Advanced multimodal Brazilian educational assistant.

This agent combines the authentic Brazilian educational coaching personality of Flashinho
with advanced multimodal capabilities powered by Google Gemini 2.5 Pro model.
"""
import logging
from typing import Dict, Optional, Any

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.response import AgentResponse
from src.memory.message_history import MessageHistory
from src.tools.flashed.tool import (
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy,
    get_user_by_pretty_id
)
from src.tools.flashed.provider import FlashedProvider
from .prompts.prompt import AGENT_FREE, AGENT_PROMPT
from .memory_manager import update_flashinho_pro_memories, initialize_flashinho_pro_memories
from .user_identification import FlashinhoProUserMatcher

logger = logging.getLogger(__name__)


class FlashinhoV2(AutomagikAgent):
    """Advanced multimodal Brazilian educational assistant powered by Google Gemini 2.5 Pro.
    
    Features:
    - Authentic Brazilian Generation Z Portuguese coaching style
    - Multimodal processing: images, audio, documents for educational content
    - Complete Flashed API integration for educational gaming
    - WhatsApp/Evolution channel integration for media handling
    - Cultural authenticity for Brazilian high school students
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Flashinho V2 with multimodal and Gemini configuration."""
        if config is None:
            config = {}

        # default/fallback models - DEFAULT TO FREE MODEL
        self.pro_model = "google-gla:gemini-2.5-pro-preview-05-06"
        self.free_model = "google-gla:gemini-2.5-flash-preview-05-20"

        config.setdefault("model", self.free_model)  # Changed: default to FREE model
        config.setdefault("vision_model", self.free_model)  # Changed: default to FREE model
        config.setdefault("supported_media", ["image", "audio", "document"])
        config.setdefault("auto_enhance_prompts", True)
        config.setdefault("enable_multi_prompt", True)

        super().__init__(config)

        self._code_prompt_text = AGENT_FREE

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
        
        logger.info("Flashinho V2 initialized with dynamic model selection based on user status")
    
    def _register_flashed_tools(self) -> None:
        """Register all Flashed API tools for educational gaming functionality."""
        # Register tools using the tool registry (same method used by MultimodalAgent)
        self.tool_registry.register_tool(get_user_data)
        self.tool_registry.register_tool(get_user_score)
        self.tool_registry.register_tool(get_user_roadmap)
        self.tool_registry.register_tool(get_user_objectives)
        self.tool_registry.register_tool(get_last_card_round)
        self.tool_registry.register_tool(get_user_energy)
        self.tool_registry.register_tool(get_user_by_pretty_id)
        
        logger.debug("Registered 7 Flashed API tools including prettyId lookup")
    
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
    
    async def _check_for_prettyid_identification(self, input_text: str) -> Optional[str]:
        """Check if the message contains a prettyId and update context accordingly.
        
        Args:
            input_text: The user's message text
            
        Returns:
            User ID if found via prettyId, None otherwise
        """
        try:
            # Use the user matcher to detect prettyId and fetch user data
            matcher = FlashinhoProUserMatcher(self.context)
            pretty_id = matcher.extract_pretty_id_from_message(input_text)
            
            if pretty_id:
                logger.info(f"Detected prettyId in message: {pretty_id}")
                
                # Fetch user data using the prettyId
                user_data = await matcher._find_user_by_pretty_id(pretty_id)
                
                if user_data and user_data.get("user", {}).get("id"):
                    user_id = user_data["user"]["id"]
                    
                    # Update context with user information
                    self.context["flashed_user_id"] = user_id
                    self.context["user_identification_method"] = "prettyId"
                    self.context["pretty_id"] = pretty_id
                    self.context["flashed_conversation_code"] = pretty_id
                    
                    # Update context with additional user data
                    user_info = user_data["user"]
                    if user_info.get("name"):
                        self.context["user_name"] = user_info["name"]
                        self.context["whatsapp_user_name"] = user_info["name"]
                    if user_info.get("phone"):
                        self.context["user_phone_number"] = user_info["phone"]
                        self.context["whatsapp_user_number"] = user_info["phone"]
                    if user_info.get("email"):
                        self.context["user_email"] = user_info["email"]
                    
                    # Ensure user exists in our database with the correct UUID and conversation code
                    await self._ensure_user_in_database(user_id, pretty_id, user_info)
                    
                    # Update the main user_id in context to match Flashed API
                    self.context["user_id"] = user_id
                    
                    logger.info(f"Successfully identified user via prettyId {pretty_id}: {user_id}")
                    logger.info(f"Updated context with user data: name={user_info.get('name')}, phone={user_info.get('phone')}")
                    
                    return user_id
                else:
                    logger.warning(f"No user data found for prettyId: {pretty_id}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking for prettyId identification: {str(e)}")
            return None
    
    async def _ensure_user_in_database(self, flashed_user_id: str, conversation_code: str, user_info: Dict[str, Any]) -> None:
        """Ensure user exists in our database with correct UUID and conversation code.
        
        Args:
            flashed_user_id: The Flashed API user UUID
            conversation_code: The conversation code (prettyId)
            user_info: User information from Flashed API
        """
        try:
            from src.db.repository.user import get_user, create_user, update_user_data
            from src.db.models import User
            from datetime import datetime
            import uuid
            
            # Convert to UUID object
            user_uuid = uuid.UUID(flashed_user_id)
            
            # Check if user already exists
            existing_user = get_user(user_uuid)
            
            if existing_user:
                # User exists, update their data to include conversation code
                current_user_data = existing_user.user_data or {}
                needs_update = False
                
                # Ensure flashed_user_id is stored
                if current_user_data.get("flashed_user_id") != flashed_user_id:
                    current_user_data["flashed_user_id"] = flashed_user_id
                    needs_update = True
                
                # Store/update conversation code
                if current_user_data.get("flashed_conversation_code") != conversation_code:
                    current_user_data["flashed_conversation_code"] = conversation_code
                    needs_update = True
                    logger.info(f"Updating conversation code for user {user_uuid}: {conversation_code}")
                
                # Update name if available and not set
                if user_info.get("name") and not current_user_data.get("name"):
                    current_user_data["name"] = user_info["name"]
                    needs_update = True
                
                if needs_update:
                    update_user_data(user_uuid, current_user_data)
                    logger.info(f"Updated user {user_uuid} with conversation code and latest info")
                
            else:
                # Create new user with the Flashed UUID as primary key
                user_data = {
                    "flashed_user_id": flashed_user_id,
                    "flashed_conversation_code": conversation_code
                }
                
                if user_info.get("name"):
                    user_data["name"] = user_info["name"]
                
                user_model = User(
                    id=user_uuid,
                    email=user_info.get("email"),
                    phone_number=user_info.get("phone"),
                    user_data=user_data,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                created_id = create_user(user_model)
                if created_id:
                    logger.info(f"Created new user {user_uuid} with conversation code {conversation_code}")
                else:
                    logger.error(f"Failed to create user {user_uuid}")
                    
        except Exception as e:
            logger.error(f"Error ensuring user in database: {str(e)}")
            # Don't raise - continue with agent execution even if DB update fails
    
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
                logger.info(f"Successfully updated Flashinho V2 memories for user {user_id}")
            else:
                logger.warning(f"Failed to update some Flashinho V2 memories for user {user_id}")
                
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
            # First check for prettyId in the message and update context if found
            prettyid_user_id = await self._check_for_prettyid_identification(input_text)
            
            # Extract user information from context (populated by Evolution handler or prettyId detection)
            user_id = (
                prettyid_user_id or 
                self.context.get("user_id") or 
                self.context.get("flashed_user_id")
            )
            whatsapp_phone = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
            whatsapp_name = self.context.get("whatsapp_user_name") or self.context.get("user_name")
            
            # Log identification method for debugging
            identification_method = self.context.get("user_identification_method", "context")
            logger.info(f"Flashinho V2 processing message from {whatsapp_name} ({whatsapp_phone}) - User ID: {user_id} via {identification_method}")
            
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
            logger.error(f"Error in Flashinho V2 run method: {str(e)}")
            # Fallback to basic execution - framework will still handle memory substitution
            return await self._run_agent(
                input_text=input_text,
                system_prompt=system_message,
                message_history=message_history_obj.get_formatted_pydantic_messages(limit=message_limit) if message_history_obj else [],
                multimodal_content=multimodal_content,
                channel_payload=channel_payload,
                message_limit=message_limit
            )


def create_agent(config: Dict[str, str]) -> FlashinhoV2:
    """Factory function to create Flashinho V2 agent instance."""
    try:
        return FlashinhoV2(config)
    except Exception as e:
        logger.error(f"Failed to create Flashinho V2 Agent: {e}")
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)