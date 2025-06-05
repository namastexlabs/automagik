"""PydanticAI framework integration for AutomagikAgent."""
import logging
from typing import Dict, List, Optional, Any, Union, Type

from src.agents.models.ai_frameworks.base import AgentAIFramework, AgentConfig
from src.agents.models.response import AgentResponse
from src.agents.models.dependencies import BaseDependencies

logger = logging.getLogger(__name__)


class PydanticAIFramework(AgentAIFramework):
    """PydanticAI framework adapter for AutomagikAgent."""
    
    def __init__(self, config: AgentConfig):
        """Initialize the PydanticAI framework adapter."""
        super().__init__(config)
        self._tools = []
        self._dependencies_type = None
        
    async def initialize(self, 
                        tools: List[Any], 
                        dependencies_type: Type[BaseDependencies],
                        mcp_servers: Optional[List[Any]] = None) -> None:
        """Initialize the PydanticAI agent instance."""
        try:
            from pydantic_ai import Agent
            
            # Store tools and dependencies type
            self._tools = tools or []
            self._dependencies_type = dependencies_type
            
            # Convert tools to PydanticAI format
            converted_tools = self.convert_tools(self._tools)
            
            # Create PydanticAI agent
            self._agent_instance = Agent(
                model=self.config.model,
                deps_type=dependencies_type,
                retries=self.config.retries,
                result_type=str,  # Default to string result
                system_prompt=""  # Will be provided at runtime
            )
            
            # Register converted tools
            for tool in converted_tools:
                if hasattr(tool, '__name__'):
                    self._agent_instance.tool(tool)
                    
            self.is_initialized = True
            logger.info(f"PydanticAI agent initialized with {len(converted_tools)} tools")
            
        except Exception as e:
            logger.error(f"Error initializing PydanticAI framework: {e}")
            self.is_initialized = False
            raise
    
    async def run(self,
                  user_input: Union[str, List[Any]],
                  dependencies: BaseDependencies,
                  message_history: Optional[List[Dict[str, Any]]] = None,
                  system_prompt: Optional[str] = None,
                  **kwargs) -> AgentResponse:
        """Run the PydanticAI agent."""
        if not self.is_ready:
            raise RuntimeError("PydanticAI framework not initialized")
            
        try:
            # Format message history for PydanticAI
            formatted_history = self.format_message_history(message_history or [])
            
            # Run the agent
            result = await self._agent_instance.run(
                user_input,
                deps=dependencies,
                message_history=formatted_history,
                **kwargs
            )
            
            # Extract tool information
            tool_calls = self.extract_tool_calls(result)
            tool_outputs = self.extract_tool_outputs(result)
            
            # Create response
            response = AgentResponse(
                text=result.data if hasattr(result, 'data') else str(result),
                success=True,
                tool_calls=tool_calls,
                tool_outputs=tool_outputs,
                system_prompt=system_prompt
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error running PydanticAI agent: {e}")
            return AgentResponse(
                text=f"Error running agent: {str(e)}",
                success=False,
                error_message=str(e)
            )
    
    def format_message_history(self, 
                              raw_messages: List[Dict[str, Any]]) -> List[Any]:
        """Convert message history to PydanticAI format."""
        try:
            from pydantic_ai.messages import ModelMessage, UserMessage, SystemMessage
            
            formatted_messages = []
            
            for message in raw_messages:
                role = message.get('role', 'user')
                content = message.get('content', '')
                
                if role == 'system':
                    formatted_messages.append(SystemMessage(content=content))
                elif role == 'assistant':
                    formatted_messages.append(ModelMessage(content=content))
                else:  # user
                    formatted_messages.append(UserMessage(content=content))
                    
            return formatted_messages
            
        except Exception as e:
            logger.error(f"Error formatting message history: {e}")
            return []
    
    def extract_tool_calls(self, result: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from PydanticAI result."""
        tool_calls = []
        
        try:
            if hasattr(result, 'all_messages'):
                for message in result.all_messages():
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        for tool_call in message.tool_calls:
                            tool_calls.append({
                                'name': tool_call.function.name,
                                'arguments': tool_call.function.arguments,
                                'id': getattr(tool_call, 'id', None)
                            })
                            
        except Exception as e:
            logger.error(f"Error extracting tool calls: {e}")
            
        return tool_calls
    
    def extract_tool_outputs(self, result: Any) -> List[Dict[str, Any]]:
        """Extract tool outputs from PydanticAI result."""
        tool_outputs = []
        
        try:
            if hasattr(result, 'all_messages'):
                for message in result.all_messages():
                    if hasattr(message, 'content') and hasattr(message, 'tool_call_id'):
                        if message.tool_call_id:  # This is a tool response
                            tool_outputs.append({
                                'tool_call_id': message.tool_call_id,
                                'output': message.content
                            })
                            
        except Exception as e:
            logger.error(f"Error extracting tool outputs: {e}")
            
        return tool_outputs
    
    def convert_tools(self, tools: List[Any]) -> List[Any]:
        """Convert tools to PydanticAI format."""
        converted_tools = []
        
        for tool in tools:
            try:
                # If it's already a function, use it directly
                if callable(tool):
                    converted_tools.append(tool)
                elif hasattr(tool, 'func') and callable(tool.func):
                    # If it's a wrapped tool, extract the function
                    converted_tools.append(tool.func)
                else:
                    logger.warning(f"Unable to convert tool: {tool}")
                    
            except Exception as e:
                logger.error(f"Error converting tool {tool}: {e}")
                
        return converted_tools
    
    async def cleanup(self) -> None:
        """Clean up PydanticAI resources."""
        self._agent_instance = None
        self.is_initialized = False
        logger.debug("PydanticAI framework cleaned up")