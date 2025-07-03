from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, ConfigDict, Field
import uuid

class BaseResponseModel(BaseModel):
    """Base model for all response models with common configuration."""
    model_config = ConfigDict(
        exclude_none=True,  # Exclude None values from response
        validate_assignment=True,  # Validate values on assignment
        extra='ignore'  # Ignore extra fields
    )

# Multimodal content models
class MediaContent(BaseResponseModel):
    """Base model for media content."""
    mime_type: str
    
class UrlMediaContent(MediaContent):
    """Media content accessible via URL."""
    media_url: str

class BinaryMediaContent(MediaContent):
    """Media content with binary data."""
    data: str  # Base64 encoded binary data
    
class ImageContent(MediaContent):
    """Image content with metadata."""
    mime_type: str = Field(pattern=r'^image/')
    width: Optional[int] = None
    height: Optional[int] = None
    alt_text: Optional[str] = None
    
class ImageUrlContent(ImageContent, UrlMediaContent):
    """Image content accessible via URL."""
    pass
    
class ImageBinaryContent(ImageContent, BinaryMediaContent):
    """Image content with binary data."""
    thumbnail_url: Optional[str] = None
    
class AudioContent(MediaContent):
    """Audio content with metadata."""
    mime_type: str = Field(pattern=r'^audio/')
    duration_seconds: Optional[float] = None
    transcript: Optional[str] = None
    
class AudioUrlContent(AudioContent, UrlMediaContent):
    """Audio content accessible via URL."""
    pass
    
class AudioBinaryContent(AudioContent, BinaryMediaContent):
    """Audio content with binary data."""
    pass
    
class DocumentContent(MediaContent):
    """Document content with metadata."""
    mime_type: str = Field(pattern=r'^(application|text)/')
    name: Optional[str] = None
    size_bytes: Optional[int] = None
    page_count: Optional[int] = None
    
class DocumentUrlContent(DocumentContent, UrlMediaContent):
    """Document content accessible via URL."""
    pass
    
class DocumentBinaryContent(DocumentContent, BinaryMediaContent):
    """Document content with binary data."""
    pass

# Define UserCreate before it's referenced by AgentRunRequest
class UserCreate(BaseResponseModel):
    """Request model for creating a new user."""
    email: Optional[str] = None
    phone_number: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None

# Update AgentRunRequest to support multimodal content
class AgentRunRequest(BaseResponseModel):
    """Request model for running an agent."""
    message_content: str
    message_type: Optional[str] = None
    # Multimodal content support
    media_contents: Optional[List[Union[
        ImageUrlContent, ImageBinaryContent,
        AudioUrlContent, AudioBinaryContent,
        DocumentUrlContent, DocumentBinaryContent
    ]]] = None
    channel_payload: Optional[Dict[str, Any]] = None
    context: dict = {}
    session_id: Optional[str] = None
    session_name: Optional[str] = None  # Optional friendly name for the session
    user_id: Optional[Union[uuid.UUID, str, int]] = None  # User ID as UUID, string, or int
    message_limit: Optional[int] = 10  # Default to last 10 messages
    session_origin: Optional[Literal["web", "whatsapp", "automagik-agent", "telegram", "discord", "slack", "cli", "app", "manychat", "automagik-spark"]] = "automagik-agent"  # Origin of the session
    agent_id: Optional[Any] = None  # Agent ID to store with messages, can be int or string
    parameters: Optional[Dict[str, Any]] = None  # Agent parameters
    messages: Optional[List[Any]] = None  # Optional message history
    system_prompt: Optional[str] = None  # Optional system prompt override
    user: Optional[UserCreate] = None  # Optional user data for creation/update
    
    # Agent Execution Parameters
    run_count: int = 1  # Number of agent iterations to run (default 1 for cost control)
    enable_rollback: bool = True  # Git rollback capability
    enable_realtime: bool = False  # Real-time streaming updates
    
    # Claude CLI specific parameters
    max_turns: Optional[int] = None  # Max turns for claude CLI (unlimited if not specified)
    resume_session: Optional[str] = None  # Resume a specific claude session ID
    force_new_session: bool = False  # Force new session even if one exists
    allowed_tools_file: Optional[str] = None  # Path to allowed_tools.json
    mcp_config_path: Optional[str] = None  # Path to .mcp.json
    system_prompt_file: Optional[str] = None  # Path to system prompt file
    whatsapp_notifications: bool = False  # Enable WhatsApp notifications
    slack_thread_ts: Optional[str] = None  # Slack thread timestamp for group chat
    
    # Enhanced orchestration parameters
    epic_id: Optional[str] = None  # Linear epic ID
    linear_project_id: Optional[str] = None  # Linear project ID
    slack_channel_id: Optional[str] = None  # Slack channel ID
    human_phone_number: Optional[str] = None  # Phone for WhatsApp alerts
    
    model_config = ConfigDict(
        exclude_none=True,
        json_schema_extra={
            "examples": [
                # Simple example - most common usage
                {
                    "message_content": "Buenas",
                    "message_limit": 10,
                    "message_type": "text",
                    "session_name": "teste",
                    "session_origin": "automagik-agent"
                },
                # Example with image
                {
                    "message_content": "What's in this image?",
                    "message_type": "image",
                    "media_contents": [
                        {
                            "mime_type": "image/jpeg",
                            "media_url": "https://example.com/image.jpg",
                            "width": 800,
                            "height": 600,
                            "alt_text": "Sample image"
                        }
                    ],
                    "session_name": "image_analysis",
                    "session_origin": "web"
                },
                # WhatsApp example
                {
                    "message_content": "Help me with my order",
                    "session_name": "customer_support",
                    "session_origin": "whatsapp",
                    "user": {
                        "phone_number": "+1234567890"
                    },
                    "channel_payload": {
                        "chat_id": "5511999999999@c.us"
                    }
                }
            ]
        }
    )

    
