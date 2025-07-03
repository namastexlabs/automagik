"""Enhanced Estruturar Agent using ChannelHandler system."""
import logging
from typing import Dict, Optional, List

from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.common.tool_wrapper_factory import ToolWrapperFactory
from automagik.agents.models.response import AgentResponse
from automagik.memory.message_history import MessageHistory
from .prompts.prompt import ESTRUTURAR_AGENT_PROMPT

# Import Evolution tools
from automagik.tools.evolution import send_business_contact, send_personal_contact

logger = logging.getLogger(__name__)


class WhitelistConfig:
    """Configuration for phone number whitelist."""
    
    def __init__(self):
        """Initialize the whitelist configuration."""
        # Default whitelist phone numbers (without country code)
        self._whitelist = [
            "555197285829",
            "5531995400658", "5531997110019", "5531972465316", "5531999911072", "5538998806612", 
            "5538999766612", "5531999286612", "5531998852688", "5531984597690", "5531998227449", 
            "5531995324579", "17814967681", "5531997174121", "5531999923252", "5531992936659", 
            "5531997115844", "17814967681", "5531997236659", "5531997131322", "5531998851698", 
            "5531992988697", "5531999923252", "5531997174121"
        ]
    
    def is_whitelisted(self, phone_number: str) -> bool:
        """Check if a phone number is in the whitelist."""
        if not phone_number:
            return False
        
        # Clean the phone number (remove non-digits)
        clean_number = ''.join(filter(str.isdigit, phone_number))
        
        # Remove Brazil country code if present
        if clean_number.startswith("55") and len(clean_number) > 11:
            clean_number = clean_number[2:]
        
        return clean_number in self._whitelist
    
    def get_whitelist(self) -> List[str]:
        """Get the current whitelist."""
        return self._whitelist.copy()


class EstruturarAgent(AutomagikAgent):
    """Enhanced Estruturar Agent with WhatsApp contact management.
    
    Leverages ChannelHandler system for Evolution payload processing and
    implements business logic for whitelist-based contact redirection.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Estruturar Agent with whitelist configuration."""
        if config is None:
            config = {}
        super().__init__(config)

        self._code_prompt_text = ESTRUTURAR_AGENT_PROMPT

        # dependencies
        self.dependencies = self.create_default_dependencies()
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        self.tool_registry.register_default_tools(self.context)
        
        # Register multimodal analysis tools
        self._register_multimodal_tools()
        
        # Initialize whitelist configuration
        self.whitelist_config = WhitelistConfig()
        
        # Register Evolution-specific tools using wrapper factory
        self._register_estruturar_tools()
        
        logger.info("Enhanced Estruturar Agent initialized with ChannelHandler system")
    
    def _register_estruturar_tools(self) -> None:
        """Register Estruturar-specific Evolution tools."""
        # Evolution tools for contact sharing
        evolution_tools = {
            'send_business_contact': send_business_contact,
            'send_personal_contact': send_personal_contact
        }
        
        for tool_name, tool_func in evolution_tools.items():
            wrapper = ToolWrapperFactory.create_context_wrapper(tool_func, self.context)
            self.tool_registry.register_tool(wrapper)
        
        logger.debug("Registered Estruturar Evolution tools")
    
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
        """Estruturar agent run with whitelist checking."""
        
        # Check whitelist before processing (leverages ChannelHandler context)
        user_number = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
        
        if user_number and not self.whitelist_config.is_whitelisted(user_number):
            logger.info(f"Message from non-whitelisted number {user_number}, not responding")
            # Return empty response for non-whitelisted contacts
            return AgentResponse(
                text="",
                tool_calls=[],
                tool_outputs=[],
                context=self.context
            )
        
        logger.info(f"Processing message from whitelisted number {user_number}")
        
        # Process with framework (Evolution tools automatically available via ChannelHandler)
        return await self._run_agent(
            input_text=input_text,
            system_prompt=system_message,
            message_history=message_history_obj.get_formatted_pydantic_messages(limit=message_limit) if message_history_obj else [],
            multimodal_content=multimodal_content,
            channel_payload=channel_payload,
            message_limit=message_limit
        )

    def _register_multimodal_tools(self):
        """Register multimodal analysis tools using common helper."""
        from automagik.agents.common.multimodal_helper import register_multimodal_tools
        register_multimodal_tools(self.tool_registry, self.dependencies)


def create_agent(config: Dict[str, str]) -> EstruturarAgent:
    """Factory function to create enhanced Estruturar agent."""
    try:
        return EstruturarAgent(config)
    except Exception as e:
        logger.error(f"Failed to create Enhanced Estruturar Agent: {e}")
        from automagik.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)