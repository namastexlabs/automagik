"""Pydantic models representing database tables."""

import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, ClassVar, Literal
import json

from pydantic import BaseModel, Field, ConfigDict, field_validator

logger = logging.getLogger(__name__)


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
        
        # Handle JSON user_data field - deserialize if it's a string
        if "user_data" in row and isinstance(row["user_data"], str):
            import json
            try:
                row["user_data"] = json.loads(row["user_data"])
            except (json.JSONDecodeError, TypeError):
                row["user_data"] = None
        
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
        
        # Handle JSON config field - deserialize if it's a string
        if "config" in row and isinstance(row["config"], str):
            import json
            try:
                row["config"] = json.loads(row["config"])
            except (json.JSONDecodeError, TypeError):
                row["config"] = None
        
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
    # Conversation branching fields
    parent_session_id: Optional[uuid.UUID] = Field(None, description="Parent session ID for branches")
    branch_point_message_id: Optional[uuid.UUID] = Field(None, description="Message where branch was created")
    branch_type: Optional[Literal["edit_branch", "manual_branch"]] = Field(None, description="Type of branch")
    is_main_branch: bool = Field(True, description="Whether this is the main conversation thread")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Session":
        """Create a Session instance from a database row dictionary."""
        if not row:
            return None
        
        # Handle JSON metadata field - deserialize if it's a string
        if "metadata" in row and isinstance(row["metadata"], str):
            import json
            try:
                row["metadata"] = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                row["metadata"] = None
        
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
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage information")
    created_at: Optional[datetime] = Field(None, description="Created at timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated at timestamp")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Message":
        """Create a Message instance from a database row dictionary."""
        if not row:
            return None
        
        # Handle JSON fields - deserialize if they're strings
        json_fields = ["raw_payload", "channel_payload", "tool_calls", "tool_outputs", "context", "usage"]
        for field in json_fields:
            if field in row and isinstance(row[field], str):
                import json
                try:
                    row[field] = json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    row[field] = None
        
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
        """Create a Prompt instance from a database row."""
        if not row:
            return None
            
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


# Preference Models
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
        """Create a Preference instance from a database row."""
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


# MCP Config Models (NMSTX-253 Refactor - Simplified Single-Table Architecture)
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
        """Create an MCPConfig instance from a database row."""
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
        """Get the list of agents assigned to this MCP server."""
        agents = self.config.get("agents", [])
        return agents if isinstance(agents, list) else []
    
    def is_assigned_to_agent(self, agent_name: str) -> bool:
        """Check if this MCP server is assigned to a specific agent."""
        agents = self.get_agents()
        return "*" in agents or agent_name in agents
    
    def get_tools_config(self) -> Dict[str, Any]:
        """Get the tools configuration (include/exclude filters)."""
        return self.config.get("tools", {})
    
    def should_include_tool(self, tool_name: str) -> bool:
        """Check if a tool should be included based on filters."""
        tools_config = self.get_tools_config()
        
        # Check exclude list first
        exclude_list = tools_config.get("exclude", [])
        if isinstance(exclude_list, list):
            for pattern in exclude_list:
                if pattern == "*" or tool_name == pattern or (pattern.endswith("*") and tool_name.startswith(pattern[:-1])):
                    return False
        
        # Check include list
        include_list = tools_config.get("include", ["*"])
        if isinstance(include_list, list):
            for pattern in include_list:
                if pattern == "*" or tool_name == pattern or (pattern.endswith("*") and tool_name.startswith(pattern[:-1])):
                    return True
        
        # Default to exclude if no include patterns match
        return False
    
    def get_environment(self) -> Dict[str, str]:
        """Get environment variables for the server."""
        env = self.config.get("environment", {})
        return env if isinstance(env, dict) else {}
    
    def get_timeout(self) -> int:
        """Get the timeout in milliseconds."""
        return self.config.get("timeout", 30000)
    
    def get_retry_count(self) -> int:
        """Get the maximum retry count."""
        return self.config.get("retry_count", 3)
    
    def is_enabled(self) -> bool:
        """Check if the server is enabled."""
        return self.config.get("enabled", True)
    
    def is_auto_start(self) -> bool:
        """Check if the server should auto-start."""
        return self.config.get("auto_start", True)
    
    def get_url(self) -> Optional[str]:
        """Get the URL for HTTP servers."""
        return self.config.get("url")
    
    def validate_config(self) -> bool:
        """Validate the configuration is complete and consistent."""
        # Check required fields
        if not self.config.get("name"):
            return False
        
        server_type = self.get_server_type()
        if server_type not in ["stdio", "http"]:
            return False
        
        # Check type-specific requirements
        if server_type == "stdio" and not self.get_command():
            return False
        
        if server_type == "http" and not self.get_url():
            return False
        
        return True


