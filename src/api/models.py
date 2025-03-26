from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

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

# Update AgentRunRequest to support multimodal content
class AgentRunRequest(BaseResponseModel):
    """Request model for running an agent."""
    message_content: str
    message_type: Optional[str] = None
    # Legacy single media fields (maintained for backward compatibility)
    mediaUrl: Optional[str] = None
    mime_type: Optional[str] = None
    # New multimodal content support
    media_contents: Optional[List[Union[
        ImageUrlContent, ImageBinaryContent,
        AudioUrlContent, AudioBinaryContent,
        DocumentUrlContent, DocumentBinaryContent
    ]]] = None
    channel_payload: Optional[Dict[str, Any]] = None
    context: dict = {}
    session_id: Optional[str] = None
    session_name: Optional[str] = None  # Optional friendly name for the session
    user_id: Optional[int] = 1  # User ID is now an integer with default value 1
    message_limit: Optional[int] = 10  # Default to last 10 messages
    session_origin: Optional[Literal["web", "whatsapp", "automagik-agent", "telegram", "discord", "slack", "cli"]] = "automagik-agent"  # Origin of the session
    agent_id: Optional[Any] = None  # Agent ID to store with messages, can be int or string
    parameters: Optional[Dict[str, Any]] = None  # Agent parameters
    messages: Optional[List[Any]] = None  # Optional message history

class AgentInfo(BaseResponseModel):
    """Information about an available agent."""
    name: str
    description: Optional[str] = None

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
    # Legacy media fields (maintained for backward compatibility)
    media_url: Optional[str] = None
    mime_type: Optional[str] = None
    # New multimodal content support
    media_contents: Optional[List[Union[
        ImageUrlContent, ImageBinaryContent, 
        AudioUrlContent, AudioBinaryContent,
        DocumentUrlContent, DocumentBinaryContent
    ]]] = None
    tool_calls: Optional[List[ToolCallModel]] = None
    tool_outputs: Optional[List[ToolOutputModel]] = None

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

class SessionInfo(BaseResponseModel):
    """Information about a session."""
    session_id: str
    user_id: Optional[int] = None
    agent_id: Optional[int] = None
    session_name: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    message_count: Optional[int] = None
    agent_name: Optional[str] = None
    session_origin: Optional[str] = None  # Origin of the session (e.g., "web", "api", "discord")

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
        super().__init__(**data)
        # Set total_count to total if only total is provided
        if self.total_count is None and hasattr(self, 'total'):
            self.total_count = self.total

class UserCreate(BaseResponseModel):
    """Request model for creating a new user."""
    email: Optional[str] = None
    phone_number: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None

class UserUpdate(BaseResponseModel):
    """Request model for updating an existing user."""
    email: Optional[str] = None
    phone_number: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None

class UserInfo(BaseResponseModel):
    """Response model for user information."""
    id: int
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