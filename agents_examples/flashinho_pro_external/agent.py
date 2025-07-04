"""Flashinho Pro External Agent - Advanced multimodal Brazilian educational assistant.

This is an external version of the Flashinho Pro agent with self-contained tools.
"""
import logging
import time
from typing import Dict, Optional, Tuple
import os

from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.response import AgentResponse
from automagik.agents.models.dependencies import AutomagikAgentsDependencies
from automagik.memory.message_history import MessageHistory

# Import tools from local tools directory
from .tools.flashed.tool import (
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy,
    get_user_by_pretty_id
)
from .tools.flashed.provider import FlashedProvider
from .tools.flashed.auth_utils import (
    UserStatusChecker, preserve_authentication_state, restore_authentication_state
)
from .tools.flashed.user_identification import (
    identify_user_comprehensive, UserIdentificationResult,
    ensure_user_uuid_matches_flashed_id, make_session_persistent
)
from .tools.flashed.workflow_runner import analyze_student_problem
from .tools.flashed.message_generator import (
    generate_math_processing_message, generate_pro_feature_message,
    generate_error_message
)
from .tools.evolution.api import send_text_message

# Import prompts
from .prompts.prompt import AGENT_PROMPT, AGENT_FREE

logger = logging.getLogger(__name__)


class FlashinhoProExternal(AutomagikAgent):
    """External version of Flashinho Pro with multimodal capabilities.
    
    This is a self-contained version that includes all necessary tools
    within its own directory structure.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Flashinho Pro External with configuration."""
        if config is None:
            config = {}

        # Default models
        self.pro_model = "google:gemini-2.5-pro"
        self.free_model = "google:gemini-2.5-flash"
        config.setdefault("supported_media", ["image", "audio", "document"])
        config.setdefault("auto_enhance_prompts", True)
        config.setdefault("enable_multi_prompt", True)

        super().__init__(config)

        self._code_prompt_text = AGENT_PROMPT

        # Setup dependencies
        self.dependencies = AutomagikAgentsDependencies(
            model_name=self.pro_model,
            model_settings={
                "temperature": 0.7,
                "max_tokens": 4096
            },
            api_keys={
                "google_api_key": os.environ.get("GEMINI_API_KEY", "")
            },
            tool_config={}
        )
        
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
            
        self.tool_registry.register_default_tools(self.context)
        
        # Register Flashed API tools
        self._register_flashed_tools()
        
        # Register multimodal analysis tools
        self._register_multimodal_tools()
        
        # Status tracking
        self._user_status_checked = False
        self._is_pro_user = False
        
        # Initialize provider
        self.flashed_provider = FlashedProvider()
        
        # Initialize user status checker
        self.user_status_checker = UserStatusChecker()
        
        logger.info("Flashinho Pro External initialized with dynamic model selection")
    
    def _register_flashed_tools(self) -> None:
        """Register all Flashed API tools."""
        self.tool_registry.register_tool(get_user_data)
        self.tool_registry.register_tool(get_user_score)
        self.tool_registry.register_tool(get_user_roadmap)
        self.tool_registry.register_tool(get_user_objectives)
        self.tool_registry.register_tool(get_last_card_round)
        self.tool_registry.register_tool(get_user_energy)
        self.tool_registry.register_tool(get_user_by_pretty_id)
        logger.debug("Flashed tools registered")
    
    def _register_multimodal_tools(self):
        """Register multimodal analysis tools."""
        # Basic multimodal support - can be extended
        logger.debug("Multimodal tools registered")
    
    async def _check_user_pro_status(self, user_id: Optional[str] = None) -> bool:
        """Check if user has Pro subscription status."""
        try:
            if not user_id:
                logger.warning("No user ID for Pro status check")
                return False
                
            return await self.flashed_provider.check_user_pro_status(user_id)
                
        except Exception as e:
            logger.error(f"Error checking Pro status: {str(e)}")
            return False
    
    async def _update_model_and_prompt_based_on_status(self, user_id: Optional[str] = None) -> None:
        """Update model and prompt based on user's Pro status."""
        if self._user_status_checked:
            return
            
        self._is_pro_user = await self._check_user_pro_status(user_id)
        self._user_status_checked = True
        
        if self._is_pro_user:
            self.model_name = self.pro_model
            self.system_message = AGENT_PROMPT
            self.vision_model = self.pro_model
            if hasattr(self, 'dependencies'):
                self.dependencies.model_name = self.pro_model
            logger.info(f"Pro user {user_id} - using {self.pro_model}")
        else:
            self.model_name = self.free_model
            self.system_message = AGENT_FREE
            self.vision_model = self.free_model
            if hasattr(self, 'dependencies'):
                self.dependencies.model_name = self.free_model
            logger.info(f"Free user {user_id} - using {self.free_model}")
    
    async def _detect_student_problem_in_image(self, multimodal_content, user_message: str = "") -> Tuple[bool, str]:
        """Detect if image contains student problem."""
        if not multimodal_content:
            return False, ""
            
        try:
            # Check for image data
            image_data = multimodal_content.get("image_data") or multimodal_content.get("image_url")
            
            if not image_data and "images" in multimodal_content:
                images = multimodal_content.get("images", [])
                if images and isinstance(images, list) and len(images) > 0:
                    first_image = images[0]
                    if isinstance(first_image, dict):
                        image_data = first_image.get("data") or first_image.get("url") or first_image.get("media_url")
                    else:
                        image_data = first_image
            
            if not image_data:
                return False, ""
            
            # Detect educational context
            educational_keywords = {
                "matemática": ["equação", "resolver", "matemática", "cálculo", "álgebra", "geometria"],
                "física": ["física", "cinemática", "força", "energia", "movimento"],
                "química": ["química", "reação", "elemento", "molécula", "átomo"],
                "biologia": ["biologia", "célula", "DNA", "fotossíntese", "evolução"],
                "educacional": ["exercício", "questão", "problema", "dúvida", "estudar", "prova"]
            }
            
            detected_subject = "geral"
            user_text = user_message.lower()
            
            for subject, keywords in educational_keywords.items():
                if any(keyword in user_text for keyword in keywords):
                    detected_subject = subject
                    break
            
            is_educational = detected_subject != "geral" or any(
                keyword in user_text for keywords in educational_keywords.values() for keyword in keywords
            )
            
            if is_educational:
                context = f"educational content detected: {detected_subject} problem"
                logger.info(f"Student problem detected: {context}")
                return True, context
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error detecting student problem: {str(e)}")
            return False, ""
    
    async def _send_processing_message(self, phone: str, user_name: str, problem_context: str, user_message: str = ""):
        """Send processing message via Evolution."""
        try:
            message = await generate_math_processing_message(
                user_name=user_name,
                math_context=problem_context,
                user_message=user_message
            )
            
            instance = (
                self.context.get("evolution_instance") or 
                self.context.get("whatsapp_instance") or
                self.context.get("instanceId")
            )
            
            if not instance:
                logger.warning("No Evolution instance in context")
                return
                
            success, msg_id = await send_text_message(
                instance_name=instance,
                number=phone,
                text=message
            )
            
            if success:
                logger.debug(f"Processing message sent to {phone}")
            else:
                logger.error(f"Failed to send processing message: {msg_id}")
                
        except Exception as e:
            logger.error(f"Error sending processing message: {str(e)}")
    
    async def _handle_student_problem_flow(self, multimodal_content, user_id: str, phone: str, problem_context: str, user_message: str = "") -> str:
        """Handle student problem solving flow."""
        try:
            user_name = self.context.get("flashed_user_name", "")
            await self._send_processing_message(phone, user_name, problem_context, user_message)
            
            # Extract image data
            image_data = multimodal_content.get("image_data") or multimodal_content.get("image_url")
            
            if not image_data and "images" in multimodal_content:
                images = multimodal_content.get("images", [])
                if images and isinstance(images, list) and len(images) > 0:
                    first_image = images[0]
                    if isinstance(first_image, dict):
                        image_data = first_image.get("data") or first_image.get("url") or first_image.get("media_url")
                    else:
                        image_data = first_image
            
            if not image_data:
                logger.error("No image data found")
                return "Desculpa, não consegui acessar a imagem. Pode tentar enviar novamente?"
            
            workflow_id = f"flashinho_{int(time.time())}_{str(user_id)[:8]}"
            logger.info(f"Starting workflow {workflow_id}")
            
            try:
                result_text = await analyze_student_problem(image_data, user_message)
                duration = time.time() - float(workflow_id.split('_')[1])
                logger.info(f"Workflow completed in {duration:.2f}s")
                
                result_text += f"\n\n<!-- workflow:{workflow_id} -->"
                return result_text
                
            except Exception as e:
                logger.error(f"Workflow failed: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"Error in problem flow: {str(e)}")
            
            error_msg = await generate_error_message(
                user_name=self.context.get("flashed_user_name"),
                error_context="falha ao processar o problema",
                suggestion="tentar enviar a imagem novamente"
            )
            
            return error_msg
    
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
        """Main run method for the agent."""
        try:
            self.current_channel_payload = channel_payload
            
            # User identification
            phone_number = (
                self.context.get("whatsapp_user_number") or 
                self.context.get("user_phone_number")
            )
            
            user_id = self.context.get("user_id") or self.context.get("flashed_user_id")
            
            # Check Pro status
            if user_id:
                await self._update_model_and_prompt_based_on_status(user_id)
            
            # Handle multimodal content
            if multimodal_content:
                if not self._is_pro_user:
                    # Free user - show upgrade message
                    pro_message = await generate_pro_feature_message(
                        user_name=self.context.get("flashed_user_name"),
                        feature_name="análise de imagens educacionais"
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
                else:
                    # Pro user - check for student problems
                    is_student_problem, problem_context = await self._detect_student_problem_in_image(
                        multimodal_content, input_text
                    )
                    
                    if is_student_problem and phone_number:
                        result_text = await self._handle_student_problem_flow(
                            multimodal_content, user_id, phone_number, problem_context, input_text
                        )
                        
                        return AgentResponse(
                            text=result_text,
                            success=True,
                            usage={
                                "model": self.pro_model,
                                "request_tokens": 0,
                                "response_tokens": 0,
                                "total_tokens": 0
                            }
                        )
            
            # Regular chat flow
            logger.info(f"Regular chat for user {user_id}")
            
            return await self._run_agent(
                input_text=input_text,
                system_prompt=system_message,
                message_history=message_history_obj.get_formatted_pydantic_messages(limit=message_limit) if message_history_obj else [],
                multimodal_content=multimodal_content,
                channel_payload=channel_payload,
                message_limit=message_limit
            )
            
        except Exception as e:
            logger.error(f"Error in run method: {str(e)}")
            
            error_msg = await generate_error_message(
                user_name=self.context.get("flashed_user_name"),
                error_context="erro geral",
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
    
    @property
    def model_name(self) -> str:
        """Get the current model name."""
        return self.dependencies.model_name or self.free_model
    
    @model_name.setter
    def model_name(self, value: str) -> None:
        """Set the current model name."""
        self.dependencies.model_name = value