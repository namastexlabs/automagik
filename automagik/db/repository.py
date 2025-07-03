"""Repository functions for database operations."""

import uuid
import json
import logging
from typing import List, Optional, Union, Tuple

from automagik.db.connection import execute_query
from automagik.db.models import Agent, User, Session, Message, Memory
from automagik.utils.version import SERVICE_INFO

# Configure logger
logger = logging.getLogger(__name__)

#
# Agent Repository Functions
#

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
                "SELECT * FROM agents WHERE active = TRUE ORDER BY name"
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
                config, version, active, run_id, system_prompt,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, 
                %s, %s, %s, %s, %s,
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
                agent.run_id,
                agent.system_prompt
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
                system_prompt = %s,
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
                agent.system_prompt,
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
    """Delete an agent from the database.
    
    Args:
        agent_id: The agent ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query("DELETE FROM agents WHERE id = %s", (agent_id,), fetch=False)
        logger.info(f"Deleted agent {agent_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting agent {agent_id}: {str(e)}")
        return False

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


#
# User Repository Functions
#

def get_user(user_id: int) -> Optional[User]:
    """Get a user by ID.
    
    Args:
        user_id: The user ID
        
    Returns:
        User object if found, None otherwise
    """
    try:
        result = execute_query(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        return User.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        return None


def get_user_by_email(email: str) -> Optional[User]:
    """Get a user by email.
    
    Args:
        email: The user email
        
    Returns:
        User object if found, None otherwise
    """
    try:
        result = execute_query(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )
        return User.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting user by email {email}: {str(e)}")
        return None


def get_user_by_identifier(identifier: str) -> Optional[User]:
    """Get a user by ID, email, or phone number.
    
    Args:
        identifier: The user ID, email, or phone number
        
    Returns:
        User object if found, None otherwise
    """
    try:
        # First check if it's an ID
        if identifier.isdigit():
            return get_user(int(identifier))
        
        # Try email
        user = get_user_by_email(identifier)
        if user:
            return user
        
        # Try phone number
        result = execute_query(
            "SELECT * FROM users WHERE phone_number = %s",
            (identifier,)
        )
        return User.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting user by identifier {identifier}: {str(e)}")
        return None


def list_users(page: int = 1, page_size: int = 100) -> Tuple[List[User], int]:
    """List users with pagination.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Tuple of (list of User objects, total count)
    """
    try:
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get total count
        count_result = execute_query("SELECT COUNT(*) as count FROM users")
        total_count = count_result[0]["count"]
        
        # Get paginated results
        result = execute_query(
            "SELECT * FROM users ORDER BY id LIMIT %s OFFSET %s",
            (page_size, offset)
        )
        
        users = [User.from_db_row(row) for row in result]
        return users, total_count
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return [], 0


def create_user(user: User) -> Optional[int]:
    """Create a new user.
    
    Args:
        user: The user to create
        
    Returns:
        The created user ID if successful, None otherwise
    """
    try:
        # Check if user with this email already exists
        if user.email:
            existing = get_user_by_email(user.email)
            if existing:
                # Update existing user
                user.id = existing.id
                return update_user(user)
        
        # Prepare user data
        user_data_json = json.dumps(user.user_data) if user.user_data else None
        
        # Insert the user
        result = execute_query(
            """
            INSERT INTO users (
                email, phone_number, user_data, created_at, updated_at
            ) VALUES (
                %s, %s, %s, NOW(), NOW()
            ) RETURNING id
            """,
            (
                user.email,
                user.phone_number,
                user_data_json
            )
        )
        
        user_id = result[0]["id"] if result else None
        logger.info(f"Created user with ID {user_id}")
        return user_id
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return None


def update_user(user: User) -> Optional[int]:
    """Update an existing user.
    
    Args:
        user: The user to update
        
    Returns:
        The updated user ID if successful, None otherwise
    """
    try:
        if not user.id:
            if user.email:
                existing = get_user_by_email(user.email)
                if existing:
                    user.id = existing.id
                else:
                    return create_user(user)
            else:
                return create_user(user)
        
        user_data_json = json.dumps(user.user_data) if user.user_data else None
        
        execute_query(
            """
            UPDATE users SET 
                email = %s,
                phone_number = %s,
                user_data = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                user.email,
                user.phone_number,
                user_data_json,
                user.id
            ),
            fetch=False
        )
        
        logger.info(f"Updated user with ID {user.id}")
        return user.id
    except Exception as e:
        logger.error(f"Error updating user {user.id}: {str(e)}")
        return None