# Workflow Process Models
class WorkflowProcessBase(BaseDBModel):
    """Base class for Workflow Process models."""
    
    run_id: str = Field(..., description="Unique identifier for the workflow run")
    pid: Optional[int] = Field(None, description="System process ID")
    status: str = Field(default="running", description="Process status")
    workflow_name: Optional[str] = Field(None, description="Name of the workflow")
    session_id: Optional[str] = Field(None, description="Associated session ID")
    user_id: Optional[str] = Field(None, description="User who initiated the workflow")
    workspace_path: Optional[str] = Field(None, description="Workspace directory path")
    process_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional process metadata")


class WorkflowProcessCreate(WorkflowProcessBase):
    """Data needed to create a new Workflow Process."""
    pass


class WorkflowProcessUpdate(BaseModel):
    """Data for updating an existing Workflow Process."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
    )
    
    pid: Optional[int] = Field(default=None, description="Updated process ID")
    status: Optional[str] = Field(default=None, description="Updated status")
    last_heartbeat: Optional[datetime] = Field(default=None, description="Updated heartbeat timestamp")
    process_info: Optional[Dict[str, Any]] = Field(default=None, description="Updated process metadata")


class WorkflowProcess(WorkflowProcessBase):
    """Complete Workflow Process model, including database fields."""
    
    started_at: Optional[datetime] = Field(None, description="Process start timestamp")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat timestamp")
    created_at: Optional[datetime] = Field(None, description="Created at timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated at timestamp")
    
    DB_TABLE: ClassVar[str] = "workflow_processes"
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "WorkflowProcess":
        """Create a WorkflowProcess instance from a database row."""
        if not row:
            return None
        
        # Handle JSON process_info field
        process_info = row.get("process_info")
        if isinstance(process_info, str):
            import json
            try:
                process_info = json.loads(process_info)
            except (json.JSONDecodeError, TypeError):
                process_info = {}
        
        return cls(
            run_id=row["run_id"],
            pid=row.get("pid"),
            status=row.get("status", "running"),
            workflow_name=row.get("workflow_name"),
            session_id=row.get("session_id"),
            user_id=row.get("user_id"),
            started_at=row.get("started_at"),
            workspace_path=row.get("workspace_path"),
            last_heartbeat=row.get("last_heartbeat"),
            process_info=process_info or {},
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )


# Tool Models
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


# Workflow Run Models
class WorkflowRunBase(BaseDBModel):
    """Base class for Workflow Run models."""
    
    run_id: str = Field(..., description="Claude SDK unique run identifier")
    workflow_name: str = Field(..., description="Workflow name (architect, implement, test, etc.)")
    task_input: str = Field(..., description="Original human request message")
    
    # Optional core fields
    agent_type: Optional[str] = Field(None, description="Agent categorization")
    ai_model: Optional[str] = Field(None, description="AI model used (sonnet, opus)")
    session_id: Optional[uuid.UUID] = Field(None, description="Session ID reference")
    session_name: Optional[str] = Field(None, description="Human/orchestrator chosen session name")
    
    # Git repository context
    git_repo: Optional[str] = Field(None, description="Repository URL or local path")
    git_branch: Optional[str] = Field(None, description="Working branch")
    initial_commit_hash: Optional[str] = Field(None, description="Git commit hash at start")
    final_commit_hash: Optional[str] = Field(None, description="Git commit hash at completion")
    git_diff_added_lines: int = Field(0, description="Lines added from git diff")
    git_diff_removed_lines: int = Field(0, description="Lines removed from git diff")
    git_diff_files_changed: int = Field(0, description="Number of files modified")
    git_diff_stats: Dict[str, Any] = Field(default_factory=dict, description="Detailed diff stats")
    
    # Execution status
    status: str = Field("pending", description="Workflow status")
    result: Optional[str] = Field(None, description="Final workflow output")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    
    # Workspace management
    workspace_id: Optional[str] = Field(None, description="Claude SDK workspace identifier")
    workspace_persistent: bool = Field(True, description="Keep workspace after completion")
    workspace_auto_merge: bool = Field(False, description="Automatically merge to main branch")
    workspace_cleaned_up: bool = Field(False, description="Workspace cleanup status")
    workspace_path: Optional[str] = Field(None, description="Local filesystem workspace directory")
    temp_workspace: bool = Field(False, description="Whether using temporary isolated workspace")
    
    # Cost and token tracking
    cost_estimate: Optional[float] = Field(None, description="Estimated API cost in USD")
    input_tokens: int = Field(0, description="Tokens sent to LLM")
    output_tokens: int = Field(0, description="Tokens generated by LLM")
    total_tokens: int = Field(0, description="Total tokens used")
    
    # User context
    user_id: Optional[uuid.UUID] = Field(None, description="User who initiated workflow")
    
    # Extensible data
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional workflow data")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate workflow status."""
        allowed_statuses = {'pending', 'running', 'completed', 'failed', 'killed'}
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {allowed_statuses}")
        return v

    @field_validator('input_tokens', 'output_tokens', 'total_tokens')
    @classmethod
    def validate_tokens(cls, v):
        """Validate token counts are non-negative."""
        if v < 0:
            raise ValueError("Token counts must be non-negative")
        return v


