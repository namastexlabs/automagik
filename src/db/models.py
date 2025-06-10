"""Pydantic models representing database tables."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, ClassVar

from pydantic import BaseModel, Field, ConfigDict


class BaseDBModel(BaseModel):
    """Base model for all database models."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
    )


class User(BaseDBModel):
    """User model corresponding to the users table."""
    id: Optional[uuid.UUID] = Field(None, description="User ID")
    email: Optional[str] = Field(None, description="User email")
    phone_number: Optional[str] = Field(None, description="User phone number")
    user_data: Optional[Dict[str, Any]] = Field(None, description="Additional user data")
    created_at: Optional[datetime] = Field(None, description="Created at timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated at timestamp")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "User":
        """Create a User instance from a database row dictionary."""
        if not row:
            return None
        return cls(**row)


class Agent(BaseDBModel):
    """Agent model corresponding to the agents table."""
    id: Optional[int] = Field(None, description="Agent ID")
    name: str = Field(..., description="Agent name")
    type: str = Field(..., description="Agent type")
    model: str = Field(..., description="Model used by the agent")
    description: Optional[str] = Field(None, description="Agent description")
    version: Optional[str] = Field(None, description="Agent version")
    config: Optional[Dict[str, Any]] = Field(None, description="Agent configuration")
    active: bool = Field(True, description="Whether the agent is active")
    run_id: int = Field(0, description="Current run ID")
    system_prompt: Optional[str] = Field(None, description="System prompt for the agent")
    active_default_prompt_id: Optional[int] = Field(None, description="ID of the active default prompt")
    created_at: Optional[datetime] = Field(None, description="Created at timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated at timestamp")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Agent":
        """Create an Agent instance from a database row dictionary."""
        if not row:
            return None
        return cls(**row)


class Session(BaseDBModel):
    """Session model corresponding to the sessions table."""
    id: Optional[uuid.UUID] = Field(None, description="Session ID")
    user_id: Optional[uuid.UUID] = Field(None, description="User ID")
    agent_id: Optional[int] = Field(None, description="Agent ID")
    agent_name: Optional[str] = Field(None, description="Name of the agent associated with the session")
    name: Optional[str] = Field(None, description="Session name")
    platform: Optional[str] = Field(None, description="Platform")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: Optional[datetime] = Field(None, description="Created at timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated at timestamp")
    run_finished_at: Optional[datetime] = Field(None, description="Run finished at timestamp")
    message_count: Optional[int] = Field(None, description="Number of messages in the session")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Session":
        """Create a Session instance from a database row dictionary."""
        if not row:
            return None
        return cls(**row)


class Message(BaseDBModel):
    """Message model corresponding to the messages table."""
    id: Optional[uuid.UUID] = Field(None, description="Message ID")
    session_id: Optional[uuid.UUID] = Field(None, description="Session ID")
    user_id: Optional[uuid.UUID] = Field(None, description="User ID")
    agent_id: Optional[int] = Field(None, description="Agent ID")
    role: str = Field(..., description="Message role (user, assistant, system)")
    text_content: Optional[str] = Field(None, description="Message text content")
    media_url: Optional[str] = Field(None, description="Media URL")
    mime_type: Optional[str] = Field(None, description="MIME type")
    message_type: Optional[str] = Field(None, description="Message type")
    raw_payload: Optional[Dict[str, Any]] = Field(None, description="Raw message payload")
    channel_payload: Optional[Dict[str, Any]] = Field(None, description="Channel-specific payload data")
    tool_calls: Optional[Dict[str, Any]] = Field(None, description="Tool calls")
    tool_outputs: Optional[Dict[str, Any]] = Field(None, description="Tool outputs")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    user_feedback: Optional[str] = Field(None, description="User feedback")
    flagged: Optional[str] = Field(None, description="Flagged status")
    context: Optional[Dict[str, Any]] = Field(None, description="Message context")
    created_at: Optional[datetime] = Field(None, description="Created at timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated at timestamp")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Message":
        """Create a Message instance from a database row dictionary."""
        if not row:
            return None
        return cls(**row)


class Memory(BaseDBModel):
    """Memory model corresponding to the memories table."""
    id: Optional[uuid.UUID] = Field(None, description="Memory ID")
    name: str = Field(..., description="Memory name")
    description: Optional[str] = Field(None, description="Memory description")
    content: Optional[str] = Field(None, description="Memory content")
    session_id: Optional[uuid.UUID] = Field(None, description="Session ID")
    user_id: Optional[uuid.UUID] = Field(None, description="User ID")
    agent_id: Optional[int] = Field(None, description="Agent ID")
    read_mode: Optional[str] = Field(None, description="Read mode")
    access: Optional[str] = Field(None, description="Access permissions")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: Optional[datetime] = Field(None, description="Created at timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated at timestamp")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Memory":
        """Create a Memory instance from a database row dictionary."""
        if not row:
            return None
        return cls(**row)


