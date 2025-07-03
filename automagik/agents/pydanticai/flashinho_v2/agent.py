"""Flashinho V2 Agent - Advanced multimodal Brazilian educational assistant.

This agent combines the authentic Brazilian educational coaching personality of Flashinho
with advanced multimodal capabilities powered by Google Gemini 2.5 Pro model.
"""
import logging
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
import uuid

from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.response import AgentResponse
from automagik.memory.message_history import MessageHistory
from automagik.tools.flashed.tool import (
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy,
    get_user_by_pretty_id
)
from automagik.tools.flashed.provider import FlashedProvider
from .prompts import AGENT_FREE, AGENT_PROMPT
# Import shared authentication utilities from tools/flashed
from automagik.tools.flashed.auth_utils import UserStatusChecker
from automagik.tools.flashed.user_identification import (
    build_external_key,
    attach_user_by_external_key,
    attach_user_by_flashed_id_lookup,
    find_user_by_whatsapp_id,
    user_has_conversation_code,
    identify_user_comprehensive,
    UserIdentificationResult,
    ensure_user_uuid_matches_flashed_id
)
from .memories import FlashinhoMemories
from .session_utils import (
    update_message_history_user_id,
    update_session_user_id,
    make_session_persistent,
    ensure_session_row,
)
from .api_client import FlashinhoAPI


logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for model selection based on user status."""
    model_name: str
    vision_model: str
    system_message: str


# UserIdentificationResult is now imported from shared utilities


class FlashinhoV2(AutomagikAgent):
    """Advanced multimodal Brazilian educational assistant powered by Google Gemini 2.5 Pro.
    
    Features:
    - Authentic Brazilian Generation Z Portuguese coaching style
    - Multimodal processing: images, audio, documents for educational content
    - Complete Flashed API integration for educational gaming
    - WhatsApp/Evolution channel integration for media handling
    - Cultural authenticity for Brazilian high school students
    """
    
    # Model constants - these are dynamically selected based on user subscription
    PRO_MODEL = "google:gemini-2.5-pro"  # For Pro users
    FREE_MODEL = "google:gemini-2.5-flash"  # For Free users
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Flashinho V2 with multimodal and Gemini configuration."""
        config = config or {}
        config.setdefault("supported_media", ["image", "audio", "document"])
        config.setdefault("auto_enhance_prompts", True)
        config.setdefault("enable_multi_prompt", True)

        super().__init__(config)

        self._code_prompt_text = AGENT_FREE
        self._setup_dependencies()
        self._register_flashed_tools()
        self._initialize_user_status()
        
        logger.info("Flashinho V2 initialized with dynamic model selection based on user status")
    
    def _setup_dependencies(self) -> None:
        """Setup agent dependencies."""
        self.dependencies = self.create_default_dependencies()
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        self.tool_registry.register_default_tools(self.context)
        
        # Register multimodal analysis tools
        self._register_multimodal_tools()
    
    def _initialize_user_status(self) -> None:
        """Initialize user status tracking."""
        self._user_status_checked = False
        self._is_pro_user = False
        self.flashed_provider = FlashedProvider()
    
    def _register_flashed_tools(self) -> None:
        """Register all Flashed API tools for educational gaming functionality."""
        flashed_tools = [
            get_user_data, get_user_score, get_user_roadmap, 
            get_user_objectives, get_last_card_round, get_user_energy,
            get_user_by_pretty_id
        ]
        
        for tool in flashed_tools:
            self.tool_registry.register_tool(tool)
        
        logger.debug(f"Registered {len(flashed_tools)} Flashed API tools")
    
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
                system_message=AGENT_PROMPT
            )
        else:
            return ModelConfig(
                model_name=self.FREE_MODEL,
                vision_model=self.FREE_MODEL,
                system_message=AGENT_FREE
            )
    
    def _apply_model_config(self, config: ModelConfig, user_id: str) -> None:
        """Apply model configuration to agent and dependencies."""
        # Update agent properties
        self.model_name = config.model_name
        self.system_message = config.system_message
        self.vision_model = config.vision_model
        
        # Update LLM client if available
        if hasattr(self, 'llm_client') and hasattr(self.llm_client, 'model'):
            self.llm_client.model = config.model_name
        
        # Update dependencies
        if hasattr(self, 'dependencies'):
            self._update_dependencies_config(config)
        
        status = "Pro" if config.model_name == self.PRO_MODEL else "Free"
        logger.info(f"User {user_id} is a {status} user. Using model: {config.model_name}")
    
    def _update_dependencies_config(self, config: ModelConfig) -> None:
        """Update dependencies with model configuration."""
        if hasattr(self.dependencies, 'model_name'):
            self.dependencies.model_name = config.model_name
        if hasattr(self.dependencies, 'llm_client') and hasattr(self.dependencies.llm_client, 'model'):
            self.dependencies.llm_client.model = config.model_name
        if hasattr(self.dependencies, 'prompt'):
            self.dependencies.prompt = config.system_message
    
    async def _update_model_and_prompt_based_on_status(self, user_id: Optional[str] = None) -> None:
        """Update model and prompt based on user's Pro status."""
        if self._user_status_checked or not user_id:
            return
        
        self._is_pro_user = await self._check_user_pro_status(user_id)
        self._user_status_checked = True
        
        config = self._create_model_config(self._is_pro_user)
        self._apply_model_config(config, user_id)
    
    async def _ensure_user_memories_ready(self, user_id: Optional[str] = None) -> None:
        """Ensure user memories are initialized and updated for prompt variables."""
        if not self.db_id:
            logger.warning("No agent database ID available, skipping memory initialization")
            return
        
        try:
            safe_user_id = str(user_id) if user_id else None
            await FlashinhoMemories.init_defaults(self.db_id, safe_user_id)

            # Fetch fresh data once per run – avoids duplicate provider calls inside memory layer
            api_data = await FlashinhoAPI().fetch_all(user_id)
            success = await FlashinhoMemories.refresh_from_api(self.db_id, safe_user_id or "", api_data)
            
            if success:
                logger.info(f"Successfully updated Flashinho V2 memories for user {user_id}")
            else:
                logger.warning(f"Failed to update some Flashinho V2 memories for user {user_id}")
        except Exception as e:
            logger.error(f"Error ensuring user memories ready: {str(e)}")
    
    async def _identify_user(self, channel_payload: Optional[dict], message_history_obj: Optional[MessageHistory], current_message: Optional[str] = None) -> UserIdentificationResult:
        """Comprehensive user identification process."""
        # Store references for other methods
        self.current_channel_payload = channel_payload
        self.current_message_history = message_history_obj
        
        # Log initial state
        initial_user_id = self.context.get("user_id")
        history_user_id = message_history_obj.user_id if message_history_obj else None
        logger.info(f"🔍 User identification starting - Context: {initial_user_id}, History: {history_user_id}")
        
        # PRIORITY: If we have a user_id from message history, use it first
        if history_user_id and not initial_user_id:
            self.context["user_id"] = str(history_user_id)
            logger.info(f"🔍 Using user_id from session history: {history_user_id}")
        
        # Try multiple identification methods
        await self._try_session_key_identification(channel_payload)
        await self._try_external_key_identification(message_history_obj, history_user_id)
        await self._try_flashed_id_identification(message_history_obj, history_user_id)
        
        # Try conversation code extraction from current message
        conversation_code_processed = False
        if current_message:
            conversation_code_processed = await self._try_extract_and_process_conversation_code(current_message, self.context.get("user_id"))
        
        # Check conversation code requirement (skip if just processed)
        user_id = self.context.get("user_id")
        if conversation_code_processed:
            requires_conversation_code = False
            logger.info("Conversation code processed in current message, skipping requirement check")
        else:
            requires_conversation_code = await self._check_conversation_code_requirement(user_id)
        
        return UserIdentificationResult(
            user_id=user_id,
            method=self.context.get("user_identification_method"),
            requires_conversation_code=requires_conversation_code
        )
    
    async def _try_session_key_identification(self, channel_payload: Optional[dict]) -> None:
        """Try to identify user by session key."""
        session_key = await self._build_session_user_key(channel_payload)
        if session_key:
            self.context["session_user_key"] = session_key
            await self._attach_user_by_session_key(session_key)
    
    async def _try_external_key_identification(self, message_history_obj: Optional[MessageHistory], history_user_id: Optional[str]) -> None:
        """Try to identify user by external key."""
        if self.context.get("user_id"):
            return
        
        external_key = build_external_key(self.context)
        if external_key:
            found_by_key = await attach_user_by_external_key(self.context, external_key)
            if found_by_key:
                logger.info(f"🔑 User identified via external_key: {self.context.get('user_id')}")
                await self._sync_message_history_if_needed(message_history_obj, history_user_id)
    
    async def _try_flashed_id_identification(self, message_history_obj: Optional[MessageHistory], history_user_id: Optional[str]) -> None:
        """Try to identify user by Flashed ID lookup."""
        if self.context.get("user_id"):
            return
        
        found_by_flashed_id = await attach_user_by_flashed_id_lookup(self.context)
        if found_by_flashed_id:
            logger.info(f"🔍 User identified via flashed_id_lookup: {self.context.get('user_id')}")
            await self._sync_message_history_if_needed(message_history_obj, history_user_id)
    
    async def _sync_message_history_if_needed(self, message_history_obj: Optional[MessageHistory], history_user_id: Optional[str]) -> None:
        """Sync message history with new user ID if needed."""
        new_user_id = self.context.get("user_id")
        if message_history_obj and new_user_id and new_user_id != str(history_user_id):
            await update_message_history_user_id(message_history_obj, new_user_id)
            await update_session_user_id(message_history_obj, new_user_id)
    
    async def _handle_conversation_code_flow(self, input_text: str, user_id: Optional[str], message_history_obj: Optional[MessageHistory], history_user_id: Optional[str], **kwargs) -> Optional[AgentResponse]:
        """Handle conversation code extraction and processing flow."""
        # Don't extract again - this was already done in _identify_user
        # Just check if we now have a valid user_id after identification
        new_user_id = self.context.get("user_id")
        
        if not new_user_id:
            # No user identified, request conversation code
            return self._create_conversation_code_request_response()
        
        logger.info(f"🔍 User identified via conversation code - Context user_id: {new_user_id}")
        
        # Sync message history after successful identification
        if message_history_obj and new_user_id and new_user_id != str(history_user_id):
            await update_message_history_user_id(message_history_obj, new_user_id)
            await update_session_user_id(message_history_obj, new_user_id)
        
        # User identified successfully - return None to continue normal flow
        logger.info("User identified successfully, continuing with normal agent flow")
        return None
    
    def _create_conversation_code_request_response(self) -> AgentResponse:
        """Create response requesting conversation code."""
        return AgentResponse(
            text=self._generate_conversation_code_request(),
            success=True,
            usage={
                "model": self.FREE_MODEL,
                "request_tokens": 0,
                "response_tokens": 0,
                "total_tokens": 0
            }
        )
    
    def _create_introduction_prompt(self) -> str:
        """Create introduction prompt after conversation code confirmation."""
        user_name = self.context.get("flashed_user_name", "")
        
        if user_name:
            return (f"O usuário {user_name} acabou de confirmar seu código de conversa "
                   "e agora está autenticado no sistema. Apresente-se de forma calorosa e "
                   "pergunte como pode ajudá-lo com seus estudos hoje.")
        else:
            return ("O usuário acabou de confirmar seu código de conversa "
                   "e agora está autenticado no sistema. Apresente-se de forma calorosa e "
                   "pergunte como pode ajudá-lo com seus estudos hoje.")
    
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
            # Identify user through multiple methods
            identification_result = await self._identify_user(channel_payload, message_history_obj, input_text)
            
            # Handle conversation code flow if required
            if identification_result.requires_conversation_code:
                response = await self._handle_conversation_code_flow(
                    input_text, identification_result.user_id, message_history_obj,
                    message_history_obj.user_id if message_history_obj else None,
                    multimodal_content=multimodal_content,
                    system_message=system_message,
                    channel_payload=channel_payload,
                    message_limit=message_limit
                )
                if response:
                    return response
            
            # Setup user-specific configuration
            user_id = identification_result.user_id
            if user_id:
                await self._update_model_and_prompt_based_on_status(user_id)
                await self._ensure_user_memories_ready(user_id)
                
                if message_history_obj:
                    await make_session_persistent(self, self.current_message_history, user_id)
            
            # Log execution context
            self._log_execution_context(user_id)
            
            # Add the current user message to history before the agent runs.
            if message_history_obj:
                safe_context = {k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in self.context.items()}
                try:
                    # Ensure DB session row exists before inserting messages
                    from uuid import UUID
                    hist_user = message_history_obj.user_id or user_id
                    ensure_session_row(
                        UUID(message_history_obj.session_id),
                        UUID(str(hist_user)) if hist_user else None,
                    )

                    message_history_obj.add(
                        content=input_text,
                        agent_id=self.db_id,
                        context=safe_context,
                        channel_payload=channel_payload,
                    )
                except Exception as e:
                    logger.error(f"Error recording user message: {e}")
            
            # Prepare message history for the LLM call.
            pydantic_messages = (
                message_history_obj.get_formatted_pydantic_messages(limit=message_limit or 20)
                if message_history_obj
                else []
            )
            
            # Execute agent using the framework directly (bypass AutomagikAgent.run to avoid message duplication)
            logger.info("Sending %s messages to AI model", len(pydantic_messages))
            
            response = await self._run_agent(
                input_text=input_text,
                system_prompt=system_message,
                message_history=pydantic_messages,
                multimodal_content=multimodal_content,
                channel_payload=channel_payload,
                message_limit=message_limit
            )
            
            # Basic response sanity log.
            if response and response.text:
                logger.info("FlashinhoV2 response length: %s chars", len(response.text))
            
            # Save the agent response to message history
            if message_history_obj and response:
                try:
                    logger.info(f"🔍 Saving agent response to message history")
                    message_history_obj.add_response(
                        content=response.text,
                        tool_calls=getattr(response, 'tool_calls', None),
                        tool_outputs=getattr(response, 'tool_outputs', None),
                        system_prompt=getattr(response, "system_prompt", None),
                        usage=getattr(response, 'usage', None),
                        agent_id=self.db_id
                    )
                except Exception as e:
                    logger.error(f"🔍 Error saving agent response: {e}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in FlashinhoV2 run method: {str(e)}")
            return self._create_error_response(e)
    
    def _log_execution_context(self, user_id: Optional[str]) -> None:
        """Log execution context for debugging."""
        user_phone = self.context.get("user_phone_number") or self.context.get("whatsapp_user_number")
        user_name = self.context.get("user_name") or self.context.get("whatsapp_user_name")
        tools_count = len(self.tool_registry.tools) if hasattr(self.tool_registry, 'tools') else 'unknown'
        
        logger.info(f"Running agent with user_id: {user_id}, phone: {user_phone}, name: {user_name}")
        logger.info(f"Using model: {self.model_name}, tools: {tools_count}")
    
    def _create_error_response(self, error: Exception) -> AgentResponse:
        """Create error response with Brazilian Portuguese message."""
        return AgentResponse(
            text="Desculpa, mano! Tive um probleminha técnico aqui. 😅 Tenta mandar a mensagem de novo?",
            success=False,
            error_message=str(error),
            usage={
                "model": self.FREE_MODEL,
                "request_tokens": 0,
                "response_tokens": 0,
                "total_tokens": 0
            }
        )

    async def _check_conversation_code_requirement(self, user_id: Optional[str]) -> bool:
        """Return *True* when the current user still needs to supply a
        conversation-code.

        Logic order:
            1. Try WhatsApp-lookup (most common entry path).
            2. If we already have a ``user_id`` – check if that DB user has the
               code stored.
            3. Default to *True* on any error (safe-side).
        """
        try:
            # 1️⃣  WhatsApp based identification
            whatsapp_id = (
                self.context.get("whatsapp_user_number")
                or self.context.get("user_phone_number")
            )

            if not whatsapp_id and getattr(self, "current_channel_payload", None):
                whatsapp_id = (
                    self.current_channel_payload.get("user", {}).get("phone_number")
                )

            if whatsapp_id:
                user = await find_user_by_whatsapp_id(str(whatsapp_id))
                if user:
                    # Update context with this user information in all cases.
                    self.context.update(
                        {
                            "user_id": str(user.id),
                            "flashed_user_id": user.user_data.get("flashed_user_id") if user.user_data else None,
                            "flashed_conversation_code": user.user_data.get("flashed_conversation_code") if user.user_data else None,
                            "flashed_user_name": user.user_data.get("flashed_user_name") if user.user_data else None,
                            "user_identification_method": "whatsapp_id_lookup",
                        }
                    )

                    await self._sync_session_after_identification(str(user.id))

                    return not user_has_conversation_code(user)

            # 2️⃣  Fallback to the supplied user_id from context
            if not user_id:
                return True

            from automagik.db.repository.user import get_user
            import uuid as _uuid

            db_user = get_user(_uuid.UUID(str(user_id)))
            if not db_user:
                return True

            return not user_has_conversation_code(db_user)

        except Exception as e:
            logger.error("Error checking conversation code requirement: %s", e)
            return True  # Safe default

    async def _try_extract_and_process_conversation_code(self, message: str, user_id: Optional[str]) -> bool:
        """Try to extract conversation code from message and process it.
        Returns True if conversation code was found and processed successfully.
        """
        try:
            from automagik.db.repository.user import get_user, update_user_data
            
            # Use the UserStatusChecker to extract conversation code
            status_checker = UserStatusChecker()
            conversation_code = status_checker.extract_conversation_code_from_message(message)
            
            if not conversation_code:
                logger.info("No conversation code found in message")
                return False
            
            logger.info(f"Found conversation code in message: {conversation_code}")
            
            # Get user data by conversation code from Flashed API
            user_result = await status_checker.get_user_by_conversation_code(conversation_code)
            
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
            
            logger.info(f"Successfully identified user via conversation code: {flashed_user_id}")
            
            # 🔧 SURGICAL FIX: Ensure UUID synchronization with Flashed system
            if user_id:
                try:
                    # Get phone number from API payload (preserve it)
                    api_phone_number = None
                    
                    # Extract from channel payload first (most reliable)
                    if hasattr(self, "current_channel_payload") and self.current_channel_payload:
                        api_phone_number = self.current_channel_payload.get("user", {}).get("phone_number")
                    
                    # Fallback to context
                    if not api_phone_number:
                        api_phone_number = (
                            self.context.get("user_phone_number") or 
                            self.context.get("whatsapp_user_number")
                        )
                    
                    # Fallback to phone from Flashed API response if no API payload phone
                    if not api_phone_number and phone:
                        api_phone_number = phone
                        logger.info(f"🔍 Using phone number from Flashed API response: {api_phone_number}")
                    else:
                        logger.info(f"🔍 Extracted API phone number: {api_phone_number}")
                    
                    if not api_phone_number:
                        logger.error("No phone number available from API payload or Flashed response")
                        return False
                    
                    # Prepare Flashed user data
                    flashed_user_data = {
                        "name": name,
                        "phone": phone,
                        "email": email,
                        "conversation_code": conversation_code
                    }
                    
                    # 🎯 KEY FIX: Ensure user UUID matches Flashed user_id
                    final_user_id = await ensure_user_uuid_matches_flashed_id(
                        phone_number=api_phone_number,  # Always preserve API phone
                        flashed_user_id=flashed_user_id,
                        flashed_user_data=flashed_user_data
                    )
                    
                    logger.info(f"UUID synchronization complete. Final user_id: {final_user_id}")
                    
                    # Update context with synchronized user information
                    self.context.update({
                        "user_id": final_user_id,  # Now guaranteed to match Flashed UUID
                        "flashed_user_id": flashed_user_id,
                        "flashed_conversation_code": conversation_code,
                        "flashed_user_name": name,
                        "user_identification_method": "conversation_code"
                    })
                    
                    # Make session persistent with final user ID
                    await make_session_persistent(self, self.current_message_history, final_user_id)
                    
                    return True
                        
                except Exception as e:
                    logger.error(f"Error in UUID synchronization: {str(e)}")
                    return False
            else:
                # No user_id in context yet, but we have flashed user info
                logger.info(f"No user_id in context, but successfully identified flashed user: {flashed_user_id}")
                
                # 🔧 SURGICAL FIX: Handle no-context case with UUID synchronization
                try:
                    # Get phone number from API payload (preserve it)
                    api_phone_number = None
                    
                    # Extract from channel payload first (most reliable)
                    if hasattr(self, "current_channel_payload") and self.current_channel_payload:
                        api_phone_number = self.current_channel_payload.get("user", {}).get("phone_number")
                    
                    # Fallback to context
                    if not api_phone_number:
                        api_phone_number = (
                            self.context.get("user_phone_number") or 
                            self.context.get("whatsapp_user_number")
                        )
                    
                    # Fallback to phone from Flashed API response if no API payload phone
                    if not api_phone_number and phone:
                        api_phone_number = phone
                        logger.info(f"🔍 Using phone number from Flashed API response (no context): {api_phone_number}")
                    else:
                        logger.info(f"🔍 Extracted API phone number (no context): {api_phone_number}")
                    
                    if not api_phone_number:
                        logger.error("No phone number available from API payload or Flashed response")
                        return False
                    
                    # Prepare Flashed user data
                    flashed_user_data = {
                        "name": name,
                        "phone": phone,
                        "email": email,
                        "conversation_code": conversation_code
                    }
                    
                    # 🎯 KEY FIX: Ensure user UUID matches Flashed user_id (same as above)
                    final_user_id = await ensure_user_uuid_matches_flashed_id(
                        phone_number=api_phone_number,  # Always preserve API phone
                        flashed_user_id=flashed_user_id,
                        flashed_user_data=flashed_user_data
                    )
                    
                    logger.info(f"UUID synchronization complete (no context). Final user_id: {final_user_id}")
                    
                    # Update context with synchronized user information
                    self.context.update({
                        "user_id": final_user_id,  # Now guaranteed to match Flashed UUID
                        "flashed_user_id": flashed_user_id,
                        "flashed_conversation_code": conversation_code,
                        "flashed_user_name": name,
                        "user_identification_method": "conversation_code"
                    })
                    
                    # Make session persistent with final user ID
                    await make_session_persistent(self, self.current_message_history, final_user_id)
                    
                    return True
                
                except Exception as e:
                    logger.error(f"Error in UUID synchronization (no context): {str(e)}")
                    return False
                
        except Exception as e:
            logger.error(f"Error extracting and processing conversation code: {str(e)}")
            return False
    
    def _generate_conversation_code_request(self) -> str:
        """Generate a message requesting the conversation code in Flashinho's style.
        
        Returns:
            Message requesting conversation code
        """
        return ("E aí! 👋 Pra eu conseguir te dar aquela força nos estudos de forma "
                "personalizada, preciso do seu código de conversa! 🔑\n\n"
                "Manda aí seu código pra gente começar com tudo! 🚀✨")

    async def _build_session_user_key(self, channel_payload: Optional[dict] = None) -> Optional[str]:
        """Return composite key <session_name>|<whatsapp_id> used for user look-up.
        Computed locally – no need for caller to supply it.
        """
        try:
            session_name = self.context.get("session_name")
            whatsapp_id = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")

            if channel_payload:
                if not session_name:
                    session_name = channel_payload.get("session_name")
                if not whatsapp_id:
                    whatsapp_id = channel_payload.get("user", {}).get("phone_number")

            if session_name and whatsapp_id:
                return f"{session_name}|{whatsapp_id}"
        except Exception as e:
            logger.error(f"Error building session_user_key: {e}")
        return None

    async def _attach_user_by_session_key(self, session_key: Optional[str]) -> None:
        """Attach existing user by composite session key."""
        if not session_key or self.context.get("user_id"):
            return
        try:
            from automagik.db.repository.user import list_users
            users, _ = list_users(page=1, page_size=1000)
            for u in users:
                if u.user_data and u.user_data.get("session_user_key") == session_key:
                    self.context["user_id"] = str(u.id)
                    logger.info(f"🔗 Attached user {u.id} via session_user_key {session_key}")
                    return
        except Exception as e:
            logger.error(f"Error during session_user_key lookup: {e}")

    async def _sync_session_after_identification(self, user_id: str) -> None:
        """Update history/session tables after we've attached a user."""
        if not getattr(self, "current_message_history", None):
            return
        history = self.current_message_history
        if str(history.user_id) != str(user_id):
            await update_message_history_user_id(history, str(user_id))
            await update_session_user_id(history, str(user_id))
        await make_session_persistent(self, history, str(user_id))

    def _register_multimodal_tools(self):
        """Register multimodal analysis tools using common helper."""
        from automagik.agents.common.multimodal_helper import register_multimodal_tools
        register_multimodal_tools(self.tool_registry, self.dependencies)


def create_agent(config: Dict[str, str]) -> FlashinhoV2:
    """Factory function to create Flashinho V2 agent instance."""
    try:
        return FlashinhoV2(config)
    except Exception as e:
        logger.error(f"Failed to create Flashinho V2 Agent: {e}")
        from automagik.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)