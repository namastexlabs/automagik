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
from .memory_manager import update_flashinho_pro_memories, initialize_flashinho_pro_memories


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
            await initialize_flashinho_pro_memories(self.db_id, safe_user_id)
            success = await update_flashinho_pro_memories(self.db_id, safe_user_id, self.context)
            
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
        
        external_key = self._get_external_key()
        if external_key:
            found_by_key = await self._attach_user_by_external_key(external_key)
            if found_by_key:
                logger.info(f"🔑 User identified via external_key: {self.context.get('user_id')}")
                await self._sync_message_history_if_needed(message_history_obj, history_user_id)
    
    async def _try_flashed_id_identification(self, message_history_obj: Optional[MessageHistory], history_user_id: Optional[str]) -> None:
        """Try to identify user by Flashed ID lookup."""
        if self.context.get("user_id"):
            return
        
        found_by_flashed_id = await self._attach_user_by_flashed_id_lookup()
        if found_by_flashed_id:
            logger.info(f"🔍 User identified via flashed_id_lookup: {self.context.get('user_id')}")
            await self._sync_message_history_if_needed(message_history_obj, history_user_id)
    
    async def _sync_message_history_if_needed(self, message_history_obj: Optional[MessageHistory], history_user_id: Optional[str]) -> None:
        """Sync message history with new user ID if needed."""
        new_user_id = self.context.get("user_id")
        if message_history_obj and new_user_id and new_user_id != str(history_user_id):
            await self._update_message_history_user_id(message_history_obj, new_user_id)
            await self._update_session_user_id(message_history_obj, new_user_id)
    
    async def _handle_conversation_code_flow(self, input_text: str, user_id: Optional[str], message_history_obj: Optional[MessageHistory], history_user_id: Optional[str], **kwargs) -> Optional[AgentResponse]:
        """Handle conversation code extraction and processing flow."""
        conversation_code_extracted = await self._try_extract_and_process_conversation_code(input_text, user_id)
        
        if not conversation_code_extracted:
            return self._create_conversation_code_request_response()
        
        # Sync message history after conversation code processing
        new_user_id = self.context.get("user_id")
        logger.info(f"🔍 After conversation code processing - Context user_id: {new_user_id}")
        
        if message_history_obj and new_user_id and new_user_id != str(history_user_id):
            await self._update_message_history_user_id(message_history_obj, new_user_id)
            await self._update_session_user_id(message_history_obj, new_user_id)
        
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
                
                # 🔧 FIX: Make session persistent for identified users
                if message_history_obj:
                    await self._make_session_persistent(message_history_obj, user_id)
                    
                    # 🔧 CRITICAL FIX: Re-check message history after making session persistent
                    # This ensures we get the full conversation history from database
                    logger.info(f"🔍 Re-checking message history after making session persistent")
                    try:
                        formatted_messages = message_history_obj.get_formatted_pydantic_messages(limit=message_limit or 20)
                        logger.info(f"🔍 After persistence: {len(formatted_messages)} messages found in history")
                        for i, msg in enumerate(formatted_messages[-3:]):  # Show last 3 messages
                            msg_type = type(msg).__name__
                            content = ""
                            if hasattr(msg, 'parts') and msg.parts:
                                for part in msg.parts:
                                    if hasattr(part, 'content'):
                                        content = part.content[:50] + "..." if len(part.content) > 50 else part.content
                                        break
                            logger.info(f"🔍   After persistence Message {i}: {msg_type} - {content}")
                    except Exception as e:
                        logger.error(f"🔍 Error re-checking message history after persistence: {e}")
            
            # Log execution context
            self._log_execution_context(user_id)
            
            # 🔍 DEBUG: Check message history and add current message before running agent
            if message_history_obj:
                try:
                    # Add current user message to history BEFORE running the agent
                    logger.info(f"🔍 Adding current user message to history before agent run")
                    # 🔧 Convert any UUID objects inside context to strings for JSON serialization
                    safe_context = {}
                    for k, v in self.context.items():
                        if isinstance(v, uuid.UUID):
                            safe_context[k] = str(v)
                        else:
                            safe_context[k] = v

                    message_history_obj.add(
                        content=input_text,
                        agent_id=self.db_id,
                        context=safe_context,
                        channel_payload=channel_payload
                    )
                    
                    # Now check the updated message history
                    formatted_messages = message_history_obj.get_formatted_pydantic_messages(limit=message_limit or 20)
                    logger.info(f"🔍 Message history check: {len(formatted_messages)} messages found (including current)")
                    for i, msg in enumerate(formatted_messages[-3:]):  # Show last 3 messages
                        msg_type = type(msg).__name__
                        content = ""
                        if hasattr(msg, 'parts') and msg.parts:
                            for part in msg.parts:
                                if hasattr(part, 'content'):
                                    content = part.content[:50] + "..." if len(part.content) > 50 else part.content
                                    break
                        logger.info(f"🔍   Message {i}: {msg_type} - {content}")
                except Exception as e:
                    logger.error(f"🔍 Error checking message history: {e}")
            else:
                logger.info("🔍 No message_history_obj provided to FlashinhoV2")
            
            # Execute agent using the framework directly (bypass AutomagikAgent.run to avoid message duplication)
            pydantic_messages = message_history_obj.get_formatted_pydantic_messages(limit=message_limit or 20) if message_history_obj else []
            logger.info(f"🔍 CRITICAL: Sending {len(pydantic_messages)} messages to AI model")
            for i, msg in enumerate(pydantic_messages):
                msg_type = type(msg).__name__
                content_preview = ""
                if hasattr(msg, 'parts') and msg.parts:
                    for part in msg.parts:
                        if hasattr(part, 'content'):
                            content_preview = part.content[:100] + "..." if len(part.content) > 100 else part.content
                            break
                logger.info(f"🔍   AI Model Message {i}: {msg_type} - {content_preview}")
            
            response = await self._run_agent(
                input_text=input_text,
                system_prompt=system_message,
                message_history=pydantic_messages,
                multimodal_content=multimodal_content,
                channel_payload=channel_payload,
                message_limit=message_limit
            )
            
            # 🔍 DEBUG: Check if response shows conversation awareness
            if response and response.text:
                response_preview = response.text[:200] + "..." if len(response.text) > 200 else response.text
                logger.info(f"🔍 AI Response preview: {response_preview}")
                
                # Check if response references previous conversation
                conversation_indicators = ["lembra", "dissemos", "conversa anterior", "falamos", "mencionou", "disse antes"]
                has_memory_reference = any(indicator in response.text.lower() for indicator in conversation_indicators)
                logger.info(f"🔍 Response shows conversation awareness: {has_memory_reference}")
            
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
        """Check if user needs to provide conversation code.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if conversation code is required, False otherwise
        """
        try:
            logger.info(f"🧪 Checking conversation code requirement for user_id: {user_id}")
            
            # 🍝 SPAGHETTI APPROACH: Check for existing user by whatsapp_id in user_data
            whatsapp_id = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
            
            # If no WhatsApp ID in context, try to extract from channel payload
            if not whatsapp_id and hasattr(self, 'current_channel_payload') and self.current_channel_payload:
                user_data = self.current_channel_payload.get("user", {})
                whatsapp_id = user_data.get("phone_number")
                logger.info(f"🍝 Extracted WhatsApp ID from channel payload: {whatsapp_id}")
            
            if whatsapp_id:
                # 🔧 Ensure whatsapp_id is a string to prevent UUID attribute errors
                if not isinstance(whatsapp_id, str):
                    whatsapp_id = str(whatsapp_id)
                logger.info(f"🍝 Checking for existing user with whatsapp_id: {whatsapp_id}")
                try:
                    from src.db.repository.user import list_users
                    
                    # Get all users and check their user_data for whatsapp_id
                    users, _ = list_users(page=1, page_size=1000)  # Get all users
                    
                    for user in users:
                        if user.user_data:
                            stored_whatsapp_id = user.user_data.get("whatsapp_id")
                            if stored_whatsapp_id:
                                # Normalize both IDs for comparison - ensure they're strings
                                stored_normalized = str(stored_whatsapp_id).replace("+", "").replace("-", "").replace("@s.whatsapp.net", "")
                                current_normalized = str(whatsapp_id).replace("+", "").replace("-", "").replace("@s.whatsapp.net", "")
                                
                                logger.info(f"🍝 Comparing stored: '{stored_normalized}' vs current: '{current_normalized}'")
                                
                                if stored_normalized == current_normalized:
                                    # Found user with matching whatsapp_id
                                    conversation_code = user.user_data.get("flashed_conversation_code")
                                    if conversation_code:
                                        logger.info(f"🍝 Found existing user {user.id} with whatsapp_id {whatsapp_id} and conversation code!")
                                        # 🍝 SPAGHETTI: Update current context to use this user
                                        self.context["user_id"] = str(user.id)
                                        self.context["flashed_user_id"] = user.user_data.get("flashed_user_id")
                                        self.context["flashed_conversation_code"] = conversation_code
                                        self.context["flashed_user_name"] = user.user_data.get("flashed_user_name")
                                        self.context["user_identification_method"] = "whatsapp_id_lookup"
                                        logger.info(f"🍝 Updated context to use existing user {user.id}")
                                        
                                        # 🔧 FIX: Sync session history with the identified user
                                        if hasattr(self, 'current_message_history') and self.current_message_history:
                                            history_user_id = self.current_message_history.user_id
                                            if str(user.id) != str(history_user_id):
                                                logger.info(f"🔄 Syncing session history from {history_user_id} to {user.id}")
                                                await self._update_message_history_user_id(self.current_message_history, str(user.id))
                                                await self._update_session_user_id(self.current_message_history, str(user.id))
                                            # Make session persistent after user identification
                                            await self._make_session_persistent(self.current_message_history, str(user.id))
                                        
                                        return False  # No need to ask for conversation code
                                    else:
                                        logger.info(f"🍝 Found user {user.id} with whatsapp_id but no conversation code")
                                        # Update context to use this user but still require conversation code
                                        self.context["user_id"] = str(user.id)
                                        
                                        # 🔧 FIX: Sync session history with the identified user
                                        if hasattr(self, 'current_message_history') and self.current_message_history:
                                            history_user_id = self.current_message_history.user_id
                                            if str(user.id) != str(history_user_id):
                                                logger.info(f"🔄 Syncing session history from {history_user_id} to {user.id}")
                                                await self._update_message_history_user_id(self.current_message_history, str(user.id))
                                                await self._update_session_user_id(self.current_message_history, str(user.id))
                                            # Make session persistent after user identification
                                            await self._make_session_persistent(self.current_message_history, str(user.id))
                                        
                                        return True
                                    
                except Exception as e:
                    logger.error(f"🍝 Error in whatsapp_id lookup: {str(e)}")
            
            if not user_id:
                return True  # No user ID means conversation code required
            
            from src.db.repository.user import get_user
            
            # 🔧 Ensure user_id is a string before uuid.UUID conversion
            if isinstance(user_id, uuid.UUID):
                user_uuid = user_id
            else:
                user_uuid = uuid.UUID(str(user_id))
            
            # Get user from database
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

    async def _try_extract_and_process_conversation_code(self, message: str, user_id: Optional[str]) -> bool:
        """Try to extract conversation code from message and process it.
        Returns True if conversation code was found and processed successfully.
        """
        try:
            from .user_status_checker import UserStatusChecker
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
                        external_key = self._get_external_key() or current_user_data.get("external_key")
                        
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
                        if hasattr(self, 'current_message_history') and self.current_message_history:
                            await self._make_session_persistent(self.current_message_history, user_id)
                        
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
                        external_key = self._get_external_key() or current_user_data.get("external_key")
                        
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
                        external_key = self._get_external_key()
                        
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
                    if hasattr(self, 'current_message_history') and self.current_message_history:
                        await self._make_session_persistent(self.current_message_history, flashed_user_id)
                    
                except Exception as e:
                    logger.error(f"Error in database operations: {str(e)}")
                    # Still set the user_id for the session even if DB operations fail
                    self.context["user_id"] = flashed_user_id
                    
                    # 🔍 DEBUG: Log context after error
                    logger.info(f"🔍 After error - Context user_id: {self.context.get('user_id')}")
                    
                    # 🔧 FIX: Make session persistent even after errors
                    if hasattr(self, 'current_message_history') and self.current_message_history:
                        await self._make_session_persistent(self.current_message_history, flashed_user_id)
                
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

    async def _update_message_history_user_id(self, message_history_obj: MessageHistory, new_user_id: str) -> None:
        """Update MessageHistory object and existing messages to use the new user_id.
        
        Args:
            message_history_obj: The MessageHistory object to update
            new_user_id: The new user_id (Flashed UUID) to use
        """
        try:
            from src.db.repository.message import update_message
            
            old_user_id = message_history_obj.user_id
            new_user_uuid = uuid.UUID(new_user_id)
            
            logger.info(f"🔄 Updating MessageHistory user_id from {old_user_id} to {new_user_id}")
            
            # Update the MessageHistory object itself
            message_history_obj.user_id = new_user_uuid
            
            # Update all existing messages in this session to use the new user_id
            session_uuid = uuid.UUID(message_history_obj.session_id)
            
            # Get all messages in this session that have the old user_id
            session_messages = message_history_obj.all_messages()
            
            updated_count = 0
            for message in session_messages:
                if message.user_id == old_user_id:
                    # Update this message to use the new user_id
                    try:
                        message.user_id = new_user_uuid
                        success = update_message(message)
                        if success:
                            updated_count += 1
                            logger.debug(f"🔄 Updated message {message.id} user_id to {new_user_id}")
                        else:
                            logger.warning(f"⚠️ Failed to update message {message.id} user_id")
                    except Exception as e:
                        logger.error(f"❌ Error updating message {message.id}: {str(e)}")
            
            logger.info(f"✅ Successfully updated {updated_count} messages to use new user_id {new_user_id}")
            
            # Also update the session to use the new user_id
            try:
                from src.db.repository.session import get_session, update_session
                session = get_session(session_uuid)
                if session and session.user_id == old_user_id:
                    session.user_id = new_user_uuid
                    update_session(session)
                    logger.info(f"✅ Updated session {session_uuid} user_id to {new_user_id}")
            except Exception as e:
                logger.error(f"❌ Error updating session user_id: {str(e)}")
                
        except Exception as e:
            logger.error(f"❌ Error in _update_message_history_user_id: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def _update_session_user_id(self, message_history_obj: Optional[MessageHistory], new_user_id: str) -> None:
        """Update the session's user_id after conversation code processing.
        
        This ensures that all future messages in the session use the correct Flashed user ID.
        
        Args:
            message_history_obj: The MessageHistory object to update
            new_user_id: The new user ID (Flashed UUID) to use
        """
        if not message_history_obj or not new_user_id:
            return
            
        try:
            from src.db.repository.session import update_session
            from src.db.models import Session
            
            # Get the session from message history
            session_info = message_history_obj.get_session_info()
            if not session_info:
                logger.warning("No session info found in MessageHistory")
                return
                
            # Update the session's user_id
            session = Session(
                id=session_info.id,
                user_id=uuid.UUID(new_user_id)
            )
            
            success = update_session(session)
            if success:
                logger.info(f"✅ Updated session {session_info.id} to use Flashed user_id {new_user_id}")
            else:
                logger.warning(f"Failed to update session user_id")
                
        except Exception as e:
            logger.error(f"Error updating session user_id: {str(e)}")

    async def _make_session_persistent(self, message_history_obj: Optional[MessageHistory], user_id: str) -> None:
        """Make a local-only session persistent in the database after user identification.
        
        This is called after a user is identified via conversation code to ensure
        that the session history is properly saved to the database.
        
        Args:
            message_history_obj: The MessageHistory object to make persistent
            user_id: The user ID to associate with the session
        """
        if not message_history_obj or not user_id:
            return
            
        try:
            from src.db.repository.session import create_session, get_session
            from src.db.repository.message import create_message
            from src.db.models import Session, Message
            from datetime import datetime, timezone
            from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart
            
            # Check if session is in local-only mode
            if not getattr(message_history_obj, '_local_only', False):
                logger.debug("Session is already persistent, no action needed")
                return
                
            session_uuid = uuid.UUID(message_history_obj.session_id)
            user_uuid = uuid.UUID(user_id)
            
            # 🔧 CRITICAL FIX: Save local messages to database BEFORE clearing them
            local_messages = getattr(message_history_obj, '_local_messages', [])
            logger.info(f"📝 Found {len(local_messages)} local messages to save to database")
            
            # Check if session already exists in database
            existing_session = get_session(session_uuid)
            if not existing_session:
                # Create the session in the database first
                session = Session(
                    id=session_uuid,
                    user_id=user_uuid,
                    name=f"Session-{session_uuid}",
                    platform="automagik"
                )
                
                success = create_session(session)
                if not success:
                    logger.warning(f"Failed to create session {session_uuid} in database")
                    return
                    
                logger.info(f"✅ Created session {session_uuid} in database")
            else:
                logger.debug(f"Session {session_uuid} already exists in database")
            
            # Save local messages to database
            saved_count = 0
            for local_msg in local_messages:
                try:
                    # Determine message role and content
                    role = "user"
                    content = ""
                    
                    if isinstance(local_msg, ModelRequest):
                        role = "user"
                        # Extract content from UserPromptPart
                        for part in local_msg.parts:
                            if isinstance(part, UserPromptPart):
                                content = part.content
                                break
                    elif isinstance(local_msg, ModelResponse):
                        role = "assistant"
                        # Extract content from TextPart
                        for part in local_msg.parts:
                            if isinstance(part, TextPart):
                                content = part.content
                                break
                    else:
                        # Handle system messages or other types
                        if hasattr(local_msg, 'parts'):
                            for part in local_msg.parts:
                                if hasattr(part, 'content'):
                                    content = part.content
                                    break
                        else:
                            continue  # Skip unknown message types
                    
                    if content:
                        # Create message in database
                        message = Message(
                            id=uuid.uuid4(),
                            session_id=session_uuid,
                            user_id=user_uuid,
                            agent_id=self.db_id,
                            role=role,
                            text_content=content,
                            message_type="text",
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc)
                        )
                        
                        message_id = create_message(message)
                        if message_id:
                            saved_count += 1
                            logger.debug(f"💾 Saved {role} message to database: {content[:50]}...")
                        else:
                            logger.warning(f"Failed to save {role} message to database")
                            
                except Exception as msg_error:
                    logger.error(f"Error saving local message to database: {msg_error}")
                    continue
            
            logger.info(f"💾 Successfully saved {saved_count}/{len(local_messages)} local messages to database")
            
            # Update MessageHistory to use persistent mode
            message_history_obj._local_only = False
            message_history_obj.user_id = user_uuid
            
            # 🔧 CRITICAL FIX: Reload messages from database after saving local messages
            logger.info(f"🔄 Reloading message history from database after making session persistent")
            try:
                # Clear local messages and reload from database
                message_history_obj._local_messages.clear()
                db_messages = message_history_obj.all_messages()  # This will now read from database
                logger.info(f"🔄 Reloaded {len(db_messages)} messages from database for session {session_uuid}")
            except Exception as reload_error:
                logger.error(f"🔄 Error reloading messages from database: {reload_error}")
            
            logger.info(f"✅ Made session {session_uuid} persistent for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error making session persistent: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def _get_external_key(self) -> Optional[str]:
        """Get external key for user identification.
        
        Creates a unique key combining session name and phone number for consistent user tracking.
        
        Returns:
            External key in format "session_name|phone_number" or None
        """
        session_name = self.context.get("session_name")
        phone_number = (
            self.context.get("whatsapp_user_number") or 
            self.context.get("user_phone_number") or
            self.context.get("whatsapp_id")
        )
        
        if session_name and phone_number:
            # Normalize phone number for consistency - ensure it's a string
            normalized_phone = str(phone_number).replace("+", "").replace("-", "").replace("@s.whatsapp.net", "")
            return f"{session_name}|{normalized_phone}"
        return None
    
    async def _attach_user_by_external_key(self, external_key: str) -> bool:
        """Try to attach existing user by external key.
        
        Args:
            external_key: The external key to search for
            
        Returns:
            True if user was found and attached, False otherwise
        """
        if not external_key:
            return False
            
        try:
            from src.db.repository.user import list_users
            
            logger.info(f"🔑 Searching for user with external_key: {external_key}")
            
            # Search all users for matching external_key
            users, _ = list_users(page=1, page_size=1000)
            
            for user in users:
                if user.user_data and user.user_data.get("external_key") == external_key:
                    # Found user with matching external key
                    logger.info(f"🔑 Found user {user.id} with external_key {external_key}")
                    
                    # Update context with user info
                    self.context["user_id"] = str(user.id)
                    self.context["flashed_user_id"] = user.user_data.get("flashed_user_id")
                    self.context["flashed_conversation_code"] = user.user_data.get("flashed_conversation_code")
                    self.context["flashed_user_name"] = user.user_data.get("flashed_user_name")
                    self.context["user_identification_method"] = "external_key"
                    
                    return True
                    
            logger.info(f"🔑 No user found with external_key {external_key}")
            return False
            
        except Exception as e:
            logger.error(f"Error in external_key lookup: {str(e)}")
            return False
            
    async def _attach_user_by_flashed_id_lookup(self) -> bool:
        """Try to find user by searching all users for Flashed user IDs.
        
        This is a fallback method when external_key and session_key approaches fail.
        
        Returns:
            True if user was found and attached, False otherwise
        """
        try:
            from src.db.repository.user import list_users
            
            logger.info(f"🔍 Searching for any user with flashed_user_id (fallback lookup)")
            
            # Get all users and check their user_data for flashed_user_id
            users, _ = list_users(page=1, page_size=1000)
            
            for user in users:
                if user.user_data and user.user_data.get("flashed_user_id"):
                    # Found user with Flashed user ID
                    flashed_user_id = user.user_data.get("flashed_user_id")
                    conversation_code = user.user_data.get("flashed_conversation_code")
                    
                    if conversation_code:  # Only use users with conversation codes
                        logger.info(f"🔍 Found user {user.id} with flashed_user_id {flashed_user_id}")
                        
                        # Update context with user info
                        self.context["user_id"] = str(user.id)
                        self.context["flashed_user_id"] = flashed_user_id
                        self.context["flashed_conversation_code"] = conversation_code
                        self.context["flashed_user_name"] = user.user_data.get("flashed_user_name")
                        self.context["user_identification_method"] = "flashed_id_lookup"
                        
                        return True
                        
            logger.info(f"🔍 No user found with flashed_user_id")
            return False
            
        except Exception as e:
            logger.error(f"Error in flashed_id lookup: {str(e)}")
            return False
            

def create_agent(config: Dict[str, str]) -> FlashinhoV2:
    """Factory function to create Flashinho V2 agent instance."""
    try:
        return FlashinhoV2(config)
    except Exception as e:
        logger.error(f"Failed to create Flashinho V2 Agent: {e}")
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)