def delete_user(user_id: int) -> bool:
    """Delete a user.
    
    Args:
        user_id: The user ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "DELETE FROM users WHERE id = %s",
            (user_id,),
            fetch=False
        )
        logger.info(f"Deleted user with ID {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return False


#
# Session Repository Functions
#

def get_session(session_id: uuid.UUID) -> Optional[Session]:
    """Get a session by ID.
    
    Args:
        session_id: The session ID
        
    Returns:
        Session object if found, None otherwise
    """
    try:
        result = execute_query(
            "SELECT * FROM sessions WHERE id = %s",
            (str(session_id),)
        )
        return Session.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {str(e)}")
        return None


def get_session_by_name(name: str) -> Optional[Session]:
    """Get a session by name.
    
    Args:
        name: The session name
        
    Returns:
        Session object if found, None otherwise
    """
    try:
        result = execute_query(
            "SELECT * FROM sessions WHERE name = %s",
            (name,)
        )
        return Session.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting session by name {name}: {str(e)}")
        return None


def list_sessions(
    user_id: Optional[int] = None, 
    agent_id: Optional[int] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    sort_desc: bool = True
) -> Union[List[Session], Tuple[List[Session], int]]:
    """List sessions with optional filtering and pagination.
    
    Args:
        user_id: Filter by user ID
        agent_id: Filter by agent ID
        page: Page number (1-based, optional)
        page_size: Number of items per page (optional)
        sort_desc: Sort by most recent first if True
        
    Returns:
        If pagination is requested (page and page_size provided):
            Tuple of (list of Session objects, total count)
        Otherwise:
            List of Session objects
    """
    try:
        count_query = "SELECT COUNT(*) as count FROM sessions"
        query = "SELECT * FROM sessions"
        params = []
        conditions = []
        
        if user_id is not None:
            conditions.append("user_id = %s")
            params.append(user_id)
        
        if agent_id is not None:
            conditions.append("agent_id = %s")
            params.append(agent_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            count_query += " WHERE " + " AND ".join(conditions)
        
        # Add sorting
        sort_direction = "DESC" if sort_desc else "ASC"
        query += f" ORDER BY updated_at {sort_direction}, created_at {sort_direction}"
        
        # Get total count for pagination
        count_result = execute_query(count_query, tuple(params) if params else None)
        total_count = count_result[0]['count'] if count_result else 0
        
        # Add pagination if requested
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query += " LIMIT %s OFFSET %s"
            params.append(page_size)
            params.append(offset)
        
        result = execute_query(query, tuple(params) if params else None)
        sessions = [Session.from_db_row(row) for row in result]
        
        # Return with count for pagination or just the list
        if page is not None and page_size is not None:
            return sessions, total_count
        return sessions
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        if page is not None and page_size is not None:
            return [], 0
        return []


def create_session(session: Session) -> Optional[uuid.UUID]:
    """Create a new session.
    
    Args:
        session: The session to create
        
    Returns:
        The created session ID if successful, None otherwise
    """
    try:
        # Check if a session with this name already exists
        if session.name:
            existing = get_session_by_name(session.name)
            if existing:
                # Update existing session
                session.id = existing.id
                return update_session(session)
        
        # Ensure session has an ID
        if session.id is None:
            session.id = uuid.uuid4()
            logger.info(f"Generated new UUID for session: {session.id}")
        
        # Prepare session data
        metadata_json = json.dumps(session.metadata) if session.metadata else None
        
        # Use provided ID or let the database generate one
        session_id_param = str(session.id) if session.id else None
        
        # Insert the session
        result = execute_query(
            """
            INSERT INTO sessions (
                id, user_id, agent_id, name, platform,
                metadata, created_at, updated_at, run_finished_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, NOW(), NOW(), %s
            ) RETURNING id
            """,
            (
                session_id_param,
                session.user_id,
                session.agent_id,
                session.name,
                session.platform,
                metadata_json,
                session.run_finished_at
            )
        )
        
        session_id = uuid.UUID(result[0]["id"]) if result else None
        logger.info(f"Created session with ID {session_id}")
        return session_id
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return None


def update_session(session: Session) -> Optional[uuid.UUID]:
    """Update an existing session.
    
    Args:
        session: The session to update
        
    Returns:
        The updated session ID if successful, None otherwise
    """
    try:
        if not session.id:
            if session.name:
                existing = get_session_by_name(session.name)
                if existing:
                    session.id = existing.id
                else:
                    return create_session(session)
            else:
                return create_session(session)
        
        metadata_json = json.dumps(session.metadata) if session.metadata else None
        
        execute_query(
            """
            UPDATE sessions SET 
                user_id = %s,
                agent_id = %s,
                name = %s,
                platform = %s,
                metadata = %s,
                updated_at = NOW(),
                run_finished_at = %s
            WHERE id = %s
            """,
            (
                session.user_id,
                session.agent_id,
                session.name,
                session.platform,
                metadata_json,
                session.run_finished_at,
                str(session.id)
            ),
            fetch=False
        )
        
        logger.info(f"Updated session with ID {session.id}")
        return session.id
    except Exception as e:
        logger.error(f"Error updating session {session.id}: {str(e)}")
        return None


def delete_session(session_id: uuid.UUID) -> bool:
    """Delete a session.
    
    Args:
        session_id: The session ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "DELETE FROM sessions WHERE id = %s",
            (str(session_id),),
            fetch=False
        )
        logger.info(f"Deleted session with ID {session_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        return False


def finish_session(session_id: uuid.UUID) -> bool:
    """Mark a session as finished.
    
    Args:
        session_id: The session ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "UPDATE sessions SET run_finished_at = NOW(), updated_at = NOW() WHERE id = %s",
            (str(session_id),),
            fetch=False
        )
        logger.info(f"Marked session {session_id} as finished")
        return True
    except Exception as e:
        logger.error(f"Error finishing session {session_id}: {str(e)}")
        return False


#
# Memory Repository Functions
#

def get_memory(memory_id: uuid.UUID) -> Optional[Memory]:
    """Get a memory by ID.
    
    Args:
        memory_id: The memory ID
        
    Returns:
        Memory object if found, None otherwise
    """
    try:
        result = execute_query(
            """
            SELECT id, name, description, content, session_id, user_id, agent_id,
                   read_mode, access, metadata, created_at, updated_at
            FROM memories 
            WHERE id = %s
            """,
            (str(memory_id),)
        )
        return Memory.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting memory {memory_id}: {str(e)}")
        return None


def get_memory_by_name(name: str, agent_id: Optional[int] = None, 
                      user_id: Optional[int] = None, 
                      session_id: Optional[uuid.UUID] = None) -> Optional[Memory]:
    """Get a memory by name with optional filters for agent, user, and session.
    
    Args:
        name: The memory name
        agent_id: Optional agent ID filter
        user_id: Optional user ID filter
        session_id: Optional session ID filter
        
    Returns:
        Memory object if found, None otherwise
    """
    try:
        query = """
            SELECT id, name, description, content, session_id, user_id, agent_id,
                   read_mode, access, metadata, created_at, updated_at
            FROM memories 
            WHERE name = %s
        """
        params = [name]
        
        # Add optional filters
        if agent_id is not None:
            query += " AND agent_id = %s"
            params.append(agent_id)
        if user_id is not None:
            query += " AND user_id = %s"
            params.append(user_id)
        if session_id is not None:
            query += " AND session_id = %s"
            params.append(str(session_id))
            
        query += " LIMIT 1"
        
        result = execute_query(query, params)
        return Memory.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting memory by name {name}: {str(e)}")
        return None


def list_memories(agent_id: Optional[int] = None, 
                 user_id: Optional[int] = None, 
                 session_id: Optional[uuid.UUID] = None,
                 read_mode: Optional[str] = None,
                 name_pattern: Optional[str] = None) -> List[Memory]:
    """List memories with optional filters.
    
    Args:
        agent_id: Optional agent ID filter
        user_id: Optional user ID filter
        session_id: Optional session ID filter
        read_mode: Optional read mode filter
        name_pattern: Optional name pattern to match (using ILIKE)
        
    Returns:
        List of Memory objects
    """
    try:
        query = """
            SELECT id, name, description, content, session_id, user_id, agent_id,
                   read_mode, access, metadata, created_at, updated_at
            FROM memories 
            WHERE 1=1
        """
        params = []
        
        # Add optional filters
        if agent_id is not None:
            query += " AND agent_id = %s"
            params.append(agent_id)
        if user_id is not None:
            query += " AND user_id = %s"
            params.append(user_id)
        if session_id is not None:
            query += " AND session_id = %s"
            params.append(str(session_id))
        if read_mode is not None:
            query += " AND read_mode = %s"
            params.append(read_mode)
        if name_pattern is not None:
            query += " AND name ILIKE %s"
            params.append(f"%{name_pattern}%")
            
        query += " ORDER BY name ASC"
        
        result = execute_query(query, params)
        return [Memory.from_db_row(row) for row in result] if result else []
    except Exception as e:
        logger.error(f"Error listing memories: {str(e)}")
        return []


def create_memory(memory: Memory) -> Optional[uuid.UUID]:
    """Create a new memory or update an existing one.
    
    Args:
        memory: The memory to create
        
    Returns:
        The memory ID if successful, None otherwise
    """
    try:
        # Check if a memory with this name already exists for the same context
        if memory.name:
            query = "SELECT id FROM memories WHERE name = %s"
            params = [memory.name]
            
            # Add optional filters
            if memory.agent_id is not None:
                query += " AND agent_id = %s"
                params.append(memory.agent_id)
            if memory.user_id is not None:
                query += " AND user_id = %s"
                params.append(memory.user_id)
            if memory.session_id is not None:
                query += " AND session_id = %s"
                params.append(str(memory.session_id))
                
            result = execute_query(query, params)
            
            if result:
                # Update existing memory
                memory.id = result[0]["id"]
                return update_memory(memory)
        
        # Generate a UUID for the memory if not provided
        if not memory.id:
            memory.id = uuid.uuid4()
        
        # Prepare memory data
        metadata_json = json.dumps(memory.metadata) if memory.metadata else None
        
        # Insert the memory
        result = execute_query(
            """
            INSERT INTO memories (
                id, name, description, content, session_id, user_id, agent_id,
                read_mode, access, metadata, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, NOW(), NOW()
            ) RETURNING id
            """,
            (
                str(memory.id),
                memory.name,
                memory.description,
                memory.content,
                str(memory.session_id) if memory.session_id else None,
                memory.user_id,
                memory.agent_id,
                memory.read_mode,
                memory.access,
                metadata_json
            )
        )
        
        memory_id = uuid.UUID(result[0]["id"]) if result else None
        logger.info(f"Created memory {memory.name} with ID {memory_id}")
        return memory_id
    except Exception as e:
        logger.error(f"Error creating memory {memory.name}: {str(e)}")
        return None


def update_memory(memory: Memory) -> Optional[uuid.UUID]:
    """Update an existing memory.
    
    Args:
        memory: The memory to update
        
    Returns:
        The updated memory ID if successful, None otherwise
    """
    try:
        if not memory.id:
            # Try to find by name and context
            query = "SELECT id FROM memories WHERE name = %s"
            params = [memory.name]
            
            # Add optional filters
            if memory.agent_id is not None:
                query += " AND agent_id = %s"
                params.append(memory.agent_id)
            if memory.user_id is not None:
                query += " AND user_id = %s"
                params.append(memory.user_id)
            if memory.session_id is not None:
                query += " AND session_id = %s"
                params.append(str(memory.session_id))
                
            result = execute_query(query, params)
            
            if result:
                memory.id = result[0]["id"]
            else:
                return create_memory(memory)
        
        # Prepare memory data
        metadata_json = json.dumps(memory.metadata) if memory.metadata else None
        
        execute_query(
            """
            UPDATE memories SET 
                name = %s,
                description = %s,
                content = %s,
                session_id = %s,
                user_id = %s,
                agent_id = %s,
                read_mode = %s,
                access = %s,
                metadata = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                memory.name,
                memory.description,
                memory.content,
                str(memory.session_id) if memory.session_id else None,
                memory.user_id,
                memory.agent_id,
                memory.read_mode,
                memory.access,
                metadata_json,
                str(memory.id)
            ),
            fetch=False
        )
        
        logger.info(f"Updated memory {memory.name} with ID {memory.id}")
        return memory.id
    except Exception as e:
        logger.error(f"Error updating memory {memory.id}: {str(e)}")
        return None


