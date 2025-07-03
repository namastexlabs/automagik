"""Agent repository functions for database operations."""

import uuid
import json
import logging
from typing import List, Optional, Dict

from automagik.db.connection import execute_query
from automagik.db.models import Agent
from automagik.utils.version import SERVICE_INFO

# Configure logger
logger = logging.getLogger(__name__)


def get_agent(agent_id: int) -> Optional[Agent]:
    """Get an agent by ID.
    
    Args:
        agent_id: The agent ID
        
    Returns:
        Agent object if found, None otherwise
    """
    try:
        result = execute_query(
            "SELECT * FROM agents WHERE id = %s",
            (agent_id,)
        )
        return Agent.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {str(e)}")
        return None


def get_agent_by_name(name: str) -> Optional[Agent]:
    """Get an agent by name.
    
    Args:
        name: The agent name
        
    Returns:
        Agent object if found, None otherwise
    """
    try:
        result = execute_query(
            "SELECT * FROM agents WHERE name = %s",
            (name,)
        )
        return Agent.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting agent by name {name}: {str(e)}")
        return None


def list_agents(active_only: bool = True) -> List[Agent]:
    """List all agents.
    
    Args:
        active_only: Whether to only include active agents
        
    Returns:
        List of Agent objects
    """
    try:
        if active_only:
            result = execute_query(
                "SELECT * FROM agents WHERE active = %s ORDER BY name",
                (True,)
            )
        else:
            result = execute_query(
                "SELECT * FROM agents ORDER BY name"
            )
        return [Agent.from_db_row(row) for row in result]
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        return []


def create_agent(agent: Agent) -> Optional[int]:
    """Create a new agent.
    
    Args:
        agent: The agent to create
        
    Returns:
        The created agent ID if successful, None otherwise
    """
    try:
        # Check if agent with this name already exists
        existing = get_agent_by_name(agent.name)
        if existing:
            # Update existing agent
            agent.id = existing.id
            return update_agent(agent)
        
        # Prepare the agent for insertion
        if not agent.version:
            agent.version = SERVICE_INFO.get("version", "0.1.0")
        
        config_json = json.dumps(agent.config) if agent.config else None
        
        # Insert the agent
        result = execute_query(
            """
            INSERT INTO agents (
                name, type, model, description, 
                config, version, active, run_id,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, 
                %s, %s, %s, %s,
                NOW(), NOW()
            ) RETURNING id
            """,
            (
                agent.name,
                agent.type,
                agent.model,
                agent.description,
                config_json,
                agent.version,
                agent.active,
                agent.run_id
            )
        )
        
        agent_id = result[0]["id"] if result else None
        logger.info(f"Created agent {agent.name} with ID {agent_id}")
        return agent_id
    except Exception as e:
        logger.error(f"Error creating agent {agent.name}: {str(e)}")
        return None


def update_agent(agent: Agent) -> Optional[int]:
    """Update an existing agent.
    
    Args:
        agent: The agent to update
        
    Returns:
        The updated agent ID if successful, None otherwise
    """
    try:
        if not agent.id:
            existing = get_agent_by_name(agent.name)
            if existing:
                agent.id = existing.id
            else:
                return create_agent(agent)
        
        config_json = json.dumps(agent.config) if agent.config else None
        
        execute_query(
            """
            UPDATE agents SET 
                name = %s,
                type = %s,
                model = %s,
                description = %s,
                config = %s,
                version = %s,
                active = %s,
                run_id = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                agent.name,
                agent.type,
                agent.model,
                agent.description,
                config_json,
                agent.version,
                agent.active,
                agent.run_id,
                agent.id
            ),
            fetch=False
        )
        
        logger.info(f"Updated agent {agent.name} with ID {agent.id}")
        return agent.id
    except Exception as e:
        logger.error(f"Error updating agent {agent.name}: {str(e)}")
        return None


def delete_agent(agent_id: int) -> bool:
    """Delete an agent.
    
    Args:
        agent_id: The agent ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "DELETE FROM agents WHERE id = %s",
            (agent_id,),
            fetch=False
        )
        logger.info(f"Deleted agent with ID {agent_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting agent {agent_id}: {str(e)}")
        return False