class AgentInfo(BaseResponseModel):
    """Information about an available agent."""
    id: int
    name: str
    description: Optional[str] = None

class AgentCreateRequest(BaseResponseModel):
    """Request model for creating a new agent."""
    name: str = Field(..., description="Agent name")
    type: str = Field(default="pydanticai", description="Agent type")
    model: str = Field(default="openai:gpt-4o-mini", description="Default model")
    description: Optional[str] = Field(None, description="Agent description")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Agent configuration")

class AgentUpdateRequest(BaseResponseModel):
    """Request model for updating an existing agent."""
    type: Optional[str] = Field(None, description="Agent type")
    model: Optional[str] = Field(None, description="Default model")
    description: Optional[str] = Field(None, description="Agent description")
    config: Optional[Dict[str, Any]] = Field(None, description="Agent configuration")
    active: Optional[bool] = Field(None, description="Whether agent is active")

class AgentCreateResponse(BaseResponseModel):
    """Response model for agent creation."""
    status: str = "success"
    message: str
    agent_id: int
    agent_name: str

class AgentUpdateResponse(BaseResponseModel):
    """Response model for agent update."""
    status: str = "success"
    message: str
    agent_name: str

class AgentDeleteResponse(BaseResponseModel):
    """Response model for agent deletion."""
    status: str = "success"
    message: str
    agent_name: str

class AgentCopyRequest(BaseResponseModel):
    """Request model for copying an existing agent."""
    new_name: str = Field(..., description="Name for the copied agent")
    description: Optional[str] = Field(None, description="New description for the copied agent")
    system_prompt: Optional[str] = Field(None, description="New system prompt for the copied agent")
    model: Optional[str] = Field(None, description="New model for the copied agent")
    tool_config: Optional[Dict[str, Any]] = Field(None, description="New tool configuration")

class AgentCopyResponse(BaseResponseModel):
    """Response model for agent copying."""
    status: str = "success"
    message: str
    source_agent: str
    new_agent: str
    agent_id: int

class ToolInfo(BaseResponseModel):
    """Information about an available tool."""
    name: str = Field(..., description="Tool name")
    type: str = Field(..., description="Tool type: 'mcp' or 'code'")
    description: str = Field(..., description="Tool description")
    server_name: Optional[str] = Field(None, description="MCP server name (for MCP tools)")
    module: Optional[str] = Field(None, description="Module path (for code tools)")
    context_signature: str = Field(default="RunContext[Dict]", description="Context signature")
    parameters: List[Dict[str, Any]] = Field(default_factory=list, description="Tool parameters")

class ToolExecuteRequest(BaseResponseModel):
    """Request model for executing a tool."""
    context: Dict[str, Any] = Field(default_factory=dict, description="Tool execution context")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")

class ToolExecuteResponse(BaseResponseModel):
    """Response model for tool execution."""
    status: str = "success"
    result: Any = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if failed")

