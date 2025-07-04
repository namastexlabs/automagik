"""Flashinho The First Agent - The Original Minimal Pattern."""
from typing import Dict
from automagik.agents.models.automagik_agent import AutomagikAgent


class FlashinhoTheFirstAgent(AutomagikAgent):
    """Flashinho The First - The original educational assistant."""
    
    # Declarative configuration
    DEFAULT_MODEL = "openai:gpt-3.5-turbo"
    DEFAULT_CONFIG = {
        "language": "pt-BR",
        "version": "1.0"
    }
    
    # External agent configuration
    PACKAGE_ENV_FILE = ".env"
    EXTERNAL_API_KEYS = [
        ("FLASHED_API_KEY", "Flashed API authentication key"),
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