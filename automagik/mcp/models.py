"""Pydantic models for MCP server configuration and management."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MCPServerType(str, Enum):
    """Types of MCP servers supported."""
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


class MCPServerStatus(str, Enum):
    """Status of MCP server."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server."""
    
    model_config = ConfigDict(
        exclude_none=True,
        validate_assignment=True,
        extra='ignore'
    )
    
    # Basic configuration
    name: str = Field(..., description="Unique name for the MCP server")
    server_type: MCPServerType = Field(..., description="Type of MCP server (stdio or http)")
    description: Optional[str] = Field(None, description="Description of the MCP server")
    
    # Server connection details
    command: Optional[List[str]] = Field(None, description="Command to start stdio server")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables for stdio server")
    http_url: Optional[str] = Field(None, description="URL for HTTP server")
    
    # Agent assignment
    agent_names: List[str] = Field(default_factory=list, description="Agents that can use this server")
    
    # Configuration options
    auto_start: bool = Field(True, description="Whether to auto-start the server")
    max_retries: int = Field(3, description="Maximum connection retries")
    timeout_seconds: int = Field(30, description="Connection timeout in seconds")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the server")
    priority: int = Field(0, description="Priority for server selection (higher = more priority)")
    
    @field_validator('command')
    @classmethod
    def validate_command_for_stdio(cls, v, info):
        """Validate command is provided for stdio servers."""
        if info.data.get('server_type') == MCPServerType.STDIO and not v:
            raise ValueError("Command is required for stdio servers")
        return v
    
    @field_validator('http_url')
    @classmethod
    def validate_url_for_http(cls, v, info):
        """Validate URL is provided for HTTP servers."""
        if info.data.get('server_type') == MCPServerType.HTTP and not v:
            raise ValueError("HTTP URL is required for HTTP servers")
        return v


class MCPServerState(BaseModel):
    """Current state of an MCP server."""
    
    model_config = ConfigDict(exclude_none=True)
    
    name: str
    status: MCPServerStatus
    started_at: Optional[datetime] = None
    last_error: Optional[str] = None
    error_count: int = 0
    connection_attempts: int = 0
    last_ping: Optional[datetime] = None
    tools_discovered: List[str] = Field(default_factory=list)
    resources_discovered: List[str] = Field(default_factory=list)
    
    
class MCPToolInfo(BaseModel):
    """Information about an MCP tool."""
    
    model_config = ConfigDict(exclude_none=True)
    
    name: str
    description: Optional[str] = None
    server_name: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None


class MCPResourceInfo(BaseModel):
    """Information about an MCP resource."""
    
    model_config = ConfigDict(exclude_none=True)
    
    uri: str
    name: Optional[str] = None
    description: Optional[str] = None
    server_name: str
    mime_type: Optional[str] = None


class MCPServerListResponse(BaseModel):
    """Response for listing MCP servers."""
    
    model_config = ConfigDict(exclude_none=True)
    
    servers: List[MCPServerState]
    total: int


class MCPServerCreateRequest(BaseModel):
    """Request to create a new MCP server configuration."""
    
    model_config = ConfigDict(exclude_none=True)
    
    name: str = Field(..., description="Unique name for the MCP server")
    server_type: MCPServerType = Field(..., description="Type of MCP server")
    description: Optional[str] = None
    command: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    http_url: Optional[str] = None
    agent_names: List[str] = Field(default_factory=list)
    auto_start: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30
    tags: List[str] = Field(default_factory=list)
    priority: int = 0


class MCPServerUpdateRequest(BaseModel):
    """Request to update an MCP server configuration."""
    
    model_config = ConfigDict(exclude_none=True)
    
    description: Optional[str] = None
    command: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    http_url: Optional[str] = None
    agent_names: Optional[List[str]] = None
    auto_start: Optional[bool] = None
    max_retries: Optional[int] = None
    timeout_seconds: Optional[int] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = None


class MCPToolCallRequest(BaseModel):
    """Request to call an MCP tool."""
    
    model_config = ConfigDict(exclude_none=True)
    
    tool_name: str = Field(..., description="Name of the tool to call")
    server_name: str = Field(..., description="Name of the MCP server")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool")
    timeout_seconds: Optional[int] = Field(30, description="Timeout for the tool call")


class MCPToolCallResponse(BaseModel):
    """Response from an MCP tool call."""
    
    model_config = ConfigDict(exclude_none=True)
    
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    tool_name: str
    server_name: str


class MCPResourceAccessRequest(BaseModel):
    """Request to access an MCP resource."""
    
    model_config = ConfigDict(exclude_none=True)
    
    uri: str = Field(..., description="URI of the resource to access")
    server_name: str = Field(..., description="Name of the MCP server")


class MCPResourceAccessResponse(BaseModel):
    """Response from accessing an MCP resource."""
    
    model_config = ConfigDict(exclude_none=True)
    
    success: bool
    content: Optional[str] = None
    mime_type: Optional[str] = None
    error: Optional[str] = None
    uri: str
    server_name: str


class MCPHealthResponse(BaseModel):
    """Health check response for MCP system."""
    
    model_config = ConfigDict(exclude_none=True)
    
    status: str = "healthy"
    servers_total: int
    servers_running: int
    servers_error: int
    tools_available: int
    resources_available: int
    timestamp: datetime = Field(default_factory=datetime.now)