"""Enhanced Simple Agent using new framework patterns with multimodal support."""
from typing import Dict, List

from src.agents.models.automagik_agent import AutomagikAgent
from .prompts.prompt import AGENT_PROMPT

# Export commonly used functions for backward compatibility with tests
from src.agents.common.message_parser import (
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
        """Initialize with automatic multimodal setup."""
        # inject multimodal defaults
        if config is None:
            config = {}
        config.setdefault("vision_model", "openai:gpt-4o")
        config.setdefault("supported_media", ["image", "audio", "document"])
        config.setdefault("auto_enhance_prompts", True)

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

        # simple helper: analyze_image tool for compatibility
        self._register_helper_tools()

    def _register_helper_tools(self):
        deps = self.dependencies

        async def analyze_image(ctx, question: str = "What do you see in this image?") -> str:
            if not deps or not deps.has_media('image'):
                return "No images are attached to analyze."
            return f"Image analysis requested: {question}"

        async def analyze_document(ctx, question: str = "What is this document about?") -> str:
            if not deps or not deps.has_media('document'):
                return "No documents are attached to analyze."
            
            documents = deps.current_documents
            if not documents:
                return "No documents found in the current context."
            
            # Get the first document for analysis
            doc = documents[0]
            doc_name = doc.get('name', 'document')
            doc_size = doc.get('size_bytes', 0)
            
            return f"Document analysis requested for '{doc_name}' ({doc_size} bytes): {question}"

        async def analyze_attached_media(ctx, media_type: str = "any") -> str:
            """Analyze any attached media (images, documents, audio)."""
            if not deps:
                return "No media context available."
            
            if not deps.has_media():
                return "No media files are attached to analyze."
            
            analysis_parts = []
            
            # Check images
            if deps.has_media('image'):
                images = deps.current_images
                analysis_parts.append(f"Found {len(images)} image(s) attached")
            
            # Check documents  
            if deps.has_media('document'):
                documents = deps.current_documents
                doc_names = [doc.get('name', 'unnamed') for doc in documents]
                analysis_parts.append(f"Found {len(documents)} document(s): {', '.join(doc_names)}")
            
            # Check audio
            if deps.has_media('audio'):
                audio = deps.current_audio
                analysis_parts.append(f"Found {len(audio)} audio file(s) attached")
            
            if analysis_parts:
                return "Media analysis: " + "; ".join(analysis_parts)
            else:
                return "No supported media types found for analysis."

        analyze_image.__name__ = "analyze_image"
        analyze_document.__name__ = "analyze_document" 
        analyze_attached_media.__name__ = "analyze_attached_media"
        
        self.tool_registry.register_tool(analyze_image)
        self.tool_registry.register_tool(analyze_document)
        self.tool_registry.register_tool(analyze_attached_media)


def create_agent(config: Dict[str, str]) -> SimpleAgent:
    """Factory function to create enhanced simple agent with multimodal support."""
    try:
        return SimpleAgent(config)
    except Exception:
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)