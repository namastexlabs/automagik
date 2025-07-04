"""Database module for Automagik Agents.

This module provides a clean repository pattern for database operations,
with specialized repository functions for each entity type.
"""

# Export models
from automagik.db.models import (
    Agent,
    User,
    Session,
    Memory,
    Message,
    MCPConfig,
    MCPConfigCreate,
    MCPConfigUpdate,
    WorkflowProcess,
    WorkflowProcessCreate,
    WorkflowProcessUpdate,
    WorkflowRun,
    WorkflowRunCreate,
    WorkflowRunUpdate,
    ToolDB,
    ToolExecutionDB,
    ToolCreate,
    ToolUpdate,
    Workflow,
    WorkflowCreate,
    WorkflowUpdate
)

# Export connection utilities
from automagik.db.connection import (
    get_connection_pool,
    get_db_connection,
    get_db_cursor,
    execute_query,
    execute_batch
)

# Export all repository functions
from automagik.db.repository import (
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
    list_messages_for_user,
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
    delete_memory,
    create_memories_bulk
)

# Import MCP repository functions (simplified architecture - NMSTX-253)
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

# Import workflow process repository functions
from automagik.db.repository.workflow_process import (
    create_workflow_process,
    get_workflow_process,
    list_workflow_processes,
    update_workflow_process,
    mark_process_terminated,
    get_stale_processes,
    cleanup_old_processes
)

# Import UUID-compatible user repository functions
from automagik.db.repository.user import (
    get_user,
    get_user_by_email,
    get_user_by_identifier,
    list_users,
    create_user,
    update_user,
    delete_user,
    ensure_default_user_exists,
)


# Import tool repository functions
from automagik.db.repository.tool import (
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

# Import workflow run repository functions
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

# Import workflow repository functions
from automagik.db.repository.workflow import (
    create_workflow,
    get_workflow,
    get_workflow_by_name,
    list_workflows,
    update_workflow,
    delete_workflow,
    register_workflow
)