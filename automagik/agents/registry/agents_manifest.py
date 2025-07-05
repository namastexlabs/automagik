"""Declarative agents manifest - centralized agent configuration.

This file contains all agent registrations in one place, eliminating
the need for scattered create_agent functions across individual agents.
"""

import logging
from typing import Dict, Any
from .agent_registry import AgentRegistry, Framework

logger = logging.getLogger(__name__)

def load_agents_manifest():
    """Load all agents into the registry declaratively."""
    logger.info("Loading agents manifest...")
    
    # Clear existing registrations (for testing/reloading)
    AgentRegistry.clear()
    
    # ===== CORE FRAMEWORK AGENTS =====
    
    # Simple Agent (PydanticAI) - Default general purpose agent
    try:
        from automagik.agents.pydanticai.simple.agent import SimpleAgent
        AgentRegistry.register(
            name="simple",
            agent_class=SimpleAgent,
            framework=Framework.PYDANTIC_AI,
            default_model="openai:gpt-4o-mini",
            description="Enhanced simple agent with multimodal capabilities",
            fallback_models=["openai:gpt-4o", "anthropic:claude-3-5-sonnet-20241022"],
            framework_preferences={
                "pydanticai": "openai:gpt-4o-mini",
                "agno": "openai:gpt-4o"
            },
            supported_media=["text", "image", "audio", "document"],
            default_config={
                "auto_enhance_prompts": True,
                "enable_agno_for_multimodal": True,
                "framework_type": "auto"
            }
        )
    except ImportError as e:
        logger.warning(f"Could not register simple agent: {e}")
    
    # Claude Code Agent - Genie orchestrator
    try:
        from automagik.agents.claude_code import ClaudeCodeAgent
        AgentRegistry.register(
            name="claude_code",
            agent_class=ClaudeCodeAgent,
            framework=Framework.CLAUDE_CODE,
            default_model="anthropic:claude-3-5-sonnet-20241022",
            description="Genie orchestrator for Claude Code workflows",
            fallback_models=["anthropic:claude-3-5-haiku-20241022"],
            supported_media=["text"],
            default_config={
                "enable_workflows": True,
                "enable_memory": True,
                "enable_orchestration": True
            }
        )
    except ImportError as e:
        logger.warning(f"Could not register claude_code agent: {e}")
    
    # ===== SPECIALIZED AGENTS =====
    
    # Sofia Agent - Meeting coordination
    try:
        from automagik.agents.pydanticai.sofia.agent import SofiaAgent
        AgentRegistry.register(
            name="sofia",
            agent_class=SofiaAgent,
            framework=Framework.PYDANTIC_AI,
            default_model="openai:gpt-4o",
            description="AI assistant for meeting coordination and Airtable management",
            fallback_models=["openai:gpt-4o-mini", "anthropic:claude-3-5-sonnet-20241022"],
            supported_media=["text"],
            default_config={
                "enable_airtable": True,
                "enable_bella": True,
                "meeting_coordination": True
            },
            external_api_keys=[
                ("AIRTABLE_API_KEY", "Airtable API access"),
                ("BELLA_API_KEY", "Bella meeting platform access")
            ]
        )
    except ImportError as e:
        logger.warning(f"Could not register sofia agent: {e}")
    
    # Discord Agent - Discord bot functionality  
    try:
        from automagik.agents.pydanticai.discord.agent import DiscordAgent
        AgentRegistry.register(
            name="discord",
            agent_class=DiscordAgent,
            framework=Framework.PYDANTIC_AI,
            default_model="openai:gpt-4o-mini",
            description="Discord bot agent with multimodal support",
            fallback_models=["openai:gpt-4o", "anthropic:claude-3-5-sonnet-20241022"],
            supported_media=["text", "image", "audio"],
            default_config={
                "discord_integration": True,
                "multimodal": True,
                "auto_enhance_prompts": True
            }
        )
    except ImportError as e:
        logger.warning(f"Could not register discord agent: {e}")
    
    # ===== EVOLUTION WHATSAPP AGENTS =====
    # External agents are now managed separately and loaded from external_agents directory
    
    
    
    # Automagik Genie Agent
    try:
        from automagik.agents.pydanticai.automagik_genie.agent import AutomagikGenieAgent
        AgentRegistry.register(
            name="automagik_genie",
            agent_class=AutomagikGenieAgent, 
            framework=Framework.PYDANTIC_AI,
            default_model="anthropic:claude-3-5-sonnet-20241022",
            description="Automagik Genie orchestrator agent", 
            fallback_models=["openai:gpt-4o", "anthropic:claude-3-5-haiku-20241022"],
            supported_media=["text"],
            default_config={
                "orchestration": True,
                "memory": True,
                "workflows": True
            }
        )
    except ImportError as e:
        logger.warning(f"Could not register automagik_genie agent: {e}")
    
    # ===== EXTERNAL AGENTS DISCOVERY =====
    _discover_external_agents()
    
    # Log registration summary
    stats = AgentRegistry.get_registry_stats()
    logger.info(f"Agents manifest loaded: {stats['enabled_agents']} enabled, {stats['disabled_agents']} disabled")
    for framework, count in stats['agents_by_framework'].items():
        logger.info(f"  {framework}: {count} agents")

