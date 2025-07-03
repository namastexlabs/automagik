"""Repository modules for database operations.

This package contains the repository modules for each entity type in the database.
All repository functions are re-exported here for easier imports.
"""

# Agent repository functions
from automagik.db.repository.agent import (
    get_agent,
    get_agent_by_name,
    list_agents,
    create_agent,
    update_agent,
    delete_agent,
    increment_agent_run_id,
    link_session_to_agent,
    register_agent,
    update_agent_active_prompt_id
)

# User repository functions
from automagik.db.repository.user import (
    get_user,
    get_user_by_email,
    get_user_by_identifier,
    list_users,
    create_user,
    update_user,
    delete_user,
    ensure_default_user_exists
)

# Session repository functions
from automagik.db.repository.session import (
    get_session,
    get_session_by_name,
    list_sessions,
    create_session,
    update_session,
    delete_session,
    finish_session,
    update_session_name_if_empty
)

# Message repository functions
from automagik.db.repository.message import (
    get_message,
    list_messages,
    list_messages_for_user,
    count_messages,
    create_message,
    update_message,
    delete_message,
    delete_session_messages,
    list_session_messages,
    get_system_prompt
)

# Memory repository functions
from automagik.db.repository.memory import (
    get_memory,
    get_memory_by_name,
    list_memories,
    create_memory,
    update_memory,
    delete_memory,
    create_memories_bulk
)

# Prompt repository functions
from automagik.db.repository.prompt import (
    get_prompt_by_id,
    get_active_prompt,
    find_code_default_prompt,
    get_latest_version_for_status,
    create_prompt,
    update_prompt,
    set_prompt_active,
    get_prompts_by_agent_id,
    delete_prompt
)

# MCP repository functions (simplified architecture - NMSTX-253)
from automagik.db.repository.mcp import (
    get_mcp_config,
    get_mcp_config_by_name,
    list_mcp_configs,
    create_mcp_config,
    update_mcp_config,
    update_mcp_config_by_name,
    delete_mcp_config,
    delete_mcp_config_by_name,
    get_agent_mcp_configs,
    get_configs_by_server_type
)

# Workflow Process repository functions
from automagik.db.repository.workflow_process import (
    get_workflow_process,
    list_workflow_processes,
    create_workflow_process,
    update_workflow_process,
    delete_workflow_process,
    update_heartbeat,
    mark_process_terminated,
    get_running_processes,
    get_stale_processes,
    cleanup_old_processes
)

# Workflow Run repository functions
from automagik.db.repository.workflow_run import (
    create_workflow_run,
    get_workflow_run,
    get_workflow_run_by_run_id,
    update_workflow_run,
    update_workflow_run_by_run_id,
    list_workflow_runs,
    delete_workflow_run,
    get_workflow_runs_by_session,
    get_recent_workflow_runs
)

# Export all imported functions
__all__ = [
    # Agent functions
    "get_agent",
    "get_agent_by_name",
    "list_agents",
    "create_agent",
    "update_agent",
    "delete_agent",
    "increment_agent_run_id",
    "link_session_to_agent",
    "register_agent",
    "update_agent_active_prompt_id",
    
    # User functions
    "get_user",
    "get_user_by_email",
    "get_user_by_identifier",
    "list_users",
    "create_user",
    "update_user",
    "delete_user",
    "ensure_default_user_exists",
    
    # Session functions
    "get_session",
    "get_session_by_name",
    "list_sessions",
    "create_session",
    "update_session",
    "delete_session",
    "finish_session",
    "update_session_name_if_empty",
    
    # Message functions
    "get_message",
    "list_messages",
    "list_messages_for_user",
    "count_messages",
    "create_message",
    "update_message",
    "delete_message",
    "delete_session_messages",
    "list_session_messages",
    "get_system_prompt",
    
    # Memory functions
    "get_memory",
    "get_memory_by_name",
    "list_memories",
    "create_memory",
    "update_memory",
    "delete_memory",
    "create_memories_bulk",
    
    # Prompt functions
    "get_prompt_by_id",
    "get_active_prompt",
    "find_code_default_prompt",
    "get_latest_version_for_status",
    "create_prompt",
    "update_prompt",
    "set_prompt_active",
    "get_prompts_by_agent_id",
    "delete_prompt",
    
    # MCP functions (simplified architecture - NMSTX-253)
    "get_mcp_config",
    "get_mcp_config_by_name",
    "list_mcp_configs",
    "create_mcp_config",
    "update_mcp_config",
    "update_mcp_config_by_name",
    "delete_mcp_config",
    "delete_mcp_config_by_name",
    "get_agent_mcp_configs",
    "get_configs_by_server_type",
    
    # Workflow Process functions
    "get_workflow_process",
    "list_workflow_processes",
    "create_workflow_process",
    "update_workflow_process",
    "delete_workflow_process",
    "update_heartbeat",
    "mark_process_terminated",
    "get_running_processes",
    "get_stale_processes",
    "cleanup_old_processes",
    
    # Workflow Run functions
    "create_workflow_run",
    "get_workflow_run",
    "get_workflow_run_by_run_id",
    "update_workflow_run",
    "update_workflow_run_by_run_id",
    "list_workflow_runs",
    "delete_workflow_run",
    "get_workflow_runs_by_session",
    "get_recent_workflow_runs",
]
