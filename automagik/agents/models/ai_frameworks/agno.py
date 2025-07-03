"""Agno framework integration for AutomagikAgent."""
import logging
from typing import Dict, List, Optional, Any, Union, Type
import asyncio
from datetime import datetime

from automagik.agents.models.ai_frameworks.base import AgentAIFramework, AgentConfig
from automagik.agents.models.response import AgentResponse
from automagik.agents.models.dependencies import BaseDependencies

logger = logging.getLogger(__name__)


def _truncate_base64(data_str: str, max_length: int = 50) -> str:
    """Truncate base64 data for logging without exposing full content."""
    if not data_str or len(data_str) <= max_length:
        return data_str
    return f"{data_str[:max_length//2]}...{data_str[-max_length//2:]}"


class AgnoFramework(AgentAIFramework):
    """Agno framework adapter for AutomagikAgent.
    
    This adapter integrates Agno's high-performance, multimodal agent framework
    with AutomagikAgent's abstraction layer.
    """
    
    def __init__(self, config: AgentConfig):
        """Initialize the Agno framework adapter."""
        super().__init__(config)
        self._tools = []
        self._dependencies_type = None
        self._telemetry_enabled = True  # Can be disabled with AGNO_TELEMETRY=false
        
    async def initialize(self, 
                        tools: List[Any], 
                        dependencies_type: Type[BaseDependencies],
                        mcp_servers: Optional[List[Any]] = None) -> None:
        """Initialize the Agno agent instance."""
        try:
            # Reduce verbose logging from Agno and related libraries
            import logging
            agno_logger = logging.getLogger('agno')
            agno_logger.setLevel(logging.WARNING)
            
            # Also reduce httpx/openai client verbosity
            httpx_logger = logging.getLogger('httpx')
            httpx_logger.setLevel(logging.WARNING)
            openai_logger = logging.getLogger('openai')
            openai_logger.setLevel(logging.WARNING)
            
            from agno.agent import Agent
            from agno.models.openai import OpenAIChat
            from agno.models.google import Gemini
            from agno.models.groq import Groq
            from agno.models.anthropic import Claude
            
            # Store tools and dependencies type
            self._tools = tools or []
            self._dependencies_type = dependencies_type
            
            # Map model string to Agno model instance
            model_str = self.config.model
            model_instance = self._create_model_instance(model_str)
            
            # Create Agno agent
            self._agent_instance = Agent(
                model=model_instance,
                markdown=True,  # Enable markdown formatting
                show_tool_calls=True,  # Show tool execution
                instructions=""  # Will be provided at runtime via system prompt
            )
            
            # Initialize tools list if not present
            if not hasattr(self._agent_instance, 'tools') or self._agent_instance.tools is None:
                self._agent_instance.tools = []
            
            # Register tools with Agno
            for tool in self._tools:
                if callable(tool) and hasattr(tool, '__name__'):
                    try:
                        # Agno uses a different tool registration pattern
                        # Tools are registered via the agent's tool decorator
                        wrapped_tool = self._wrap_tool_for_agno(tool)
                        self._agent_instance.tools.append(wrapped_tool)
                        logger.debug(f"🔧 {tool.__name__}")
                    except Exception as e:
                        logger.warning(f"Failed to register tool {tool.__name__}: {e}")
            
            self.is_initialized = True
            tool_count = len(self._agent_instance.tools) if self._agent_instance.tools else 0
            logger.info(f"Agno agent initialized with {tool_count} tools")
            
        except Exception as e:
            logger.error(f"Error initializing Agno framework: {e}")
            self.is_initialized = False
            raise
    
    def _create_model_instance(self, model_str: str):
        """Create Agno model instance from model string."""
        from agno.models.openai import OpenAIChat
        from agno.models.google import Gemini
        from agno.models.groq import Groq
        from agno.models.anthropic import Claude
        
        # Parse model string (format: "provider:model-name")
        if ":" in model_str:
            provider, model_name = model_str.split(":", 1)
        else:
            # Default to OpenAI if no provider specified
            provider = "openai"
            model_name = model_str
        
        provider = provider.lower()
        
        # Map GEMINI_API_KEY to GOOGLE_API_KEY for Agno compatibility
        if provider in ["gemini", "google"]:
            import os
            
            # Try to get GEMINI_API_KEY from settings or environment
            if not os.environ.get("GOOGLE_API_KEY"):
                try:
                    from automagik.config import settings
                    gemini_key = settings.GEMINI_API_KEY
                except Exception:
                    gemini_key = None
                
                # Fall back to environment variable if settings not available
                if not gemini_key:
                    gemini_key = os.environ.get("GEMINI_API_KEY")
                
                if gemini_key:
                    os.environ["GOOGLE_API_KEY"] = gemini_key
                    logger.debug("Mapped GEMINI_API_KEY to GOOGLE_API_KEY for Agno Gemini model")
        
        # Create appropriate model instance
        if provider == "openai":
            # Handle audio-preview models for multimodal
            if "audio-preview" in model_name:
                # Audio models need special configuration
                # For now, use the standard vision model which can handle audio transcription
                logger.info(f"Audio model {model_name} requested, using vision-capable model for audio transcription")
                return OpenAIChat(
                    id="gpt-4o",  # Use the vision model which supports audio
                    temperature=self.config.temperature
                )
            return OpenAIChat(
                id=model_name,
                temperature=self.config.temperature
            )
        elif provider == "gemini" or provider == "google":
            return Gemini(
                id=model_name,
                temperature=self.config.temperature
            )
        elif provider == "groq":
            return Groq(
                id=model_name,
                temperature=self.config.temperature
            )
        elif provider in ["anthropic", "claude"]:
            return Claude(
                id=model_name,
                temperature=self.config.temperature
            )
        else:
            # Default to OpenAI for unknown providers
            logger.warning(f"Unknown provider {provider}, defaulting to OpenAI")
            return OpenAIChat(id=model_str, temperature=self.config.temperature)
    
    def _wrap_tool_for_agno(self, tool):
        """Wrap a tool function for Agno compatibility."""
        # Agno expects tools to be functions that can be called directly
        # Our tools might have different signatures, so we wrap them
        async def wrapped_tool(*args, **kwargs):
            try:
                # Handle the specific parameter format used by Agno tool calling
                # Agno sends tools with 'args' and 'kwargs' as parameters
                if 'args' in kwargs and 'kwargs' in kwargs:
                    # Extract the actual arguments from the nested structure
                    actual_args = kwargs.get('args', {})
                    actual_kwargs = kwargs.get('kwargs', {})
                    
                    # Handle both sync and async tools
                    if asyncio.iscoroutinefunction(tool):
                        return await tool(**actual_kwargs)
                    else:
                        return tool(**actual_kwargs)
                else:
                    # Handle direct parameter calling (fallback)
                    if asyncio.iscoroutinefunction(tool):
                        return await tool(*args, **kwargs)
                    else:
                        return tool(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error executing tool {tool.__name__}: {e}")
                raise
        
        # Preserve original function metadata
        wrapped_tool.__name__ = tool.__name__
        wrapped_tool.__doc__ = tool.__doc__
        
        return wrapped_tool
    
    async def run(self,
                  user_input: Union[str, List[Any]],
                  dependencies: BaseDependencies,
                  message_history: Optional[List[Any]] = None,
                  system_prompt: Optional[str] = None,
                  **kwargs) -> AgentResponse:
        """Run the Agno agent with multimodal support."""
        if not self.is_ready:
            raise RuntimeError("Agno framework not initialized")
            
        import time
        start_time = time.time()
        
        try:
            # Handle multimodal inputs and track for cost calculation
            run_kwargs = {}
            multimodal_content = {"images": [], "audio": [], "videos": []}
            
            # Extract media contents if present
            if isinstance(user_input, list):
                # Multimodal input format
                text_input = None
                images = []
                audio_contents = []
                videos = []
                
                for i, item in enumerate(user_input):
                    if isinstance(item, str):
                        text_input = item
                    elif isinstance(item, dict):
                        media_type = item.get("type", "")
                        
                        if media_type == "image":
                            agno_image = self._create_agno_image(item)
                            if agno_image:
                                images.append(agno_image)
                                multimodal_content["images"].append(item)
                            else:
                                logger.warning(f"❌ Failed to create agno_image")
                        elif media_type == "audio":
                            agno_audio = self._create_agno_audio(item)
                            if agno_audio:
                                audio_contents.append(agno_audio)
                                multimodal_content["audio"].append(item)
                        elif media_type == "video":
                            agno_video = self._create_agno_video(item)
                            if agno_video:
                                videos.append(agno_video)
                                multimodal_content["videos"].append(item)
                        else:
                            logger.warning(f"❌ Unknown media_type: '{media_type}'")
                
                # Set multimodal parameters
                if images:
                    run_kwargs["images"] = images
                if audio_contents:
                    run_kwargs["audio"] = audio_contents
                if videos:
                    run_kwargs["videos"] = videos
                    
                user_input = text_input or "Process this multimedia content"
            
            # Set system prompt as instructions
            if system_prompt:
                self._agent_instance.instructions = system_prompt
            
            # Debug: Log what we're passing to Agno (minimal)
            if "images" in run_kwargs:
                logger.debug(f"🔍 Agno processing {len(run_kwargs['images'])} image(s)")
            if "audio" in run_kwargs:
                logger.debug(f"🔍 Agno processing {len(run_kwargs['audio'])} audio file(s)")
            if "videos" in run_kwargs:
                logger.debug(f"🔍 Agno processing {len(run_kwargs['videos'])} video(s)")
            
            # Run the agent
            run_response = await self._agent_instance.arun(
                user_input,
                stream=False,
                **run_kwargs
            )
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Extract response data with comprehensive usage tracking
            response_text = self._extract_response_text(run_response)
            tool_calls = self._extract_tool_calls(run_response)
            tool_outputs = self._extract_tool_outputs(run_response)
            
            # 🎯 ENHANCED USAGE TRACKING: Pass multimodal content and timing
            usage_info = self._extract_usage_info(
                run_response, 
                processing_time_ms=processing_time_ms,
                multimodal_content=multimodal_content if any(multimodal_content.values()) else None
            )
            
            # Create standardized response
            return AgentResponse(
                text=response_text,
                success=True,
                tool_calls=tool_calls,
                tool_outputs=tool_outputs,
                system_prompt=system_prompt,
                usage=usage_info
            )
            
        except Exception as e:
            logger.error(f"Error running Agno agent: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return AgentResponse(
                text=f"Error running agent: {str(e)}",
                success=False,
                error_message=str(e)
            )
    
    def _create_agno_image(self, image_data: Dict) -> Any:
        """Create Agno Image object from image data."""
        try:
            from agno.media import Image
            
            if "url" in image_data:
                return Image(url=image_data["url"])
            elif "data" in image_data:
                # Base64 data
                import base64
                if image_data["data"].startswith("data:"):
                    # Extract base64 from data URL
                    _, data = image_data["data"].split(",", 1)
                    content = base64.b64decode(data)
                else:
                    content = base64.b64decode(image_data["data"])
                return Image(content=content)
            else:
                logger.warning(f"Unknown image format: {image_data}")
                return None
        except Exception as e:
            logger.error(f"Error creating Agno image: {e}")
            return None
    
    def _create_agno_audio(self, audio_data: Dict) -> Any:
        """Create Agno Audio object from audio data."""
        try:
            from agno.media import Audio
            
            if "data" in audio_data:
                # Base64 data
                import base64
                if audio_data["data"].startswith("data:"):
                    # Extract base64 from data URL
                    _, data = audio_data["data"].split(",", 1)
                    content = base64.b64decode(data)
                else:
                    content = base64.b64decode(audio_data["data"])
                
                # Get format from mime type
                mime_type = audio_data.get("mime_type", "audio/wav")
                format_map = {
                    "audio/wav": "wav",
                    "audio/mp3": "mp3",
                    "audio/mpeg": "mp3",
                    "audio/ogg": "ogg",
                    "audio/webm": "webm"
                }
                audio_format = format_map.get(mime_type, "wav")
                
                return Audio(content=content, format=audio_format)
            else:
                logger.warning(f"Unknown audio format: {audio_data}")
                return None
        except Exception as e:
            logger.error(f"Error creating Agno audio: {e}")
            return None
    
    def _create_agno_video(self, video_data: Dict) -> Any:
        """Create Agno Video object from video data."""
        try:
            from agno.media import Video
            
            if "filepath" in video_data:
                return Video(filepath=video_data["filepath"])
            elif "url" in video_data:
                # Download and save temporarily
                import tempfile
                import requests
                
                response = requests.get(video_data["url"])
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                    tmp.write(response.content)
                    return Video(filepath=tmp.name)
            else:
                logger.warning(f"Unknown video format: {video_data}")
                return None
        except Exception as e:
            logger.error(f"Error creating Agno video: {e}")
            return None
    
    def _extract_response_text(self, run_response) -> str:
        """Extract text from Agno RunResponse."""
        if hasattr(run_response, 'content'):
            return str(run_response.content)
        elif hasattr(run_response, 'output'):
            return str(run_response.output)
        else:
            return str(run_response)
    
    def _extract_tool_calls(self, run_response) -> List[Dict[str, Any]]:
        """Extract tool calls from Agno RunResponse."""
        tool_calls = []
        
        # Check if response has events
        if hasattr(run_response, 'events') and run_response.events:
            for event in run_response.events:
                if event.event == "ToolCallStarted":
                    tool_calls.append({
                        "tool": event.tool,
                        "args": event.args if hasattr(event, 'args') else {},
                        "started_at": event.timestamp if hasattr(event, 'timestamp') else None
                    })
        
        return tool_calls
    
    def _extract_tool_outputs(self, run_response) -> List[Dict[str, Any]]:
        """Extract tool outputs from Agno RunResponse."""
        tool_outputs = []
        
        # Check if response has events
        if hasattr(run_response, 'events') and run_response.events:
            for event in run_response.events:
                if event.event == "ToolCallCompleted":
                    tool_outputs.append({
                        "tool": event.tool,
                        "output": event.result if hasattr(event, 'result') else None,
                        "completed_at": event.timestamp if hasattr(event, 'timestamp') else None
                    })
        
        return tool_outputs
    
    def _extract_usage_info(self, run_response, processing_time_ms: float = 0.0, multimodal_content: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract comprehensive usage information from Agno RunResponse with multimodal cost tracking."""
        try:
            # Use the new unified usage calculator for comprehensive tracking
            from automagik.utils.usage_calculator import UnifiedUsageCalculator
            
            calculator = UnifiedUsageCalculator()
            breakdown = calculator.extract_agno_usage(
                result=run_response,
                model=str(self.config.model),
                processing_time_ms=processing_time_ms,
                multimodal_content=multimodal_content
            )
            
            # Return comprehensive usage data
            return calculator.create_legacy_compatible_usage(breakdown)
            
        except Exception as e:
            logger.warning(f"Could not use UnifiedUsageCalculator, falling back to basic usage: {e}")
            # Fallback to basic usage tracking
            return self._extract_basic_usage_info(run_response)
    
    def _extract_basic_usage_info(self, run_response) -> Dict[str, Any]:
        """Fallback basic usage extraction for backward compatibility."""
        usage = {
            "request_tokens": 0,
            "response_tokens": 0,
            "total_tokens": 0,
            "model": str(self.config.model),
            "framework": "agno"
        }
        
        # Agno tracks metrics differently - check for usage in response
        if hasattr(run_response, 'usage'):
            if hasattr(run_response.usage, 'prompt_tokens'):
                usage["request_tokens"] = run_response.usage.prompt_tokens
            if hasattr(run_response.usage, 'completion_tokens'):
                usage["response_tokens"] = run_response.usage.completion_tokens
            if hasattr(run_response.usage, 'total_tokens'):
                usage["total_tokens"] = run_response.usage.total_tokens
        
        # Add timing information if available
        if hasattr(run_response, 'duration_ms'):
            usage["duration_ms"] = run_response.duration_ms
        
        # Add event counts for observability
        if hasattr(run_response, 'events') and run_response.events:
            event_counts = {}
            for event in run_response.events:
                event_type = event.event
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            usage["event_counts"] = event_counts
        
        return usage
    
    def format_message_history(self, 
                              raw_messages: List[Any]) -> List[Any]:
        """Convert message history to Agno format."""
        # Agno uses a simpler message format
        # For now, we'll convert to a list of strings
        formatted_messages = []
        
        for message in (raw_messages or []):
            if isinstance(message, dict):
                role = message.get('role', 'user')
                content = message.get('content', '')
                
                # Format as role: content
                if role != 'system':  # System messages handled separately
                    formatted_messages.append(f"{role}: {content}")
            elif isinstance(message, str):
                formatted_messages.append(message)
        
        return formatted_messages
    
    def extract_tool_calls(self, result: Any) -> List[Dict[str, Any]]:
        """Public method to extract tool calls."""
        return self._extract_tool_calls(result)
        
    def extract_tool_outputs(self, result: Any) -> List[Dict[str, Any]]:
        """Public method to extract tool outputs."""
        return self._extract_tool_outputs(result)
        
    def convert_tools(self, tools: List[Any]) -> List[Any]:
        """Convert tools to Agno-compatible format."""
        # Agno tools are just functions, so minimal conversion needed
        converted = []
        for tool in tools:
            if callable(tool):
                converted.append(self._wrap_tool_for_agno(tool))
        return converted
    
    async def cleanup(self) -> None:
        """Clean up Agno resources."""
        # Agno is lightweight and doesn't require explicit cleanup
        # But we'll clear references
        self._agent_instance = None
        self._tools = []
        super().cleanup()