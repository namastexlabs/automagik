"""Flashinho Old Make Agent - External Agent with Simplest Pattern.

This demonstrates the new simplified external agent pattern:
- No create_agent function needed
- No factory boilerplate
- Just the agent class with DEFAULT_MODEL
- Prompt loaded from prompt.md file via PROMPT_FILE attribute
"""
from typing import Dict
from automagik.agents.models.automagik_agent import AutomagikAgent
# Tools will be registered from the centralized location via tool_registry


class FlashinhoOldMakeAgent(AutomagikAgent):
    """Flashinho Old Make Agent - External agent using simplest pattern."""
    
    # Declarative configuration (used at API startup)
    DEFAULT_MODEL = "openai:gpt-4o-mini"
    DEFAULT_CONFIG = {
        "supported_media": ["image", "audio", "document"],
        "auto_enhance_prompts": True,
        "enable_multi_prompt": False,
        "language": "pt-BR"
    }
    
    # External agent configuration
    PACKAGE_ENV_FILE = ".env"
    EXTERNAL_API_KEYS = [
        ("FLASHED_API_KEY", "Flashed API authentication key"),
    ]
    
    # Prompt configuration - loaded automatically from prompt.md
    PROMPT_FILE = "prompt.md"
    
    def __init__(self, config: Dict[str, str] = None) -> None:
        """Initialize the agent."""
        # Initialize AutomagikAgent with merged config
        # This automatically:
        # - Loads .env file if PACKAGE_ENV_FILE is set
        # - Registers external API keys if EXTERNAL_API_KEYS is set  
        # - Loads prompt from file if PROMPT_FILE is set
        super().__init__(config or {})
        
        # Flashinho-specific tools are registered centrally via tool_registry
        # The tool_registry will have access to all shared tools including Flashed tools
        
        # Create dependencies
        self.dependencies = self.create_default_dependencies()
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Register default tools
        self.tool_registry.register_default_tools(self.context)


# That's it! No create_agent function needed with the new pattern!