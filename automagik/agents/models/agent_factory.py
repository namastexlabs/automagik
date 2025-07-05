from typing import Dict, Optional, Type, List
import logging
import os
import sys
import traceback
import uuid
import importlib
import importlib.util
from pathlib import Path
from threading import Lock
import inspect  # NEW - to help debug callable methods
import asyncio  # NEW

from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.placeholder import PlaceholderAgent

# Import declarative registry
from automagik.agents.registry import AgentRegistry, load_agents_manifest

logger = logging.getLogger(__name__)

class AgentFactory:
    """A factory for creating agent instances with declarative registry support."""

    # Legacy registry for backward compatibility
    _agent_classes = {}
    _agent_creators = {}
    _agent_templates: Dict[str, AutomagikAgent] = {}  # Store one template per agent
    _agent_locks: Dict[str, Lock] = {}  # Per-agent creation locks
    _agent_locks_async: Dict[str, asyncio.Lock] = {}  # NEW asyncio-based locks per agent
    _lock_creation_lock = asyncio.Lock()  # NEW global lock to protect _agent_locks_async
    _session_agents: Dict[str, AutomagikAgent] = {}  # Cache agents by session for conversational continuity
    
    # Registry initialization flag
    _registry_initialized = False
    
    @classmethod
    def _ensure_registry_loaded(cls):
        """Ensure the declarative agent registry is loaded."""
        if not cls._registry_initialized:
            try:
                load_agents_manifest()
                cls._registry_initialized = True
                logger.info("Declarative agent registry loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load agent registry: {e}")
                logger.error(traceback.format_exc())
    
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
    def create_agent(cls, agent_type: str, config: Optional[Dict[str, str]] = None, 
                    framework: Optional[str] = None) -> AutomagikAgent:
        """Create an agent of the specified type.
        
        Args:
            agent_type: The type of agent to create
            config: Optional configuration override
            framework: Optional framework to use (e.g., 'pydanticai', 'agno')
            
        Returns:
            An initialized agent instance
            
        Raises:
            ValueError: If the agent type is unknown
        """
        if config is None:
            config = {}
            
        logger.debug(f"Creating agent of type {agent_type} with framework {framework}")
        
        # Ensure declarative registry is loaded
        cls._ensure_registry_loaded()
        
        # Check for virtual agent first
        agent_source = config.get("agent_source")
        if agent_source == "virtual":
            logger.info(f"Creating virtual agent: {agent_type}")
            return cls._create_virtual_agent(agent_type, config)
        
        # Default to simple agent
        if not agent_type:
            agent_type = "simple"
        
        # Set framework in config if provided
        if framework:
            config["framework_type"] = framework
        
        # ===== NEW: Try declarative registry first =====
        try:
            agent = AgentRegistry.create_agent(agent_type, config)
            if agent and not isinstance(agent, PlaceholderAgent):
                logger.debug(f"Successfully created {agent_type} agent using declarative registry")
                return agent
        except Exception as e:
            logger.debug(f"Declarative registry failed for '{agent_type}': {e}")
            # Continue to legacy fallback
        
        # Use agent type as-is, no normalization
        
        # Ensure external agents are discovered if environment variable is set
        if os.environ.get("AUTOMAGIK_EXTERNAL_AGENTS_DIR") and len(cls._agent_creators) == 0:
            logger.info(f"No agents registered yet, discovering agents first...")
            cls.discover_agents()
        
        # Log available creators for debugging
        logger.debug(f"Looking for agent '{agent_type}' in {len(cls._agent_creators)} registered creators")
        logger.debug(f"Available creators: {list(cls._agent_creators.keys())}")
        
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
        frameworks_to_try = []
        
        # If framework is specified, try that first
        if framework:
            frameworks_to_try.append(framework)
        
        # Add default frameworks to try
        # IMPORTANT: Don't include claude_code for external agents - it should only be used for "claude_code" specifically
        default_frameworks = ["pydanticai", "agno"]
        # Only add claude_code if the agent_type is specifically "claude_code"
        if agent_type == "claude_code":
            default_frameworks.append("claude_code")
            
        for fw in default_frameworks:
            if fw not in frameworks_to_try:
                frameworks_to_try.append(fw)
                
        for fw in frameworks_to_try:
            try:
                if fw == "claude_code":
                    # Special case for single-module claude_code agent
                    module_path = f"automagik.agents.{fw}"
                else:
                    # Framework directory structure
                    module_path = f"automagik.agents.{fw}.{agent_type}"
                    
                module = importlib.import_module(module_path)
                
                if hasattr(module, "create_agent"):
                    agent = module.create_agent(config)
                    # Register for future use with framework prefix for uniqueness
                    if fw == "claude_code":
                        cls.register_agent_creator(fw, module.create_agent)
                    else:
                        cls.register_agent_creator(f"{fw}.{agent_type}", module.create_agent)
                        # Also register without framework prefix for backward compatibility
                        if agent_type not in cls._agent_creators:
                            cls.register_agent_creator(agent_type, module.create_agent)
                    logger.debug(f"Successfully created {agent_type} agent from {fw} framework via dynamic import")
                    return agent
            except ImportError:
                logger.debug(f"Could not import {agent_type} from {fw} framework")
                continue
            except Exception as e:
                logger.error(f"Error dynamically creating agent {agent_type} from {fw}: {str(e)}")
                continue
                
        logger.warning(f"Could not import agent module for {agent_type} from any framework")
        
        # Check if this might be an external agent that wasn't discovered
        external_dir = os.environ.get("AUTOMAGIK_EXTERNAL_AGENTS_DIR")
        if external_dir:
            logger.error(f"Agent '{agent_type}' not found. External agents directory is set to: {external_dir}")
            logger.error(f"Available external agents: {[k for k in cls._agent_creators.keys() if '.' not in k and k not in ['simple', 'claude_code']]}")
        
        # Unknown agent type
        logger.error(f"Unknown agent type: {agent_type}")
        return PlaceholderAgent({"name": "unknown_agent_type", "error": f"Unknown agent type: {agent_type}"})
        
    @classmethod
    def discover_agents(cls, framework: Optional[str] = None) -> None:
        """Discover available agents in framework directories.
        
        Args:
            framework: Optional specific framework to discover, or None for all
        """
        # Framework directories to scan
        framework_directories = ["pydanticai", "agno"]
        frameworks_to_scan = [framework] if framework else framework_directories
        
        for fw in frameworks_to_scan:
            cls._discover_agents_in_directory(fw)
        
        # Also discover claude_code agent (single module)
        cls._discover_single_agent("claude_code")
        
        # Scan deprecated simple directory for backward compatibility
        simple_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "simple"
        if simple_dir.exists():
            logger.warning("Found deprecated simple directory - agents should be migrated to framework directories")
            try:
                # Import the deprecation shim which re-exports agents
                importlib.import_module("automagik.agents.simple")
                logger.info("Loaded simple directory deprecation shim")
            except Exception as e:
                logger.error(f"Error loading simple directory: {e}")
        
        # Discover external agents if configured
        cls._discover_external_agents()
    
    @classmethod
    def _discover_external_agents(cls) -> None:
        """Discover agents from external directories configured via environment variable."""
        external_agents_dir = os.environ.get("AUTOMAGIK_EXTERNAL_AGENTS_DIR")
        if not external_agents_dir:
            return
        
        external_path = Path(external_agents_dir).resolve()
        if not external_path.exists():
            logger.info(f"External agents directory does not exist: {external_path}")
            return
        
        logger.info(f"Discovering external agents from: {external_path}")
        
        # Add external agents directory to Python path for imports
        external_path_str = str(external_path)
        if external_path_str not in sys.path:
            sys.path.insert(0, external_path_str)
            logger.debug(f"Added to Python path: {external_path_str}")
        
        # Scan external agents directory for agent folders
        for agent_dir in external_path.iterdir():
            if agent_dir.is_dir() and not agent_dir.name.startswith('.') and not agent_dir.name.startswith('__'):
                try:
                    # Look for an __init__.py file first (preferred), then agent.py
                    init_file = agent_dir / "__init__.py"
                    agent_file = agent_dir / "agent.py"
                    
                    module = None
                    
                    if init_file.exists():
                        # Load from __init__.py (preferred - allows proper package structure)
                        try:
                            spec = importlib.util.spec_from_file_location(
                                agent_dir.name,  # Use simple module name, not nested
                                init_file
                            )
                            module = importlib.util.module_from_spec(spec)
                            
                            # Add the module to sys.modules to support relative imports
                            sys.modules[agent_dir.name] = module
                            
                            spec.loader.exec_module(module)
                            logger.debug(f"Loaded external agent module from __init__.py: {agent_dir.name}")
                            
                        except Exception as e:
                            logger.warning(f"Failed to load from __init__.py for {agent_dir.name}: {e}")
                            module = None
                    
                    # Fallback to agent.py if __init__.py failed or doesn't exist
                    if module is None and agent_file.exists():
                        try:
                            spec = importlib.util.spec_from_file_location(
                                f"{agent_dir.name}_agent",  # Unique name to avoid conflicts
                                agent_file
                            )
                            module = importlib.util.module_from_spec(spec)
                            
                            # Add to sys.modules
                            sys.modules[f"{agent_dir.name}_agent"] = module
                            
                            spec.loader.exec_module(module)
                            logger.debug(f"Loaded external agent module from agent.py: {agent_dir.name}")
                            
                        except Exception as e:
                            logger.warning(f"Failed to load from agent.py for {agent_dir.name}: {e}")
                            module = None
                    
                    # Check for create_agent function
                    if module and hasattr(module, "create_agent") and callable(module.create_agent):
                        cls.register_agent_creator(agent_dir.name, module.create_agent)
                        logger.info(f"✅ Discovered external agent: {agent_dir.name}")
                    elif module:
                        # NEW: Look for agent class directly if no create_agent function
                        agent_class = None
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (isinstance(attr, type) and 
                                issubclass(attr, AutomagikAgent) and 
                                attr != AutomagikAgent and
                                attr_name.endswith('Agent')):
                                agent_class = attr
                                logger.debug(f"Found external agent class {attr_name}")
                                break
                        
                        if agent_class:
                            cls.register_agent_class(agent_dir.name, agent_class)
                            logger.info(f"✅ Discovered external agent class: {agent_dir.name}")
                        else:
                            logger.warning(f"External agent {agent_dir.name} loaded but missing create_agent function or Agent class")
                    else:
                        logger.debug(f"No valid agent module found in {agent_dir.name}")
                        
                except Exception as e:
                    logger.error(f"Error loading external agent {agent_dir.name}: {str(e)}")
                    import traceback
                    logger.debug(f"Full traceback for {agent_dir.name}: {traceback.format_exc()}")
    
    @classmethod
    def _discover_single_agent(cls, agent_name: str) -> None:
        """Discover a single agent module.
        
        Args:
            agent_name: Name of the agent module (e.g., 'claude_code')
        """
        logger.info(f"Discovering {agent_name} agent")
        try:
            # Import the agent module directly
            module_name = f"automagik.agents.{agent_name}"
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
        logger.info(f"Discovering agents in {directory_name} framework")
        
        # Path to the agents directory
        agents_dir = Path(os.path.dirname(os.path.dirname(__file__))) / directory_name
        
        if not agents_dir.exists():
            logger.warning(f"{directory_name.title()} agents directory not found: {agents_dir}")
            return
            
        # Scan for agent directories
        for item in agents_dir.iterdir():
            if item.is_dir() and not item.name.startswith('__') and not item.name.startswith('.') and item.name != 'shared':
                try:
                    # Try to import the module
                    module_name = f"automagik.agents.{directory_name}.{item.name}"
                    module = importlib.import_module(module_name)
                    
                    # Check if the module has a create_agent function
                    if hasattr(module, "create_agent") and callable(module.create_agent):
                        # Use agent name as-is, no prefixes
                        agent_name = item.name
                        cls.register_agent_creator(agent_name, module.create_agent)
                        logger.debug(f"Discovered and registered {directory_name} agent: {agent_name}")
                    else:
                        # NEW: Look for agent class directly if no create_agent function
                        # Try to find an agent class in the module
                        agent_class = None
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (isinstance(attr, type) and 
                                issubclass(attr, AutomagikAgent) and 
                                attr != AutomagikAgent and
                                attr_name.endswith('Agent')):
                                agent_class = attr
                                logger.debug(f"Found agent class {attr_name} in {item.name}")
                                break
                        
                        if agent_class:
                            # Register the class directly
                            agent_name = item.name
                            cls.register_agent_class(agent_name, agent_class)
                            logger.debug(f"Discovered and registered {directory_name} agent class: {agent_name}")
                except Exception as e:
                    logger.error(f"Error importing {directory_name} agent from {item.name}: {str(e)}")
    
    @classmethod
    def list_available_agents(cls) -> List[str]:
        """List all available agent names.
        
        Returns:
            List of available agent names
        """
        # Ensure declarative registry is loaded
        cls._ensure_registry_loaded()
        
        # Get agents from declarative registry first
        registry_agents = AgentRegistry.list_agents(enabled_only=True)
        
        # Combine with legacy registry for backward compatibility
        legacy_agents = []
        for name in list(cls._agent_creators.keys()) + list(cls._agent_classes.keys()):
            if name not in legacy_agents and name not in registry_agents:
                legacy_agents.append(name)
        
        # Combine and sort
        all_agents = sorted(registry_agents + legacy_agents)
        
        logger.debug(f"Available agents: {len(all_agents)} total ({len(registry_agents)} from registry, {len(legacy_agents)} legacy)")
        return all_agents
        
    @classmethod
    def get_default_agent(cls, framework: str, config: Optional[Dict[str, str]] = None) -> AutomagikAgent:
        """Get the default agent for a specific framework.
        
        Args:
            framework: The framework name (e.g., 'pydanticai', 'agno')
            config: Optional configuration override
            
        Returns:
            Default agent instance for the framework
        """
        if config is None:
            config = {}
            
        # Set framework in config
        config["framework_type"] = framework
        
        # Define default agents per framework
        default_agents = {
            "pydanticai": "simple",
            "agno": "simple",  # Fallback to simple if agno doesn't have its own
            "claude": "claude_code",  # Alias for claude_code
            "claude_code": "claude_code",
            "langchain": "simple",  # Future framework
            "langgraph": "simple"   # Future framework
        }
        
        default_agent_type = default_agents.get(framework, "simple")
        logger.debug(f"Getting default agent '{default_agent_type}' for framework '{framework}'")
        
        return cls.create_agent(default_agent_type, config, framework)
        
    @classmethod
    def list_agents_by_framework(cls) -> Dict[str, List[str]]:
        """List available agents grouped by framework.
        
        Returns:
            Dictionary mapping framework names to lists of agent names
        """
        # Ensure declarative registry is loaded
        cls._ensure_registry_loaded()
        
        # Get from declarative registry first
        agents_by_framework = AgentRegistry.list_by_framework()
        
        # Merge with legacy registry for backward compatibility
        cls.discover_agents()
        
        # Group legacy registered agents by framework
        for agent_name in cls._agent_creators.keys():
            if "." in agent_name:
                # Framework-prefixed agent (e.g., "pydanticai.simple")
                framework, agent = agent_name.split(".", 1)
                if framework not in agents_by_framework:
                    agents_by_framework[framework] = []
                if agent not in agents_by_framework[framework]:
                    agents_by_framework[framework].append(agent)
            else:
                # Check if agent is already in registry
                found_in_registry = False
                for fw_agents in agents_by_framework.values():
                    if agent_name in fw_agents:
                        found_in_registry = True
                        break
                
                # Only add to legacy if not in registry
                if not found_in_registry:
                    if "pydanticai" not in agents_by_framework:
                        agents_by_framework["pydanticai"] = []
                    if agent_name not in agents_by_framework["pydanticai"]:
                        agents_by_framework["pydanticai"].append(agent_name)
                    
        return agents_by_framework
        
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
            
            # Check if this is a virtual agent by looking in the database
            try:
                from automagik.db.repository.agent import get_agent_by_name as get_db_agent
                db_agent = get_db_agent(agent_name)
                if db_agent:
                    # Load model from database
                    if db_agent.model:
                        config["model"] = db_agent.model
                        logger.debug(f"Loaded model '{db_agent.model}' for agent {agent_name} from database")
                    
                    # Merge database config
                    if db_agent.config and isinstance(db_agent.config, dict):
                        config.update(db_agent.config)
                        logger.debug(f"Loaded config for agent {agent_name} from database")
                    elif db_agent.config:
                        logger.warning(f"Agent {agent_name} has invalid config in database")
            except Exception as e:
                logger.debug(f"Could not load config for agent {agent_name} from database: {e}")
                
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
    def get_agent_with_session(cls, agent_name: str, session_id: str = None, user_id: str = None, session_name: str = None) -> AutomagikAgent:
        """Get an agent instance with session-based caching for conversational continuity.
        
        For conversational agents, this method maintains agent instances
        across requests within the same session to preserve user memory and context.
        
        Args:
            agent_name: Name of the agent to get
            session_id: Session identifier for caching
            user_id: User identifier for additional context
            
        Returns:
            Agent instance (cached for session if applicable)
        """
        # For conversational agents, use session-based caching
        conversational_agents = set()  # External agents managed separately
        
        if agent_name in conversational_agents and session_id:
            session_key = f"{agent_name}:{session_id}"
            
            # Check if we have a cached agent for this session
            if session_key in cls._session_agents:
                logger.debug(f"Reusing cached agent instance for session {session_id}")
                cached_agent = cls._session_agents[session_key]
                
                # Update context with current session/user info if available
                if hasattr(cached_agent, 'context'):
                    if user_id:
                        cached_agent.context['user_id'] = user_id
                    cached_agent.context['session_id'] = session_id
                    # IMPORTANT: Update session_name in cached agent context
                    if session_name:
                        cached_agent.context['session_name'] = session_name
                
                # MEMORY FIX: Restore conversation history for cached agents
                cls._restore_conversation_history(cached_agent, session_id, user_id)
                    
                return cached_agent
            else:
                # Create new agent and cache it for this session
                logger.debug(f"Creating and caching new agent instance for session {session_id}")
                agent = cls.get_agent(agent_name)
                
                # Set session context
                if hasattr(agent, 'context'):
                    if user_id:
                        agent.context['user_id'] = user_id
                    agent.context['session_id'] = session_id
                    # IMPORTANT: Pass session_name to agent so it respects API naming rules
                    if session_name:
                        agent.context['session_name'] = session_name
                
                # Cache the agent for future requests in this session
                cls._session_agents[session_key] = agent
                
                return agent
        else:
            # For non-conversational agents or when no session, use standard behavior
            return cls.get_agent(agent_name)
    
    @classmethod
    def _restore_conversation_history(cls, agent: AutomagikAgent, session_id: str, user_id: str = None) -> None:
        """Restore conversation history for cached agents to maintain conversational continuity.
        
        Args:
            agent: The cached agent instance
            session_id: Session identifier
            user_id: User identifier for filtering
        """
        try:
            # Store the complete conversation history in agent context
            # This ensures the agent has access to the full conversation even
            # when receiving fresh MessageHistory objects from requests
            if hasattr(agent, 'context'):
                # Store session info for history restoration
                agent.context['_cached_session_id'] = session_id
                agent.context['_cached_user_id'] = user_id
                agent.context['_conversation_history_restored'] = True
                
                logger.debug(f"Conversation history context restored for session {session_id}")
        except Exception as e:
            logger.error(f"Error restoring conversation history: {str(e)}")
            
    @classmethod
    def clear_session_cache(cls, session_id: str = None, agent_name: str = None):
        """Clear cached agents for sessions.
        
        Args:
            session_id: Clear only this session (if provided)
            agent_name: Clear only this agent type (if provided)
        """
        if session_id and agent_name:
            # Clear specific agent-session combination
            session_key = f"{agent_name}:{session_id}"
            if session_key in cls._session_agents:
                del cls._session_agents[session_key]
                logger.debug(f"Cleared cached agent for {session_key}")
        elif session_id:
            # Clear all agents for this session
            to_remove = [key for key in cls._session_agents.keys() if key.endswith(f":{session_id}")]
            for key in to_remove:
                del cls._session_agents[key]
            logger.debug(f"Cleared {len(to_remove)} cached agents for session {session_id}")
        elif agent_name:
            # Clear all sessions for this agent type
            to_remove = [key for key in cls._session_agents.keys() if key.startswith(f"{agent_name}:")]
            for key in to_remove:
                del cls._session_agents[key]
            logger.debug(f"Cleared {len(to_remove)} cached agents for agent {agent_name}")
        else:
            # Clear all cached agents
            count = len(cls._session_agents)
            cls._session_agents.clear()
            logger.debug(f"Cleared all {count} cached agents")
    
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
                    from automagik.db import get_session_by_name
                    
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
                    from automagik.db import register_agent, list_agents
                    
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
                    from automagik.db import link_session_to_agent
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
    
    @classmethod
    def _create_virtual_agent(cls, agent_name: str, config: Dict[str, any]) -> AutomagikAgent:
        """Create a virtual agent from database configuration.
        
        Args:
            agent_name: Name of the virtual agent
            config: Agent configuration dictionary
            
        Returns:
            AutomagikAgent instance configured from database
        """
        logger.info(f"Creating virtual agent: {agent_name}")
        
        try:
            # Create AutomagikAgent instance with virtual config
            agent = AutomagikAgent(config)
            agent.name = agent_name
            
            # Set up dependencies for virtual agent
            cls._setup_virtual_dependencies(agent, config)
            
            # Set up tools from tool_config if provided
            tool_config = config.get("tool_config", {})
            if tool_config:
                cls._setup_virtual_tools(agent, tool_config)
            
            # Set up model from config
            cls._setup_model_selection(agent, config)
            
            logger.info(f"Successfully created virtual agent: {agent_name}")
            return agent
            
        except Exception as e:
            logger.error(f"Error creating virtual agent {agent_name}: {str(e)}")
            logger.error(traceback.format_exc())
            # Return placeholder agent with error info
            return PlaceholderAgent({
                "name": f"{agent_name}_virtual_error",
                "error": f"Failed to create virtual agent: {str(e)}"
            })
    
    @classmethod
    def _setup_virtual_tools(cls, agent: AutomagikAgent, tool_config: Dict[str, any]) -> None:
        """Set up tools for a virtual agent from configuration.
        
        Args:
            agent: The AutomagikAgent instance
            tool_config: Tool configuration dictionary
        """
        enabled_tools = tool_config.get("enabled_tools", [])
        permissions = tool_config.get("tool_permissions", {})
        
        logger.debug(f"Setting up virtual agent tools: {enabled_tools}")
        
        # Load tools by name from the tool registry
        for tool_name in enabled_tools:
            try:
                # Get tool from registry and apply permissions
                tool_permissions = permissions.get(tool_name, {})
                logger.debug(f"Registering tool {tool_name} with permissions: {tool_permissions}")
                
                # For now, just log the tools - actual tool registration would happen
                # in the agent initialization where tools are loaded
                # This is a placeholder for the full tool integration
                
            except Exception as e:
                logger.warning(f"Failed to register tool {tool_name}: {str(e)}")
    
    @classmethod
    def _setup_model_selection(cls, agent: AutomagikAgent, config: Dict[str, any]) -> None:
        """Set up model selection for a virtual agent.
        
        Args:
            agent: The AutomagikAgent instance
            config: Agent configuration dictionary
        """
        # Check for class-level model override (future Model Descriptor Pattern)
        if hasattr(agent.__class__, 'model'):
            if callable(agent.__class__.model):
                model = agent.__class__.model(agent, config)
                logger.debug(f"Using callable model selector: {model}")
            else:
                model = agent.__class__.model
                logger.debug(f"Using class-level model: {model}")
        else:
            # Use model from virtual agent config
            model = config.get("default_model", "openai:gpt-4o-mini")
            logger.debug(f"Using config model: {model}")
        
        # Update the agent's model configuration
        if hasattr(agent, 'config') and hasattr(agent.config, 'model'):
            agent.config.model = model
        elif hasattr(agent, 'config'):
            agent.config.config["model"] = model
    
    @classmethod
    def _setup_virtual_dependencies(cls, agent: AutomagikAgent, config: Dict[str, any]) -> None:
        """Set up dependencies for a virtual agent.
        
        Args:
            agent: The AutomagikAgent instance
            config: Agent configuration dictionary
        """
        try:
            from automagik.agents.models.dependencies import AutomagikAgentsDependencies
            
            # Get model for dependencies
            model = config.get("default_model", "openai:gpt-4o-mini")
            
            # Create dependencies instance
            dependencies = AutomagikAgentsDependencies(
                model_name=model,
                model_settings={},
                api_keys={},
                tool_config=config.get("tool_config", {})
            )
            
            # Set dependencies on agent
            agent.set_dependencies(dependencies)
            logger.debug(f"Set up dependencies for virtual agent with model: {model}")
            
        except Exception as e:
            logger.error(f"Error setting up virtual agent dependencies: {str(e)}")
            logger.error(traceback.format_exc())
