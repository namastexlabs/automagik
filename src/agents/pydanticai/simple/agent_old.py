"""Ultra-simplified SimpleAgent demonstrating the potential of the framework."""
from __future__ import annotations

from src.agents.models.automagik_agent import AutomagikAgent
from .prompts.prompt import AGENT_PROMPT

# Backward compatibility imports for tests


class SimpleAgent(AutomagikAgent):
    """Ultra-simplified SimpleAgent - minimal boilerplate."""
    
    def __init__(self, config: dict[str, str]) -> None:
        """Initialize with absolute minimum code."""
        super().__init__(config, framework_type="pydantic_ai")
        
        # Agent essentials - just 4 lines!
        self._code_prompt_text = AGENT_PROMPT
        self.dependencies = self.create_default_dependencies()
        self.tool_registry.register_default_tools(self.context)
        self.tool_registry.register_evolution_tools(self.context)


def create_agent(config: dict[str, str]) -> SimpleAgent:
    """One-line factory function."""
    return SimpleAgent(config)