# Prompt Models
class PromptBase(BaseDBModel):
    """Base class for Prompt models."""
    
    agent_id: int = Field(..., description="ID of the agent this prompt belongs to")
    prompt_text: str = Field(..., description="The actual prompt text content")
    version: int = Field(default=1, description="Version number for this prompt")
    is_active: bool = Field(default=False, description="Whether this prompt is currently active")
    is_default_from_code: bool = Field(default=False, description="Whether this prompt was defined in code")
    status_key: str = Field(default="default", description="Status key this prompt applies to (e.g., 'default', 'APPROVED', etc.)")
    name: Optional[str] = Field(default=None, description="Optional descriptive name for this prompt")


class PromptCreate(PromptBase):
    """Data needed to create a new Prompt."""
    pass


class PromptUpdate(BaseModel):
    """Data for updating an existing Prompt."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
    )
    
    prompt_text: Optional[str] = Field(default=None, description="Updated prompt text")
    is_active: Optional[bool] = Field(default=None, description="Whether to set this prompt as active")
    name: Optional[str] = Field(default=None, description="Updated prompt name")


class Prompt(PromptBase):
    """Complete Prompt model, including database fields."""
    
    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Timestamp when this prompt was created")
    updated_at: datetime = Field(..., description="Timestamp when this prompt was last updated")
    
    DB_TABLE: ClassVar[str] = "prompts"
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Prompt":
        """Create a Prompt instance from a database row.
        
        Args:
            row: Database row as dictionary
            
        Returns:
            Prompt instance
        """
        if not row:
            return None
            
        # Convert database row to model
        return cls(
            id=row["id"],
            agent_id=row["agent_id"],
            prompt_text=row["prompt_text"],
            version=row["version"],
            is_active=row["is_active"],
            is_default_from_code=row["is_default_from_code"],
            status_key=row["status_key"],
            name=row["name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


# Preference Models [EPIC-SIMULATION-TEST]
class PreferenceBase(BaseDBModel):
    """Base class for Preference models."""
    
    user_id: uuid.UUID = Field(..., description="ID of the user these preferences belong to")
    category: str = Field(..., description="Preference category (e.g., 'ui', 'behavior', 'notifications')")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="JSON object containing preference key-value pairs")
    version: int = Field(default=1, description="Schema version for preference migration")


class PreferenceCreate(PreferenceBase):
    """Data needed to create new Preferences."""
    pass


class PreferenceUpdate(BaseModel):
    """Data for updating existing Preferences."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
    )
    
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="Updated preference values")
    version: Optional[int] = Field(default=None, description="Updated schema version")


