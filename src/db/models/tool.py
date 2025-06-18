"""Tool management models for the automagik agents platform."""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator


class BaseDBModel(BaseModel):
    """Base model for database entities."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
    )


class ToolDB(BaseDBModel):
    """Database model for tools."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(..., description="Tool name")
    type: str = Field(..., description="Tool type: code, mcp, or hybrid")
    description: Optional[str] = Field(None, description="Tool description")
    
    # For code tools
    module_path: Optional[str] = Field(None, description="Python module path")
    function_name: Optional[str] = Field(None, description="Function name")
    
    # For MCP tools
    mcp_server_name: Optional[str] = Field(None, description="MCP server name")
    mcp_tool_name: Optional[str] = Field(None, description="MCP tool name")
    
    # Tool metadata
    parameters_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for parameters")
    capabilities: List[str] = Field(default_factory=list, description="Tool capabilities")
    categories: List[str] = Field(default_factory=list, description="Tool categories")
    
    # Configuration
    enabled: bool = Field(True, description="Whether tool is enabled")
    agent_restrictions: List[str] = Field(default_factory=list, description="Agents that can use this tool")
    
    # Execution metadata
    execution_count: int = Field(0, description="Number of times executed")
    last_executed_at: Optional[datetime] = Field(None, description="Last execution time")
    average_execution_time_ms: int = Field(0, description="Average execution time in milliseconds")
    
    # Audit fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    DB_TABLE: ClassVar[str] = "tools"
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "ToolDB":
        """Create model from database row."""
        # Handle JSON fields
        if "parameters_schema" in row and isinstance(row["parameters_schema"], str):
            try:
                row["parameters_schema"] = json.loads(row["parameters_schema"])
            except (json.JSONDecodeError, TypeError):
                row["parameters_schema"] = None
                
        if "capabilities" in row and isinstance(row["capabilities"], str):
            try:
                row["capabilities"] = json.loads(row["capabilities"])
            except (json.JSONDecodeError, TypeError):
                row["capabilities"] = []
                
        if "categories" in row and isinstance(row["categories"], str):
            try:
                row["categories"] = json.loads(row["categories"])
            except (json.JSONDecodeError, TypeError):
                row["categories"] = []
                
        if "agent_restrictions" in row and isinstance(row["agent_restrictions"], str):
            try:
                row["agent_restrictions"] = json.loads(row["agent_restrictions"])
            except (json.JSONDecodeError, TypeError):
                row["agent_restrictions"] = []
        
        return cls(**row)
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        """Validate tool type."""
        allowed_types = {'code', 'mcp', 'hybrid'}
        if v not in allowed_types:
            raise ValueError(f"Tool type must be one of: {allowed_types}")
        return v


class ToolExecutionDB(BaseDBModel):
    """Database model for tool execution logs."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tool_id: uuid.UUID = Field(..., description="Tool ID")
    agent_name: Optional[str] = Field(None, description="Agent that executed the tool")
    session_id: Optional[str] = Field(None, description="Session ID")
    
    # Execution details
    parameters: Optional[Dict[str, Any]] = Field(None, description="Tool parameters")
    context: Optional[Dict[str, Any]] = Field(None, description="Execution context")
    
    # Results
    status: str = Field(..., description="Execution status: success, error, timeout")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    
    # Audit
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    
    DB_TABLE: ClassVar[str] = "tool_executions"
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "ToolExecutionDB":
        """Create model from database row."""
        # Handle JSON fields
        for field in ["parameters", "context", "result"]:
            if field in row and isinstance(row[field], str):
                try:
                    row[field] = json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    row[field] = None
        
        return cls(**row)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate execution status."""
        allowed_statuses = {'success', 'error', 'timeout'}
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {allowed_statuses}")
        return v


class ToolCreate(BaseModel):
    """Model for creating new tools."""
    name: str = Field(..., description="Tool name")
    type: str = Field(..., description="Tool type: code, mcp, or hybrid")
    description: Optional[str] = Field(None, description="Tool description")
    
    # For code tools
    module_path: Optional[str] = Field(None, description="Python module path")
    function_name: Optional[str] = Field(None, description="Function name")
    
    # For MCP tools
    mcp_server_name: Optional[str] = Field(None, description="MCP server name")
    mcp_tool_name: Optional[str] = Field(None, description="MCP tool name")
    
    # Tool metadata
    parameters_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for parameters")
    capabilities: List[str] = Field(default_factory=list, description="Tool capabilities")
    categories: List[str] = Field(default_factory=list, description="Tool categories")
    
    # Configuration
    enabled: bool = Field(True, description="Whether tool is enabled")
    agent_restrictions: List[str] = Field(default_factory=list, description="Agents that can use this tool")


class ToolUpdate(BaseModel):
    """Model for updating existing tools."""
    description: Optional[str] = None
    enabled: Optional[bool] = None
    parameters_schema: Optional[Dict[str, Any]] = None
    capabilities: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    agent_restrictions: Optional[List[str]] = None