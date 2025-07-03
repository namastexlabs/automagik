"""Enhanced Simple Agent using new framework patterns with multimodal support."""
from typing import Dict, List

from automagik.agents.models.automagik_agent import AutomagikAgent
from .prompts.prompt import AGENT_PROMPT

# Export commonly used functions for backward compatibility with tests
from automagik.agents.common.message_parser import (
    extract_all_messages,
    extract_tool_calls,
    extract_tool_outputs,
)


class SimpleAgent(AutomagikAgent):
    """Enhanced Simple Agent with multimodal capabilities.
    
    Features:
    - Image analysis and description
    - Document reading and summarization  
    - Audio transcription (when supported)
    - Automatic model switching to vision-capable models
    - Built-in multimodal analysis tools
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize with complete multimodal setup."""
        # inject multimodal defaults
        if config is None:
            config = {}
        
        # Enhanced multimodal configuration
        config.setdefault("supported_media", ["image", "audio", "video", "document"])
        config.setdefault("auto_enhance_prompts", True)
        config.setdefault("enable_agno_for_multimodal", True)  # Use Agno for multimodal content
        # Use "auto" to enable framework switching based on content type
        config.setdefault("framework_type", "auto")

        super().__init__(config)

        self._code_prompt_text = AGENT_PROMPT

        # dependencies setup
        self.dependencies = self.create_default_dependencies()
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)

        # Register default tools
        self.tool_registry.register_default_tools(self.context)

        # Register Evolution WhatsApp helpers for parity with Sofia
        self.tool_registry.register_evolution_tools(self.context)

        # Register enhanced multimodal tools
        self._register_multimodal_tools()
        
        # Add multimodal capability tool
        self._register_media_capabilities_tool()

    def _register_multimodal_tools(self):
        """Register multimodal analysis tools using common helper."""
        try:
            from automagik.agents.common.multimodal_helper import register_multimodal_tools
            register_multimodal_tools(self.tool_registry, self.dependencies)
        except ImportError:
            # Fallback: register basic multimodal tools manually
            self._register_basic_multimodal_tools()
    
    def _register_basic_multimodal_tools(self):
        """Register basic multimodal tools as fallback."""
        
        async def analyze_image(ctx, description: str = "Analyze this image") -> str:
            """Analyze images attached to messages."""
            return f"Image analysis requested: {description}. The framework will automatically process any attached images."
            
        async def transcribe_audio(ctx, language: str = "auto") -> str:
            """Transcribe audio files."""
            return f"Audio transcription requested in language: {language}. The framework will automatically process any attached audio files."
            
        async def analyze_document(ctx, extract_type: str = "summary") -> str:
            """Analyze documents (PDFs, text files, etc)."""
            return f"Document analysis requested (type: {extract_type}). The framework will automatically process any attached documents."
        
        self.tool_registry.register_tool(analyze_image)
        self.tool_registry.register_tool(transcribe_audio)
        self.tool_registry.register_tool(analyze_document)
    
    def _register_media_capabilities_tool(self):
        """Register tool to describe multimodal capabilities."""
        
        async def describe_multimodal_capabilities(ctx) -> str:
            """Describe what media types and analysis I can perform."""
            return """🎯 **Enhanced Multimodal Capabilities**

📷 **Images**: 
- Object detection and recognition
- Scene description and analysis
- Text extraction (OCR) from images
- Chart and diagram interpretation

🎵 **Audio**:
- Speech transcription (multiple languages)
- Speaker identification
- Audio quality analysis
- Background sound detection

📄 **Documents**:
- PDF text extraction
- Document structure analysis
- Content summarization
- Table and data extraction

🎥 **Video** (limited):
- Frame extraction and analysis
- Content summarization

🤖 **Framework**: Automatically uses optimal framework (Agno for multimodal, PydanticAI for text)
⚡ **Performance**: Ultra-fast processing with comprehensive usage tracking

Simply attach any media files and I'll analyze them automatically!"""
        
        self.tool_registry.register_tool(describe_multimodal_capabilities)


def create_agent(config: Dict[str, str]) -> SimpleAgent:
    """Factory function to create enhanced simple agent with multimodal support."""
    try:
        return SimpleAgent(config)
    except Exception:
        from automagik.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)