class AgentRunResponse(BaseResponseModel):
    """Response model for agent execution."""
    status: str = "success"
    message: str
    session_id: Optional[str] = None
    agent_name: str
    execution_time: Optional[float] = None
    # Additional response data
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

class HealthResponse(BaseResponseModel):
    """Response model for health check endpoint."""
    status: str
    timestamp: datetime
    version: str
    environment: str = "development"  # Default to development if not specified

class DeleteSessionResponse(BaseResponseModel):
    """Response model for session deletion."""
    status: str
    session_id: str
    message: str

class ToolCallModel(BaseResponseModel):
    """Model for a tool call."""
    tool_name: str
    args: Dict
    tool_call_id: str

class ToolOutputModel(BaseResponseModel):
    """Model for a tool output."""
    tool_name: str
    tool_call_id: str
    content: Any

class MessageModel(BaseResponseModel):
    """Model for a single message in the conversation."""
    role: str
    content: str
    assistant_name: Optional[str] = None
    # Multimodal content support
    media_contents: Optional[List[Union[
        ImageUrlContent, ImageBinaryContent, 
        AudioUrlContent, AudioBinaryContent,
        DocumentUrlContent, DocumentBinaryContent
    ]]] = None
    tool_calls: Optional[List[ToolCallModel]] = None
    tool_outputs: Optional[List[ToolOutputModel]] = None
    system_prompt: Optional[str] = None

    model_config = ConfigDict(
        exclude_none=True,
        json_schema_extra={"examples": [{"role": "assistant", "content": "Hello!"}]}
    )

class PaginationParams(BaseResponseModel):
    """Pagination parameters."""
    page: int = 1
    page_size: int = 50
    sort_desc: bool = True  # True for most recent first

class SessionResponse(BaseResponseModel):
    """Response model for session retrieval."""
    session_id: str
    messages: List[MessageModel]
    exists: bool
    total_messages: int
    current_page: int
    total_pages: int
    system_prompt: Optional[str] = None

class SessionInfo(BaseResponseModel):
    """Information about a session."""
    session_id: str
    user_id: Optional[uuid.UUID] = None
    agent_id: Optional[int] = None
    session_name: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    message_count: Optional[int] = None
    agent_name: Optional[str] = None
    session_origin: Optional[str] = None  # Origin of the session (e.g., "web", "api", "discord")
    system_prompt: Optional[str] = None

class SessionListResponse(BaseResponseModel):
    """Response model for listing all sessions."""
    sessions: List[SessionInfo]
    total: int
    total_count: int = None  # Added for backward compatibility
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    
    # Make sure both total and total_count have the same value for backward compatibility
    def __init__(self, **data):
        if 'total' in data and 'total_count' not in data:
            data['total_count'] = data['total']
        super().__init__(**data)

# UserCreate moved to before AgentRunRequest

class UserUpdate(BaseResponseModel):
    """Request model for updating an existing user."""
    email: Optional[str] = None
    phone_number: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None

class UserInfo(BaseResponseModel):
    """Response model for user information."""
    id: uuid.UUID
    email: Optional[str] = None
    phone_number: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserListResponse(BaseResponseModel):
    """Response model for listing users."""
    users: List[UserInfo]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    has_next: Optional[bool] = None
    has_prev: Optional[bool] = None

class DeleteMessageResponse(BaseResponseModel):
    """Response model for message deletion."""
    status: str = "success"
    message_id: uuid.UUID
    detail: str = "Message deleted successfully"

class CreateMessageRequest(BaseResponseModel):
    """Request model for creating a new message."""
    session_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    agent_id: Optional[int] = None
    role: str = Field(..., description="Message role (user, assistant, system)")
    text_content: Optional[str] = None
    media_url: Optional[str] = None
    mime_type: Optional[str] = None
    message_type: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None
    channel_payload: Optional[Dict[str, Any]] = None
    tool_calls: Optional[Dict[str, Any]] = None
    tool_outputs: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    user_feedback: Optional[str] = None
    flagged: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None

class CreateMessageResponse(BaseResponseModel):
    """Response model for message creation."""
    status: str = "success"
    message_id: uuid.UUID
    detail: str = "Message created successfully"

