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
        """Enhanced run method with conversation code requirement and memory-based personalization."""
        
        try:
            # First check if user has conversation code in their user_data
            user_id = self.context.get("user_id")
            requires_conversation_code = await self._check_conversation_code_requirement(user_id)
            
            if requires_conversation_code:
                # User needs to provide conversation code first
                conversation_code_request = self._generate_conversation_code_request()
                
                return AgentResponse(
                    text=conversation_code_request,
                    success=True,
                    usage={
                        "model": self.free_model,
                        "request_tokens": 0,
                        "response_tokens": 0,
                        "total_tokens": 0
                    }
                )
            
            # Extract user information from context (populated by Evolution handler)
            user_id = self.context.get("user_id")
            user_phone = self.context.get("user_phone_number") or self.context.get("whatsapp_user_number")
            user_name = self.context.get("user_name") or self.context.get("whatsapp_user_name")
            
            # Check Pro status and update model/prompt if we have user info
            if user_id:
                await self._update_model_and_prompt_based_on_status(user_id)
                
                # Ensure user memories are ready for prompt template variables
                await self._ensure_user_memories_ready(user_id)
            
            # Log context information for debugging
            logger.info(f"Running agent with user_id: {user_id}, phone: {user_phone}, name: {user_name}")
            logger.info(f"Using model: {self.model_name}, tools: {len(self.agent.tools) if hasattr(self.agent, 'tools') else 'unknown'}")
            
            # Use parent's run method for the actual execution
            return await super().run(
                input_text,
                multimodal_content=multimodal_content,
                system_message=system_message,
                message_history_obj=message_history_obj,
                channel_payload=channel_payload,
                message_limit=message_limit
            )
            
        except Exception as e:
            logger.error(f"Error in FlashinhoV2 run method: {str(e)}")
            # Fallback to basic response
            return AgentResponse(
                text=f"Desculpa, mano! Tive um probleminha técnico aqui. 😅 Tenta mandar a mensagem de novo?",
                success=False,
                error_message=str(e),
                usage={
                    "model": self.free_model,
                    "request_tokens": 0,
                    "response_tokens": 0,
                    "total_tokens": 0
                }
            )
    
    async def _check_conversation_code_requirement(self, user_id: Optional[str]) -> bool:
        """Check if user needs to provide conversation code.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if conversation code is required, False otherwise
        """
        try:
            if not user_id:
                return True  # No user ID means conversation code required
            
            from src.db.repository.user import get_user
            import uuid
            
            # Get user from database
            user_uuid = uuid.UUID(user_id)
            user = get_user(user_uuid)
            
            if not user:
                return True  # User not found means conversation code required
            
            # Check if user has conversation code in user_data
            user_data = user.user_data or {}
            conversation_code = user_data.get("flashed_conversation_code")
            
            if not conversation_code:
                logger.info(f"User {user_id} does not have conversation code - requiring code")
                return True
            
            logger.info(f"User {user_id} has conversation code: {conversation_code}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking conversation code requirement: {str(e)}")
            return True  # Default to requiring code on error
    
    def _generate_conversation_code_request(self) -> str:
        """Generate a message requesting the conversation code in Flashinho's style.
        
        Returns:
            Message requesting conversation code
        """
        return ("E aí, mano! 👋 Pra eu conseguir te dar aquela força nos estudos de forma "
                "personalizada, preciso do seu código de conversa! 🔑\n\n"
                "Manda aí seu código pra gente começar com tudo! 🚀✨")


def create_agent(config: Dict[str, str]) -> FlashinhoV2:
    """Factory function to create Flashinho V2 agent instance."""
    try:
        return FlashinhoV2(config)
    except Exception as e:
        logger.error(f"Failed to create Flashinho V2 Agent: {e}")
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)