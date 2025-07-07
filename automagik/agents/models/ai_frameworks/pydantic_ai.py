"""PydanticAI framework integration for AutomagikAgent."""
import logging
from typing import Dict, List, Optional, Any, Union, Type

from automagik.agents.models.ai_frameworks.base import AgentAIFramework, AgentConfig
from automagik.agents.models.response import AgentResponse
from automagik.agents.models.dependencies import BaseDependencies

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
            import time
            start_time = time.time()
            
            # Detect multimodal content from user input
            multimodal_content = self._detect_multimodal_content(user_input, kwargs)
            
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
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Extract tool information
            tool_calls = self.extract_tool_calls(result)
            tool_outputs = self.extract_tool_outputs(result)
            
            # Extract usage information with processing time and multimodal content
            usage_info = self.extract_usage_info(
                result, 
                processing_time_ms=processing_time_ms,
                multimodal_content=multimodal_content
            )
            
            # Create response (using updated API)
            response = AgentResponse(
                text=result.output if hasattr(result, 'output') else str(result),
                success=True,
                tool_calls=tool_calls,
                tool_outputs=tool_outputs,
                system_prompt=system_prompt,
                usage=usage_info
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error running PydanticAI agent: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
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
        tool_results = {}  # Map tool call IDs to results
        
        try:
            if hasattr(result, 'all_messages'):
                # First pass: collect tool results from ToolReturnPart
                for message in result.all_messages():
                    if hasattr(message, 'parts') and message.parts:
                        for part in message.parts:
                            # Check if this is a tool return part
                            if hasattr(part, 'tool_call_id') and hasattr(part, 'content') and 'ToolReturnPart' in str(type(part)):
                                tool_results[part.tool_call_id] = part.content
                
                # Second pass: extract tool calls from ToolCallPart and match with results
                for message in result.all_messages():
                    if hasattr(message, 'parts') and message.parts:
                        for part in message.parts:
                            # Check if this is a tool call part
                            if hasattr(part, 'tool_call_id') and hasattr(part, 'tool_name') and hasattr(part, 'args') and 'ToolCallPart' in str(type(part)):
                                tool_calls.append({
                                    'name': part.tool_name,
                                    'args': part.args,
                                    'id': part.tool_call_id,
                                    'result': tool_results.get(part.tool_call_id, None)
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
    
    def extract_usage_info(self, result: Any, processing_time_ms: float = 0.0, multimodal_content: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Extract usage information from PydanticAI result using simplified usage calculator."""
        if not result:
            return None
        
        try:
            # Import our simplified usage calculator
            from automagik.utils.usage_calculator import UnifiedUsageCalculator
            calculator = UnifiedUsageCalculator()
            
            # Extract usage using our new simplified calculator
            breakdown = calculator.extract_pydantic_ai_usage(
                result=result,
                model=self.config.model,
                processing_time_ms=processing_time_ms,
                multimodal_content=multimodal_content
            )
            
            # Detect content types based on input
            content_types = ["text"]  # Always include text
            if multimodal_content:
                if multimodal_content.get("images"):
                    content_types.append("image")
                if multimodal_content.get("audio"):
                    content_types.append("audio")
                if multimodal_content.get("videos"):
                    content_types.append("video")
            
            breakdown.content_types = content_types
            
            # Convert to legacy compatible format for API response
            return calculator.create_legacy_compatible_usage(breakdown)
            
        except Exception as e:
            logger.error(f"Error extracting usage info: {e}")
            # Fallback to basic extraction
            try:
                # Detect content types for fallback usage (safely handle multimodal_content)
                content_types = ["text"]
                if multimodal_content and isinstance(multimodal_content, dict):
                    if multimodal_content.get("images"):
                        content_types.append("image")
                    if multimodal_content.get("audio"):
                        content_types.append("audio")
                    if multimodal_content.get("videos"):
                        content_types.append("video")
                
                usage_info = {
                    "framework": "pydantic_ai",
                    "model": self.config.model,
                    "request_tokens": 0,
                    "response_tokens": 0,
                    "total_tokens": 0,
                    "content_types": content_types,
                    "processing_time_ms": processing_time_ms
                }
                
                # Extract basic usage from result
                if hasattr(result, 'all_messages'):
                    for message in result.all_messages():
                        if hasattr(message, 'usage') and message.usage:
                            usage = message.usage
                            usage_info["request_tokens"] = (usage_info.get("request_tokens", 0) or 0) + (usage.request_tokens or 0)
                            usage_info["response_tokens"] = (usage_info.get("response_tokens", 0) or 0) + (usage.response_tokens or 0)
                            usage_info["total_tokens"] = (usage_info.get("total_tokens", 0) or 0) + (usage.total_tokens or 0)
                
                return usage_info if usage_info["total_tokens"] > 0 else None
                
            except Exception as fallback_error:
                logger.error(f"Fallback usage extraction failed: {fallback_error}")
                return None
    
    def _detect_multimodal_content(self, user_input: Union[str, List[Any]], kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect multimodal content from user input and kwargs."""
        multimodal_content = {"images": [], "audio": [], "videos": []}
        has_multimodal = False
        
        try:
            # Check if user_input is a list (multimodal input)
            if isinstance(user_input, list):
                for item in user_input:
                    if isinstance(item, dict):
                        content_type = item.get("type", "").lower()
                        if "image" in content_type:
                            multimodal_content["images"].append(item)
                            has_multimodal = True
                        elif "audio" in content_type:
                            multimodal_content["audio"].append(item)
                            has_multimodal = True
                        elif "video" in content_type:
                            multimodal_content["videos"].append(item)
                            has_multimodal = True
            
            # Check kwargs for media content
            if "media_contents" in kwargs:
                media_contents = kwargs["media_contents"]
                if isinstance(media_contents, list):
                    for media in media_contents:
                        if isinstance(media, dict):
                            mime_type = media.get("mime_type", "").lower()
                            if "image" in mime_type:
                                multimodal_content["images"].append(media)
                                has_multimodal = True
                            elif "audio" in mime_type:
                                multimodal_content["audio"].append(media)
                                has_multimodal = True
                            elif "video" in mime_type:
                                multimodal_content["videos"].append(media)
                                has_multimodal = True
            
            # Check for image attachments in user_input string
            if isinstance(user_input, str):
                # Look for base64 image data or image URLs
                if "data:image" in user_input or "base64" in user_input.lower():
                    multimodal_content["images"].append({"type": "image", "detected": "base64_in_text"})
                    has_multimodal = True
            
            return multimodal_content if has_multimodal else None
            
        except Exception as e:
            logger.error(f"Error detecting multimodal content: {e}")
            return None
    
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