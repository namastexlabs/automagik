"""Centralized declarative agent registry.

This module provides a declarative way to register agents with their configurations,
eliminating the need for scattered create_agent functions across individual agents.
"""

from typing import Dict, Type, Optional, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Framework(Enum):
    """Supported agent frameworks."""
    PYDANTIC_AI = "pydanticai"
    AGNO = "agno" 
    CLAUDE_CODE = "claude_code"
    AUTO = "auto"  # Framework auto-detection

@dataclass
class ModelConfig:
    """Model configuration for an agent."""
    default_model: str
    fallback_models: List[str] = field(default_factory=list)
    framework_preferences: Dict[str, str] = field(default_factory=dict)
    
    def get_model_for_framework(self, framework: str) -> str:
        """Get the preferred model for a specific framework."""
        return self.framework_preferences.get(framework, self.default_model)

@dataclass 
class AgentDescriptor:
    """Declarative agent descriptor."""
    name: str
    agent_class: Type
    framework: Framework
    model_config: ModelConfig
    description: str = ""
    supported_media: List[str] = field(default_factory=lambda: ["text"])
    default_config: Dict[str, Any] = field(default_factory=dict)
    package_env_file: Optional[str] = None
    external_api_keys: List[tuple] = field(default_factory=list)
    enabled: bool = True
    
    # Factory function (optional - for backward compatibility)
    factory_function: Optional[Callable] = None

