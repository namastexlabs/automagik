"""PydanticAI agents package.

This package contains agents built with PydanticAI framework.
(Previously located at src.agents.simple)
"""

import os
import importlib
import logging
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)

# Discover agents in subfolders
def discover_agents():
    """Discover agent modules in the pydanticai agent type directory."""
    agents = {}
    current_dir = Path(__file__).parent
    
    for item in current_dir.iterdir():
        if item.is_dir() and not item.name.startswith('__') and not item.name.startswith('.'):
            try:
                # Try to import the module
                module_name = f"src.agents.pydanticai.{item.name}"
                module = importlib.import_module(module_name)
                
                # Check if the module has a create_agent function
                if hasattr(module, "create_agent") and callable(module.create_agent):
                    agent_name = item.name
                    agents[agent_name] = module.create_agent
            except Exception as e:
                logger.error(f"Error importing agent from {item.name}: {str(e)}")
    
    return agents

# Get discovered agents
_discovered_agents = discover_agents()

def create_agent(agent_name=None):
    """Create an agent instance by name.
    
    Args:
        agent_name: The name of the agent to create
                   If None, creates a simple agent.
        
    Returns:
        An instance of the requested agent
    
    Raises:
        ValueError: If the agent cannot be found or created
    """
    # If no agent_name specified or it's "simple", default to simple
    if agent_name is None or agent_name == "simple":
        agent_name = "simple"
    
    # Remove _agent suffix if present (for normalization)
    if agent_name.endswith("_agent"):
        base_name = agent_name
    else:
        base_name = f"{agent_name}_agent"
    
    logger.info(f"Creating agent: {base_name}")
    
    # Try to find the agent in discovered agents
    if base_name in _discovered_agents:
        return _discovered_agents[base_name]()
    
    # Direct import approach if agent wasn't discovered
    try:
        module_path = f"src.agents.pydanticai.{base_name}"
        module = importlib.import_module(module_path)
        
        if hasattr(module, "create_agent"):
            return module.create_agent()
        else:
            raise ValueError(f"Module {module_path} has no create_agent function")
            
    except ImportError as e:
        raise ValueError(f"Could not import agent module for {base_name}: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error creating agent {base_name}: {str(e)}")