class Preference(PreferenceBase):
    """Complete Preference model, including database fields."""
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier")
    created_at: datetime = Field(..., description="Timestamp when preferences were created")
    updated_at: datetime = Field(..., description="Timestamp when preferences were last updated")
    
    DB_TABLE: ClassVar[str] = "preferences"
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Preference":
        """Create a Preference instance from a database row.
        
        Args:
            row: Database row as dictionary
            
        Returns:
            Preference instance
        """
        if not row:
            return None
            
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            category=row["category"],
            preferences=row["preferences"],
            version=row["version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


class PreferenceHistory(BaseDBModel):
    """Audit log for preference changes."""
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier")
    preference_id: uuid.UUID = Field(..., description="ID of the preference that was changed")
    old_value: Optional[Dict[str, Any]] = Field(None, description="Previous preference values")
    new_value: Dict[str, Any] = Field(..., description="New preference values")
    changed_by: Optional[uuid.UUID] = Field(None, description="User who made the change")
    changed_at: datetime = Field(..., description="Timestamp of the change")
    
    DB_TABLE: ClassVar[str] = "preference_history"


# MCP Models
class MCPServerDB(BaseDBModel):
    """MCP Server model corresponding to the mcp_servers table."""
    id: Optional[int] = Field(None, description="MCP Server ID")
    name: str = Field(..., description="Unique server name")
    server_type: str = Field(..., description="Server type (stdio or http)")
    description: Optional[str] = Field(None, description="Server description")
    
    # Connection configuration
    command: Optional[List[str]] = Field(None, description="Command array for stdio servers")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    http_url: Optional[str] = Field(None, description="HTTP URL for http servers")
    
    # Behavior configuration
    auto_start: bool = Field(True, description="Whether to auto-start the server")
    max_retries: int = Field(3, description="Maximum connection retries")
    timeout_seconds: int = Field(30, description="Connection timeout in seconds")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    priority: int = Field(0, description="Server priority")
    
    # State tracking
    status: str = Field("stopped", description="Current server status")
    enabled: bool = Field(True, description="Whether server is enabled")
    started_at: Optional[datetime] = Field(None, description="When server was started")
    last_error: Optional[str] = Field(None, description="Last error message")
    error_count: int = Field(0, description="Number of errors")
    connection_attempts: int = Field(0, description="Number of connection attempts")
    last_ping: Optional[datetime] = Field(None, description="Last successful ping")
    
    # Discovery results
    tools_discovered: Optional[List[str]] = Field(None, description="Discovered tool names")
    resources_discovered: Optional[List[str]] = Field(None, description="Discovered resource URIs")
    
    # Audit trail
    created_at: Optional[datetime] = Field(None, description="Created timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated timestamp")
    last_started: Optional[datetime] = Field(None, description="Last started timestamp")
    last_stopped: Optional[datetime] = Field(None, description="Last stopped timestamp")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "MCPServerDB":
        """Create an MCPServerDB instance from a database row dictionary."""
        if not row:
            return None
        return cls(**row)


class AgentMCPServerDB(BaseDBModel):
    """Agent MCP Server assignment model corresponding to the agent_mcp_servers table."""
    id: Optional[int] = Field(None, description="Assignment ID")
    agent_id: int = Field(..., description="Agent ID")
    mcp_server_id: int = Field(..., description="MCP Server ID")
    created_at: Optional[datetime] = Field(None, description="Created timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated timestamp")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "AgentMCPServerDB":
        """Create an AgentMCPServerDB instance from a database row dictionary."""
        if not row:
            return None
        return cls(**row)


# New Simplified MCP Config Models (NMSTX-253 Refactor)
class MCPConfigBase(BaseDBModel):
    """Base class for MCP Config models."""
    
    name: str = Field(..., description="Unique server identifier")
    config: Dict[str, Any] = Field(..., description="Complete JSON configuration")


class MCPConfigCreate(MCPConfigBase):
    """Data needed to create a new MCP Config."""
    pass


class MCPConfigUpdate(BaseModel):
    """Data for updating an existing MCP Config."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
    )
    
    config: Optional[Dict[str, Any]] = Field(default=None, description="Updated configuration")


class MCPConfig(MCPConfigBase):
    """Complete MCP Config model, including database fields."""
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier")
    created_at: datetime = Field(..., description="Timestamp when config was created")
    updated_at: datetime = Field(..., description="Timestamp when config was last updated")
    
    DB_TABLE: ClassVar[str] = "mcp_configs"
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "MCPConfig":
        """Create an MCPConfig instance from a database row.
        
        Args:
            row: Database row as dictionary
            
        Returns:
            MCPConfig instance
        """
        if not row:
            return None
            
        return cls(
            id=row["id"],
            name=row["name"],
            config=row["config"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def get_server_type(self) -> str:
        """Get the server type from config."""
        return self.config.get("server_type", "stdio")
    
    def get_command(self) -> List[str]:
        """Get the command array for stdio servers."""
        return self.config.get("command", [])
    
    def get_agents(self) -> List[str]:
        """Get the list of agent names this server is assigned to."""
        return self.config.get("agents", [])
    
    def get_tools_config(self) -> Dict[str, List[str]]:
        """Get the tools configuration (include/exclude lists)."""
        return self.config.get("tools", {})
    
    def get_environment(self) -> Dict[str, str]:
        """Get environment variables for the server."""
        return self.config.get("environment", {})
    
    def is_enabled(self) -> bool:
        """Check if the server is enabled."""
        return self.config.get("enabled", True)
    
    def should_auto_start(self) -> bool:
        """Check if the server should auto-start."""
        return self.config.get("auto_start", True)
    
    def get_timeout(self) -> int:
        """Get the timeout in milliseconds."""
        return self.config.get("timeout", 30000)
    
    def get_retry_count(self) -> int:
        """Get the retry count."""
        return self.config.get("retry_count", 3)
    
    def is_assigned_to_agent(self, agent_name: str) -> bool:
        """Check if this server is assigned to a specific agent."""
        agents = self.get_agents()
        return agent_name in agents or "*" in agents
    
    def get_filtered_tools(self, available_tools: List[str]) -> List[str]:
        """Filter tools based on include/exclude configuration."""
        tools_config = self.get_tools_config()
        include = tools_config.get("include", ["*"])
        exclude = tools_config.get("exclude", [])
        
        # If include has "*", start with all available tools
        if "*" in include:
            filtered = available_tools.copy()
        else:
            # Only include specified tools
            filtered = [tool for tool in available_tools if tool in include]
        
        # Remove excluded tools
        filtered = [tool for tool in filtered if tool not in exclude]
        
        return filtered