def delete_memory(memory_id: uuid.UUID) -> bool:
    """Delete a memory.
    
    Args:
        memory_id: The memory ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "DELETE FROM memories WHERE id = %s",
            (str(memory_id),),
            fetch=False
        )
        logger.info(f"Deleted memory with ID {memory_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting memory {memory_id}: {str(e)}")
        return False


#
# Message Repository Functions
#

def create_message(message: Message) -> Optional[uuid.UUID]:
    """Create a new message.
    
    Args:
        message: The message to create
        
    Returns:
        The created message ID if successful, None otherwise
    """
    try:
        # Generate ID if not provided
        if not message.id:
            message.id = uuid.uuid4()
            
        # Handle JSON fields
        raw_payload_json = json.dumps(message.raw_payload) if message.raw_payload else None
        tool_calls_json = json.dumps(message.tool_calls) if message.tool_calls else None
        tool_outputs_json = json.dumps(message.tool_outputs) if message.tool_outputs else None
        context_json = json.dumps(message.context) if message.context else None
        
        execute_query(
            """
            INSERT INTO messages (
                id, session_id, user_id, agent_id, role, 
                text_content, media_url, mime_type, message_type,
                raw_payload, tool_calls, tool_outputs, 
                system_prompt, user_feedback, flagged, context,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, 
                %s, %s, %s, %s,
                %s, %s, %s, 
                %s, %s, %s, %s,
                NOW(), NOW()
            )
            """,
            (
                str(message.id), 
                str(message.session_id) if message.session_id else None,
                message.user_id,
                message.agent_id,
                message.role,
                message.text_content,
                message.media_url,
                message.mime_type,
                message.message_type,
                raw_payload_json,
                tool_calls_json,
                tool_outputs_json,
                message.system_prompt,
                message.user_feedback,
                message.flagged,
                context_json,
            ),
            fetch=False
        )
        
        logger.info(f"Created message with ID {message.id}")
        return message.id
    except Exception as e:
        logger.error(f"Error creating message: {str(e)}")
        return None


def get_message(message_id: uuid.UUID) -> Optional[Message]:
    """Get a message by ID.
    
    Args:
        message_id: The message ID
        
    Returns:
        Message object if found, None otherwise
    """
    try:
        result = execute_query(
            "SELECT * FROM messages WHERE id = %s",
            (str(message_id),)
        )
        return Message.from_db_row(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting message {message_id}: {str(e)}")
        return None


def list_messages(session_id: uuid.UUID, limit: int = 100, offset: int = 0, sort_desc: bool = False) -> List[Message]:
    """List messages for a session with pagination.
    
    Args:
        session_id: The session ID
        limit: Maximum number of messages to retrieve (default: 100)
        offset: Number of messages to skip (default: 0)
        sort_desc: Whether to sort by descending creation time (newest first)
        
    Returns:
        List of Message objects
    """
    try:
        # Set sort order
        sort_direction = "DESC" if sort_desc else "ASC"
        
        result = execute_query(
            f"""
            SELECT * FROM messages 
            WHERE session_id = %s
            ORDER BY created_at {sort_direction}, updated_at {sort_direction}
            LIMIT %s OFFSET %s
            """,
            (str(session_id), limit, offset)
        )
        
        messages = []
        for row in result:
            message = Message.from_db_row(row)
            if message:
                messages.append(message)
                
        return messages
    except Exception as e:
        logger.error(f"Error listing messages for session {session_id}: {str(e)}")
        return []


def list_messages_for_user(session_id: uuid.UUID, user_id: Optional[uuid.UUID] = None, 
                          offset: int = 0, limit: Optional[int] = None, 
                          sort_desc: bool = False) -> List[Message]:
    """List messages for a session, optionally filtered by user_id.
    
    Args:
        session_id: The UUID of the session
        user_id: Optional user UUID to filter messages (None returns all users)
        offset: Number of messages to skip
        limit: Maximum number of messages to return (None for all)
        sort_desc: Sort by descending created_at if True
        
    Returns:
        List of Message objects
    """
    from automagik.db.repository.message import list_messages_for_user as _list_messages_for_user
    return _list_messages_for_user(session_id, user_id, offset, limit, sort_desc)


def update_message(message: Message) -> Optional[uuid.UUID]:
    """Update a message.
    
    Args:
        message: The message to update
        
    Returns:
        The updated message ID if successful, None otherwise
    """
    try:
        if not message.id:
            return create_message(message)
            
        # Handle JSON fields
        raw_payload_json = json.dumps(message.raw_payload) if message.raw_payload else None
        tool_calls_json = json.dumps(message.tool_calls) if message.tool_calls else None
        tool_outputs_json = json.dumps(message.tool_outputs) if message.tool_outputs else None
        context_json = json.dumps(message.context) if message.context else None
        
        execute_query(
            """
            UPDATE messages SET 
                session_id = %s,
                user_id = %s,
                agent_id = %s,
                role = %s,
                text_content = %s,
                media_url = %s,
                mime_type = %s,
                message_type = %s,
                raw_payload = %s,
                tool_calls = %s,
                tool_outputs = %s,
                system_prompt = %s,
                user_feedback = %s,
                flagged = %s,
                context = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                str(message.session_id) if message.session_id else None,
                message.user_id,
                message.agent_id,
                message.role,
                message.text_content,
                message.media_url,
                message.mime_type,
                message.message_type,
                raw_payload_json,
                tool_calls_json,
                tool_outputs_json,
                message.system_prompt,
                message.user_feedback,
                message.flagged,
                context_json,
                str(message.id)
            ),
            fetch=False
        )
        
        logger.info(f"Updated message with ID {message.id}")
        return message.id
    except Exception as e:
        logger.error(f"Error updating message {message.id}: {str(e)}")
        return None


