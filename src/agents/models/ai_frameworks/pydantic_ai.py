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
            
            # Create PydanticAI agent (without tools initially)
            self._agent_instance = Agent(
                model=self.config.model,
                deps_type=dependencies_type,
                retries=self.config.retries,
                output_type=str,  # Default to string result (updated API)
                system_prompt=""  # Will be provided at runtime
            )
            
            # Register converted tools using the decorator approach
            for tool in converted_tools:
                if callable(tool) and hasattr(tool, '__name__'):
                    # Use the tool decorator to register the function
                    self._agent_instance.tool(tool)
                    logger.debug(f"Registered tool: {tool.__name__}")
                    
            self.is_initialized = True
            logger.info(f"PydanticAI agent initialized with {len(converted_tools)} tools")
            
        except Exception as e:
            logger.error(f"Error initializing PydanticAI framework: {e}")
            self.is_initialized = False
            raise
    
    async def run(self,
                  user_input: Union[str, List[Any]],
                  dependencies: BaseDependencies,
                  message_history: Optional[List[Any]] = None,
                  system_prompt: Optional[str] = None,
                  **kwargs) -> AgentResponse:
        """Run the PydanticAI agent."""
        if not self.is_ready:
            raise RuntimeError("PydanticAI framework not initialized")
            
        try:
            # Format message history for PydanticAI
            formatted_history = self.format_message_history(message_history or [])
            
            # Add system prompt to message history if provided
            if system_prompt:
                from pydantic_ai.messages import ModelRequest, SystemPromptPart
                
                # Check if there's already a system message in the history
                has_system_message = False
                for msg in formatted_history:
                    if hasattr(msg, 'parts') and any(isinstance(part, SystemPromptPart) for part in msg.parts):
                        has_system_message = True
                        break
                
                # Only add system prompt if there isn't one already
                if not has_system_message:
                    system_message = ModelRequest(parts=[SystemPromptPart(content=system_prompt)])
                    # Insert system message at the beginning of history
                    formatted_history.insert(0, system_message)
            
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
            
            # Create response (using updated API)
            response = AgentResponse(
                text=result.output if hasattr(result, 'output') else str(result),
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
                              raw_messages: List[Any]) -> List[Any]:
        """Convert message history to PydanticAI format."""
        try:
            from pydantic_ai.messages import ModelRequest, ModelResponse, SystemPromptPart, UserPromptPart, TextPart
            
            formatted_messages = []
            
            for message in raw_messages:
                # Check if message is already a PydanticAI ModelMessage
                if hasattr(message, 'parts'):
                    # Already a PydanticAI message, use as-is
                    formatted_messages.append(message)
                    continue
                
                # Handle dictionary messages (legacy format)
                if isinstance(message, dict):
                    role = message.get('role', 'user')
                    content = message.get('content', '')
                    
                    if role == 'system':
                        # System messages are handled as ModelRequest with SystemPromptPart
                        formatted_messages.append(ModelRequest(parts=[SystemPromptPart(content=content)]))
                    elif role == 'assistant':
                        # Assistant messages are ModelResponse with TextPart
                        formatted_messages.append(ModelResponse(parts=[TextPart(content=content)]))
                    else:  # user
                        # User messages are ModelRequest with UserPromptPart
                        formatted_messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
                else:
                    # Unknown message type, log warning and skip
                    logger.warning(f"Unknown message type in history: {type(message)}")
                    
            return formatted_messages
            
        except Exception as e:
            logger.error(f"Error formatting message history: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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