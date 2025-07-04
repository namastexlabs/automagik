"""Flashinho Pro External Agent - Minimal Pattern with External API."""
from typing import Dict
from automagik.agents.models.automagik_agent import AutomagikAgent


class FlashinhoProExternalAgent(AutomagikAgent):
    """Flashinho Pro External - Demonstrates external API integration."""
    
    # Declarative configuration
    DEFAULT_MODEL = "openai:gpt-4o"
    DEFAULT_CONFIG = {
        "supported_media": ["image", "audio", "video", "document"],
        "language": "pt-BR",
        "external_api_enabled": True
    }
    
    # External agent configuration
    PACKAGE_ENV_FILE = ".env"
    EXTERNAL_API_KEYS = [
        ("FLASHED_API_KEY", "Flashed API authentication key"),
        ("EVOLUTION_API_KEY", "Evolution API key for WhatsApp"),
    ]
    
    # Prompt file
    PROMPT_FILE = "prompt.md"
    
    def __init__(self, config: Dict[str, str] = None) -> None:
        """Initialize the agent."""
        super().__init__(config or {})
        
        # Create dependencies and register tools
        self.dependencies = self.create_default_dependencies()
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Register centralized tools
        self.tool_registry.register_default_tools(self.context)