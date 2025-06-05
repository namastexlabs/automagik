"""Deprecation shim for src.agents.simple module.

This module has been moved to src.agents.pydanticai.
Please update your imports to use the new location.
"""
import warnings
from typing import Dict, Any

# Import all agents from the new location
from src.agents.pydanticai.discord import create_agent as create_discord_agent
from src.agents.pydanticai.estruturar import create_agent as create_estruturar_agent
from src.agents.pydanticai.flashinho import create_agent as create_flashinho_agent
from src.agents.pydanticai.prompt_maker import create_agent as create_prompt_maker_agent
from src.agents.pydanticai.simple import create_agent as create_simple_agent
from src.agents.pydanticai.sofia import create_agent as create_sofia_agent
from src.agents.pydanticai.stan import create_agent as create_stan_agent
from src.agents.pydanticai.stan_email import create_agent as create_stan_email_agent
from src.agents.pydanticai.summary import create_agent as create_summary_agent

# Issue deprecation warning
warnings.warn(
    "The 'src.agents.simple' module is deprecated and will be removed in a future version. "
    "Please use 'src.agents.pydanticai' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export create_agent functions for backward compatibility
def create_agent(agent_type: str, config: Dict[str, Any] = None):
    """Create an agent with deprecation warning."""
    warnings.warn(
        f"Creating agent '{agent_type}' from deprecated 'src.agents.simple'. "
        f"Please update to 'src.agents.pydanticai.{agent_type}'",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Map agent types to new create functions
    agent_creators = {
        'discord': create_discord_agent,
        'estruturar': create_estruturar_agent,
        'flashinho': create_flashinho_agent,
        'prompt_maker': create_prompt_maker_agent,
        'simple': create_simple_agent,
        'sofia': create_sofia_agent,
        'stan': create_stan_agent,
        'stan_email': create_stan_email_agent,
        'summary': create_summary_agent,
    }
    
    if agent_type in agent_creators:
        return agent_creators[agent_type](config or {})
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

# For backward compatibility, also export individual creators
discord = create_discord_agent
estruturar = create_estruturar_agent
flashinho = create_flashinho_agent
prompt_maker = create_prompt_maker_agent
simple = create_simple_agent
sofia = create_sofia_agent
stan = create_stan_agent
stan_email = create_stan_email_agent
summary = create_summary_agent