"""Flashinho V2 Agent - Advanced multimodal Brazilian educational assistant.

This agent combines the authentic Brazilian educational coaching personality of Flashinho
with advanced multimodal capabilities powered by Google Gemini 2.5 Pro model.
"""
import logging
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
import uuid

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.response import AgentResponse
from src.memory.message_history import MessageHistory
from src.tools.flashed.tool import (
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy,
    get_user_by_pretty_id
)
from src.tools.flashed.provider import FlashedProvider
from .prompts import AGENT_FREE, AGENT_PROMPT
from .identification import (
    UserStatusChecker,
    build_external_key,
    attach_user_by_external_key,
    attach_user_by_flashed_id_lookup,
    find_user_by_whatsapp_id,
    user_has_conversation_code,
)
from .memories import FlashinhoMemories
from .session_utils import (
    update_message_history_user_id,
    update_session_user_id,
    make_session_persistent,
)
from .api_client import FlashinhoAPI


logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for model selection based on user status."""
    model_name: str
    vision_model: str
    system_message: str


@dataclass
class UserIdentificationResult:
    """Result of user identification process."""
    user_id: Optional[str]
    method: Optional[str]
    requires_conversation_code: bool
    conversation_code_extracted: bool = False


class FlashinhoV2(AutomagikAgent):
    """Advanced multimodal Brazilian educational assistant powered by Google Gemini 2.5 Pro.
    
    Features:
    - Authentic Brazilian Generation Z Portuguese coaching style
    - Multimodal processing: images, audio, documents for educational content
    - Complete Flashed API integration for educational gaming
    - WhatsApp/Evolution channel integration for media handling
    - Cultural authenticity for Brazilian high school students
    """
    
    # Model constants
    PRO_MODEL = "google-gla:gemini-2.5-pro-preview-05-06"
    FREE_MODEL = "google-gla:gemini-2.5-flash-preview-05-20"
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Flashinho V2 with multimodal and Gemini configuration."""
        config = config or {}
        
        # Set default configuration
        config.setdefault("model", self.FREE_MODEL)
        config.setdefault("vision_model", self.FREE_MODEL)
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
    
    async def _identify_user(self, channel_payload: Optional[dict], message_history_obj: Optional[MessageHistory]) -> UserIdentificationResult:
        """Comprehensive user identification process."""
        # Store references for other methods
        self.current_channel_payload = channel_payload
        self.current_message_history = message_history_obj
        
        # Log initial state
        initial_user_id = self.context.get("user_id")
        history_user_id = message_history_obj.user_id if message_history_obj else None
        logger.info(f"🔍 User identification starting - Context: {initial_user_id}, History: {history_user_id}")
        
        # Try multiple identification methods
        await self._try_session_key_identification(channel_payload)
        await self._try_external_key_identification(message_history_obj, history_user_id)
        await self._try_flashed_id_identification(message_history_obj, history_user_id)
        
        # Check conversation code requirement
        user_id = self.context.get("user_id")
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
        conversation_code_extracted = await self._try_extract_and_process_conversation_code(input_text, user_id)
        
        if not conversation_code_extracted:
            return self._create_conversation_code_request_response()
        
        # Sync message history after conversation code processing
        new_user_id = self.context.get("user_id")
        logger.info(f"🔍 After conversation code processing - Context user_id: {new_user_id}")
        
        if message_history_obj and new_user_id and new_user_id != str(history_user_id):
            await update_message_history_user_id(message_history_obj, new_user_id)
            await update_session_user_id(message_history_obj, new_user_id)
        
        # Run agent with introduction
        introduction_prompt = self._create_introduction_prompt()
        logger.info("Running agent with introduction prompt after conversation code confirmation")
        
        return await super().run(input_text=introduction_prompt, **kwargs)
    
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
            identification_result = await self._identify_user(channel_payload, message_history_obj)
            
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

            from src.db.repository.user import get_user
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
            from src.db.repository.user import get_user, update_user_data
            
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
            
            # Update user data in our database
            if user_id:
                try:
                    # 🔧 Ensure user_id is a string before uuid.UUID conversion
                    if isinstance(user_id, uuid.UUID):
                        user_uuid = user_id
                    else:
                        user_uuid = uuid.UUID(str(user_id))
                    
                    user = get_user(user_uuid)
                    
                    if user:
                        # Update user_data with conversation code and flashed info
                        current_user_data = user.user_data or {}
                        updated_user_data = current_user_data.copy()
                        
                        # Get whatsapp_id from context for spaghetti lookup, but preserve existing if available
                        context_whatsapp_id = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
                        existing_whatsapp_id = current_user_data.get("whatsapp_id")
                        
                        # Preserve existing WhatsApp ID if it exists, otherwise use context
                        whatsapp_id = existing_whatsapp_id if existing_whatsapp_id else context_whatsapp_id
                        
                        # Preserve session_key
                        session_key = self.context.get("session_user_key") or current_user_data.get("session_user_key")
                        
                        # Get external_key for consistent user tracking
                        external_key = build_external_key(self.context) or current_user_data.get("external_key")
                        
                        logger.info(f"WhatsApp ID preservation: existing={existing_whatsapp_id}, context={context_whatsapp_id}, final={whatsapp_id}")
                        
                        updated_user_data.update({
                            "flashed_conversation_code": conversation_code,
                            "flashed_user_id": flashed_user_id,
                            "flashed_user_name": name,
                            "flashed_user_phone": phone,
                            "flashed_user_email": email,
                            "whatsapp_id": whatsapp_id,  # Store for spaghetti lookup
                            "session_user_key": session_key,
                            "external_key": external_key  # Store for reliable lookup
                        })
                        
                        update_user_data(user_uuid, updated_user_data)
                        logger.info(f"Updated user {user_id} with conversation code {conversation_code}")
                        
                        # 🔍 DEBUG: Log before context update
                        logger.info(f"🔍 Before context update - user_id: {self.context.get('user_id')}")
                        
                        # Update context with flashed user information
                        self.context.update({
                            "flashed_user_id": flashed_user_id,
                            "flashed_conversation_code": conversation_code,
                            "flashed_user_name": name,
                            "user_identification_method": "conversation_code"
                        })
                        
                        # 🔍 DEBUG: Log after context update
                        logger.info(f"🔍 After context update - user_id: {self.context.get('user_id')}")
                        
                        # 🔧 FIX: Make session persistent after successful user identification
                        await make_session_persistent(self, self.current_message_history, user_id)
                        
                        return True
                    else:
                        logger.error(f"User {user_id} not found in database")
                        return False
                        
                except Exception as e:
                    logger.error(f"Error updating user data: {str(e)}")
                    return False
            else:
                # No user_id in context yet, but we have flashed user info
                # Update context with flashed user information for this session
                logger.info(f"No user_id in context, but successfully identified flashed user: {flashed_user_id}")
                self.context.update({
                    "flashed_user_id": flashed_user_id,
                    "flashed_conversation_code": conversation_code,
                    "flashed_user_name": name,
                    "flashed_user_phone": phone,
                    "flashed_user_email": email,
                    "user_identification_method": "conversation_code"
                })
                
                # Try to find or create user with Flashed UUID
                try:
                    from src.db.repository.user import get_user, create_user
                    from src.db.models import User
                    from datetime import datetime
                    
                    # 🔧 Ensure user_id is a string before uuid.UUID conversion
                    if isinstance(user_id, uuid.UUID):
                        user_uuid = user_id
                    else:
                        user_uuid = uuid.UUID(str(user_id))
                    
                    # Check if user already exists with the Flashed UUID
                    existing_user = get_user(user_uuid)
                    
                    if existing_user:
                        # User exists with correct UUID, just update the conversation code
                        current_user_data = existing_user.user_data or {}
                        updated_user_data = current_user_data.copy()
                        
                        # Get whatsapp_id from context for spaghetti lookup, but preserve existing if available
                        context_whatsapp_id = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
                        existing_whatsapp_id = current_user_data.get("whatsapp_id")
                        
                        # Preserve existing WhatsApp ID if it exists, otherwise use context
                        whatsapp_id = existing_whatsapp_id if existing_whatsapp_id else context_whatsapp_id
                        
                        # Preserve session_key
                        session_key = self.context.get("session_user_key") or current_user_data.get("session_user_key")
                        
                        # Get external_key for consistent user tracking
                        external_key = build_external_key(self.context) or current_user_data.get("external_key")
                        
                        logger.info(f"WhatsApp ID preservation: existing={existing_whatsapp_id}, context={context_whatsapp_id}, final={whatsapp_id}")
                        
                        updated_user_data.update({
                            "flashed_conversation_code": conversation_code,
                            "flashed_user_id": flashed_user_id,
                            "flashed_user_name": name,
                            "flashed_user_phone": phone,
                            "flashed_user_email": email,
                            "whatsapp_id": whatsapp_id,  # Store for spaghetti lookup
                            "session_user_key": session_key,
                            "external_key": external_key  # Store for reliable lookup
                        })
                        
                        update_user_data(user_uuid, updated_user_data)
                        self.context["user_id"] = flashed_user_id
                        logger.info(f"Updated existing user {flashed_user_id} with conversation code")
                        
                        # 🔍 DEBUG: Log context after existing user update
                        logger.info(f"🔍 After existing user update - Context user_id: {self.context.get('user_id')}")
                    else:
                        # Create new user with Flashed UUID
                        logger.info(f"🔍 Creating new user with Flashed UUID: {flashed_user_id}")
                        
                        context_whatsapp_id = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
                        
                        # For new users, try to find existing WhatsApp ID from other users with same phone
                        # This handles the case where a WhatsApp user exists but conversation code creates new user
                        whatsapp_id = context_whatsapp_id
                        if not whatsapp_id and phone:
                            # Try to find WhatsApp ID from existing users with same phone
                            try:
                                from src.db.repository.user import list_users
                                users, _ = list_users(page=1, page_size=1000)
                                for existing_user in users:
                                    if existing_user.user_data:
                                        existing_whatsapp = existing_user.user_data.get("whatsapp_id")
                                        if existing_whatsapp and phone in existing_whatsapp:
                                            whatsapp_id = existing_whatsapp
                                            logger.info(f"Found WhatsApp ID from existing user: {whatsapp_id}")
                                            break
                            except Exception as e:
                                logger.warning(f"Error finding existing WhatsApp ID: {e}")
                        
                        logger.info(f"New user WhatsApp ID: context={context_whatsapp_id}, final={whatsapp_id}")
                        
                        # Get external_key for consistent user tracking
                        external_key = build_external_key(self.context)
                        
                        user_data = {
                            "flashed_conversation_code": conversation_code,
                            "flashed_user_id": flashed_user_id,
                            "flashed_user_name": name,
                            "flashed_user_phone": phone,
                            "flashed_user_email": email,
                            "whatsapp_id": whatsapp_id,  # Store for spaghetti lookup
                            "session_user_key": self.context.get("session_user_key"),
                            "external_key": external_key  # Store for reliable lookup
                        }
                        
                        user_model = User(
                            id=user_uuid,
                            email=email,
                            phone_number=phone,
                            user_data=user_data,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        
                        created_id = create_user(user_model)
                        if created_id:
                            self.context["user_id"] = flashed_user_id
                            logger.info(f"Created new user with Flashed UUID {flashed_user_id}")
                            
                            # 🔍 DEBUG: Log context after new user creation
                            logger.info(f"🔍 After new user creation - Context user_id: {self.context.get('user_id')}")
                        else:
                            logger.warning("Failed to create new user, but conversation code is still valid for session")
                            
                    # Always set the user_id in context, even if database operations fail
                    self.context["user_id"] = flashed_user_id
                    
                    # 🔍 DEBUG: Log final context state
                    logger.info(f"🔍 Final context state - user_id: {self.context.get('user_id')}")
                    
                    # 🔧 FIX: Make session persistent after successful user identification
                    await make_session_persistent(self, self.current_message_history, flashed_user_id)
                
                except Exception as e:
                    logger.error(f"Error in database operations: {str(e)}")
                    # Still set the user_id for the session even if DB operations fail
                    self.context["user_id"] = flashed_user_id
                    
                    # 🔍 DEBUG: Log context after error
                    logger.info(f"🔍 After error - Context user_id: {self.context.get('user_id')}")
                    
                    # 🔧 FIX: Make session persistent even after errors
                    await make_session_persistent(self, self.current_message_history, flashed_user_id)
                
                return True
                
        except Exception as e:
            logger.error(f"Error extracting and processing conversation code: {str(e)}")
            return False
    
    def _generate_conversation_code_request(self) -> str:
        """Generate a message requesting the conversation code in Flashinho's style.
        
        Returns:
            Message requesting conversation code
        """
        return ("E aí, mano! 👋 Pra eu conseguir te dar aquela força nos estudos de forma "
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
            from src.db.repository.user import list_users
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


def create_agent(config: Dict[str, str]) -> FlashinhoV2:
    """Factory function to create Flashinho V2 agent instance."""
    try:
        return FlashinhoV2(config)
    except Exception as e:
        logger.error(f"Failed to create Flashinho V2 Agent: {e}")
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)