class UpdateMessageRequest(BaseResponseModel):
    """Request model for updating a message."""
    session_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    agent_id: Optional[int] = None
    role: Optional[str] = None
    text_content: Optional[str] = None
    media_url: Optional[str] = None
    mime_type: Optional[str] = None
    message_type: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None
    channel_payload: Optional[Dict[str, Any]] = None
    tool_calls: Optional[Dict[str, Any]] = None
    tool_outputs: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    user_feedback: Optional[str] = None
    flagged: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
    # Branching options
    create_branch: bool = Field(False, description="Whether to create a new conversation branch instead of updating in-place")
    branch_name: Optional[str] = Field(None, description="Optional name for the new branch session (only used when create_branch=True)")
    run_agent: bool = Field(True, description="Whether to re-run the agent from the branch point (only used when create_branch=True)")

class UpdateMessageResponse(BaseResponseModel):
    """Response model for message update."""
    status: str = "success"
    message_id: uuid.UUID
    detail: str = "Message updated successfully"
    # Branching response fields (only present when create_branch=True)
    branch_session_id: Optional[uuid.UUID] = Field(None, description="ID of the new branch session (only when create_branch=True)")
    original_session_id: Optional[uuid.UUID] = Field(None, description="ID of the original session (only when create_branch=True)")
    branch_point_message_id: Optional[uuid.UUID] = Field(None, description="ID of the branch point message (only when create_branch=True)")

class MessageResponse(BaseResponseModel):
    """Response model for a single message."""
    id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    agent_id: Optional[int] = None
    role: str
    text_content: Optional[str] = None
    media_url: Optional[str] = None
    mime_type: Optional[str] = None
    message_type: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None
    channel_payload: Optional[Dict[str, Any]] = None
    tool_calls: Optional[Dict[str, Any]] = None
    tool_outputs: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    user_feedback: Optional[str] = None
    flagged: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class MessageListResponse(BaseResponseModel):
    """Response model for listing messages."""
    messages: List[MessageResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    has_next: Optional[bool] = None
    has_prev: Optional[bool] = None

# Message branching API models
class CreateBranchRequest(BaseResponseModel):
    """Request model for creating a conversation branch from a message."""
    edited_message_content: str = Field(..., description="New content for the message at branch point")
    branch_name: Optional[str] = Field(None, description="Optional name for the new branch session")
    run_agent: bool = Field(True, description="Whether to re-run the agent from the branch point")

class CreateBranchResponse(BaseResponseModel):
    """Response model for branch creation."""
    status: str = "success"
    branch_session_id: uuid.UUID
    original_session_id: uuid.UUID
    branch_point_message_id: uuid.UUID
    detail: str = "Branch created successfully"

class BranchInfo(BaseResponseModel):
    """Information about a conversation branch."""
    session_id: uuid.UUID
    session_name: Optional[str] = None
    branch_type: Optional[Literal["edit_branch", "manual_branch"]] = None
    branch_point_message_id: Optional[uuid.UUID] = None
    is_main_branch: bool = True
    created_at: Optional[datetime] = None
    message_count: Optional[int] = None

class SessionBranchesResponse(BaseResponseModel):
    """Response model for listing session branches."""
    main_session: BranchInfo
    branches: List[BranchInfo]
    total_branches: int

class BranchTreeNode(BaseResponseModel):
    """Node in a branch tree structure."""
    session_id: uuid.UUID
    session_name: Optional[str] = None
    branch_type: Optional[Literal["edit_branch", "manual_branch"]] = None
    branch_point_message_id: Optional[uuid.UUID] = None
    is_main_branch: bool = True
    created_at: Optional[datetime] = None
    message_count: Optional[int] = None
    children: List["BranchTreeNode"] = Field(default_factory=list)

class SessionBranchTreeResponse(BaseResponseModel):
    """Response model for session branch tree."""
    root: BranchTreeNode
    total_sessions: int

# Make BranchTreeNode work with forward references
BranchTreeNode.model_rebuild()

# Prompt API models
class PromptResponse(BaseResponseModel):
    """Response model for a single prompt."""
    id: int
    agent_id: int
    prompt_text: str
    version: int
    is_active: bool
    is_default_from_code: bool
    status_key: str
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class PromptListResponse(BaseResponseModel):
    """Response model for listing prompts."""
    prompts: List[PromptResponse]
    total: int
    agent_id: int

class PromptCreateRequest(BaseResponseModel):
    """Request model for creating a new prompt."""
    prompt_text: str
    status_key: str = "default"
    name: Optional[str] = None
    is_active: bool = False
    version: int = 1

class PromptUpdateRequest(BaseResponseModel):
    """Request model for updating an existing prompt."""
    prompt_text: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None 