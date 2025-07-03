"""MCP-specific exceptions for automagik-agents framework."""

from typing import Optional


class MCPError(Exception):
    """Base exception for MCP-related errors."""
    
    def __init__(self, message: str, server_name: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.server_name = server_name
        
    def __str__(self) -> str:
        if self.server_name:
            return f"MCP Error [{self.server_name}]: {self.message}"
        return f"MCP Error: {self.message}"


class MCPServerError(MCPError):
    """Exception raised when MCP server operations fail."""
    
    def __init__(self, message: str, server_name: Optional[str] = None, error_code: Optional[str] = None):
        super().__init__(message, server_name)
        self.error_code = error_code
        
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.error_code:
            return f"{base_msg} (Code: {self.error_code})"
        return base_msg


class MCPConnectionError(MCPError):
    """Exception raised when MCP server connection fails."""
    
    def __init__(self, message: str, server_name: Optional[str] = None, retry_count: int = 0):
        super().__init__(message, server_name)
        self.retry_count = retry_count
        
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.retry_count > 0:
            return f"{base_msg} (Retries: {self.retry_count})"
        return base_msg


class MCPToolError(MCPError):
    """Exception raised when MCP tool execution fails."""
    
    def __init__(self, message: str, tool_name: Optional[str] = None, server_name: Optional[str] = None):
        super().__init__(message, server_name)
        self.tool_name = tool_name
        
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.tool_name:
            return f"{base_msg} (Tool: {self.tool_name})"
        return base_msg


class MCPConfigurationError(MCPError):
    """Exception raised when MCP configuration is invalid."""
    
    def __init__(self, message: str, config_field: Optional[str] = None):
        super().__init__(message)
        self.config_field = config_field
        
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.config_field:
            return f"{base_msg} (Field: {self.config_field})"
        return base_msg