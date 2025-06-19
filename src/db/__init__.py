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
    Message,
    MCPServerDB,
    AgentMCPServerDB,
    MCPConfig,
    MCPConfigCreate,
    MCPConfigUpdate,
    WorkflowProcess,
    WorkflowProcessCreate,
    WorkflowProcessUpdate,
    ToolDB,
    ToolExecutionDB,
    ToolCreate,
    ToolUpdate
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

# Import MCP repository functions
from src.db.repository.mcp import (
    # Legacy MCP server functions
    get_mcp_server,
    get_mcp_server_by_name,
    list_mcp_servers,
    create_mcp_server,
    update_mcp_server,
    delete_mcp_server,
    update_mcp_server_status,
    update_mcp_server_discovery,
    increment_connection_attempts,
    assign_agent_to_server,
    remove_agent_from_server,
    get_agent_servers,
    get_server_agents,
    get_agent_server_assignments,
    get_servers_with_agents_optimized,
    
    # New simplified MCP config functions (NMSTX-253)
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

# Import workflow process repository functions
from src.db.repository.workflow_process import (
    create_workflow_process,
    get_workflow_process,
    list_workflow_processes,
    update_workflow_process,
    mark_process_terminated,
    get_stale_processes,
    cleanup_old_processes
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

# Import FlashinhoV2 UUID migration utilities
from src.db.repository.user_uuid_migration import (
    ensure_user_uuid_matches_flashed_id,
    migrate_user_uuid_to_flashed_id,
    find_user_by_flashed_id,
    find_user_by_phone_number,
)

# Import tool repository functions
from src.db.repository.tool import (
    list_tools,
    get_tool_by_name,
    get_tool_by_id,
    create_tool,
    update_tool,
    delete_tool,
    get_tools_by_mcp_server,
    get_tools_by_category,
    log_tool_execution,
    get_tool_execution_stats,
    get_tool_categories
)