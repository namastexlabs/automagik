"""FlashinhoAgent implementation with PydanticAI.

This module provides a FlashinhoAgent class that uses PydanticAI for LLM integration
and inherits common functionality from AutomagikAgent.
"""
import logging
import traceback
from typing import Dict, Any, Optional, Union

from pydantic_ai import Agent, RunContext
from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.models.response import AgentResponse
from src.memory.message_history import MessageHistory

from src.tools.flashed.tool import get_user_data, get_user_score, get_user_roadmap, get_user_objectives, get_last_card_round, get_user_energy

# Import only necessary utilities
from src.agents.common.message_parser import (
    extract_tool_calls, 
    extract_tool_outputs,
    extract_all_messages
)
from src.agents.common.dependencies_helper import (
    parse_model_settings,
    create_model_settings,
    create_usage_limits,
    get_model_name,
    add_system_message_to_history
)

logger = logging.getLogger(__name__)

class FlashinhoAgent(AutomagikAgent):
    """FlashinhoAgent implementation using PydanticAI.
    
    This agent provides a basic implementation that follows the PydanticAI
    conventions for multimodal support and tool calling.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize the FlashinhoAgent.
        
        Args:
            config: Dictionary with configuration options
        """
        from src.agents.simple.flashinho_agent.prompts.prompt import AGENT_PROMPT
        
        # Initialize the base agent
        super().__init__(config)
        
        # Register the code-defined prompt for this agent
        # This call is asynchronous but we're in a synchronous __init__,
        # so we'll register the prompt later during the first run
        self._prompt_registered = False
        self._code_prompt_text = AGENT_PROMPT
        
        # PydanticAI-specific agent instance
        self._agent_instance: Optional[Agent] = None
        
        # Configure dependencies
        self.dependencies = AutomagikAgentsDependencies(
            model_name=get_model_name(config=config),
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
        
        logger.info("FlashinhoAgent initialized successfully")
    
    async def _initialize_pydantic_agent(self) -> None:
        """Initialize the underlying PydanticAI agent."""
        if self._agent_instance is not None:
            return
            
        # Get model configuration
        model_name = self.dependencies.model_name
        model_settings = create_model_settings(self.dependencies.model_settings, model_name)
        
        # Convert tools to PydanticAI format
        tools = self.tool_registry.convert_to_pydantic_tools()
        
        # Add external tools via wrappers
        tools.append(self._create_get_user_data_wrapper())
        tools.append(self._create_get_user_score_wrapper())
        tools.append(self._create_get_user_roadmap_wrapper())
        tools.append(self._create_get_user_objectives_wrapper())
        tools.append(self._create_get_last_card_round_wrapper())
        tools.append(self._create_get_user_energy_wrapper())

        logger.info(f"Prepared {len(tools)} tools for PydanticAI agent")
                    
        try:
            # Create agent instance
            self._agent_instance = Agent(
                model='openai:gpt-4o',
                tools=tools,
                model_settings=model_settings,
                deps_type=AutomagikAgentsDependencies
            )
            
            logger.info(f"Initialized agent with model: {model_name} and {len(tools)} tools")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            raise
    
    def _create_get_user_data_wrapper(self):
        """Create a wrapper for the get_user_data function that handles the context properly.
        
        This creates a custom wrapper that follows the PydanticAI expected format, 
        ensuring the ctx parameter is handled correctly when the tool is called.
        
        Returns:
            A wrapped version of the get_user_data function.
        """
        # Capture a reference to the context at creation time
        agent_context = self.context
        
        async def get_user_data_wrapper(ctx: RunContext[AutomagikAgentsDependencies]) -> Dict[str, Any]:
            """Get user data from Flashed API.
            
            Args:
                ctx: The run context with dependencies
                
            Returns:
                User data containing cadastro and metadata
            """
            # Use the captured context reference directly
            return await get_user_data(agent_context)
            
        return get_user_data_wrapper

    def _create_get_user_score_wrapper(self):
        """Create a wrapper for the get_user_score function that handles the context properly.
        
        This creates a custom wrapper that follows the PydanticAI expected format, 
        ensuring the ctx parameter is handled correctly when the tool is called.
        
        Returns:
            A wrapped version of the get_user_score function.
        """
        # Capture a reference to the context at creation time
        agent_context = self.context
        
        async def get_user_score_wrapper(ctx: RunContext[AutomagikAgentsDependencies]) -> Dict[str, Any]:
            """Get user score data from Flashed API.
            
            Args:
                ctx: The run context with dependencies
                
            Returns:
                - score: User score data
                    - flashinhoEnergy: User's current energy
                    - sequence: Study streak
                    - dailyProgress: Daily progress percentage
            """
            # Use the captured context reference directly
            return await get_user_score(agent_context)
            
        return get_user_score_wrapper

    def _create_get_user_roadmap_wrapper(self):
        """Create a wrapper for the get_user_roadmap function that handles the context properly.
        
        This creates a custom wrapper that follows the PydanticAI expected format, 
        ensuring the ctx parameter is handled correctly when the tool is called.
        
        Returns:
            A wrapped version of the get_user_roadmap function.
        """
        # Capture a reference to the context at creation time
        agent_context = self.context
        
        async def get_user_roadmap_wrapper(ctx: RunContext[AutomagikAgentsDependencies]) -> Dict[str, Any]:
            """Get user roadmap data from Flashed API.
            
            Args:
                ctx: The run context with dependencies
                
            Returns:
                User roadmap data containing subjects and due date
            """
            # Use the captured context reference directly
            return await get_user_roadmap(agent_context)
            
        return get_user_roadmap_wrapper

    def _create_get_user_objectives_wrapper(self):
        """Create a wrapper for the get_user_objectives function that handles the context properly.
        
        This creates a custom wrapper that follows the PydanticAI expected format, 
        ensuring the ctx parameter is handled correctly when the tool is called.
        
        Returns:
            A wrapped version of the get_user_objectives function.
        """
        # Capture a reference to the context at creation time
        agent_context = self.context
        
        async def get_user_objectives_wrapper(ctx: RunContext[AutomagikAgentsDependencies]) -> Dict[str, Any]:
            """Get user objectives from Flashed API.
            
            Args:
                ctx: The run context with dependencies
                
            Returns:
                List of objectives ordered by completion date
            """
            # Use the captured context reference directly
            return await get_user_objectives(agent_context)
            
        return get_user_objectives_wrapper

    def _create_get_last_card_round_wrapper(self):
        """Create a wrapper for the get_last_card_round function that handles the context properly.
        
        This creates a custom wrapper that follows the PydanticAI expected format, 
        ensuring the ctx parameter is handled correctly when the tool is called.
        
        Returns:
            A wrapped version of the get_last_card_round function.
        """
        # Capture a reference to the context at creation time
        agent_context = self.context
        
        async def get_last_card_round_wrapper(ctx: RunContext[AutomagikAgentsDependencies]) -> Dict[str, Any]:
            """Get last card round data from Flashed API.
            
            Args:
                ctx: The run context with dependencies
                
            Returns:
                Last card round data with cards and round length
            """
            # Use the captured context reference directly
            return await get_last_card_round(agent_context)
            
        return get_last_card_round_wrapper

    def _create_get_user_energy_wrapper(self):
        """Create a wrapper for the get_user_energy function that handles the context properly.
        
        This creates a custom wrapper that follows the PydanticAI expected format, 
        ensuring the ctx parameter is handled correctly when the tool is called.
        
        Returns:
            A wrapped version of the get_user_energy function.
        """
        # Capture a reference to the context at creation time
        agent_context = self.context
        
        async def get_user_energy_wrapper(ctx: RunContext[AutomagikAgentsDependencies]) -> Dict[str, Any]:
            """Get user energy value from Flashed API.
            
            Args:
                ctx: The run context with dependencies
                
            Returns:
                User energy data with current energy value
            """
            # Use the captured context reference directly
            return await get_user_energy(agent_context)
            
        return get_user_energy_wrapper
        
    async def run(self, input_text: str, *, multimodal_content=None, system_message=None, message_history_obj: Optional[MessageHistory] = None,
                 channel_payload: Optional[Dict] = None,
                 message_limit: Optional[int] = 20) -> AgentResponse:
        """Run the agent with the given input.
        
        Args:
            input_text: Text input for the agent
            multimodal_content: Optional multimodal content
            system_message: Optional system message for this run (ignored in favor of template)
            message_history_obj: Optional MessageHistory instance for DB storage
            
        Returns:
            AgentResponse object with result and metadata
        """
        # Register the code-defined prompt if not already done
        await self._check_and_register_prompt()
        
        # Load the active prompt template for this agent
        await self.load_active_prompt_template(status_key="default")
        
        # Ensure memory variables are initialized
        if self.db_id:
            await self.initialize_memory_variables(getattr(self.dependencies, 'user_id', None))
                
        # Initialize the agent
        await self._initialize_pydantic_agent()
        
        # Get message history in PydanticAI format
        pydantic_message_history = []
        if message_history_obj:
            pydantic_message_history = message_history_obj.get_formatted_pydantic_messages(limit=message_limit)
        
        # Prepare user input (handle multimodal content)
        user_input = input_text
        # hehe
        if multimodal_content:
            if hasattr(self.dependencies, 'configure_for_multimodal'):
                self.dependencies.configure_for_multimodal(True)
            user_input = {"text": input_text, "multimodal_content": multimodal_content}
        
        try:
            # Get filled system prompt
            filled_system_prompt = await self.get_filled_system_prompt(
                user_id=getattr(self.dependencies, 'user_id', None)
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