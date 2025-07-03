"""Enhanced Stan Agent implementation using new framework patterns.

This demonstrates how to maintain full business logic while dramatically
reducing boilerplate code using the enhancement framework.
"""
import logging
from typing import Dict, Optional, Any

from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.common.tool_wrapper_factory import ToolWrapperFactory
from automagik.agents.models.response import AgentResponse
from automagik.memory.message_history import MessageHistory
from automagik.db.models import Memory
from automagik.db.repository import create_memory
from automagik.db.repository.user import update_user_data

from .specialized.backoffice import backoffice_agent
from .specialized.product import product_agent
from .specialized.order import order_agent
from automagik.tools.blackpearl.tool import get_or_create_contact
from automagik.tools import blackpearl
from automagik.tools.blackpearl import verificar_cnpj

logger = logging.getLogger(__name__)


class StanAgent(AutomagikAgent):
    """Enhanced Stan Agent maintaining full business logic with reduced verbosity.
    
    This version reduces the original 454-line implementation while preserving
    all BlackPearl integration, multi-prompt management, and specialized tools.
    """
    
    # Configuration - replaces 20+ lines of boilerplate
    default_model = "openai:o1-mini"
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Stan Agent with automatic setup."""
        if config is None:
            config = {}
        config.setdefault("enable_multi_prompt", True)

        super().__init__(config)

        # dependencies and prompt default (will be filled by prompts)
        self.dependencies = self.create_default_dependencies()
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        self.tool_registry.register_default_tools(self.context)
        
        # Register Stan-specific tools (replaces 50+ lines of tool registration)
        self._register_stan_tools()
        
        logger.info("Enhanced Stan Agent initialized")
    
    def _register_stan_tools(self) -> None:
        """Register Stan-specific tools using the new wrapper factory."""
        # Use the wrapper factory to eliminate tool wrapper boilerplate
        stan_tools = {
            'verificar_cnpj': verificar_cnpj,
            'product_agent': product_agent,
            'backoffice_agent': backoffice_agent,
            'order_agent': order_agent
        }
        
        for tool_name, tool_func in stan_tools.items():
            if tool_name.endswith('_agent'):
                # Special wrapper for agent tools
                wrapper = ToolWrapperFactory.create_agent_tool_wrapper(tool_func, self.context)
            else:
                # Standard context wrapper
                wrapper = ToolWrapperFactory.create_context_wrapper(tool_func, self.context)
            
            self.tool_registry.register_tool(wrapper)
    
    async def handle_contact_management(
        self,
        channel_payload: Optional[Dict],
        user_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not channel_payload:
            return None

        try:
            user_number = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
            user_name = self.context.get("whatsapp_user_name") or self.context.get("user_name")

            if not user_number:
                logger.debug("No user number found; skipping BlackPearl contact management")
                return None

            contact = await self._get_or_create_blackpearl_contact(user_number, user_name, user_id)

            if contact:
                self._update_context_with_contact_info(contact)

                status = contact.get("status_aprovacao", "NOT_REGISTERED")
                await self.load_prompt_by_status(status)

                await self._store_user_memory(user_id, user_name, user_number, contact)

                logger.info(f"BlackPearl Contact: {contact.get('id')} - {user_name}")
                return contact

            # fallback
            await self.load_prompt_by_status("NOT_REGISTERED")
        except Exception as exc:
            logger.error(f"BlackPearl contact management error: {exc}")
            await self.load_prompt_by_status("NOT_REGISTERED")

        return None
    
    async def _get_or_create_blackpearl_contact(
        self, 
        user_number: str, 
        user_name: Optional[str], 
        user_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Get or create BlackPearl contact - delegates to existing utility."""
        return await get_or_create_contact(
            self.context, 
            user_number, 
            user_name,
            user_id,
            self.db_id
        )
    
    def _update_context_with_contact_info(self, contact: Dict[str, Any]) -> None:
        """Update context with BlackPearl contact information."""
        super()._update_context_with_contact_info(contact)
        
        # Stan-specific context updates - store for async execution
        self._pending_contact_updates = contact
    
    async def _handle_stan_contact_updates(self, contact: Dict[str, Any]) -> None:
        """Handle Stan-specific contact updates including cliente information."""
        try:
            # Get cliente information
            cliente_blackpearl = await blackpearl.get_clientes(
                self.context, 
                contatos_id=contact["id"]
            )
            
            if cliente_blackpearl and "results" in cliente_blackpearl and cliente_blackpearl["results"]:
                cliente = cliente_blackpearl["results"][0]
                self.context["blackpearl_cliente_id"] = cliente.get("id")
                self.context["blackpearl_cliente_nome"] = cliente.get("razao_social")
                self.context["blackpearl_cliente_email"] = cliente.get("email")
                
                logger.info(f"BlackPearl Cliente: {cliente.get('id')} - {cliente.get('razao_social')}")
                
                # Update user data in database
                user_id = self.context.get("user_id")
                if user_id:
                    update_user_data(user_id, {
                        "blackpearl_contact_id": contact.get("id"),
                        "blackpearl_cliente_id": cliente.get("id")
                    })
                    
        except Exception as e:
            logger.error(f"Error updating cliente info: {str(e)}")
    
    async def _store_user_memory(
        self, 
        user_id: Optional[str], 
        user_name: Optional[str], 
        user_number: Optional[str],
        contact: Dict[str, Any]
    ) -> None:
        """Store Stan-specific user information in memory."""
        if not self.db_id:
            return
            
        try:
            user_info = {
                "user_id": user_id,
                "user_name": user_name,
                "user_number": user_number,
                "blackpearl_contact_id": contact.get("id"),
                "blackpearl_cliente_id": self.context.get("blackpearl_cliente_id"),
                "blackpearl_cliente_nome": self.context.get("blackpearl_cliente_nome"),
                "blackpearl_cliente_email": self.context.get("blackpearl_cliente_email"),
            }
            
            # Filter out None values
            user_info_content = {k: v for k, v in user_info.items() if v is not None}
            
            # Create memory entry
            memory_to_create = Memory(
                name="user_information",
                content=str(user_info_content),
                user_id=user_id,
                read_mode="system_prompt",
                access="read_write",
                agent_id=self.db_id
            )
            
            create_memory(memory=memory_to_create)
            logger.info(f"Created/Updated user_information memory for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error storing Stan user memory: {str(e)}")
    
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
        """Stan agent run implementation preserving all original business logic."""
        
        # Extract user_id for BlackPearl operations
        user_id = self.context.get("user_id")
        logger.info(f"Context User ID: {user_id}")
        
        # Initialize prompts if needed (using enhanced multi-prompt manager)
        if not self.prompt_manager.is_registered() and self.db_id:
            await self.initialize_prompts()
        
        # Handle BlackPearl contact management leveraging ChannelHandler system
        # Note: user info is automatically extracted by ChannelHandler and available in context
        contact = await self.handle_contact_management(channel_payload, user_id)
        
        # Handle Stan-specific contact updates
        if hasattr(self, '_pending_contact_updates'):
            await self._handle_stan_contact_updates(self._pending_contact_updates)
            
            # Store user memory with all contact information (context populated by ChannelHandler)
            user_name = self.context.get("whatsapp_user_name") or self.context.get("user_name")
            user_number = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
            
            if contact:
                await self._store_user_memory(user_id, user_name, user_number, contact)
            
            delattr(self, '_pending_contact_updates')
        
        # Use the framework to handle execution (inherited from AutomagikAgent)
        return await self._run_agent(
            input_text=input_text,
            system_prompt=system_message,
            message_history=message_history_obj.get_formatted_pydantic_messages(limit=message_limit) if message_history_obj else [],
            multimodal_content=multimodal_content,
            channel_payload=channel_payload,
            message_limit=message_limit
        )


def create_agent(config: Dict[str, str]) -> StanAgent:
    """Factory function to create enhanced Stan agent."""
    try:
        return StanAgent(config)
    except Exception as e:
        logger.error(f"Failed to create Enhanced Stan Agent: {e}")
        from automagik.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)