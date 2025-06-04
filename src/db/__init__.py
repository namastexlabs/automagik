"""Database module for Automagik Agents.

This module provides a clean repository pattern for database operations,
with specialized repository functions for each entity type.
"""

# Export models
from src.db.models import (
    Agent,
    User,
    Session,
    Memory,
    Message
)

# Export connection utilities
from src.db.connection import (
    get_connection_pool,
    get_db_connection,
    get_db_cursor,
    execute_query,
    execute_batch
)

# Export all repository functions
from src.db.repository import (
    # Agent repository
    get_agent,
    get_agent_by_name,
    list_agents,
    create_agent,
    update_agent,
    delete_agent,
    increment_agent_run_id,
    link_session_to_agent,
    register_agent,
    
    # Session repository
    get_session,
    get_session_by_name,
    list_sessions,
    create_session,
    update_session,
    delete_session,
    finish_session,
    update_session_name_if_empty,
    
    # Message repository
    get_message,
    list_messages,
    count_messages,
    create_message,
    update_message,
    delete_message,
    delete_session_messages,
    list_session_messages,
    get_system_prompt,
    
    # Memory repository
    get_memory,
    get_memory_by_name,
    list_memories,
    create_memory,
    update_memory,
    delete_memory
)

# Import UUID-compatible user repository functions
from src.db.repository.user import (
    get_user,
    get_user_by_email,
    get_user_by_identifier,
    list_users,
    create_user,
    update_user,
    delete_user,
    ensure_default_user_exists,
)