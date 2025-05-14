from typing import Dict, Optional, Type, Union, List
import logging
import os
import traceback
import uuid
import importlib
from pathlib import Path
import copy
from threading import Lock

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import BaseDependencies
from src.agents.models.placeholder import PlaceholderAgent

logger = logging.getLogger(__name__)

class AgentFactory:
    """A factory for creating agent instances."""

    _agent_classes = {}
    _agent_creators = {}
    _agent_templates: Dict[str, AutomagikAgent] = {}  # Store one template per agent
    _agent_locks: Dict[str, Lock] = {}  # Per-agent creation locks
    
    @classmethod
    def _normalize_agent_name(cls, name: str) -> str:
        """Normalize agent name to ensure consistency.
        
        This function standardizes agent names by:
        1. Converting to lowercase
        2. Ensuring the name always ends with '_agent'
        3. Removing any duplicate '_agent' suffixes
        
        Args:
            name: The agent name to normalize
            
        Returns:
            Normalized agent name
        """
        # Convert to lowercase
        normalized = name.lower() if name else "simple_agent"
        
        # Remove any existing _agent suffix
        base_name = normalized.replace('_agent', '')
        
        # Always add _agent suffix
        return f"{base_name}_agent"
    
    @classmethod
    def register_agent_class(cls, name: str, agent_class: Type[AutomagikAgent]) -> None:
        """Register an agent class with the factory.
        
        Args:
            name: The name of the agent class
            agent_class: The agent class to register
        """
        normalized_name = cls._normalize_agent_name(name)
        cls._agent_classes[normalized_name] = agent_class
        
    @classmethod
    def register_agent_creator(cls, name: str, creator_fn) -> None:
        """Register an agent creator function with the factory.
        
        Args:
            name: The name of the agent type
            creator_fn: The function to create an agent
        """
        normalized_name = cls._normalize_agent_name(name)
        cls._agent_creators[normalized_name] = creator_fn
    
    @classmethod
    def create_agent(cls, agent_type: str, config: Optional[Dict[str, str]] = None) -> AutomagikAgent:
        """Create an agent of the specified type.
        
        Args:
            agent_type: The type of agent to create
            config: Optional configuration override
            
        Returns:
            An initialized agent instance
            
        Raises:
            ValueError: If the agent type is unknown
        """
        if config is None:
            config = {}
            
        logger.info(f"Creating agent of type {agent_type}")
        
        # Default to simple agent
        if not agent_type:
            agent_type = "simple"
        
        # Normalize agent type
        normalized_agent_type = cls._normalize_agent_name(agent_type)
        
        # Try to create using a registered creator function
        if normalized_agent_type in cls._agent_creators:
            try:
                agent = cls._agent_creators[normalized_agent_type](config)
                logger.info(f"Successfully created {normalized_agent_type} agent using creator function")
                return agent
            except Exception as e:
                logger.error(f"Error creating {normalized_agent_type} agent: {str(e)}")
                logger.error(traceback.format_exc())
                return PlaceholderAgent({"name": f"{normalized_agent_type}_error", "error": str(e)})
        
        # Try to create using a registered class
        if normalized_agent_type in cls._agent_classes:
            try:
                agent = cls._agent_classes[normalized_agent_type](config)
                logger.info(f"Successfully created {normalized_agent_type} agent using agent class")
                return agent
            except Exception as e:
                logger.error(f"Error creating {normalized_agent_type} agent: {str(e)}")
                logger.error(traceback.format_exc())
                return PlaceholderAgent({"name": f"{normalized_agent_type}_error", "error": str(e)})
        
        # Try dynamic import for agent types not explicitly registered
        try:
            # Try to import from simple agents folder
            module_path = f"src.agents.simple.{normalized_agent_type}"
            module = importlib.import_module(module_path)
            
            if hasattr(module, "create_agent"):
                agent = module.create_agent(config)
                # Register for future use
                cls.register_agent_creator(normalized_agent_type, module.create_agent)
                logger.info(f"Successfully created {normalized_agent_type} agent via dynamic import")
                return agent
        except ImportError:
            logger.warning(f"Could not import agent module for {normalized_agent_type}")
        except Exception as e:
            logger.error(f"Error dynamically creating agent {normalized_agent_type}: {str(e)}")
            logger.error(traceback.format_exc())
            return PlaceholderAgent({"name": f"{normalized_agent_type}_error", "error": str(e)})
                
        # Unknown agent type
        logger.error(f"Unknown agent type: {agent_type}")
        return PlaceholderAgent({"name": "unknown_agent_type", "error": f"Unknown agent type: {agent_type}"})
        
    @classmethod
    def discover_agents(cls) -> None:
        """Discover available agents in the simple folder.
        
        This method automatically scans the src/agents/simple directory for agent modules
        and registers them with the factory.
        """
        logger.info("Discovering agents in simple folder")
        
        # Path to the simple agents directory
        simple_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "simple"
        
        if not simple_dir.exists():
            logger.warning(f"Simple agents directory not found: {simple_dir}")
            return
            
        # Scan for agent directories
        for item in simple_dir.iterdir():
            if item.is_dir() and not item.name.startswith('__'):
                try:
                    # Try to import the module
                    module_name = f"src.agents.simple.{item.name}"
                    module = importlib.import_module(module_name)
                    
                    # Check if the module has a create_agent function
                    if hasattr(module, "create_agent") and callable(module.create_agent):
                        # Always normalize agent name
                        normalized_name = cls._normalize_agent_name(item.name)
                        cls.register_agent_creator(normalized_name, module.create_agent)
                        logger.debug(f"Discovered and registered agent: {normalized_name}")
                except Exception as e:
                    logger.error(f"Error importing agent from {item.name}: {str(e)}")
    
    @classmethod
    def list_available_agents(cls) -> List[str]:
        """List all available agent names.
        
        Returns:
            List of available agent names
        """
        # Combine creators and classes, ensuring all are properly normalized
        agents = []
        
        for name in list(cls._agent_creators.keys()) + list(cls._agent_classes.keys()):
            normalized_name = cls._normalize_agent_name(name)
            if normalized_name not in agents:
                agents.append(normalized_name)
        
        return agents
        
    @classmethod
    def get_agent(cls, agent_name: str) -> AutomagikAgent:
        """Get an agent instance by name.
        
        Args:
            agent_name: Name of the agent to get
            
        Returns:
            Agent instance
            
        Raises:
            ValueError: If the agent is not found
        """
        # Normalize the agent name
        normalized_name = cls._normalize_agent_name(agent_name)
        
        # Ensure only one thread builds the template first time
        lock = cls._agent_locks.setdefault(normalized_name, Lock())
        with lock:
            if normalized_name in cls._agent_templates:
                # Return a deep copy to guarantee statelessness
                return copy.deepcopy(cls._agent_templates[normalized_name])

            # Create initial configuration with name
            config = {
                "name": normalized_name
            }

            # Build a new template agent (will self-register prompts etc.)
            template_agent = cls.create_agent(normalized_name, config)

            # Cache template for future requests
            cls._agent_templates[normalized_name] = template_agent

            return copy.deepcopy(template_agent)
    
    @classmethod
    def link_agent_to_session(cls, agent_name: str, session_id_or_name: str) -> bool:
        """Link an agent to a session in the database.
        
        Args:
            agent_name: The name of the agent to link
            session_id_or_name: Either a session ID or name
            
        Returns:
            True if the link was successful, False otherwise
        """
        try:
            # Make sure the session_id is a UUID string
            session_id = session_id_or_name
            try:
                # Try to parse as UUID
                uuid.UUID(session_id_or_name)
            except ValueError:
                # Not a UUID, try to look up by name
                logger.info(f"Session ID is not a UUID, treating as session name: {session_id_or_name}")
                
                # Use the appropriate database function to get session by name
                try:
                    from src.db import get_session_by_name
                    
                    session = get_session_by_name(session_id_or_name)
                    if not session:
                        logger.error(f"Session with name '{session_id_or_name}' not found")
                        return False
                        
                    session_id = str(session.id)
                    logger.info(f"Found session ID {session_id} for name {session_id_or_name}")
                except Exception as e:
                    logger.error(f"Error looking up session by name: {str(e)}")
                    return False

            # Get the agent (creating it if necessary)
            agent = cls.get_agent(agent_name)
            agent_id = getattr(agent, "db_id", None)
            
            if not agent_id:
                # Try to register the agent in the database
                try:
                    from src.db import register_agent
                    
                    # Extract agent metadata
                    agent_type = agent_name.replace("_agent", "")
                    description = getattr(agent, "description", f"{agent_name} agent")
                    model = getattr(getattr(agent, "config", {}), "model", "")
                    config = getattr(agent, "config", {})
                    
                    # If config is not a dict, convert it
                    if not isinstance(config, dict):
                        if hasattr(config, "__dict__"):
                            config = config.__dict__
                        else:
                            config = {"config": str(config)}
                    
                    # Register the agent
                    agent_id = register_agent(
                        name=agent_name,
                        agent_type=agent_type,
                        model=model,
                        description=description,
                        config=config
                    )
                    
                    # Update the agent's db_id
                    agent.db_id = agent_id
                    
                except Exception as e:
                    logger.error(f"Error registering agent in database: {str(e)}")
                    logger.error(traceback.format_exc())
                    return False
            
            # Link the session to the agent
            if agent_id:
                try:
                    from src.db import link_session_to_agent
                    return link_session_to_agent(uuid.UUID(session_id), agent_id)
                except Exception as e:
                    logger.error(f"Error linking agent to session: {str(e)}")
                    logger.error(traceback.format_exc())
                    return False
            else:
                logger.error(f"Could not find or create agent ID for agent {agent_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error linking agent {agent_name} to session {session_id_or_name}: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    @classmethod
    def get_agent_class(cls, agent_type: str) -> Optional[Type[AutomagikAgent]]:
        """Get the agent class for a given agent type.
        
        Args:
            agent_type: The type of agent to get the class for
            
        Returns:
            The agent class, or None if not found
        """
        # Check if we have a registered class
        if agent_type in cls._agent_classes:
            return cls._agent_classes[agent_type]
            
        # For creator functions, we need to instantiate one to get its class
        if agent_type in cls._agent_creators:
            try:
                agent = cls._agent_creators[agent_type]({})
                return agent.__class__
            except Exception as e:
                logger.error(f"Error creating agent to get class: {str(e)}")
                return None
                
        return None
