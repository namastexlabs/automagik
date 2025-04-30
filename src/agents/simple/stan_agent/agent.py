"""StanAgentAgent implementation with PydanticAI.

This module provides a StanAgentAgent class that uses PydanticAI for LLM integration
and inherits common functionality from AutomagikAgent.
"""
import logging
import traceback
from typing import Dict, Optional, Any

from pydantic_ai import Agent, RunContext
from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.models.response import AgentResponse
from src.agents.simple.stan_agent.models import EvolutionMessagePayload
from src.agents.simple.stan_agent.specialized.backoffice import backoffice_agent
from src.agents.simple.stan_agent.specialized.product import product_agent
from src.agents.simple.stan_agent.specialized.order import order_agent
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
from src.tools.blackpearl.api import fetch_blackpearl_product_details
from src.tools.evolution.api import send_evolution_media_logic

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
        # Import the default prompt (not_registered)
        from src.agents.simple.stan_agent.prompts.not_registered import PROMPT as DEFAULT_PROMPT
        
        # Initialize the base agent with the default prompt
        super().__init__(config, DEFAULT_PROMPT)
        
        # Explicitly set the system prompt for this agent instance
        self._system_prompt = DEFAULT_PROMPT
        
        # PydanticAI-specific agent instance
        self._agent_instance: Optional[Agent] = None
        
        # Configure dependencies
        self.dependencies = AutomagikAgentsDependencies(
            model_name="openai:o4-mini",
            # model_settings=parse_model_settings(config)
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
        
        logger.info("StanAgentAgent initialized successfully")

    def _use_prompt_based_on_contact_status(self, status: StatusAprovacaoEnum, contact_id: str) -> None:
        """Updates the system_prompt based on the contact's approval status."""
        # Import prompts dynamically within the cases to avoid loading all at once
        match status:
            case StatusAprovacaoEnum.NOT_REGISTERED:
                logger.info(f" Contact {contact_id} is not registered yet")
                from src.agents.simple.stan_agent.prompts.not_registered import PROMPT as STATUS_PROMPT
            case StatusAprovacaoEnum.PENDING_REVIEW:
                logger.info(f" Contact {contact_id} is pending approval")
                from src.agents.simple.stan_agent.prompts.pending_review import PROMPT as STATUS_PROMPT
            case StatusAprovacaoEnum.VERIFYING:
                logger.info(f" Contact {contact_id} is being verified")
                from src.agents.simple.stan_agent.prompts.verifying import PROMPT as STATUS_PROMPT
            case StatusAprovacaoEnum.APPROVED:
                logger.info(f" Contact {contact_id} is approved")
                from src.agents.simple.stan_agent.prompts.approved import PROMPT as STATUS_PROMPT
            case StatusAprovacaoEnum.REJECTED:
                logger.info(f" Contact {contact_id} was rejected")
                from src.agents.simple.stan_agent.prompts.rejected import PROMPT as STATUS_PROMPT
            case _:
                logger.warning(f" Contact {contact_id} has unknown status: {status}. Using UNKNOWN prompt.")
                from src.agents.simple.stan_agent.prompts.not_registered import PROMPT as STATUS_PROMPT
        
        self.system_prompt = STATUS_PROMPT

    async def _initialize_pydantic_agent(self) -> None:
        """Initialize the underlying PydanticAI agent."""
        if self._agent_instance:
            logger.debug("PydanticAI agent already initialized.")
            return

        logger.info("Initializing PydanticAI agent...")
        
        # Pass imported tools directly to the constructor
        # Combine imported tools and specialized agents into one list
        all_tools = [
            self._create_verificar_cnpj_wrapper(),
            self._create_product_agent_wrapper(),
            # self._create_order_agent_wrapper(),
            self._create_backoffice_agent_wrapper(),
        ]
        
        # Initialize Agent with tools
        self._agent_instance = Agent(
            self.dependencies.model_name,
            deps_type=AutomagikAgentsDependencies,
            model_settings=self.dependencies.model_settings,
            tools=all_tools,  # Pass combined list of tools and sub-agents
        )
        
        logger.info("PydanticAI agent initialization complete with tools.")

    def _create_verificar_cnpj_wrapper(self):
        """Create a wrapper for the verificar_cnpj function that handles the context properly.
        
        This creates a custom wrapper that follows the PydanticAI expected format, 
        ensuring the ctx parameter is handled correctly when the tool is called.
        
        Returns:
            A wrapped version of the verificar_cnpj function.
        """
        # Capture a reference to the context at creation time
        agent_context = self.context
        
        async def verificar_cnpj_wrapper(ctx: RunContext[AutomagikAgentsDependencies], cnpj: str) -> Dict[str, Any]:
            """Verify a CNPJ in the Blackpearl API.
            
            Args:
                ctx: The run context with dependencies
                cnpj: The CNPJ number to verify (format: xx.xxx.xxx/xxxx-xx or clean numbers)
                
            Returns:
                CNPJ verification result containing validation status and company information if valid
            """
            # Use the captured context reference directly
            return await verificar_cnpj(agent_context, cnpj)
            
        return verificar_cnpj_wrapper

    def _create_product_agent_wrapper(self):
        """Create a wrapper for the product_agent function that handles the context properly.
        
        This creates a custom wrapper that follows the PydanticAI expected format,
        ensuring proper context handling when the agent is called.
        
        Returns:
            A wrapped version of the product_agent function.
        """
        # Capture a reference to the context at creation time
        agent_context = self.context
        
        async def product_agent_wrapper(ctx: RunContext[AutomagikAgentsDependencies], input_text: str) -> str:
            """Specialized product agent with expertise in product information and catalog management.
            
            Args:
                ctx: The run context with dependencies
                input_text: The user's text query about products
            
            Returns:
                Response from the product agent
            """
            # We need to manually ensure evolution_payload is in the context
            # because it appears to be lost when using set_context
            if ctx.deps:
                # First check if evolution_payload is in the agent_context
                if agent_context and "evolution_payload" in agent_context:
                    # Apply evolution_payload in multiple ways for maximum compatibility
                    # 1. Set it directly on the deps object
                    ctx.deps.evolution_payload = agent_context["evolution_payload"]
                    
                    # 2. Create a new context dict with all existing items plus evolution_payload
                    updated_context = dict(ctx.deps.context) if hasattr(ctx.deps, 'context') and ctx.deps.context else {}
                    updated_context["evolution_payload"] = agent_context["evolution_payload"]
                    
                    # 3. Set the updated context
                    ctx.deps.set_context(updated_context)
                    
                    # 4. For direct access in the RunContext
                    if hasattr(ctx, '__dict__'):
                        ctx.__dict__['evolution_payload'] = agent_context["evolution_payload"]
                        
                    # 5. Set parent_context for nested tool calls
                    if hasattr(ctx, '__dict__'):
                        ctx.__dict__['parent_context'] = agent_context
                # If no evolution_payload was found, log a warning
                else:
                    logger.warning("No evolution_payload found in agent_context to pass to product_agent")
            
            # Now proceed with normal execution
            return await product_agent(ctx, input_text)
            
        return product_agent_wrapper

    def _create_order_agent_wrapper(self):
        """Create a wrapper for the order_agent function that handles the context properly.
        
        This creates a custom wrapper that follows the PydanticAI expected format,
        ensuring proper context handling when the agent is called.
        
        Returns:
            A wrapped version of the order_agent function.
        """
        # Capture a reference to the context at creation time
        agent_context = self.context
        
        async def order_agent_wrapper(ctx: RunContext[AutomagikAgentsDependencies], input_text: str) -> str:
            """Specialized order agent with expertise in sales orders and order management.
            
            Args:
                ctx: The run context with dependencies
                input_text: The user's text query about orders
            
            Returns:
                Response from the order agent
            """
            # We need to manually ensure evolution_payload is in the context
            # because it appears to be lost when using set_context
            if ctx.deps:
                # First check if evolution_payload is in the agent_context
                if agent_context and "evolution_payload" in agent_context:
                    # Apply evolution_payload in multiple ways for maximum compatibility
                    # 1. Set it directly on the deps object
                    ctx.deps.evolution_payload = agent_context["evolution_payload"]
                    
                    # 2. Create a new context dict with all existing items plus evolution_payload
                    updated_context = dict(ctx.deps.context) if hasattr(ctx.deps, 'context') and ctx.deps.context else {}
                    updated_context["evolution_payload"] = agent_context["evolution_payload"]
                    
                    # 3. Set the updated context
                    ctx.deps.set_context(updated_context)
                    
                    # 4. For direct access in the RunContext
                    if hasattr(ctx, '__dict__'):
                        ctx.__dict__['evolution_payload'] = agent_context["evolution_payload"]
                        
                    # 5. Set parent_context for nested tool calls
                    if hasattr(ctx, '__dict__'):
                        ctx.__dict__['parent_context'] = agent_context
                # If no evolution_payload was found, log a warning
                else:
                    logger.warning("No evolution_payload found in agent_context to pass to order_agent")
            
            # Now proceed with normal execution and pass the updated context
            return await order_agent(ctx, input_text)
            
        return order_agent_wrapper

    def _create_backoffice_agent_wrapper(self):
        """Create a wrapper for the backoffice_agent function that handles the context properly.
        
        This creates a custom wrapper that follows the PydanticAI expected format,
        ensuring proper context handling when the agent is called.
        
        Returns:
            A wrapped version of the backoffice_agent function.
        """
        # Capture a reference to the context at creation time
        agent_context = self.context
        
        async def backoffice_agent_wrapper(ctx: RunContext[AutomagikAgentsDependencies], input_text: str) -> str:
            """Specialized backoffice agent with access to BlackPearl and Omie tools.
            
            Args:
                ctx: The run context with dependencies
                input_text: The user's text query about backoffice operations
            
            Returns:
                Response from the backoffice agent
            """
            ctx.deps.set_context(agent_context)
            return await backoffice_agent(ctx, input_text)
            
        return backoffice_agent_wrapper

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
            # Store evolution_payload in both self.context and dependencies context
            self.context["evolution_payload"] = evolution_payload
            self.dependencies.set_context({"evolution_payload": evolution_payload})

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
                    logger.info(f" BlackPearl Cliente ID: {self.context['blackpearl_cliente_id']} and Name: {self.context['blackpearl_cliente_nome']}")
                    
                # Set user information in dependencies if available
                if hasattr(self.dependencies, 'set_user_info'):
                    self.dependencies.set_user_info({
                        "name": user_name,
                        "phone": user_number,
                        "blackpearl_contact_id": contato_blackpearl.get("id"),
                        "blackpearl_cliente_id": self.context["blackpearl_cliente_id"]
                    })
            update_user_data(user_id, {"blackpearl_contact_id": contato_blackpearl.get("id"), "blackpearl_cliente_id": self.context["blackpearl_cliente_id"]})
            
            logger.info(f" BlackPearl Contact ID: {contato_blackpearl.get('id')} and Name: {user_name}")

        
        # Handle different contact registration statuses
        if contato_blackpearl:
            status_aprovacao_str = contato_blackpearl.get("status_aprovacao", "NOT_REGISTERED")
            self._use_prompt_based_on_contact_status(status_aprovacao_str, contato_blackpearl.get('id'))

        # Ensure memory variables are initialized
        if self.db_id:
            await self.initialize_memory_variables(user_id)
        
            # Create a memory entry snapshotting the user info used for this run
            user_info_for_memory = {
                "user_id": user_id,
                "user_name": user_name,
                "user_number": user_number,
                "blackpearl_contact_id": self.context.get("blackpearl_contact_id"),
                "blackpearl_cliente_id": self.context.get("blackpearl_cliente_id"),
                "blackpearl_cliente_email": self.context.get("blackpearl_cliente_email"),
            }
            # Filter out None values before saving
            user_info_content = {k: v for k, v in user_info_for_memory.items() if v is not None}
            
            # Create a Memory object instance
            memory_to_create = Memory(
                name="user_information",
                content=str(user_info_content),
                user_id=user_id,
                read_mode="system_prompt",
                access="read_write",
                agent_id=self.db_id
            )
            
            # Call create_memory with the Memory object
            create_memory(memory=memory_to_create)
            logger.info(f"Created/Updated user_information memory for user {user_id}")

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