def _discover_external_agents():
    """Discover and register external agents from AUTOMAGIK_EXTERNAL_AGENTS_DIR."""
    import os
    import sys
    from pathlib import Path
    import importlib.util
    
    external_agents_dir = os.environ.get("AUTOMAGIK_EXTERNAL_AGENTS_DIR")
    if not external_agents_dir:
        return
        
    external_path = Path(external_agents_dir).resolve()
    if not external_path.exists():
        logger.info(f"External agents directory does not exist: {external_path}")
        return
        
    logger.info(f"Discovering external agents from: {external_path}")
    
    # Add to Python path
    external_path_str = str(external_path)
    if external_path_str not in sys.path:
        sys.path.insert(0, external_path_str)
        
    # Scan for agent directories  
    for agent_dir in external_path.iterdir():
        if not agent_dir.is_dir() or agent_dir.name.startswith('.') or agent_dir.name.startswith('__'):
            continue
            
        try:
            # Look for __init__.py or agent.py
            init_file = agent_dir / "__init__.py"
            agent_file = agent_dir / "agent.py"
            
            module = None
            agent_class = None
            
            # Try to load module and extract agent class
            if init_file.exists():
                spec = importlib.util.spec_from_file_location(agent_dir.name, init_file)
                module = importlib.util.module_from_spec(spec)
                sys.modules[agent_dir.name] = module
                spec.loader.exec_module(module)
                
            elif agent_file.exists():
                spec = importlib.util.spec_from_file_location(f"{agent_dir.name}_agent", agent_file)
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"{agent_dir.name}_agent"] = module
                spec.loader.exec_module(module)
            
            if module:
                # Try to find agent class and create_agent function
                create_agent_fn = getattr(module, 'create_agent', None)
                
                # Look for agent class
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        hasattr(attr, '__init__') and 
                        attr_name.endswith('Agent') and 
                        attr_name != 'AutomagikAgent'):
                        agent_class = attr
                        break
                
                if agent_class and create_agent_fn:
                    # Register external agent with default configuration
                    AgentRegistry.register(
                        name=agent_dir.name,
                        agent_class=agent_class,
                        framework=Framework.PYDANTIC_AI,  # Default framework for externals
                        default_model="openai:gpt-4o-mini",  # Default model
                        description=f"External agent: {agent_dir.name}",
                        fallback_models=["openai:gpt-4o", "anthropic:claude-3-5-sonnet-20241022"],
                        factory_function=create_agent_fn,  # For backward compatibility
                        external_api_keys=getattr(agent_class, 'EXTERNAL_API_KEYS', []),
                        package_env_file=getattr(agent_class, 'PACKAGE_ENV_FILE', None)
                    )
                    
                    logger.info(f"✅ Registered external agent: {agent_dir.name}")
                else:
                    logger.warning(f"External agent {agent_dir.name} missing agent class or create_agent function")
                    
        except Exception as e:
            logger.error(f"Error registering external agent {agent_dir.name}: {e}")

# Convenience functions for dynamic registration
def register_external_agent(
    name: str,
    agent_class: type,
    default_model: str = "openai:gpt-4o-mini",
    **kwargs
):
    """Register an external agent dynamically."""
    AgentRegistry.register(
        name=name,
        agent_class=agent_class,
        framework=Framework.PYDANTIC_AI,
        default_model=default_model,
        description=kwargs.get('description', f"External agent: {name}"),
        **kwargs
    )

def update_agent_config(name: str, **config_updates):
    """Update configuration for a registered agent."""
    descriptor = AgentRegistry.get_agent_descriptor(name)
    if descriptor:
        descriptor.default_config.update(config_updates)
        logger.info(f"Updated config for agent '{name}': {config_updates}")
        return True
    return False