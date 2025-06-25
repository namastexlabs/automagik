"""Flashinho Pro Agent - Advanced multimodal Brazilian educational assistant.

This agent combines the authentic Brazilian educational coaching personality of Flashinho
with advanced multimodal capabilities powered by Google Gemini 2.5 Pro model.
Includes mathematical problem detection and solving via flashinho_thinker workflow.
"""
import logging
import time
from typing import Dict, Optional, Tuple

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.response import AgentResponse
from src.memory.message_history import MessageHistory
from src.tools.flashed.tool import (
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy,
    get_user_by_pretty_id
)
from src.tools.flashed.provider import FlashedProvider
from .prompts.prompt import AGENT_PROMPT, AGENT_FREE
from .memory_manager import update_flashinho_pro_memories, initialize_flashinho_pro_memories
from .user_identification import FlashinhoProUserMatcher

# Import shared utilities from tools/flashed
from src.tools.flashed.auth_utils import UserStatusChecker
from src.tools.flashed.user_identification import (
    identify_user_comprehensive, UserIdentificationResult,
    ensure_user_uuid_matches_flashed_id, make_session_persistent
)
from src.tools.flashed.workflow_runner import run_flashinho_thinker_workflow, analyze_math_image
from src.tools.flashed.message_generator import (
    generate_math_processing_message, generate_pro_feature_message,
    generate_error_message
)
from src.tools.evolution.api import send_text_message
from src.utils.multimodal import detect_content_type, is_image_type

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
        
        # Register multimodal analysis tools
        self._register_multimodal_tools()
        
        # Flag to track if we've checked user status
        self._user_status_checked = False
        # Default to non-pro until verified
        self._is_pro_user = False
        
        # Initialize provider
        self.flashed_provider = FlashedProvider()
        
        # Initialize user status checker for shared authentication
        self.user_status_checker = UserStatusChecker()
        
        logger.info("Flashinho Pro initialized with dynamic model selection, math detection, and workflow integration")
    
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
                    
                    # Update context with additional user data
                    user_info = user_data["user"]
                    if user_info.get("name"):
                        self.context["user_name"] = user_info["name"]
                    if user_info.get("phone"):
                        self.context["user_phone_number"] = user_info["phone"]
                    if user_info.get("email"):
                        self.context["user_email"] = user_info["email"]
                    
                    logger.info(f"Successfully identified user via prettyId {pretty_id}: {user_id}")
                    return user_id
                else:
                    logger.warning(f"No user found for prettyId: {pretty_id}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking for prettyId identification: {str(e)}")
            return None

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
    
    async def _detect_math_in_image(self, multimodal_content) -> Tuple[bool, str]:
        """Detect if image contains math problem and extract context.
        
        Args:
            multimodal_content: Multimodal content dictionary
            
        Returns:
            Tuple of (is_math_detected, math_context_description)
        """
        if not multimodal_content:
            return False, ""
            
        try:
            # Check if we have image content
            image_data = multimodal_content.get("image_data") or multimodal_content.get("image_url")
            if not image_data:
                return False, ""
            
            # Use multimodal analysis to detect math content
            # For now, we'll use a simple heuristic based on the message content
            # and assume images with math-related keywords are math problems
            
            # TODO: Implement proper image analysis using multimodal tools
            # This is a placeholder that could be enhanced with actual image analysis
            
            # For now, treat all images as potentially mathematical if sent to Pro
            return True, "mathematical content detected in image"
            
        except Exception as e:
            logger.error(f"Error detecting math in image: {str(e)}")
            return False, ""
    
    async def _send_processing_message(self, phone: str, user_name: str, math_context: str, user_message: str = ""):
        """Send customized processing message via Evolution.
        
        Args:
            phone: User's phone number
            user_name: User's name
            math_context: Context about the math problem
            user_message: Original user message for context
        """
        try:
            # Generate personalized message using LLM
            message = await generate_math_processing_message(
                user_name=user_name,
                math_context=math_context,
                user_message=user_message
            )
            
            # Get Evolution instance from context
            instance = (
                self.context.get("evolution_instance") or 
                self.context.get("whatsapp_instance") or
                self.context.get("instanceId")
            )
            
            if not instance:
                logger.warning("No Evolution instance in context, cannot send message")
                return
                
            # Send message using Evolution API directly
            success, msg_id = await send_text_message(
                instance_name=instance,
                number=phone,
                text=message
            )
            
            if success:
                logger.info(f"Sent processing message to {phone}: {message[:50]}...")
            else:
                logger.error(f"Failed to send processing message: {msg_id}")
                
        except Exception as e:
            logger.error(f"Error sending processing message: {str(e)}")
    
    async def _handle_math_problem_flow(self, multimodal_content, user_id: str, phone: str, math_context: str, user_message: str = "") -> str:
        """Handle the complete math problem solving flow.
        
        Args:
            multimodal_content: Multimodal content with image
            user_id: User ID
            phone: User's phone number
            math_context: Context about the math problem
            user_message: Original user message
            
        Returns:
            Result text from workflow execution
        """
        try:
            # Send processing message to user
            user_name = self.context.get("flashed_user_name", "")
            await self._send_processing_message(phone, user_name, math_context, user_message)
            
            # Extract image data
            image_data = multimodal_content.get("image_data") or multimodal_content.get("image_url")
            
            if not image_data:
                return "Desculpa, não consegui acessar a imagem. Pode tentar enviar novamente?"
            
            # Use the analyze_math_image convenience function from workflow_runner
            result_text = await analyze_math_image(image_data)
            
            logger.info(f"Math problem workflow completed for user {user_id}")
            return result_text
            
        except Exception as e:
            logger.error(f"Error in math problem flow: {str(e)}")
            
            # Generate error message using LLM
            error_msg = await generate_error_message(
                user_name=self.context.get("flashed_user_name"),
                error_context="falha ao processar problema matemático",
                suggestion="tentar enviar a imagem novamente"
            )
            
            return error_msg
    
    async def _identify_user_with_conversation_code(self, input_text: str, message_history_obj: Optional[MessageHistory]) -> UserIdentificationResult:
        """Identify user using shared authentication utilities.
        
        Args:
            input_text: User's message text
            message_history_obj: Message history object
            
        Returns:
            UserIdentificationResult with identification details
        """
        try:
            # Use shared user identification logic
            identification_result = await identify_user_comprehensive(
                context=self.context,
                channel_payload=getattr(self, 'current_channel_payload', None),
                message_history_obj=message_history_obj,
                current_message=input_text
            )
            
            # Handle conversation code flow if needed
            if identification_result.requires_conversation_code:
                # Try to extract and process conversation code from current message
                conversation_code_processed = await self._try_extract_and_process_conversation_code(
                    input_text, identification_result.user_id, message_history_obj
                )
                
                if conversation_code_processed:
                    identification_result.requires_conversation_code = False
                    identification_result.user_id = self.context.get("user_id")
            
            return identification_result
            
        except Exception as e:
            logger.error(f"Error in user identification: {str(e)}")
            return UserIdentificationResult(
                user_id=None,
                method=None,
                requires_conversation_code=True
            )
    
    async def _try_extract_and_process_conversation_code(self, message: str, user_id: Optional[str], message_history_obj: Optional[MessageHistory]) -> bool:
        """Try to extract and process conversation code from message.
        
        Args:
            message: User's message
            user_id: Current user ID
            message_history_obj: Message history object
            
        Returns:
            True if conversation code was processed successfully
        """
        try:
            # Extract conversation code using shared utility
            conversation_code = self.user_status_checker.extract_conversation_code_from_message(message)
            
            if not conversation_code:
                return False
            
            logger.info(f"Found conversation code in message: {conversation_code}")
            
            # Get user data by conversation code
            user_result = await self.user_status_checker.get_user_by_conversation_code(conversation_code)
            
            if not user_result["success"]:
                logger.error(f"Failed to get user by conversation code: {user_result.get('error')}")
                return False
            
            # Extract user information from Flashed API response
            flashed_user_data = user_result["user_data"]
            user_info = flashed_user_data.get("user", {})
            flashed_user_id = user_info.get("id")
            name = user_info.get("name")
            phone = user_info.get("phone")
            email = user_info.get("email")
            
            if not flashed_user_id:
                logger.error("No user ID found in Flashed API response")
                return False
            
            # Get phone number from context or API response
            api_phone_number = (
                self.context.get("whatsapp_user_number") or 
                self.context.get("user_phone_number") or
                phone
            )
            
            if not api_phone_number:
                logger.error("No phone number available")
                return False
            
            # Prepare Flashed user data
            flashed_user_data_dict = {
                "name": name,
                "phone": phone,
                "email": email,
                "conversation_code": conversation_code
            }
            
            # Ensure user UUID matches Flashed user_id
            final_user_id = await ensure_user_uuid_matches_flashed_id(
                phone_number=api_phone_number,
                flashed_user_id=flashed_user_id,
                flashed_user_data=flashed_user_data_dict
            )
            
            # Update context with synchronized user information
            self.context.update({
                "user_id": final_user_id,
                "flashed_user_id": flashed_user_id,
                "flashed_conversation_code": conversation_code,
                "flashed_user_name": name,
                "user_identification_method": "conversation_code"
            })
            
            # Make session persistent
            if message_history_obj:
                await make_session_persistent(self, message_history_obj, final_user_id)
            
            logger.info(f"Successfully processed conversation code for user: {final_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing conversation code: {str(e)}")
            return False
    
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
        """Enhanced run method with conversation code auth, math detection, and workflow integration."""
        
        try:
            # Store channel payload for later use
            self.current_channel_payload = channel_payload
            
            # 1. Handle user identification with conversation code
            identification_result = await self._identify_user_with_conversation_code(input_text, message_history_obj)
            
            if identification_result.requires_conversation_code:
                # User needs to provide conversation code
                request_message = self.user_status_checker.generate_conversation_code_request_message()
                return AgentResponse(
                    text=request_message,
                    success=True,
                    usage={
                        "model": self.free_model,
                        "request_tokens": 0,
                        "response_tokens": 0,
                        "total_tokens": 0
                    }
                )
            
            # 2. Check Pro status and update model/prompt
            user_id = identification_result.user_id
            if user_id:
                await self._update_model_and_prompt_based_on_status(user_id)
                await self._ensure_user_memories_ready(user_id)
            
            # 3. Check for math problem in image (Pro users only)
            if self._is_pro_user and multimodal_content:
                is_math, math_context = await self._detect_math_in_image(multimodal_content)
                
                if is_math:
                    phone = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
                    
                    if phone:
                        # Handle math problem flow with workflow
                        result_text = await self._handle_math_problem_flow(
                            multimodal_content, user_id, phone, math_context, input_text
                        )
                        
                        return AgentResponse(
                            text=result_text,
                            success=True,
                            metadata={
                                "workflow": "flashinho_thinker", 
                                "math_detected": True,
                                "user_type": "pro"
                            },
                            usage={
                                "model": self.pro_model,
                                "request_tokens": 0,  # Will be filled by workflow
                                "response_tokens": 0,
                                "total_tokens": 0
                            }
                        )
                    else:
                        logger.error("No phone number available for Evolution message")
            
            elif multimodal_content and not self._is_pro_user:
                # Non-Pro user trying to use math solving
                pro_message = await generate_pro_feature_message(
                    user_name=self.context.get("flashed_user_name"),
                    feature_name="análise de imagens matemáticas"
                )
                
                return AgentResponse(
                    text=pro_message,
                    success=True,
                    metadata={"feature_restricted": True, "user_type": "free"},
                    usage={
                        "model": self.free_model,
                        "request_tokens": 0,
                        "response_tokens": 0,
                        "total_tokens": 0
                    }
                )
            
            # 4. Regular chat flow
            whatsapp_phone = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
            whatsapp_name = self.context.get("whatsapp_user_name") or self.context.get("user_name")
            identification_method = self.context.get("user_identification_method", "context")
            
            logger.info(f"Flashinho Pro regular chat from {whatsapp_name} ({whatsapp_phone}) - User ID: {user_id} via {identification_method}")
            
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
            
            # Generate error response
            error_msg = await generate_error_message(
                user_name=self.context.get("flashed_user_name"),
                error_context="erro geral no processamento",
                suggestion="tentar novamente"
            )
            
            return AgentResponse(
                text=error_msg,
                success=False,
                error_message=str(e),
                usage={
                    "model": self.free_model,
                    "request_tokens": 0,
                    "response_tokens": 0,
                    "total_tokens": 0
                }
            )
    
    def _register_multimodal_tools(self):
        """Register multimodal analysis tools using common helper."""
        from src.agents.common.multimodal_helper import register_multimodal_tools
        register_multimodal_tools(self.tool_registry, self.dependencies)


def create_agent(config: Dict[str, str]) -> FlashinhoPro:
    """Factory function to create Flashinho Pro agent instance."""
    try:
        return FlashinhoPro(config)
    except Exception as e:
        logger.error(f"Failed to create Flashinho Pro Agent: {e}")
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)