"""MCP client functionality for automagik-agents framework.

This package provides MCP (Model Context Protocol) client integration,
allowing agents to connect to and use MCP servers for extended functionality.

NMSTX-256 Integration: Completely refactored to use PydanticAI's native MCP classes
with the simplified single-table architecture for better maintainability
and standards compliance.
"""

# New PydanticAI-based implementation (NMSTX-256)
from .client import (
    MCPManager, 
    get_mcp_manager, 
    shutdown_mcp_manager
)

# Common models and exceptions
from .models import MCPServerConfig, MCPServerStatus, MCPServerType
from .exceptions import MCPError, MCPServerError, MCPConnectionError

__all__ = [
    # Main MCP interface (NMSTX-256)
    "MCPManager",
    "get_mcp_manager", 
    "shutdown_mcp_manager",
    
    # Models and exceptions
    "MCPServerConfig", 
    "MCPServerStatus",
    "MCPServerType",
    "MCPError",
    "MCPServerError", 
    "MCPConnectionError",
]