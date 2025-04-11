"""StanAgentAgent implementation with PydanticAI.

This module provides a StanAgentAgent class that uses PydanticAI for LLM integration
and inherits common functionality from AutomagikAgent.
"""
import logging
import traceback
from typing import Dict, Optional

from pydantic_ai import Agent
from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.models.response import AgentResponse
from src.agents.simple.stan_agent.models import EvolutionMessagePayload
from src.agents.simple.stan_agent.specialized.backoffice import backoffice_agent
from src.agents.simple.stan_agent.specialized.product import product_agent
from src.db.models import Memory
from src.db.repository import create_memory
from src.db.repository.user import update_user_data
from src.memory.message_history import MessageHistory
from src.agents.simple.stan_agent.utils import get_or_create_contact

# Import only necessary utilities
from src.agents.common.message_parser import (
    extract_tool_calls, 
    extract_tool_outputs,
    extract_all_messages
)
from src.agents.common.dependencies_helper import (
    parse_model_settings,
    create_usage_limits,
    get_model_name,
    add_system_message_to_history
)
from src.tools import blackpearl
from src.tools.blackpearl.schema import StatusAprovacaoEnum
from src.tools.blackpearl import verificar_cnpj

logger = logging.getLogger(__name__)

class StanAgent(AutomagikAgent):
    """StanAgentAgent implementation using PydanticAI.
    
    This agent provides a basic implementation that follows the PydanticAI
    conventions for multimodal support and tool calling.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize the StanAgentAgent.
        
        Args:
            config: Dictionary with configuration options
        """
        from src.agents.simple.stan_agent.prompts.prompt import AGENT_PROMPT
        
        # Initialize the base agent
        super().__init__(config, AGENT_PROMPT)
        
        # PydanticAI-specific agent instance
        self._agent_instance: Optional[Agent] = None
        
        # Configure dependencies
        self.dependencies = AutomagikAgentsDependencies(
            model_name=get_model_name(config),
            model_settings=parse_model_settings(config)
        )
        
        # Set agent_id if available
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Set usage limits if specified in config
        usage_limits = create_usage_limits(config)
        if usage_limits:
            self.dependencies.set_usage_limits(usage_limits)
        
        # Register default tools
        self.tool_registry.register_default_tools(self.context)
        
        # Register BlackPearl CNPJ verification tool with context injection
        self.tool_registry.register_tool_with_context(verificar_cnpj, self.context)
        
        logger.info("StanAgentAgent initialized successfully")
    
    async def _initialize_pydantic_agent(self) -> None:
        """Initialize the underlying PydanticAI agent."""
        if self._agent_instance is not None:
            return
            
        # Get model configuration
        model_name = self.dependencies.model_name
        
        
        # Register specialized agents         
        logger.info(f"Current context: {self.context}")
        # Register specialized agents using the simpler method
        self.tool_registry.register_tool(backoffice_agent)
        self.tool_registry.register_tool(product_agent)
        
        # Convert tools to PydanticAI format
        tools = self.tool_registry.convert_to_pydantic_tools()
        logger.info(f"Prepared {len(tools)} tools for PydanticAI agent")
        
        
        try:
            # Create agent instance
            self._agent_instance = Agent(
                model="openai:o3-mini",
                system_prompt=self.system_prompt,
                tools=tools,
                deps_type=AutomagikAgentsDependencies
            )
            
            logger.info(f"Initialized agent with model: {model_name} and {len(tools)} tools")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            raise
        
    async def run(self, input_text: str, *, multimodal_content=None, system_message=None, message_history_obj: Optional[MessageHistory] = None,
                 channel_payload: Optional[dict] = None,
                 message_limit: Optional[int] = 20) -> AgentResponse:
        
        user_id = self.context.get("user_id")
        logger.info(f"Context User ID: {user_id}")
        # Convert channel_payload to EvolutionMessagePayload if provided
        evolution_payload = None
        if channel_payload:
            try:
                # Convert the dictionary to EvolutionMessagePayload model
                evolution_payload = EvolutionMessagePayload(**channel_payload)
                logger.debug("Successfully converted channel_payload to EvolutionMessagePayload")
            except Exception as e:
                logger.error(f"Failed to convert channel_payload to EvolutionMessagePayload: {str(e)}")
        
        # Extract user information
        user_number, user_name = None, None
        if evolution_payload:
            user_number = evolution_payload.get_user_number()
            user_name = evolution_payload.get_user_name()
            logger.debug(f"Extracted user info: number={user_number}, name={user_name}")
        
        # Get or create contact in BlackPearl
        contato_blackpearl = None
        cliente_blackpearl = None
        if user_number:
            contato_blackpearl = await get_or_create_contact(
                self.context, 
                user_number, 
                user_name,
                user_id,
                self.db_id
            )
            
            if contato_blackpearl:
                user_name = contato_blackpearl.get("nome", user_name)
                # Store contact_id in context for future use if needed
                self.context["blackpearl_contact_id"] = contato_blackpearl.get("id")
                
                cliente_blackpearl = await blackpearl.get_clientes(self.context, contatos_id=contato_blackpearl["id"])
                if cliente_blackpearl and "results" in cliente_blackpearl and cliente_blackpearl["results"]:
                    cliente_blackpearl = cliente_blackpearl["results"][0]
                
                if cliente_blackpearl:
                    self.context["blackpearl_cliente_id"] = cliente_blackpearl.get("id")
                    self.context["blackpearl_cliente_nome"] = cliente_blackpearl.get("razao_social")
                    self.context["blackpearl_cliente_email"] = cliente_blackpearl.get("email")
                    logger.info(f"🔮 BlackPearl Cliente ID: {self.context['blackpearl_cliente_id']} and Name: {self.context['blackpearl_cliente_nome']}")
                    
                # Set user information in dependencies if available
                if hasattr(self.dependencies, 'set_user_info'):
                    self.dependencies.set_user_info({
                        "name": user_name,
                        "phone": user_number,
                        "blackpearl_contact_id": contato_blackpearl.get("id"),
                        "blackpearl_cliente_id": self.context["blackpearl_cliente_id"]
                    })
            update_user_data(user_id, {"blackpearl_contact_id": contato_blackpearl.get("id"), "blackpearl_cliente_id": self.context["blackpearl_cliente_id"]})
            
            logger.info(f"🔮 BlackPearl Contact ID: {contato_blackpearl.get('id')} and Name: {user_name}")

        
        # Handle different contact registration statuses
        if contato_blackpearl:
            status_aprovacao = contato_blackpearl.get("status_aprovacao")
            user_info_memory = Memory(
                name="user_information",
                description="Informações do usuário",
                content=f"- User Name: {user_name}\n- User Phone: {user_number}\n- User Status: {status_aprovacao}\n- User BlackPearl Contact ID: {contato_blackpearl.get('id')}\n- User BlackPearl Cliente ID: {self.context['blackpearl_cliente_id']} ",
                session_id=self.context.get("session_id"),
                agent_id=self.db_id,
                user_id=user_id,
                access="read",
                read_mode="system_prompt"
            )
            create_memory(
                user_info_memory
            )
            match status_aprovacao:
                case StatusAprovacaoEnum.APPROVED:
                    logger.info(f"🔮 Contact {contato_blackpearl.get('id')} is approved")
                case StatusAprovacaoEnum.PENDING_REVIEW:
                    logger.info(f"🔮 Contact {contato_blackpearl.get('id')} is pending approval")
                case StatusAprovacaoEnum.REJECTED:
                    logger.info(f"🔮 Contact {contato_blackpearl.get('id')} was rejected")
                case StatusAprovacaoEnum.NOT_REGISTERED:
                    logger.info(f"🔮 Contact {contato_blackpearl.get('id')} is not registered yet")
                case StatusAprovacaoEnum.VERIFYING:
                    logger.info(f"🔮 Contact {contato_blackpearl.get('id')} is being verified")
                case _:
                    logger.info(f"🔮 Contact {contato_blackpearl.get('id')} has unknown status: {status_aprovacao}")
        
        
        # Ensure memory variables are initialized
        if self.db_id:
            await self.initialize_memory_variables(user_id)
    
        # Initialize the agent
        await self._initialize_pydantic_agent()
        
        
        # Get message history in PydanticAI format
        pydantic_message_history = []
        if message_history_obj:
            pydantic_message_history = message_history_obj.get_formatted_pydantic_messages(limit=message_limit)
        
        user_input = input_text
        try:
            # Get filled system prompt
            filled_system_prompt = await self.get_filled_system_prompt(
                user_id=user_id
            )
            
            # Add system prompt to message history
            if filled_system_prompt:
                pydantic_message_history = add_system_message_to_history(
                    pydantic_message_history, 
                    filled_system_prompt
                )
            
            # Update dependencies with context
            if hasattr(self.dependencies, 'set_context'):
                self.dependencies.set_context(self.context)
        
            # Run the agent
            result = await self._agent_instance.run(
                user_input,
                message_history=pydantic_message_history,
                usage_limits=getattr(self.dependencies, "usage_limits", None),
                deps=self.dependencies
            )
            
            # Extract tool calls and outputs
            all_messages = extract_all_messages(result)
            tool_calls = []
            tool_outputs = []
            
            # Process each message to extract tool calls and outputs
            for msg in all_messages:
                tool_calls.extend(extract_tool_calls(msg))
                tool_outputs.extend(extract_tool_outputs(msg))
            
            # Create response
            return AgentResponse(
                text=result.data,
                success=True,
                tool_calls=tool_calls,
                tool_outputs=tool_outputs,
                raw_message=all_messages,
                system_prompt=filled_system_prompt,
            )
        except Exception as e:
            logger.error(f"Error running agent: {str(e)}")
            logger.error(traceback.format_exc())
            return AgentResponse(
                text=f"Error: {str(e)}",
                success=False,
                error_message=str(e),
                raw_message=pydantic_message_history if 'pydantic_message_history' in locals() else None
            ) 