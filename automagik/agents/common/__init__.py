"""Common utilities package for agent implementations.

This package contains common utilities that are used by multiple agent implementations,
providing reusable functionality for message parsing, session management, 
memory handling, and other shared features.
"""

from automagik.agents.common.message_parser import (
    extract_tool_calls,
    extract_tool_outputs,
    extract_all_messages,
    format_message_for_db,
    parse_user_message
)

from automagik.agents.common.session_manager import (
    create_session_id,
    create_run_id,
    create_context,
    extract_ids_from_context,
    validate_agent_id,
    validate_user_id,
    extract_multimodal_content
)

from automagik.agents.common.dependencies_helper import (
    parse_model_settings,
    create_model_settings,
    create_usage_limits,
    get_model_name,
    close_http_client,
    message_history_to_pydantic_format,
    add_system_message_to_history
)

from automagik.agents.common.prompt_builder import PromptBuilder
from automagik.agents.common.memory_handler import MemoryHandler
from automagik.agents.common.tool_registry import ToolRegistry

__all__ = [
    # Message Parser
    'extract_tool_calls',
    'extract_tool_outputs',
    'extract_all_messages',
    'format_message_for_db',
    'parse_user_message',
    
    # Session Manager
    'create_session_id',
    'create_run_id',
    'create_context',
    'extract_ids_from_context',
    'validate_agent_id',
    'validate_user_id',
    'extract_multimodal_content',
    
    # Dependencies Helper
    'parse_model_settings',
    'create_model_settings',
    'create_usage_limits',
    'get_model_name',
    'close_http_client',
    'message_history_to_pydantic_format',
    'add_system_message_to_history',
    
    # Classes
    'PromptBuilder',
    'MemoryHandler',
    'ToolRegistry'
] 