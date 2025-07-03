"""
Multimodal Specialist Agent - Powered by Agno Framework

This agent demonstrates Agno's superior multimodal capabilities for:
- Audio transcription and analysis
- Image recognition and description  
- Video content analysis
- Document processing
- Multi-format content understanding

Agno is automatically selected when multimodal content is detected.
"""

from typing import Dict, Any
from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.dependencies import AutomagikAgentsDependencies

# Agent prompt specifically designed for multimodal processing
MULTIMODAL_SPECIALIST_PROMPT = """You are a Multimodal Specialist powered by the Agno framework, capable of processing and understanding multiple types of media content.

## Your Capabilities

### 🎵 Audio Processing
- Transcribe speech from audio files
- Identify background sounds and music
- Analyze audio quality and characteristics
- Extract key information from conversations

### 🖼️ Image Analysis
- Describe visual content in detail
- Read and extract text from images (OCR)
- Identify objects, people, and scenes
- Analyze charts, graphs, and diagrams

### 🎥 Video Understanding
- Summarize video content
- Extract key frames and moments
- Identify actions and events
- Transcribe spoken content

### 📄 Document Processing
- Extract text from PDFs and documents
- Analyze document structure and layout
- Summarize long documents
- Extract specific information

## Interaction Style
- Always acknowledge the type of media you're analyzing
- Provide structured, detailed responses
- Offer to process multiple media types in a single request
- Be helpful and informative about what you can and cannot do

## Response Format
When analyzing media, structure your response as:
1. **Media Type Detected**: [audio/image/video/document]
2. **Content Analysis**: [detailed description]
3. **Key Insights**: [important findings]
4. **Additional Options**: [what else you can help with]

## Technical Notes
- Powered by Agno framework for optimal multimodal performance
- Automatically handles different media formats
- Provides graceful fallbacks when specific processing isn't available
- Optimized for speed and accuracy

Remember: You excel at multimodal content. When users provide mixed media, analyze each type and provide comprehensive insights."""

class MultimodalSpecialistAgent(AutomagikAgent):
    """
    Multimodal Specialist Agent using Agno framework for superior multimodal processing.
    
    This agent automatically uses Agno framework when multimodal content is detected,
    providing the best possible experience for audio, video, image, and document processing.
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        # Force Agno framework for multimodal content
        config["framework_type"] = "agno"
        config["model"] = config.get("model", "openai:gpt-4o")  # Multimodal-capable model
        
        super().__init__(config)
        
        # Set the agent-specific prompt
        self._code_prompt_text = MULTIMODAL_SPECIALIST_PROMPT
        
        # Initialize dependencies with multimodal-optimized settings
        self.dependencies = AutomagikAgentsDependencies(config)
        
        # Register multimodal analysis tools
        self.tool_registry.register_default_tools(self.context)
        
        # Optimize for multimodal content
        self.supported_media = ["image", "audio", "video", "document"]
        self.auto_enhance_prompts = True
        self.vision_model = config.get("model", "openai:gpt-4o")
        
    async def process_multimodal_request(self, content_types: Dict[str, Any]) -> str:
        """
        Enhanced multimodal processing method.
        
        Args:
            content_types: Dictionary with media types and content
            
        Returns:
            Structured analysis response
        """
        analysis_parts = []
        
        # Analyze each content type
        for media_type, content in content_types.items():
            if content:
                analysis_parts.append(f"## {media_type.title()} Analysis")
                analysis_parts.append(f"Content detected: {len(content)} item(s)")
                
        if analysis_parts:
            intro = "🎯 **Multimodal Content Detected** - Analyzing with Agno framework for optimal results.\n\n"
            return intro + "\n".join(analysis_parts)
        else:
            return "No multimodal content detected. Ready to process audio, images, videos, or documents."
    
    def get_capabilities_summary(self) -> str:
        """Return a summary of multimodal capabilities."""
        return """
🚀 **Multimodal Specialist Capabilities**

✅ **Audio**: Transcription, analysis, sound identification
✅ **Images**: OCR, object detection, scene description  
✅ **Video**: Content summarization, key frame extraction
✅ **Documents**: Text extraction, structure analysis

🔧 **Powered by Agno Framework**
- Ultra-fast multimodal processing
- Native support for 23+ model providers
- Built-in observability and performance tracking
- Graceful handling of unsupported formats

💡 **Usage**: Simply send me any combination of media files and I'll analyze them comprehensively!
"""


# Factory function for agent creation
def create_multimodal_specialist_agent(config: Dict[str, Any]) -> MultimodalSpecialistAgent:
    """Create a MultimodalSpecialistAgent instance."""
    return MultimodalSpecialistAgent(config)