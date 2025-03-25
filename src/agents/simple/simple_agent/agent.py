"""SimpleAgent implementation with PydanticAI.

This module provides a SimpleAgent class that uses PydanticAI for LLM integration
and inherits common functionality from AutomagikAgent.
"""
import logging
import traceback
from typing import Dict, Any, Optional, Union

from pydantic_ai import Agent
from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.models.response import AgentResponse
from src.memory.message_history import MessageHistory

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

class SimpleAgent(AutomagikAgent):
    """SimpleAgent implementation using PydanticAI.
    
    This agent provides a basic implementation that follows the PydanticAI
    conventions for multimodal support and tool calling.
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize the SimpleAgent.
        
        Args:
            config: Dictionary with configuration options
        """
        from src.agents.simple.simple_agent.prompts.prompt import AGENT_PROMPT
        
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
        
        logger.info("SimpleAgent initialized successfully")
    
    async def _initialize_pydantic_agent(self) -> None:
        """Initialize the underlying PydanticAI agent."""
        if self._agent_instance is not None:
            return
            
        # Get model configuration
        model_name = self.dependencies.model_name
        model_settings = create_model_settings(self.dependencies.model_settings)
        
        # Convert tools to PydanticAI format
        tools = self.tool_registry.convert_to_pydantic_tools()
        logger.info(f"Prepared {len(tools)} tools for PydanticAI agent")
                    
        try:
            # Create agent instance
            self._agent_instance = Agent(
                model=model_name,
                system_prompt=self.system_prompt,
                tools=tools,
                model_settings=model_settings,
                deps_type=AutomagikAgentsDependencies
            )
            
            logger.info(f"Initialized agent with model: {model_name} and {len(tools)} tools")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            raise
        
    async def run(self, input_text: str, *, multimodal_content=None, system_message=None, message_history_obj: Optional[MessageHistory] = None) -> AgentResponse:
        """Run the agent with the given input.
        
        Args:
            input_text: Text input for the agent
            multimodal_content: Optional multimodal content
            system_message: Optional system message for this run (ignored in favor of template)
            message_history_obj: Optional MessageHistory instance for DB storage
            
        Returns:
            AgentResponse object with result and metadata
        """
        # Ensure memory variables are initialized
        if self.db_id:
            await self.initialize_memory_variables(getattr(self.dependencies, 'user_id', None))
                
        # Initialize the agent
        await self._initialize_pydantic_agent()
        
        # Get message history in PydanticAI format
        pydantic_message_history = []
        if message_history_obj:
            pydantic_message_history = message_history_obj.get_formatted_pydantic_messages(limit=20)
        
        # Prepare user input (handle multimodal content)
        user_input = input_text
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