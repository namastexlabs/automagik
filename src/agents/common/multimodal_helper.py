"""Multimodal helper for all agents.

This module provides common multimodal tools and utilities that can be used
by any agent to handle images, documents, audio, and other media types.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

def register_multimodal_tools(tool_registry, dependencies):
    """Register multimodal analysis tools for any agent.
    
    Args:
        tool_registry: The agent's tool registry
        dependencies: The agent's dependencies object
    """
    
    async def analyze_image(ctx=None, question: str = "What do you see in this image?") -> str:
        """Analyze attached images."""
        if not dependencies or not dependencies.has_media('image'):
            return "No images are attached to analyze."
        
        images = dependencies.current_images
        if not images:
            return "No images found in the current context."
        
        # Get the first image for analysis
        image = images[0]
        image_name = image.get('name', 'image')
        
        return f"Image analysis requested for '{image_name}': {question}"

    async def analyze_document(ctx=None, question: str = "What is this document about?") -> str:
        """Analyze attached documents."""
        if not dependencies or not dependencies.has_media('document'):
            return "No documents are attached to analyze."
        
        documents = dependencies.current_documents
        if not documents:
            return "No documents found in the current context."
        
        # Get the first document for analysis
        doc = documents[0]
        doc_name = doc.get('name', 'document')
        doc_size = doc.get('size_bytes', 0)
        
        return f"Document analysis requested for '{doc_name}' ({doc_size} bytes): {question}"

    async def analyze_audio(ctx=None, question: str = "What is in this audio?") -> str:
        """Analyze attached audio files."""
        if not dependencies or not dependencies.has_media('audio'):
            return "No audio files are attached to analyze."
        
        audio_files = dependencies.current_audio
        if not audio_files:
            return "No audio files found in the current context."
        
        # Get the first audio file for analysis
        audio = audio_files[0]
        audio_name = audio.get('name', 'audio file')
        
        return f"Audio analysis requested for '{audio_name}': {question}"

    async def analyze_attached_media(ctx=None, media_type: str = "any") -> str:
        """Analyze any attached media (images, documents, audio)."""
        if not dependencies:
            return "No media context available."
        
        
        if not dependencies.has_media():
            return "No media files are attached to analyze."
        
        analysis_parts = []
        
        # Check images
        if dependencies.has_media('image'):
            images = dependencies.current_images
            analysis_parts.append(f"Found {len(images)} image(s) attached")
        
        # Check documents  
        if dependencies.has_media('document'):
            documents = dependencies.current_documents
            doc_names = [doc.get('name', 'unnamed') for doc in documents]
            analysis_parts.append(f"Found {len(documents)} document(s): {', '.join(doc_names)}")
        
        # Check audio
        if dependencies.has_media('audio'):
            audio = dependencies.current_audio
            analysis_parts.append(f"Found {len(audio)} audio file(s) attached")
        
        if analysis_parts:
            return "Media analysis: " + "; ".join(analysis_parts)
        else:
            return "No supported media types found for analysis."

    async def describe_media(ctx=None) -> str:
        """Get a description of all attached media."""
        if not dependencies:
            return "No media context available."
        
        return dependencies.describe_media()

    async def get_media_count(ctx=None) -> Dict[str, int]:
        """Get count of each media type."""
        if not dependencies:
            return {"images": 0, "audio": 0, "documents": 0}
        
        return dependencies.get_media_count()

    # Set function names for proper tool registration
    analyze_image.__name__ = "analyze_image"
    analyze_document.__name__ = "analyze_document" 
    analyze_audio.__name__ = "analyze_audio"
    analyze_attached_media.__name__ = "analyze_attached_media"
    describe_media.__name__ = "describe_media"
    get_media_count.__name__ = "get_media_count"
    
    # Register all tools
    tool_registry.register_tool(analyze_image)
    tool_registry.register_tool(analyze_document)
    tool_registry.register_tool(analyze_audio)
    tool_registry.register_tool(analyze_attached_media)
    tool_registry.register_tool(describe_media)
    tool_registry.register_tool(get_media_count)
    
    logger.debug("Registered multimodal analysis tools")

def configure_agent_for_multimodal(agent_config: Dict[str, Any]) -> Dict[str, Any]:
    """Configure agent settings for optimal multimodal support.
    
    Args:
        agent_config: Existing agent configuration
        
    Returns:
        Updated configuration with multimodal settings
    """
    # Ensure vision-capable model is set
    if "vision_model" not in agent_config:
        agent_config["vision_model"] = "openai:gpt-4o"
    
    # Enable multimodal support
    agent_config.setdefault("supported_media", ["image", "audio", "document"])
    agent_config.setdefault("auto_enhance_prompts", True)
    
    return agent_config

def get_media_aware_prompt_variables(dependencies) -> Dict[str, str]:
    """Get template variables that describe current media context.
    
    Args:
        dependencies: Agent dependencies with media context
        
    Returns:
        Dictionary of variables for prompt templates
    """
    if not dependencies:
        return {
            "media_description": "No media attached",
            "media_count": "0",
            "has_images": "false",
            "has_documents": "false", 
            "has_audio": "false"
        }
    
    media_desc = dependencies.describe_media()
    counts = dependencies.get_media_count()
    
    return {
        "media_description": media_desc,
        "media_count": str(sum(counts.values())),
        "has_images": "true" if counts['images'] > 0 else "false",
        "has_documents": "true" if counts['documents'] > 0 else "false",
        "has_audio": "true" if counts['audio'] > 0 else "false",
        "image_count": str(counts['images']),
        "document_count": str(counts['documents']),
        "audio_count": str(counts['audio'])
    }