class AgentRegistry:
    """Centralized registry for all agent types."""
    
    _agents: Dict[str, AgentDescriptor] = {}
    _frameworks: Dict[Framework, List[str]] = {}
    
    @classmethod
    def register(
        cls,
        name: str,
        agent_class: Type,
        framework: Framework,
        default_model: str,
        description: str = "",
        fallback_models: List[str] = None,
        framework_preferences: Dict[str, str] = None,
        supported_media: List[str] = None,
        default_config: Dict[str, Any] = None,
        package_env_file: Optional[str] = None,
        external_api_keys: List[tuple] = None,
        enabled: bool = True,
        factory_function: Optional[Callable] = None
    ) -> None:
        """Register an agent declaratively.
        
        Args:
            name: Agent name (used for lookup)
            agent_class: The agent class to instantiate
            framework: Framework this agent uses
            default_model: Default LLM model
            description: Human-readable description
            fallback_models: Alternative models if default fails
            framework_preferences: Model preferences per framework
            supported_media: Supported media types
            default_config: Default configuration
            package_env_file: Package-specific .env file
            external_api_keys: External API keys to register
            enabled: Whether this agent is enabled
            factory_function: Optional factory function for compatibility
        """
        model_config = ModelConfig(
            default_model=default_model,
            fallback_models=fallback_models or [],
            framework_preferences=framework_preferences or {}
        )
        
        descriptor = AgentDescriptor(
            name=name,
            agent_class=agent_class,
            framework=framework,
            model_config=model_config,
            description=description,
            supported_media=supported_media or ["text"],
            default_config=default_config or {},
            package_env_file=package_env_file,
            external_api_keys=external_api_keys or [],
            enabled=enabled,
            factory_function=factory_function
        )
        
        cls._agents[name] = descriptor
        
        # Update framework index
        if framework not in cls._frameworks:
            cls._frameworks[framework] = []
        if name not in cls._frameworks[framework]:
            cls._frameworks[framework].append(name)
            
        logger.debug(f"Registered agent '{name}' with framework '{framework.value}' and model '{default_model}'")
    
    @classmethod
    def get_agent_descriptor(cls, name: str) -> Optional[AgentDescriptor]:
        """Get agent descriptor by name."""
        return cls._agents.get(name)
    
    @classmethod
    def list_agents(cls, framework: Optional[Framework] = None, enabled_only: bool = True) -> List[str]:
        """List available agents, optionally filtered by framework."""
        agents = []
        
        for name, descriptor in cls._agents.items():
            if enabled_only and not descriptor.enabled:
                continue
            if framework and descriptor.framework != framework:
                continue
            agents.append(name)
            
        return sorted(agents)
    
    @classmethod
    def list_by_framework(cls) -> Dict[str, List[str]]:
        """List agents grouped by framework."""
        result = {}
        for framework, agents in cls._frameworks.items():
            # Filter by enabled status
            enabled_agents = [
                name for name in agents 
                if cls._agents[name].enabled
            ]
            if enabled_agents:
                result[framework.value] = sorted(enabled_agents)
        return result
    
    @classmethod
    def create_agent(cls, name: str, config: Optional[Dict[str, Any]] = None):
        """Create an agent instance from registry."""
        descriptor = cls.get_agent_descriptor(name)
        if not descriptor:
            raise ValueError(f"Agent '{name}' not found in registry")
            
        if not descriptor.enabled:
            raise ValueError(f"Agent '{name}' is disabled")
        
        # Merge configurations
        final_config = descriptor.default_config.copy()
        if config:
            final_config.update(config)
            
        # Add framework preference
        final_config["framework_type"] = descriptor.framework.value
        
        # Add model configuration
        final_config["default_model"] = descriptor.model_config.default_model
        if descriptor.model_config.fallback_models:
            final_config["fallback_models"] = descriptor.model_config.fallback_models
            
        # Add media support
        final_config["supported_media"] = descriptor.supported_media
        
        try:
            # Use factory function if provided (backward compatibility)
            if descriptor.factory_function:
                return descriptor.factory_function(final_config)
            
            # Create instance directly using enhanced AutomagikAgent pattern
            instance = descriptor.agent_class(final_config)
            
            # Set descriptor metadata on instance for introspection
            instance._agent_descriptor = descriptor
            
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create agent '{name}': {e}")
            # Return placeholder agent
            from automagik.agents.models.placeholder import PlaceholderAgent
            return PlaceholderAgent({
                "name": f"{name}_error",
                "error": str(e)
            })
    
    @classmethod
    def get_model_for_agent(cls, name: str, framework: Optional[str] = None) -> Optional[str]:
        """Get the model for a specific agent and framework."""
        descriptor = cls.get_agent_descriptor(name)
        if not descriptor:
            return None
            
        if framework:
            return descriptor.model_config.get_model_for_framework(framework)
        return descriptor.model_config.default_model
    
    @classmethod
    def update_agent_model(cls, name: str, model: str, framework: Optional[str] = None) -> bool:
        """Update model configuration for an agent."""
        descriptor = cls.get_agent_descriptor(name)
        if not descriptor:
            return False
            
        if framework:
            descriptor.model_config.framework_preferences[framework] = model
        else:
            descriptor.model_config.default_model = model
            
        logger.info(f"Updated model for agent '{name}': {model}")
        return True
    
    @classmethod
    def enable_agent(cls, name: str, enabled: bool = True) -> bool:
        """Enable or disable an agent."""
        descriptor = cls.get_agent_descriptor(name)
        if not descriptor:
            return False
            
        descriptor.enabled = enabled
        logger.info(f"Agent '{name}' {'enabled' if enabled else 'disabled'}")
        return True
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered agents (for testing)."""
        cls._agents.clear()
        cls._frameworks.clear()
    
    @classmethod
    def get_registry_stats(cls) -> Dict[str, Any]:
        """Get registry statistics."""
        total_agents = len(cls._agents)
        enabled_agents = sum(1 for desc in cls._agents.values() if desc.enabled)
        
        framework_counts = {}
        for framework, agents in cls._frameworks.items():
            framework_counts[framework.value] = len([
                name for name in agents if cls._agents[name].enabled
            ])
            
        return {
            "total_agents": total_agents,
            "enabled_agents": enabled_agents,
            "disabled_agents": total_agents - enabled_agents,
            "agents_by_framework": framework_counts
        }

# Convenience functions for registration
def register_agent(
    name: str,
    agent_class: Type,
    framework: str,
    default_model: str,
    **kwargs
) -> None:
    """Convenience function to register an agent."""
    framework_enum = Framework(framework)
    AgentRegistry.register(
        name=name,
        agent_class=agent_class,
        framework=framework_enum,
        default_model=default_model,
        **kwargs
    )

def register_pydantic_agent(name: str, agent_class: Type, default_model: str, **kwargs):
    """Register a PydanticAI agent."""
    return register_agent(name, agent_class, "pydanticai", default_model, **kwargs)

def register_agno_agent(name: str, agent_class: Type, default_model: str, **kwargs):
    """Register an Agno agent."""
    return register_agent(name, agent_class, "agno", default_model, **kwargs)

def register_claude_code_agent(name: str, agent_class: Type, default_model: str, **kwargs):
    """Register a Claude Code agent."""
    return register_agent(name, agent_class, "claude_code", default_model, **kwargs)