class WorkflowRunCreate(WorkflowRunBase):
    """Data needed to create a new Workflow Run."""
    completed_at: Optional[datetime] = Field(None, description="When workflow finished")
    duration_seconds: Optional[int] = Field(None, description="Execution duration in seconds")


class WorkflowRunUpdate(BaseModel):
    """Data for updating an existing Workflow Run."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
    )
    
    # Status and results
    status: Optional[str] = Field(None, description="Updated workflow status")
    result: Optional[str] = Field(None, description="Updated workflow result")
    error_message: Optional[str] = Field(None, description="Updated error message")
    
    # Session tracking
    session_id: Optional[uuid.UUID] = Field(None, description="Real Claude session ID")
    
    # Git tracking
    final_commit_hash: Optional[str] = Field(None, description="Final commit hash")
    git_diff_added_lines: Optional[int] = Field(None, description="Updated lines added")
    git_diff_removed_lines: Optional[int] = Field(None, description="Updated lines removed")
    git_diff_files_changed: Optional[int] = Field(None, description="Updated files changed")
    git_diff_stats: Optional[Dict[str, Any]] = Field(None, description="Updated diff stats")
    
    # Workspace management
    workspace_path: Optional[str] = Field(None, description="Updated workspace path")
    workspace_cleaned_up: Optional[bool] = Field(None, description="Updated cleanup status")
    
    # Token and cost tracking
    cost_estimate: Optional[float] = Field(None, description="Updated cost estimate")
    input_tokens: Optional[int] = Field(None, description="Updated input tokens")
    output_tokens: Optional[int] = Field(None, description="Updated output tokens")
    total_tokens: Optional[int] = Field(None, description="Updated total tokens")
    
    # Timing tracking
    duration_seconds: Optional[int] = Field(None, description="Execution duration in seconds")
    completed_at: Optional[datetime] = Field(None, description="When workflow finished")
    updated_at: Optional[datetime] = Field(None, description="When record was updated")
    
    # Extensible data
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


class WorkflowRun(WorkflowRunBase):
    """Complete Workflow Run model, including database fields."""
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Primary key")
    created_at: datetime = Field(..., description="When workflow was created")
    completed_at: Optional[datetime] = Field(None, description="When workflow finished")
    duration_seconds: Optional[int] = Field(None, description="Execution duration")
    updated_at: Optional[datetime] = Field(None, description="When workflow was last updated")
    
    DB_TABLE: ClassVar[str] = "workflow_runs"
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "WorkflowRun":
        """Create a WorkflowRun instance from a database row."""
        if not row:
            return None
        
        # Handle JSON fields - deserialize if they're strings
        json_fields = ["git_diff_stats", "metadata"]
        for field in json_fields:
            if field in row and isinstance(row[field], str):
                try:
                    row[field] = json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    row[field] = {} if field in ["git_diff_stats", "metadata"] else None
        
        return cls(**row)
    
    def calculate_duration(self) -> Optional[int]:
        """Calculate duration in seconds if completed."""
        if self.completed_at and self.created_at:
            delta = self.completed_at - self.created_at
            return int(delta.total_seconds())
        return None
    
    def is_completed(self) -> bool:
        """Check if workflow is in a completed state."""
        return self.status in {'completed', 'failed', 'killed'}
    
    def is_successful(self) -> bool:
        """Check if workflow completed successfully."""
        return self.status == 'completed'
    
    def get_git_diff_summary(self) -> str:
        """Get a human-readable git diff summary."""
        if not any([self.git_diff_added_lines, self.git_diff_removed_lines, self.git_diff_files_changed]):
            return "No changes"
        
        parts = []
        if self.git_diff_files_changed:
            parts.append(f"{self.git_diff_files_changed} files")
        if self.git_diff_added_lines:
            parts.append(f"+{self.git_diff_added_lines}")
        if self.git_diff_removed_lines:
            parts.append(f"-{self.git_diff_removed_lines}")
        
        return " ".join(parts)
    
    def get_cost_summary(self) -> str:
        """Get a human-readable cost summary."""
        if self.cost_estimate is None:
            return "Cost unknown"
        
        cost_str = f"${self.cost_estimate:.4f}"
        if self.total_tokens:
            cost_str += f" ({self.total_tokens:,} tokens)"
        
        return cost_str


# Workflow Models (Simple single-table design like Agents)
class WorkflowBase(BaseDBModel):
    """Base class for Workflow models."""
    
    name: str = Field(..., description="Unique workflow name")
    display_name: Optional[str] = Field(None, description="Human-readable display name")
    description: Optional[str] = Field(None, description="Workflow description")
    category: str = Field(default="custom", description="Workflow category")
    prompt_template: str = Field(..., description="Main workflow prompt template")
    allowed_tools: List[str] = Field(default_factory=list, description="List of allowed tool names")
    mcp_config: Dict[str, Any] = Field(default_factory=dict, description="MCP server configuration")
    active: bool = Field(default=True, description="Whether workflow is active")
    is_system_workflow: bool = Field(default=False, description="Whether this is a system workflow")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")


class WorkflowCreate(WorkflowBase):
    """Data needed to create a new Workflow."""
    pass


class WorkflowUpdate(BaseModel):
    """Data for updating an existing Workflow."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
    )
    
    display_name: Optional[str] = Field(None, description="Updated display name")
    description: Optional[str] = Field(None, description="Updated description")
    category: Optional[str] = Field(None, description="Updated category")
    prompt_template: Optional[str] = Field(None, description="Updated prompt template")
    allowed_tools: Optional[List[str]] = Field(None, description="Updated allowed tools")
    mcp_config: Optional[Dict[str, Any]] = Field(None, description="Updated MCP configuration")
    active: Optional[bool] = Field(None, description="Updated active status")
    config: Optional[Dict[str, Any]] = Field(None, description="Updated configuration")


