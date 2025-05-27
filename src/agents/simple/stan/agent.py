"""StanAgentAgent implementation with PydanticAI.

This module provides a StanAgentAgent class that uses PydanticAI for LLM integration
and inherits common functionality from AutomagikAgent.
"""
import logging
import traceback
import glob
import os
from typing import Dict, Optional, Any

from pydantic_ai import Agent, RunContext
from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.models.response import AgentResponse
from src.agents.simple.stan.models import EvolutionMessagePayload
from src.agents.simple.stan.specialized.backoffice import backoffice_agent
from src.agents.simple.stan.specialized.product import product_agent
from src.agents.simple.stan.specialized.order import order_agent
from src.db.models import Memory
from src.db.repository import create_memory
from src.db.repository.user import update_user_data
from src.memory.message_history import MessageHistory
from src.agents.simple.stan.utils import get_or_create_contact

# Import only necessary utilities
from src.agents.common.message_parser import (
    extract_tool_calls, 
    extract_tool_outputs,
    extract_all_messages
)
from src.agents.common.dependencies_helper import (
    create_usage_limits,
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
        # First initialize the base agent without a system prompt
        super().__init__(config)
        
        # Flag to track if we've registered the prompts yet
        self._prompts_registered = False
        
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

    async def initialize_prompts(self) -> bool:
        """Initialize agent prompts during server startup.
        
        This method registers code-defined prompts for the agent during server startup.
        For StanAgent, we have a custom implementation that loads multiple prompts
        from files.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use our custom method to register all prompts
            await self._register_all_prompts()
            return True
        except Exception as e:
            logger.error(f"Error in StanAgent.initialize_prompts: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Try to fall back to the base implementation
            logger.info("Falling back to base class prompt initialization")
            try:
                # Set a default prompt text if needed
                if not hasattr(self, '_code_prompt_text') or not self._code_prompt_text:
                    # Try to load the NOT_REGISTERED prompt
                    try:
                        from src.agents.simple.stan.prompts.not_registered import PROMPT
                        self._code_prompt_text = PROMPT
                    except ImportError:
                        # If that fails, try to load the primary prompt.py
                        try:
                            from src.agents.simple.stan.prompts.prompt import AGENT_PROMPT
                            self._code_prompt_text = AGENT_PROMPT
                        except ImportError:
                            logger.error("Failed to load any prompt for StanAgent")
                
                # Call the base implementation
                return await super().initialize_prompts()
            except Exception as e2:
                logger.error(f"Error in base initialize_prompts: {str(e2)}")
                logger.error(traceback.format_exc())
                return False
            
    async def _register_all_prompts(self) -> None:
        """Register all prompts from the prompts directory.
        
        This will load all the prompt files in the prompts directory and register them with
        the appropriate status keys based on the filename.
        """
        if self._prompts_registered:
            return
            
        # Find all prompt files in the prompts directory
        prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
        prompt_files = glob.glob(os.path.join(prompts_dir, "*.py"))
        
        # Keep track of the primary default prompt ID
        primary_default_prompt_id = None
        not_registered_prompt_id = None
        
        for prompt_file in prompt_files:
            filename = os.path.basename(prompt_file)
            status_key = os.path.splitext(filename)[0].upper()  # Use filename without extension as status key, uppercase
            
            # Skip __init__.py or any other non-prompt files
            if status_key.startswith("__") or status_key == "PROMPT":
                continue
                
            # Dynamically import the prompt
            module_name = f"src.agents.simple.stan.prompts.{status_key.lower()}"
            try:
                module = __import__(module_name, fromlist=["PROMPT"])
                prompt_text = getattr(module, "PROMPT")
                
                # Register this prompt with the appropriate status key
                # If this is the NOT_REGISTERED status, mark it for special handling
                is_primary_default = (status_key == "NOT_REGISTERED")
                
                # Store the prompt text in _code_prompt_text temporarily
                self._code_prompt_text = prompt_text
                
                # Register with the shared method
                prompt_id = await self._register_code_defined_prompt(
                    prompt_text,
                    status_key=status_key,
                    prompt_name=f"StanAgent {status_key} Prompt",
                    is_primary_default=is_primary_default
                )
                
                # Keep track of the NOT_REGISTERED prompt ID for later use
                if status_key == "NOT_REGISTERED" and prompt_id:
                    not_registered_prompt_id = prompt_id
                    
                # If this is actually a "default" status prompt, set it as the primary default
                if status_key == "DEFAULT" and prompt_id:
                    primary_default_prompt_id = prompt_id
                
                logger.info(f"Registered prompt for status key: {status_key} with ID: {prompt_id}")
                
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to import prompt from {module_name}: {str(e)}")
        
        # Create a "default" status prompt that points to NOT_REGISTERED if it doesn't exist
        # This ensures that the active_default_prompt_id is properly set
        if not primary_default_prompt_id and not_registered_prompt_id and self.db_id:
            try:
                # First, check if a default prompt already exists
                from src.db.repository.prompt import get_prompts_by_agent_id, get_prompt_by_id, create_prompt, set_prompt_active
                
                default_prompts = get_prompts_by_agent_id(self.db_id, status_key="default")
                
                if not default_prompts:
                    # Get the NOT_REGISTERED prompt to use its text
                    not_registered_prompt = get_prompt_by_id(not_registered_prompt_id)
                    
                    if not_registered_prompt:
                        # Create a new prompt with status_key="default" using the NOT_REGISTERED prompt text
                        from src.db.models import PromptCreate
                        
                        # Create the default prompt
                        default_prompt_data = PromptCreate(
                            agent_id=self.db_id,
                            prompt_text=not_registered_prompt.prompt_text,
                            version=1,
                            is_active=True,  # Make it active
                            is_default_from_code=True,
                            status_key="default",
                            name="StanAgent Default Prompt (maps to NOT_REGISTERED)"
                        )
                        
                        # Create the prompt
                        default_prompt_id = create_prompt(default_prompt_data)
                        logger.info(f"Created default status prompt with ID {default_prompt_id} that maps to NOT_REGISTERED")
                    else:
                        logger.error(f"Could not find NOT_REGISTERED prompt with ID {not_registered_prompt_id}")
                else:
                    # Use the first default prompt
                    default_prompt_id = default_prompts[0].id
                    # Make sure it's active
                    set_prompt_active(default_prompt_id, True)
                    logger.info(f"Set existing default prompt {default_prompt_id} as active")
                
                # Explicitly update the agents table to ensure the active_default_prompt_id is set
                # This is a backup in case the normal flow in set_prompt_active didn't work
                if default_prompt_id or not_registered_prompt_id:
                    prompt_id_to_use = default_prompt_id or not_registered_prompt_id
                    
                    # Update the agent record using repository method
                    from src.db.repository.agent import update_agent_active_prompt_id
                    success = update_agent_active_prompt_id(self.db_id, prompt_id_to_use)
                    if success:
                        logger.info(f"Successfully updated agent {self.db_id} with active_default_prompt_id {prompt_id_to_use}")
                    else:
                        logger.error(f"Failed to update agent {self.db_id} with active_default_prompt_id {prompt_id_to_use}")
            except Exception as e:
                logger.error(f"Error setting up default prompt: {str(e)}")
                logger.error(traceback.format_exc())
                
        self._prompts_registered = True
        logger.info("All prompts registered successfully")

    async def _use_prompt_based_on_contact_status(self, status: StatusAprovacaoEnum, contact_id: str) -> bool:
        """Updates the current prompt template based on the contact's approval status.
        
        Args:
            status: The approval status
            contact_id: The contact ID
            
        Returns:
            True if the prompt was loaded successfully, False otherwise
        """
        logger.info(f"Loading prompt for contact {contact_id} with status {status}")
        
        # Convert the status enum to a string to use as the status_key
        status_key = str(status)
        
        # Load the appropriate prompt template
        result = await self.load_active_prompt_template(status_key=status_key)
        
        if not result:
            # If no prompt for this status, try the default (NOT_REGISTERED)
            logger.warning(f"No prompt found for status {status_key}, falling back to NOT_REGISTERED")
            result = await self.load_active_prompt_template(status_key="NOT_REGISTERED")
            
            if not result:
                logger.error(f"Failed to load any prompt for contact {contact_id}")
                return False
                
        return True

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
        
        # Initialize Agent with tools (no system_prompt - will be in message history)
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
        
        # Register prompts if not already done
        if not self._prompts_registered and self.db_id:
            await self._register_all_prompts()
            
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
            
            update_user_data(user_id, {"blackpearl_contact_id": contato_blackpearl.get("id"), "blackpearl_cliente_id": self.context.get("blackpearl_cliente_id")})
            
            logger.info(f" BlackPearl Contact ID: {contato_blackpearl.get('id')} and Name: {user_name}")

        
        # Handle different contact registration statuses
        if contato_blackpearl:
            status_aprovacao_str = contato_blackpearl.get("status_aprovacao", "NOT_REGISTERED")
            await self._use_prompt_based_on_contact_status(status_aprovacao_str, contato_blackpearl.get('id'))
        else:
            # Use default prompt
            await self.load_active_prompt_template(status_key="NOT_REGISTERED")

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