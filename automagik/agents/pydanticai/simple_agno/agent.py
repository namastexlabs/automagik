"""Simple Agent implementation using Agno framework.

This demonstrates how to create an agent using Agno as the underlying
framework instead of PydanticAI, while maintaining the same interface.
"""
from typing import Dict

from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.dependencies import AutomagikAgentsDependencies


class SimpleAgnoAgent(AutomagikAgent):
    """Simple Agent powered by Agno framework.
    
    This agent demonstrates:
    - Using Agno instead of PydanticAI
    - Native multimodal capabilities
    - Ultra-fast performance
    - Built-in observability
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize with Agno framework."""
        # Force Agno framework
        config = config or {}
        config["framework_type"] = "agno"
        
        # Enable multimodal by default
        config.setdefault("model", "openai:gpt-4o")  # Multimodal model (supports images and audio transcription)
        config.setdefault("supported_media", ["image", "audio", "document", "video"])
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"SimpleAgnoAgent initializing with framework_type: {config.get('framework_type')}")
        
        super().__init__(config)
        
        # Verify framework type after initialization
        logger.info(f"SimpleAgnoAgent initialized with actual framework_type: {self.framework_type}")
        
        # Set the prompt
        self._code_prompt_text = """You are a helpful AI assistant powered by Agno framework.
You have native multimodal capabilities and can process images, audio, and video directly.

Key features:
- Ultra-fast performance (2μs agent creation)
- Native multimodal processing (no preprocessing needed)
- Built-in observability and telemetry
- Support for 23+ model providers

When users send media files, process them directly without mentioning technical details
about transcription or image analysis unless specifically asked."""
        
        # Create dependencies
        self.dependencies = self.create_default_dependencies()
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Register tools
        self.tool_registry.register_default_tools(self.context)
        
        # Add multimodal awareness tool
        async def describe_media_capabilities(ctx):
            """Describe your multimodal capabilities."""
            return """I can process:
- Images: Direct visual analysis without preprocessing
- Audio: Native audio understanding (no transcription needed)
- Video: Full video analysis (Gemini models only currently)
- Documents: Direct document processing

All media is processed natively by the model, preserving full context."""
        
        self.tool_registry.register_tool(describe_media_capabilities)


def create_agent(config: Dict[str, str]) -> SimpleAgnoAgent:
    """Factory function to create a Simple Agno agent."""
    return SimpleAgnoAgent(config)


# Example usage comparison
if __name__ == "__main__":
    import asyncio
    
    async def demo():
        # Create agent with Agno
        agent = SimpleAgnoAgent({
            "name": "simple_agno_demo",
            "model": "openai:gpt-4o"
        })
        
        # Initialize framework
        await agent.initialize_framework(
            dependencies_type=AutomagikAgentsDependencies
        )
        
        # Text example
        print("=== Text Example ===")
        response = await agent.run_agent("What framework are you using?")
        print(response.text)
        
        # Multimodal example (would work with real media)
        print("\n=== Multimodal Example ===")
        multimodal_input = [
            "What can you tell me about this image?",
            {"type": "image", "url": "https://example.com/image.jpg"}
        ]
        # response = await agent.run_agent(multimodal_input)
        print("(Would process image natively with Agno)")
    
    # asyncio.run(demo())