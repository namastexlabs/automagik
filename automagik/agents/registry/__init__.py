"""Agent registry module with declarative agent registration."""

from .agent_registry import (
    AgentRegistry,
    AgentDescriptor, 
    ModelConfig,
    Framework,
    register_agent,
    register_pydantic_agent,
    register_agno_agent,
    register_claude_code_agent,
)

from .agents_manifest import load_agents_manifest

__all__ = [
    "AgentRegistry",
    "AgentDescriptor",
    "ModelConfig", 
    "Framework",
    "register_agent",
    "register_pydantic_agent",
    "register_agno_agent", 
    "register_claude_code_agent",
    "load_agents_manifest",
]