def register_agent(name: str, agent_type: str, model: str, description: Optional[str] = None, config: Optional[Dict] = None) -> Optional[int]:
    """Register an agent in the database or update an existing one.
    
    Args:
        name: The agent name (used as-is, no normalization)
        agent_type: The agent type (will be stored in the 'type' column)
        model: The model used by the agent
        description: Optional description
        config: Optional configuration dictionary
        
    Returns:
        The agent ID if successful, None otherwise
    """
    try:
        # Use the name as-is, no normalization
        agent_name = name
        
        # Validate agent name - check if it's a variation of an existing agent
        # Get all existing agents to check against
        existing_agents = list_agents(active_only=False)
        
        # Check if this agent name is a variation of an existing agent
        for existing in existing_agents:
            # Check if the new name is the existing name with "agent" suffix
            if agent_name.lower() == f"{existing.name.lower()}agent":
                logger.warning(f"Blocked registration of '{agent_name}' - variation of existing agent '{existing.name}'")
                # Return the existing agent's ID instead
                return existing.id
            
            # Check if the new name is the existing name with "-agent" suffix  
            if agent_name.lower() == f"{existing.name.lower()}-agent":
                logger.warning(f"Blocked registration of '{agent_name}' - variation of existing agent '{existing.name}'")
                # Return the existing agent's ID instead
                return existing.id
                
            # Check if the new name is the existing name with "_agent" suffix
            if agent_name.lower() == f"{existing.name.lower()}_agent":
                logger.warning(f"Blocked registration of '{agent_name}' - variation of existing agent '{existing.name}'")
                # Return the existing agent's ID instead
                return existing.id
        
        # Check for existing agent with the exact name
        existing = get_agent_by_name(agent_name)
        
        if existing:
            # Update existing agent
            logger.info(f"Found existing agent with name {existing.name} (ID: {existing.id})")
            
            existing.type = agent_type
            existing.model = model
            existing.description = description or existing.description
            if config:
                existing.config = config
                
            # Use update_agent
            return update_agent(existing)
        
        # Create new agent with the provided name
        logger.info(f"Creating new agent with name: {agent_name}")
        
        # Serialize config to JSON if needed
        config_json = json.dumps(config) if config else None
        
        # Insert new agent
        result = execute_query(
            """
            INSERT INTO agents (
                name, type, model, description, config, active, 
                version, run_id, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, true, 
                %s, 1, NOW(), NOW()
            ) RETURNING id
            """,
            (
                agent_name, 
                agent_type, 
                model, 
                description,
                config_json, 
                "1.0.0"  # Default version
            )
        )
        
        if result:
            agent_id = result[0]["id"]
            logger.info(f"Registered agent {agent_name} with ID {agent_id}")
            return agent_id
        
        return None
    except Exception as e:
        logger.error(f"Error registering agent {name}: {str(e)}")
        return None


def increment_agent_run_id(agent_id: int) -> bool:
    """Increment the run_id of an agent.
    
    Args:
        agent_id: The agent ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "UPDATE agents SET run_id = run_id + 1, updated_at = NOW() WHERE id = %s",
            (agent_id,),
            fetch=False
        )
        logger.info(f"Incremented run_id for agent {agent_id}")
        return True
    except Exception as e:
        logger.error(f"Error incrementing run_id for agent {agent_id}: {str(e)}")
        return False


def link_session_to_agent(session_id: uuid.UUID, agent_id: int) -> bool:
    """Link a session to an agent in the database.
    
    Args:
        session_id: The session ID
        agent_id: The agent ID
        
    Returns:
        True on success, False on failure
    """
    try:
        # Check if agent exists
        agent = get_agent(agent_id)
        if not agent:
            logger.error(f"Cannot link session to non-existent agent {agent_id}")
            return False
        
        # Import here to avoid circular imports
        from automagik.db.repository.session import get_session
        
        # First, check if this session is already linked to this agent in the session table
        # This avoids unnecessary updates to messages
        session = get_session(session_id)
        
        # If session is already linked to this agent, no need to update anything
        if session and session.agent_id == agent_id:
            logger.debug(f"Session {session_id} already associated with agent {agent_id}, skipping updates")
            return True
            
        # Check if any messages in this session need updating
        message_count = execute_query(
            """
            SELECT COUNT(*) as count FROM messages 
            WHERE session_id = %s AND (agent_id IS NULL OR agent_id != %s)
            """,
            (str(session_id), agent_id)
        )
        
        needs_update = message_count and message_count[0]["count"] > 0
        
        if needs_update:
            # Only update messages that don't already have the correct agent_id
            execute_query(
                """
                UPDATE messages
                SET agent_id = %s
                WHERE session_id = %s AND (agent_id IS NULL OR agent_id != %s)
                """,
                (agent_id, str(session_id), agent_id),
                fetch=False
            )
            logger.debug(f"Updated {message_count[0]['count']} messages to associate with agent {agent_id}")
        else:
            logger.debug(f"No messages need updating for session {session_id}")
        
        # Update the sessions table with the agent_id
        execute_query(
            """
            UPDATE sessions
            SET agent_id = %s, updated_at = NOW()
            WHERE id = %s AND (agent_id IS NULL OR agent_id != %s)
            """,
            (agent_id, str(session_id), agent_id),
            fetch=False
        )
        logger.debug(f"Updated sessions table with agent_id {agent_id} for session {session_id}")
        
        logger.info(f"Session {session_id} associated with agent {agent_id} in database")
        return True
    except Exception as e:
        logger.error(f"Error linking session {session_id} to agent {agent_id}: {str(e)}")
        return False


def update_agent_active_prompt_id(agent_id: int, prompt_id: int) -> bool:
    """Update the active_default_prompt_id for an agent.
    
    Args:
        agent_id: The agent ID
        prompt_id: The prompt ID to set as active default
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            """
            UPDATE agents SET
                active_default_prompt_id = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (prompt_id, agent_id),
            fetch=False
        )
        logger.info(f"Updated agent {agent_id} with active_default_prompt_id {prompt_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating agent {agent_id} active prompt: {str(e)}")
        return False
