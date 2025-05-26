"""MCP client functionality for automagik-agents framework.

This package provides MCP (Model Context Protocol) client integration,
allowing agents to connect to and use MCP servers for extended functionality.
"""

from .client import MCPClientManager
from .models import MCPServerConfig, MCPServerStatus, MCPServerType
from .server import MCPServerManager
from .exceptions import MCPError, MCPServerError, MCPConnectionError

__all__ = [
    "MCPClientManager",
    "MCPServerConfig", 
    "MCPServerStatus",
    "MCPServerType",
    "MCPServerManager",
    "MCPError",
    "MCPServerError", 
    "MCPConnectionError",
]