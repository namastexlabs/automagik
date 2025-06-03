from typing import Dict, Optional, Type, List
import logging
import os
import traceback
import uuid
import importlib
from pathlib import Path
from threading import Lock
import inspect  # NEW - to help debug callable methods
import asyncio  # NEW

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.placeholder import PlaceholderAgent

logger = logging.getLogger(__name__)

class AgentFactory:
    """A factory for creating agent instances."""

    _agent_classes = {}
    _agent_creators = {}
    _agent_templates: Dict[str, AutomagikAgent] = {}  # Store one template per agent
    _agent_locks: Dict[str, Lock] = {}  # Per-agent creation locks
    _agent_locks_async: Dict[str, asyncio.Lock] = {}  # NEW asyncio-based locks per agent
    _lock_creation_lock = asyncio.Lock()  # NEW global lock to protect _agent_locks_async
    

    
    @classmethod
    def register_agent_class(cls, name: str, agent_class: Type[AutomagikAgent]) -> None:
        """Register an agent class with the factory.
        
        Args:
            name: The name of the agent class
            agent_class: The agent class to register
        """
        cls._agent_classes[name] = agent_class
        
    @classmethod
    def register_agent_creator(cls, name: str, creator_fn) -> None:
        """Register an agent creator function with the factory.
        
        Args:
            name: The name of the agent type
            creator_fn: The function to create an agent
        """
        cls._agent_creators[name] = creator_fn
    
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
            
        logger.debug(f"Creating agent of type {agent_type}")
        
        # Default to simple agent
        if not agent_type:
            agent_type = "simple"
        
        # Use agent type as-is, no normalization
        
        # Try to create using a registered creator function
        if agent_type in cls._agent_creators:
            try:
                agent = cls._agent_creators[agent_type](config)
                logger.debug(f"Successfully created {agent_type} agent using creator function")
                return agent
            except Exception as e:
                logger.error(f"Error creating {agent_type} agent: {str(e)}")
                logger.error(traceback.format_exc())
                return PlaceholderAgent({"name": f"{agent_type}_error", "error": str(e)})
        
        # Try to create using a registered class
        if agent_type in cls._agent_classes:
            try:
                agent = cls._agent_classes[agent_type](config)
                logger.debug(f"Successfully created {agent_type} agent using agent class")
                return agent
            except Exception as e:
                logger.error(f"Error creating {agent_type} agent: {str(e)}")
                logger.error(traceback.format_exc())
                return PlaceholderAgent({"name": f"{agent_type}_error", "error": str(e)})
        
        # Try dynamic import for agent types not explicitly registered
        try:
            # Try to import from pydanticai agents folder
            module_path = f"src.agents.pydanticai.{agent_type}"
            module = importlib.import_module(module_path)
            
            if hasattr(module, "create_agent"):
                agent = module.create_agent(config)
                # Register for future use
                cls.register_agent_creator(agent_type, module.create_agent)
                logger.debug(f"Successfully created {agent_type} agent via dynamic import")
                return agent
        except ImportError:
            logger.warning(f"Could not import agent module for {agent_type}")
        except Exception as e:
            logger.error(f"Error dynamically creating agent {agent_type}: {str(e)}")
            logger.error(traceback.format_exc())
            return PlaceholderAgent({"name": f"{agent_type}_error", "error": str(e)})
                
        # Unknown agent type
        logger.error(f"Unknown agent type: {agent_type}")
        return PlaceholderAgent({"name": "unknown_agent_type", "error": f"Unknown agent type: {agent_type}"})
        
    @classmethod
    def discover_agents(cls) -> None:
        """Discover available agents in the pydanticai and claude_code folders.
        
        This method automatically scans the src/agents/pydanticai and src/agents/claude_code
        directories for agent modules and registers them with the factory.
        
        Note: As of NMSTX-230, all orchestration is handled by the PydanticAI Genie agent
        which includes embedded LangGraph functionality for workflow orchestration.
        """
        logger.info("Discovering agents in pydanticai and claude_code folders")
        
        # Discover pydanticai agents (includes genie with embedded LangGraph)
        cls._discover_agents_in_directory("pydanticai")
        
        # Discover claude_code agent (single module, not directory of agents)
        cls._discover_single_agent("claude_code")
    
    @classmethod
    def _discover_single_agent(cls, agent_name: str) -> None:
        """Discover a single agent module.
        
        Args:
            agent_name: Name of the agent module (e.g., 'claude_code')
        """
        logger.info(f"Discovering {agent_name} agent")
        try:
            # Import the agent module directly
            module_name = f"src.agents.{agent_name}"
            module = importlib.import_module(module_name)
            
            # Check if the module has a create_agent function
            if hasattr(module, "create_agent") and callable(module.create_agent):
                cls.register_agent_creator(agent_name, module.create_agent)
                logger.debug(f"Discovered and registered {agent_name} agent")
        except Exception as e:
            logger.error(f"Error importing {agent_name} agent: {str(e)}")
    
    @classmethod
    def _discover_agents_in_directory(cls, directory_name: str) -> None:
        """Discover agents in a specific directory.
        
        Args:
            directory_name: Name of the directory to scan (e.g., 'simple', 'langgraph')
        """
        logger.info(f"Discovering agents in {directory_name} folder")
        
        # Path to the agents directory
        agents_dir = Path(os.path.dirname(os.path.dirname(__file__))) / directory_name
        
        if not agents_dir.exists():
            logger.warning(f"{directory_name.title()} agents directory not found: {agents_dir}")
            return
            
        # Scan for agent directories
        for item in agents_dir.iterdir():
            if item.is_dir() and not item.name.startswith('__') and item.name != 'shared':
                try:
                    # Try to import the module
                    module_name = f"src.agents.{directory_name}.{item.name}"
                    module = importlib.import_module(module_name)
                    
                    # Check if the module has a create_agent function
                    if hasattr(module, "create_agent") and callable(module.create_agent):
                        # Use agent name as-is, no prefixes
                        agent_name = item.name
                        cls.register_agent_creator(agent_name, module.create_agent)
                        logger.debug(f"Discovered and registered {directory_name} agent: {agent_name}")
                except Exception as e:
                    logger.error(f"Error importing {directory_name} agent from {item.name}: {str(e)}")
    
    @classmethod
    def list_available_agents(cls) -> List[str]:
        """List all available agent names.
        
        Returns:
            List of available agent names
        """
        # Combine creators and classes, use names as-is
        agents = []
        
        for name in list(cls._agent_creators.keys()) + list(cls._agent_classes.keys()):
            if name not in agents:
                agents.append(name)
        
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
        # Use the agent name as-is, no normalization
        
        # Ensure only one thread builds the template first time
        lock = cls._agent_locks.setdefault(agent_name, Lock())
        logger.debug(f"Acquired lock for agent {agent_name}")
        
        with lock:
            logger.debug(f"Template cache status for {agent_name}: {'exists' if agent_name in cls._agent_templates else 'needs creation'}")
            
            # Just create a fresh agent every time - simpler and safer than deepcopy
            # Create initial configuration with name
            config = {
                "name": agent_name
            }
                
            # Create a new agent instance from scratch - most reliable way to avoid shared state
            logger.debug(f"Creating fresh agent instance for {agent_name}")
            agent = cls.create_agent(agent_name, config) 
            
            # Set important template attributes like db_id if we had a previous template
            if agent_name in cls._agent_templates:
                # Copy DB ID if available - one bit of state we do want to preserve
                template = cls._agent_templates[agent_name]
                if hasattr(template, "db_id") and template.db_id:
                    logger.debug(f"Copying db_id {template.db_id} from template to new agent instance")
                    agent.db_id = template.db_id
            else:
                # First time, store a template for attribute reference
                logger.debug(f"Storing new agent template for {agent_name}")
                cls._agent_templates[agent_name] = agent
            
            # Verify the agent has a callable run method
            has_run = hasattr(agent, "run") and callable(getattr(agent, "run"))
            has_process = hasattr(agent, "process_message") and callable(getattr(agent, "process_message"))
            
            if not has_run or not has_process:
                logger.error(f"INVALID AGENT: {agent_name} missing callable methods: run={has_run}, process_message={has_process}")
                # Dump agent structure for debugging
                for name, value in inspect.getmembers(agent):
                    if not name.startswith('_'):  # Skip private attributes
                        is_callable = callable(value)
                        logger.debug(f"Agent attribute: {name}={type(value)} callable={is_callable}")
            else:
                logger.debug(f"Verified agent {agent_name} has required callable methods")
            
            return agent
    
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
                    from src.db import register_agent, list_agents
                    
                    # First validate if this is a variation of an existing agent
                    all_agents = list_agents(active_only=False)
                    
                    # Check if this agent name is a variation of an existing agent
                    for existing_agent in all_agents:
                        # Check for common variations
                        if (agent_name.lower() == f"{existing_agent.name.lower()}agent" or
                            agent_name.lower() == f"{existing_agent.name.lower()}-agent" or
                            agent_name.lower() == f"{existing_agent.name.lower()}_agent"):
                            # Use the existing agent instead
                            agent_id = existing_agent.id
                            logger.warning(f"Agent name '{agent_name}' is a variation of '{existing_agent.name}', using existing agent ID {agent_id}")
                            # Update the agent's db_id
                            agent.db_id = agent_id
                            break
                    
                    # If not a variation and agent_id is still None, register as new agent
                    if not agent_id:
                        # Extract agent metadata
                        agent_type = agent_name
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

    @classmethod
    async def _get_agent_lock(cls, agent_name: str) -> asyncio.Lock:
        """Get or create an asyncio.Lock for a specific agent type in a threadsafe way."""
        async with cls._lock_creation_lock:
            if agent_name not in cls._agent_locks_async:
                cls._agent_locks_async[agent_name] = asyncio.Lock()
            return cls._agent_locks_async[agent_name]

    @classmethod
    async def get_agent_async(cls, agent_name: str):
        """Asynchronous counterpart to get_agent that is safe under high concurrency."""
        lock = await cls._get_agent_lock(agent_name)
        async with lock:
            # Delegate to the synchronous get_agent for the heavy lifting.
            # This approach keeps backward-compatibility while ensuring only one concurrent
            # coroutine builds/initializes a given agent template at a time.
            return cls.get_agent(agent_name)