class Workflow(WorkflowBase):
    """Complete Workflow model, including database fields."""
    
    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Timestamp when workflow was created")
    updated_at: datetime = Field(..., description="Timestamp when workflow was last updated")
    
    DB_TABLE: ClassVar[str] = "workflows"
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "Workflow":
        """Create a Workflow instance from a database row."""
        if not row:
            return None
        
        # Handle JSON fields - deserialize if they're strings
        json_fields = ["allowed_tools", "mcp_config", "config"]
        for field in json_fields:
            if field in row and isinstance(row[field], str):
                try:
                    row[field] = json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    if field == "allowed_tools":
                        row[field] = []
                    else:
                        row[field] = {}
        
        # Handle datetime fields - parse if they're strings
        datetime_fields = ["created_at", "updated_at"]
        for field in datetime_fields:
            if field in row and isinstance(row[field], str):
                # Special handling for database default placeholders
                if row[field] in ['CURRENT_TEXT', 'CURRENT_TIMESTAMP', 'CURRENT_TIME']:
                    row[field] = datetime.utcnow()
                    continue
                    
                try:
                    # Handle ISO format datetime strings
                    if 'T' in row[field]:
                        row[field] = datetime.fromisoformat(row[field].replace('Z', '+00:00'))
                    else:
                        # Handle database datetime format
                        row[field] = datetime.strptime(row[field], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError) as e:
                    # If parsing fails, use current time as fallback
                    logger.warning(f"Failed to parse {field}: {row[field]}, using current time")
                    row[field] = datetime.utcnow()
        
        return cls(**row)
    
    # No category validation - allow any category string
