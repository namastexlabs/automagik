"""Flashinho Old Make Agent - Minimal External Agent Pattern."""
from typing import Dict
from automagik.agents.models.automagik_agent import AutomagikAgent


class FlashinhoOldMakeAgent(AutomagikAgent):
    """Flashinho Old Make Agent - Educational coach for Brazilian students."""
    
    # Declarative configuration
    DEFAULT_MODEL = "openai:gpt-4o-mini"
    DEFAULT_CONFIG = {
        "supported_media": ["image", "audio", "document"],
        "language": "pt-BR"
    }
    
    # External agent configuration
    PACKAGE_ENV_FILE = ".env"
    EXTERNAL_API_KEYS = [
        ("FLASHED_API_KEY", "Flashed API authentication key"),
    ]
    
    # Prompt file (markdown)
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