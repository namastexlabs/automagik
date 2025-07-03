"""Example agent template for external agents.

This is a minimal agent that demonstrates how to create custom agents
that can be loaded by the Automagik framework when installed via pip.
"""
from typing import Dict, Optional
from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.dependencies import AutomagikAgentsDependencies


# Define your agent's system prompt
AGENT_PROMPT = """You are a helpful AI assistant created as an example agent.
You can be customized to perform any task by modifying this prompt and adding tools.

Current capabilities:
- Basic conversation
- Example responses
- Template for building more complex agents
"""


def create_agent(config: Optional[Dict[str, str]] = None) -> AutomagikAgent:
    """
    Factory function to create an instance of the example agent.
    
    This function is called by the Automagik framework to instantiate your agent.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        AutomagikAgent instance
    """
    if config is None:
        config = {}
    
    # Create the agent instance
    agent = ExampleAgent(config)
    
    return agent


class ExampleAgent(AutomagikAgent):
    """Example agent implementation."""
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize the example agent.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # Set the agent's system prompt
        self._code_prompt_text = AGENT_PROMPT
        
        # Configure model (defaults to gpt-4o-mini)
        model_name = config.get("model", "openai:gpt-4o-mini")
        
        # Set up dependencies
        self.dependencies = AutomagikAgentsDependencies(
            model_name=model_name,
            model_settings={},
            api_keys={},
            tool_config={}
        )
        
        # Register default tools (conversation history, etc.)
        self.tool_registry.register_default_tools(self.context)
        
        # Add custom tools here if needed
        # self.tool_registry.register_tool(MyCustomTool())
    
    @property
    def model_name(self) -> str:
        """Get the model name for this agent."""
        return self.dependencies.model_name or "openai:gpt-4o-mini"