def delete_message(message_id: uuid.UUID) -> bool:
    """Delete a message.
    
    Args:
        message_id: The message ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        execute_query(
            "DELETE FROM messages WHERE id = %s",
            (str(message_id),),
            fetch=False
        )
        logger.info(f"Deleted message with ID {message_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting message {message_id}: {str(e)}")
        return False


def get_system_prompt(session_id: uuid.UUID) -> Optional[str]:
    """Get the system prompt for a session.
    
    Args:
        session_id: The session ID
        
    Returns:
        The system prompt if found, None otherwise
    """
    try:
        # First check if system prompt is stored in session metadata
        session_result = execute_query(
            """
            SELECT metadata FROM sessions 
            WHERE id = %s
            """,
            (str(session_id),)
        )
        
        if session_result and session_result[0]["metadata"]:
            metadata = session_result[0]["metadata"]
            
            # Log metadata format for debugging
            logger.debug(f"Session metadata type: {type(metadata)}")
            
            if isinstance(metadata, dict) and "system_prompt" in metadata:
                system_prompt = metadata["system_prompt"]
                logger.debug(f"Found system prompt in session metadata (dict): {system_prompt[:50]}...")
                return system_prompt
            elif isinstance(metadata, str):
                try:
                    metadata_dict = json.loads(metadata)
                    if "system_prompt" in metadata_dict:
                        system_prompt = metadata_dict["system_prompt"]
                        logger.debug(f"Found system prompt in session metadata (string->dict): {system_prompt[:50]}...")
                        return system_prompt
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse session metadata as JSON: {metadata[:100]}...")
                    # Continue to fallback
            
            # If we got here but couldn't find a system prompt, log the metadata for debugging
            logger.debug(f"No system_prompt found in metadata: {str(metadata)[:100]}...")
        
        # Fallback: look for a system role message
        logger.debug("Falling back to system role message search")
        result = execute_query(
            """
            SELECT text_content FROM messages 
            WHERE session_id = %s AND role = 'system'
            ORDER BY created_at DESC, updated_at DESC
            LIMIT 1
            """,
            (str(session_id),)
        )
        
        if result and result[0]["text_content"]:
            system_prompt = result[0]["text_content"]
            logger.debug(f"Found system prompt in system role message: {system_prompt[:50]}...")
            return system_prompt
        
        logger.warning(f"No system prompt found for session {session_id}")
        return None
    except Exception as e:
        logger.error(f"Error getting system prompt for session {session_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None