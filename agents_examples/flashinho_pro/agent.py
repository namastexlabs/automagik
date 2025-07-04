"""Flashinho Pro Agent - Minimal External Agent Pattern."""
from typing import Dict, Optional
from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.response import AgentResponse
from automagik.memory.message_history import MessageHistory
import logging

logger = logging.getLogger(__name__)


class FlashinhoProAgent(AutomagikAgent):
    """Flashinho Pro - Advanced educational assistant with Pro/Free tier support."""
    
    # Declarative configuration
    DEFAULT_MODEL = "google:gemini-2.0-flash-exp"  # Free tier default
    DEFAULT_CONFIG = {
        "supported_media": ["image", "audio", "video", "document"],
        "language": "pt-BR",
        "pro_model": "google:gemini-2.0-flash-exp",
        "free_model": "google:gemini-1.5-flash"
    }
    
    # External agent configuration
    PACKAGE_ENV_FILE = ".env"
    EXTERNAL_API_KEYS = [
        ("FLASHED_API_KEY", "Flashed API authentication key"),
        ("GEMINI_API_KEY", "Google Gemini API key"),
    ]
    
    # Prompt file
    PROMPT_FILE = "prompt.md"
    
    def __init__(self, config: Dict[str, str] = None) -> None:
        """Initialize the agent."""
        super().__init__(config or {})
        
        # Set up Pro/Free models
        self.pro_model = self.config.get("pro_model", "google:gemini-2.0-flash-exp")
        self.free_model = self.config.get("free_model", "google:gemini-1.5-flash")
        
        # Initialize state
        self._is_pro_user = False
        self._user_status_checked = False
        
        # Create dependencies and register tools
        self.dependencies = self.create_default_dependencies()
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Register centralized tools
        self.tool_registry.register_default_tools(self.context)
        
        logger.info("Flashinho Pro initialized with dynamic model selection")
    
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
        """Run method with Pro/Free tier logic."""
        try:
            # In a real implementation, check user's Pro status here
            # For now, use the default model
            
            # Check if user is trying to use multimodal content
            if multimodal_content and not self._is_pro_user:
                return AgentResponse(
                    text="🌟 Opa! Análise de imagens é um recurso Pro. Faça upgrade para usar este recurso incrível!",
                    success=True,
                    metadata={"feature_restricted": True, "user_type": "free"}
                )
            
            # Regular chat flow using parent's run method
            return await super().run(
                input_text=input_text,
                multimodal_content=multimodal_content,
                system_message=system_message,
                message_history_obj=message_history_obj,
                channel_payload=channel_payload,
                message_limit=message_limit
            )
            
        except Exception as e:
            logger.error(f"Error in Flashinho Pro: {str(e)}")
            return AgentResponse(
                text="Desculpe, tive um problema ao processar sua mensagem. Pode tentar novamente?",
                success=False,
                error_message=str(e)
            )